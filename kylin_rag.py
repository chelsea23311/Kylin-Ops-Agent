"""
麒麟官方 FAQ PDF → FAISS RAG 检索器
=====================================
方法说明：
  1. PDF 解析    : PyMuPDF (fitz)  —— 中文排版支持好，保留段落结构
  2. 分块策略    : FAQ 感知分块（Q&A 对）→ 滑动窗口兜底
  3. Embedding   : paraphrase-multilingual-MiniLM-L12-v2  —— 支持中文的多语言模型
  4. 向量库      : FAISS IndexFlatIP + L2 归一化（等效余弦相似度）
  5. 重排        : cross-encoder/ms-marco-MiniLM-L-6-v2
  6. 持久化      : faiss.write_index + pickle（避免每次重建索引）

安装依赖：
  pip install pymupdf sentence-transformers faiss-cpu numpy
"""

import os
import re
import time
import pickle
import numpy as np
import faiss

# 强制离线：禁止 sentence-transformers / transformers 联网下载模型
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"

from sentence_transformers import SentenceTransformer, CrossEncoder

# ─────────────────────────────────────────────
# 常量配置（服务器 Linux 路径）
# ─────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))

PDF_PATH    = os.path.join(BASE_DIR, "银河麒麟桌面操作系统V11 2603常见问题(FAQ) .pdf")
INDEX_PATH  = os.path.join(BASE_DIR, "kylin_faq.index")     # FAISS 索引持久化路径
META_PATH   = os.path.join(BASE_DIR, "kylin_faq_meta.pkl")  # 元数据持久化路径

MODEL_BASE = os.environ.get("RAG_MODEL_BASE", os.path.join(BASE_DIR, "models"))
EMBED_MODEL  = os.path.join(MODEL_BASE, "paraphrase-multilingual-MiniLM-L12-v2")
RERANK_MODEL = os.path.join(MODEL_BASE, "ms-marco-MiniLM-L-6-v2")

CHUNK_SIZE    = 300    # 滑动窗口分块大小（字符数）
CHUNK_OVERLAP = 50     # 滑动窗口重叠大小（字符数）


# ─────────────────────────────────────────────
# 1. PDF 解析与分块
# ─────────────────────────────────────────────
def extract_text_from_pdf(pdf_path: str) -> list:
    """
    用 PyMuPDF blocks 模式提取 PDF。
    返回段落列表（每个元素是一个视觉段落/标题块的文本）。
    blocks 模式会把跨行标题合并为一个块，避免逐行切割问题标题的问题。
    """
    import fitz  # PyMuPDF
    doc = fitz.open(pdf_path)
    paragraphs = []
    for page in doc:
        # blocks 返回：(x0, y0, x1, y1, text, block_no, block_type)
        # block_type=0 是文字块
        blocks = page.get_text("blocks")
        for b in sorted(blocks, key=lambda x: (x[1], x[0])):  # 按 y 再按 x 排序
            if b[6] != 0:  # 跳过图片块
                continue
            text = b[4].strip()
            if text:
                paragraphs.append(text)
    doc.close()
    return paragraphs


def split_faq_chunks(paragraphs: list) -> list:
    """
    FAQ 感知分块（适配银河麒麟 FAQ 实际排版）。
    输入是 extract_text_from_pdf 返回的段落列表（blocks 模式）。

    银河麒麟 PDF 排版特征：
      - 问题是加粗标题块（blocks 模式下整个标题是一个块），以？结尾
        （即使问题跨多行，blocks 模式也会把它合并为一整块）
      - 答案是普通段落块（不以？结尾）

    策略1：以"段落以？结尾"为问题边界，收集后续段落为答案
    策略2：降级兜底 —— 将所有段落拼接后滑动窗口
    每个 chunk 返回 {"text": str, "source": str}
    """
    chunks = []

    # ── 策略1：段落级别识别问题边界 ──
    question_indices = [
        i for i, p in enumerate(paragraphs)
        if p.rstrip().endswith('？') or p.rstrip().endswith('?')
    ]

    if len(question_indices) >= 3:
        for pos, q_idx in enumerate(question_indices):
            question_text = paragraphs[q_idx].strip()
            next_q_idx = question_indices[pos + 1] if pos + 1 < len(question_indices) else len(paragraphs)

            answer_parts = [
                paragraphs[j].strip()
                for j in range(q_idx + 1, next_q_idx)
                if paragraphs[j].strip()
            ]
            answer_text = '\n'.join(answer_parts)

            chunk_text = f"{question_text}\n{answer_text}" if answer_text else question_text
            if len(chunk_text) > 20:
                chunks.append({
                    "text": chunk_text,
                    "source": f"FAQ问答对#{len(chunks)+1}"
                })
        return chunks

    # ── 策略2：降级兜底 —— 拼接后滑动窗口 ──
    full_text = '\n'.join(paragraphs)
    chunks = []
    start = 0
    idx = 0
    while start < len(full_text):
        end = start + CHUNK_SIZE
        chunk_text = full_text[start:end].strip()
        if len(chunk_text) > 20:
            chunks.append({
                "text": chunk_text,
                "source": f"滑动窗口#{idx}"
            })
        start += CHUNK_SIZE - CHUNK_OVERLAP
        idx += 1

    return chunks


# ─────────────────────────────────────────────
# 2. FAISS 检索器（扩展自现有 AdvancedRAGRetriever）
# ─────────────────────────────────────────────
class KylinFAQRetriever:
    def __init__(self):
        print("[初始化] 加载 Embedding 模型...")
        self.embedding_model = SentenceTransformer(EMBED_MODEL)
        print("[初始化] 加载 Cross-Encoder 重排模型...")
        self.reranker = CrossEncoder(RERANK_MODEL)

        self.dimension = self.embedding_model.get_sentence_embedding_dimension()
        self.index = faiss.IndexFlatIP(self.dimension)
        self.metadata: list[dict] = []  # {"text": str, "source": str, "timestamp": float}

    # ── 建库 ──────────────────────────────────
    def build_from_pdf(self, pdf_path: str):
        """解析 PDF → 分块 → 向量化 → 入库"""
        print(f"[建库] 解析 PDF: {pdf_path}")
        raw_text = extract_text_from_pdf(pdf_path)

        print("[建库] 分块中...")
        chunks = split_faq_chunks(raw_text)
        print(f"[建库] 共切出 {len(chunks)} 个 chunk")

        texts = [c["text"] for c in chunks]
        sources = [c["source"] for c in chunks]

        print("[建库] 向量化中（可能需要几十秒）...")
        embeddings = self.embedding_model.encode(texts, show_progress_bar=True, batch_size=64)
        embeddings = np.array(embeddings, dtype="float32")
        faiss.normalize_L2(embeddings)

        self.index.add(embeddings)
        ts = time.time()
        for text, source in zip(texts, sources):
            self.metadata.append({"text": text, "source": source, "timestamp": ts})

        print(f"[建库] 完成，索引共 {self.index.ntotal} 条向量")

    # ── 持久化 ────────────────────────────────
    def save(self, index_path: str = INDEX_PATH, meta_path: str = META_PATH):
        faiss.write_index(self.index, index_path)
        with open(meta_path, "wb") as f:
            pickle.dump(self.metadata, f)
        print(f"[保存] 索引 → {index_path}")
        print(f"[保存] 元数据 → {meta_path}")

    def load(self, index_path: str = INDEX_PATH, meta_path: str = META_PATH):
        self.index = faiss.read_index(index_path)
        with open(meta_path, "rb") as f:
            self.metadata = pickle.load(f)
        print(f"[加载] 索引 {self.index.ntotal} 条，元数据 {len(self.metadata)} 条")

    # ── 检索（两阶段：向量召回 → Cross-Encoder 重排）────────
    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        """
        返回 top_k 条最相关的 FAQ 片段
        每条: {"text": str, "source": str, "rerank_score": float}
        """
        query_embedding = self.embedding_model.encode([query])
        query_embedding = np.array(query_embedding, dtype="float32")
        faiss.normalize_L2(query_embedding)

        # 第一阶段：向量召回（多取几倍留给重排）
        initial_k = min(top_k * 4, self.index.ntotal)
        similarities, indices = self.index.search(query_embedding, initial_k)

        candidates = []
        for sim, idx in zip(similarities[0], indices[0]):
            if idx == -1:
                continue
            doc = self.metadata[idx]
            candidates.append({
                "text": doc["text"],
                "source": doc["source"],
                "vector_score": float(sim),
            })

        if not candidates:
            return []

        # 第二阶段：Cross-Encoder 重排
        rerank_pairs = [[query, c["text"]] for c in candidates]
        rerank_scores = self.reranker.predict(rerank_pairs)

        for i, score in enumerate(rerank_scores):
            candidates[i]["rerank_score"] = float(score)

        final = sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)[:top_k]
        return final


# ─────────────────────────────────────────────
# 3. 主流程：首次运行建库并保存，后续直接加载
# ─────────────────────────────────────────────
def get_retriever() -> KylinFAQRetriever:
    """返回已就绪的检索器（自动判断是否需要重建索引）"""
    retriever = KylinFAQRetriever()

    if os.path.exists(INDEX_PATH) and os.path.exists(META_PATH):
        print("[启动] 检测到已有索引，直接加载...")
        retriever.load()
    else:
        print("[启动] 未检测到索引，开始从 PDF 建库...")
        retriever.build_from_pdf(PDF_PATH)
        retriever.save()

    return retriever


# ─────────────────────────────────────────────
# 4. 对外调用接口（供 Agent / 其他模块 import）
# ─────────────────────────────────────────────
_retriever: KylinFAQRetriever | None = None

def query_kylin_faq(question: str, top_k: int = 3) -> list[dict]:
    """
    对外接口：传入问题，返回最相关的 FAQ 片段列表
    示例返回：
      [
        {"text": "...", "source": "FAQ问答对#12", "rerank_score": 8.3},
        ...
      ]
    """
    global _retriever
    if _retriever is None:
        _retriever = get_retriever()
    return _retriever.retrieve(question, top_k=top_k)


def query_kylin_faq_as_memory(question: str, top_k: int = 3) -> list[dict]:
    """
    对外接口（后端 RAGStore 专用）：返回严格对齐
    `MemoryRetrieveResponse.kylin_manuals` 的格式。
      [{"type": "KylinManual", "title": ..., "section": ..., "summary": ...}, ...]
    与 raw_logs / reflections 不同，kylin_manuals **不做 time decay、不做 tags 过滤**。
    """
    raw = query_kylin_faq(question, top_k=top_k)
    return [
        {
            "type": "KylinManual",
            "title": "银河麒麟桌面操作系统 V11 常见问题(FAQ)",
            "section": r.get("source", ""),
            "summary": (r.get("text", "") or "").strip(),
        }
        for r in raw
    ]


# ─────────────────────────────────────────────
# 5. 命令行测试入口
# ─────────────────────────────────────────────
if __name__ == "__main__":
    retriever = get_retriever()

    test_queries = [
        "麒麟系统如何设置开机自启动",
        "无法连接网络怎么办",
        "怎么安装软件包",
        "系统分辨率设置",
    ]

    for q in test_queries:
        print(f"\n{'='*60}")
        print(f"问题：{q}")
        results = retriever.retrieve(q, top_k=3)
        for i, r in enumerate(results):
            print(f"\n  [{i+1}] 来源: {r['source']}  重排分: {r['rerank_score']:.3f}")
            print(f"       {r['text'][:200].replace(chr(10), ' ')}...")
