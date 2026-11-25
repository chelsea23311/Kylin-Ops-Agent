# app/api/v1/endpoints/knowledge.py
"""
知识库接口 —— 银河麒麟桌面操作系统 V11 FAQ 检索
供前端"知识库"页面调用。
"""
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, Query, HTTPException

from app.api import deps

router = APIRouter()


@router.get("/search", response_model=List[Dict[str, Any]])
async def search_faq(
    q: str = Query(..., min_length=1, description="检索问题"),
    top_k: int = Query(5, ge=1, le=20, description="返回条数，默认 5"),
    current_user=Depends(deps.get_current_user),
):
    """
    检索银河麒麟 FAQ 知识库。
    返回最相关的 FAQ 片段列表，按相关度降序排列。
    """
    try:
        import sys, os
        # kylin_rag.py 在仓库根目录，加入 sys.path
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
        if root not in sys.path:
            sys.path.insert(0, root)
        from kylin_rag import query_kylin_faq
        results = query_kylin_faq(q, top_k=top_k)
        return [
            {
                "section": r.get("source", ""),
                "text": (r.get("text", "") or "").strip(),
                "score": round(r.get("rerank_score", 0.0), 4),
            }
            for r in results
        ]
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"知识库检索失败：{e}")
