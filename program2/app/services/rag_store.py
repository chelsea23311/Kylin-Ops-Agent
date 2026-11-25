"""
RAG Store —— 后端运维经验记忆库
================================

管理三类记忆，对应 `MemoryRetrieveResponse` 的三个字段：

  ┌─────────────┬────────────────────────────────────────────┬──────────────┬──────────┐
  │ 记忆类型     │ 来源                                          │ Time Decay   │ Tags 过滤 │
  ├─────────────┼────────────────────────────────────────────┼──────────────┼──────────┤
  │ raw_logs    │ Step 12 写回（每次任务执行的原始日志）        │ ✅ 按 timestamp │ ✅       │
  │ reflections │ Step 12 写回（与 raw_log 同组，共享 timestamp）│ ✅ 借用 raw   │ ✅       │
  │ kylin_manuals│ kylin_rag.py 提供（FAQ PDF 静态知识）         │ ❌            │ ❌       │
  └─────────────┴────────────────────────────────────────────┴──────────────┴──────────┘

检索流程（用户提问后）：
    向量召回 → tags 过滤（raw_logs / reflections） → time decay 加权 → Cross-Encoder 重排 → top_k

写入流程（Step 12 记忆写回）：
    raw_log + reflection_result 作为一组同时写入两个 FAISS 索引，
    共享 request_id / timestamp / tags，使 reflection 能借用 raw_log 的 timestamp 做 time decay。

模型与依赖：
    Embedding : paraphrase-multilingual-MiniLM-L12-v2  （沿用 kylin_rag.py）
    Reranker  : cross-encoder/ms-marco-MiniLM-L-6-v2   （沿用 kylin_rag.py）
    向量库    : FAISS IndexFlatIP + L2 归一化（等效余弦相似度）
    持久化    : data/rag_store/{raw_log,reflection}.{index,_meta.pkl}
"""
from __future__ import annotations

import os

# 强制离线：禁止 sentence-transformers / transformers 联网检查模型更新
# 必须在 import sentence_transformers / torch 之前设置
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("HF_DATASETS_OFFLINE", "1")

import math
import pickle
import sys
import threading
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, List, Optional

# ─────────────────────────────────────────────
# 路径与常量
# ─────────────────────────────────────────────
# 使用文件位置定位仓库根目录，不依赖进程工作目录。
BASE_DIR = str(Path(__file__).resolve().parents[3])
DATA_DIR = os.path.join(BASE_DIR, "data", "rag_store")

RAW_LOG_INDEX_PATH    = os.path.join(DATA_DIR, "raw_log.index")
RAW_LOG_META_PATH     = os.path.join(DATA_DIR, "raw_log_meta.pkl")
REFLECTION_INDEX_PATH = os.path.join(DATA_DIR, "reflection.index")
REFLECTION_META_PATH  = os.path.join(DATA_DIR, "reflection_meta.pkl")

# 模型路径（可由环境变量覆盖；默认走 kylin_rag.py 的同一份 models 目录）
MODEL_BASE = os.environ.get("RAG_MODEL_BASE", os.path.join(BASE_DIR, "models"))
EMBED_MODEL_PATH  = os.path.join(MODEL_BASE, "paraphrase-multilingual-MiniLM-L12-v2")
RERANK_MODEL_PATH = os.path.join(MODEL_BASE, "ms-marco-MiniLM-L-6-v2")

# Time decay 默认衰减系数 (按"天"计算)
#   λ=0.01 → 100 天后衰减到 ~0.37
#   λ=0.1  → 10  天后衰减到 ~0.37
DEFAULT_LAMBDA = 0.01

# ─────────────────────────────────────────────
# 重模型懒加载（避免 import RAGStore 时立刻拉起 sentence-transformers/faiss）
# ─────────────────────────────────────────────
_models_loaded = False
_embedder = None
_reranker = None
_faiss = None
_np = None
_lock = threading.Lock()          # RAGStore 单例锁
_model_lock = threading.Lock()    # 模型加载专用锁（与单例锁分离，避免死锁）


def _load_models():
    global _models_loaded, _embedder, _reranker, _faiss, _np
    if _models_loaded:
        return
    with _model_lock:
        if _models_loaded:
            return
        import faiss as _f
        import numpy as _n
        from sentence_transformers import SentenceTransformer, CrossEncoder
        _faiss = _f
        _np = _n
        _embedder = SentenceTransformer(EMBED_MODEL_PATH)
        _reranker = CrossEncoder(RERANK_MODEL_PATH)
        _models_loaded = True


# ─────────────────────────────────────────────
# kylin_manuals 检索：复用仓库根目录的 kylin_rag.py
# ─────────────────────────────────────────────
def _retrieve_kylin_manuals(task_text: str, top_k: int) -> List[dict]:
    """
    调用仓库根目录 kylin_rag.py 提供的 FAQ 检索；失败时返回空列表。
    返回格式严格对齐 MemoryRetrieveResponse.kylin_manuals：
      [{"type": "KylinManual", "title": ..., "section": ..., "summary": ...}, ...]
    """
    if top_k <= 0:
        return []
    try:
        if BASE_DIR not in sys.path:
            sys.path.insert(0, BASE_DIR)
        try:
            from kylin_rag import query_kylin_faq_as_memory  # 优先使用新格式接口
            return query_kylin_faq_as_memory(task_text, top_k=top_k)
        except ImportError:
            # 兼容老接口：自行做格式转换
            from kylin_rag import query_kylin_faq
            results = query_kylin_faq(task_text, top_k=top_k)
            return [
                {
                    "type": "KylinManual",
                    "title": "银河麒麟桌面操作系统 V11 常见问题(FAQ)",
                    "section": r.get("source", ""),
                    "summary": (r.get("text", "") or "").strip()[:400],
                }
                for r in results
            ]
    except Exception as e:
        print(f"[RAGStore] kylin_manuals 检索失败：{e}")
        return []


# ─────────────────────────────────────────────
# RAGStore 主体
# ─────────────────────────────────────────────
class RAGStore:
    """全进程单例，避免重复加载模型。"""

    _instance: Optional["RAGStore"] = None

    def __init__(self):
        _load_models()
        self.dim = _embedder.get_sentence_embedding_dimension()
        self.raw_log_index = _faiss.IndexFlatIP(self.dim)
        self.raw_log_meta: List[dict] = []
        self.reflection_index = _faiss.IndexFlatIP(self.dim)
        self.reflection_meta: List[dict] = []
        os.makedirs(DATA_DIR, exist_ok=True)
        self._load_persistent()

    @classmethod
    def instance(cls) -> "RAGStore":
        if cls._instance is None:
            with _lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ── 持久化 ─────────────────────────────────────────
    def _load_persistent(self):
        if os.path.exists(RAW_LOG_INDEX_PATH) and os.path.exists(RAW_LOG_META_PATH):
            self.raw_log_index = _faiss.read_index(RAW_LOG_INDEX_PATH)
            with open(RAW_LOG_META_PATH, "rb") as f:
                self.raw_log_meta = pickle.load(f)
        if os.path.exists(REFLECTION_INDEX_PATH) and os.path.exists(REFLECTION_META_PATH):
            self.reflection_index = _faiss.read_index(REFLECTION_INDEX_PATH)
            with open(REFLECTION_META_PATH, "rb") as f:
                self.reflection_meta = pickle.load(f)

    def _save_persistent(self):
        _faiss.write_index(self.raw_log_index, RAW_LOG_INDEX_PATH)
        with open(RAW_LOG_META_PATH, "wb") as f:
            pickle.dump(self.raw_log_meta, f)
        _faiss.write_index(self.reflection_index, REFLECTION_INDEX_PATH)
        with open(REFLECTION_META_PATH, "wb") as f:
            pickle.dump(self.reflection_meta, f)

    # ── 工具方法 ───────────────────────────────────────
    def _embed(self, text: str):
        v = _embedder.encode([text])
        v = _np.array(v, dtype="float32")
        _faiss.normalize_L2(v)
        return v

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _parse_iso(ts: str) -> datetime:
        try:
            if ts and ts.endswith("Z"):
                ts = ts[:-1] + "+00:00"
            return datetime.fromisoformat(ts)
        except Exception:
            return datetime.now(timezone.utc)

    # ── 写入：Step 12 记忆写回 ──────────────────────────
    def write(
        self,
        request_id: str,
        raw_log: dict,
        reflection_result: dict,
        tags: List[str],
    ) -> dict:
        """
        将一次任务的 raw_log + reflection_result 作为一组同时写入两个索引，
        共享 request_id / timestamp / tags。

        返回：写入后的统计信息。
        """
        timestamp = (raw_log or {}).get("timestamp") or self._now_iso()
        tags = tags or []
        wrote_raw = 0
        wrote_ref = 0

        # ── raw_log ───────────────────────────────────
        if raw_log:
            raw_record = dict(raw_log)
            raw_record["timestamp"] = timestamp
            raw_record["request_id"] = request_id
            raw_record["tags"] = tags
            raw_record.setdefault("type", "Raw_Log")
            raw_text = " ".join([
                str(raw_record.get("task", "")),
                str(raw_record.get("target", "")),
                str(raw_record.get("description", "")),
            ]).strip()
            if raw_text:
                v = self._embed(raw_text)
                self.raw_log_index.add(v)
                self.raw_log_meta.append(raw_record)
                wrote_raw = 1

        # ── reflection（借用同一 timestamp/tags，便于 time decay） ──
        if reflection_result:
            ref_record = dict(reflection_result)
            ref_record["timestamp"] = timestamp        # 借用 raw_log 时间
            ref_record["request_id"] = request_id
            ref_record["tags"] = tags
            ref_record.setdefault("stage", "reflection")
            ref_text_parts = [
                str(ref_record.get("revised_tool", "")),
                str(ref_record.get("revised_command", "")),
                str(ref_record.get("reflection_reason", "")),
            ]
            ev = ref_record.get("evidence")
            if isinstance(ev, list):
                ref_text_parts.append(" ".join(map(str, ev)))
            ref_text = " ".join(p for p in ref_text_parts if p).strip()
            if ref_text:
                v = self._embed(ref_text)
                self.reflection_index.add(v)
                self.reflection_meta.append(ref_record)
                wrote_ref = 1

        if wrote_raw or wrote_ref:
            self._save_persistent()

        return {
            "status": "success",
            "request_id": request_id,
            "timestamp": timestamp,
            "tags": tags,
            "wrote_raw_log": wrote_raw,
            "wrote_reflection": wrote_ref,
            "raw_log_total": self.raw_log_index.ntotal,
            "reflection_total": self.reflection_index.ntotal,
        }

    # ── 检索：Step 4 上下文构建 ─────────────────────────
    def _retrieve_one(
        self,
        index,
        meta_list: List[dict],
        query_vec,
        top_k: int,
        tag_filter: Optional[List[str]],
        lambda_decay: float,
        rerank_query: str,
    ) -> List[dict]:
        if index.ntotal == 0 or top_k <= 0:
            return []
        initial_k = min(max(top_k * 4, top_k), index.ntotal)
        sims, idxs = index.search(query_vec, initial_k)

        now = datetime.now(timezone.utc)
        candidates = []  # (doc, similarity, dt_days)
        for sim, idx in zip(sims[0], idxs[0]):
            if idx == -1 or idx >= len(meta_list):
                continue
            doc = meta_list[idx]
            # tags 过滤：传入 tag_filter 时要求至少有一个 tag 命中
            if tag_filter:
                doc_tags = doc.get("tags") or []
                if not any(t in doc_tags for t in tag_filter):
                    continue
            ts = self._parse_iso(doc.get("timestamp") or self._now_iso())
            dt_days = max((now - ts).total_seconds() / 86400.0, 0.0)
            candidates.append((doc, float(sim), dt_days))

        if not candidates:
            return []

        # Cross-Encoder 重排
        def _doc_to_passage(d: dict) -> str:
            # raw_log / reflection 的可读文本用于重排器评分
            return " ".join([
                str(d.get("task", "")),
                str(d.get("target", "")),
                str(d.get("description", "")),
                str(d.get("revised_tool", "")),
                str(d.get("revised_command", "")),
                str(d.get("reflection_reason", "")),
            ]).strip()

        pairs = [[rerank_query, _doc_to_passage(d)] for d, _, _ in candidates]
        rerank_scores = _reranker.predict(pairs)

        # 最终得分 = rerank_score × exp(-λ·Δt_days)
        finals = []
        for (doc, _sim, dt_days), rscore in zip(candidates, rerank_scores):
            decay = math.exp(-lambda_decay * dt_days)
            finals.append((doc, float(rscore) * decay))
        finals.sort(key=lambda x: x[1], reverse=True)
        return [d for d, _ in finals[:top_k]]

    def retrieve(
        self,
        task_text: str,
        top_k_raw_log: int = 3,
        top_k_reflection: int = 1,
        top_k_manual: int = 2,
        tag_filter: Optional[List[str]] = None,
        lambda_decay: float = DEFAULT_LAMBDA,
    ) -> dict:
        """
        返回结构严格对齐 MemoryRetrieveResponse：
          {
            "raw_logs":      [...],   # 已做 time decay + tag 过滤 + rerank
            "reflections":   [...],   # 同上
            "kylin_manuals": [...],   # 不做 time decay / tag 过滤
          }
        """
        qv = self._embed(task_text)
        raw_logs = self._retrieve_one(
            self.raw_log_index, self.raw_log_meta, qv,
            top_k_raw_log, tag_filter, lambda_decay, task_text,
        )
        reflections = self._retrieve_one(
            self.reflection_index, self.reflection_meta, qv,
            top_k_reflection, tag_filter, lambda_decay, task_text,
        )
        manuals = _retrieve_kylin_manuals(task_text, top_k_manual)
        return {
            "raw_logs": raw_logs,
            "reflections": reflections,
            "kylin_manuals": manuals,
        }


# ─────────────────────────────────────────────
# 便捷函数（供 MLService 直接 import）
# ─────────────────────────────────────────────
def retrieve_memory(
    task_text: str,
    top_k_raw_log: int = 3,
    top_k_reflection: int = 1,
    top_k_manual: int = 2,
    tag_filter: Optional[List[str]] = None,
) -> dict:
    return RAGStore.instance().retrieve(
        task_text=task_text,
        top_k_raw_log=top_k_raw_log,
        top_k_reflection=top_k_reflection,
        top_k_manual=top_k_manual,
        tag_filter=tag_filter,
    )


def write_memory(
    request_id: str,
    raw_log: dict,
    reflection_result: dict,
    tags: List[str],
) -> dict:
    return RAGStore.instance().write(
        request_id=request_id,
        raw_log=raw_log,
        reflection_result=reflection_result,
        tags=tags,
    )
