"""
运维审计 BERT 模型推理服务
参考: API开发指南_BERT模型.md
启动方式: uvicorn inference_service:app --host 0.0.0.0 --port 8000
"""

import re
import os
from typing import Optional, List

import torch
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from transformers import BertTokenizer, BertForSequenceClassification
from captum.attr import LayerIntegratedGradients


# ============================================================
# 1. 全局配置与模型加载（服务启动时只加载一次）
# ============================================================
MODEL_DIR = os.getenv("MODEL_DIR", "./audit_model_v1")
MAX_LENGTH = 64
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print(f"[INFO] 加载模型中: {MODEL_DIR}  (device={DEVICE})")
tokenizer = BertTokenizer.from_pretrained(MODEL_DIR)
model = BertForSequenceClassification.from_pretrained(MODEL_DIR).to(DEVICE)
model.eval()
print("[INFO] 模型加载完成，服务就绪。")


# ============================================================
# 2. FastAPI 应用初始化
# ============================================================
app = FastAPI(
    title="运维审计风险推理 API",
    description="基于 BERT 微调的运维意图安全分类服务，支持双维度归因分析。",
    version="1.0.0",
)

# 允许跨域（前端仪表盘直接请求时使用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# 3. 请求 / 响应数据模型
# ============================================================
class InferRequest(BaseModel):
    text: str

    class Config:
        json_schema_extra = {
            "example": {"text": "[delete_file] /etc/passwd"}
        }


class TokenAttribution(BaseModel):
    token: str       # BERT 分词后的 token 字符串
    score: float     # 该 token 对危险预测的归因分数（归一化后，0.0~1.0）
    highlight: bool  # 是否建议前端高亮（score 超过均值即标记）


class InferResponse(BaseModel):
    text: str
    total_risk: float        # 整体危险概率 Label-1 (0.0~1.0)
    action_energy: float     # [Tool] 部分归因能量占比 (0.0~1.0)
    asset_sensitivity: float # Target 部分归因能量占比 (0.0~1.0)
    verdict: str             # "BLOCK" | "PASS"
    token_attributions: List[TokenAttribution]  # 每个 token 的归因分数，供前端高亮


# ============================================================
# 4. 核心推理函数
# ============================================================
def analyze_intent_risk(text: str) -> dict:
    """
    完整推理流程：
      ① 编码 → ② 计算总风险概率 → ③ Captum LIG 归因 → ④ 拆解动作/资产能量
    """
    # ── 拆解指令为 [Tool] 和 Target 两部分 ──────────────────────
    match = re.match(r"^\[([^\]]+)\]\s*(.*)", text.strip())
    tool_part   = "[" + match.group(1) + "]" if match else text
    target_part = match.group(2)               if match else ""

    # ── 分词编码 ─────────────────────────────────────────────────
    encoding = tokenizer(
        text,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=MAX_LENGTH,
    )
    input_ids      = encoding["input_ids"].to(DEVICE)
    attention_mask = encoding["attention_mask"].to(DEVICE)
    tokens         = tokenizer.convert_ids_to_tokens(input_ids[0])

    # ── 总风险概率 ───────────────────────────────────────────────
    with torch.no_grad():
        outputs = model(input_ids=input_ids, attention_mask=attention_mask)
        probs   = torch.softmax(outputs.logits, dim=-1)
    total_risk = float(probs[0, 1].item())

    # ── 找到 Tool / Target 的 Token Span ─────────────────────────
    tool_tokens   = tokenizer.tokenize(tool_part)
    target_tokens = tokenizer.tokenize(target_part) if target_part else []

    def find_span(full_tokens, sub_tokens):
        if not sub_tokens:
            return None, None
        for i in range(len(full_tokens) - len(sub_tokens) + 1):
            if full_tokens[i : i + len(sub_tokens)] == sub_tokens:
                return i, i + len(sub_tokens) - 1
        return None, None

    tool_start,   tool_end   = find_span(tokens, tool_tokens)
    target_start, target_end = find_span(tokens, target_tokens)

    # ── Captum Layer Integrated Gradients 归因 ───────────────────
    def forward_func(in_ids, attn_mask):
        """归因目标：Label-1 的 logit（危险类别）"""
        return model(input_ids=in_ids, attention_mask=attn_mask).logits[:, 1]

    lig          = LayerIntegratedGradients(forward_func, model.bert.embeddings)
    baseline_ids = torch.zeros_like(input_ids).to(DEVICE)   # 全 [PAD] 作基线

    attributions, _ = lig.attribute(
        inputs=input_ids,
        baselines=baseline_ids,
        additional_forward_args=(attention_mask,),
        n_steps=50,
        return_convergence_delta=True,
    )

    # [1, seq_len, hidden_dim] → L2 范数 → [seq_len]，只保留正贡献
    attr_scores = torch.relu(attributions.norm(dim=-1).squeeze(0))

    # ── 按 Span 累加并归一化 ──────────────────────────────────────
    total_attr = max(float(attr_scores.sum().item()), 1e-8)

    def span_energy(start, end) -> float:
        if start is None:
            return 0.0
        return float(attr_scores[start : end + 1].sum().item() / total_attr)

    action_energy    = min(span_energy(tool_start,   tool_end),   1.0)
    asset_sensitivity = min(span_energy(target_start, target_end), 1.0)

    # ── Token 级归因分数（过滤掉 [CLS] / [SEP] / [PAD] 特殊 token）──────────
    real_len   = int(attention_mask.sum().item())           # 去掉 [PAD]
    raw_scores = attr_scores[1 : real_len - 1]              # 去掉首尾 [CLS][SEP]
    real_tokens = tokens[1 : real_len - 1]

    # 归一化到 0~1
    score_max = max(float(raw_scores.max().item()), 1e-8)
    norm_scores = (raw_scores / score_max).tolist()

    # 以均值作为高亮阈值
    avg_score = sum(norm_scores) / max(len(norm_scores), 1)
    token_attributions = [
        {
            "token": tok,
            "score": round(s, 4),
            "highlight": s >= avg_score,
        }
        for tok, s in zip(real_tokens, norm_scores)
    ]

    return {
        "total_risk":          round(total_risk,        4),
        "action_energy":       round(action_energy,     4),
        "asset_sensitivity":   round(asset_sensitivity, 4),
        "token_attributions":  token_attributions,
    }


# ============================================================
# 5. 路由定义
# ============================================================
@app.get("/health", summary="健康检查")
def health():
    """确认服务是否正常运行。"""
    return {"status": "ok", "device": DEVICE, "model_dir": MODEL_DIR}


@app.post("/infer", response_model=InferResponse, summary="运维指令风险推理")
def infer(req: InferRequest):
    """
    输入一条运维指令，返回：
    - `total_risk`：整体危险概率（0~1）
    - `action_energy`：动作（Tool）部分的归因能量占比
    - `asset_sensitivity`：目标（Target/路径）部分的归因能量占比
    - `verdict`：最终判决 `BLOCK`（≥0.5）或 `PASS`（<0.5）
    """
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="text 字段不能为空")

    try:
        result = analyze_intent_risk(req.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"推理失败: {str(e)}")

    return InferResponse(
        text              = req.text,
        total_risk        = result["total_risk"],
        action_energy     = result["action_energy"],
        asset_sensitivity = result["asset_sensitivity"],
        verdict           = "BLOCK" if result["total_risk"] >= 0.5 else "PASS",
        token_attributions= result["token_attributions"],
    )
