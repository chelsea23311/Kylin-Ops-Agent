import json
import logging
from datetime import datetime
from typing import Optional,Dict, Any
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

class MLService:
    BERT_SERVICE_URL = settings.BERT_SERVICE_URL
    @staticmethod
    async def retrieve_memory(
        task_text: str,
        request_id: str = "",
        host_id: str = "",
        top_k_raw_log: int = 3,
        top_k_reflection: int = 1,
        top_k_manual: int = 2,
        tag_filter: list | None = None,
    ):
        try:
            # --- 新增调试日志 ---
            print(f"🔍 [RAG] 收到检索请求，目标文本: {task_text[:30]}...")
            
            from app.services.rag_store import RAGStore
            
            print("⏳ [RAG] 正在获取 RAGStore 实例 (如果是首次运行，此处将加载向量模型)...")
            store = RAGStore.instance()
            
            print("🚀 [RAG] 实例就绪，开始向量计算与检索...")
            result = store.retrieve(
                task_text=task_text,
                top_k_raw_log=top_k_raw_log,
                top_k_reflection=top_k_reflection,
                top_k_manual=top_k_manual,
                tag_filter=tag_filter,
            )
            print("✅ [RAG] 检索完成")
            return result
            # ------------------
        except Exception as e:
            print(f"❌ [MLService] RAG 检索异常: {e}")
            return {
                "raw_logs": [],
                "reflections": [],
                "kylin_manuals": [],
            }
    @classmethod
    async def audit_risk(cls, tool_name: str, target: str) -> Dict[str, Any]:
        input_text = f"[{tool_name}] {target}"
        print(f"🛡️ [Audit] 正在请求 BERT 风险审计: {input_text}") # 新增日志

        last_err = None
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=45.0, trust_env=False) as client:
                    response = await client.post(
                        cls.BERT_SERVICE_URL,
                        json={"text": input_text},
                    )

                    if response.status_code == 200:
                        data = response.json()
                        print(f"✅ [Audit] 审计通过，结论: {data.get('verdict')}")
                        return {
                            "total_risk": data.get("total_risk", 0.0),
                            "action_energy": data.get("action_energy"),
                            "asset_sensitivity": data.get("asset_sensitivity"),
                            "verdict": data.get("verdict", "BLOCK"),
                            "token_attributions": data.get("token_attributions", []),
                            "status": "success"
                        }

                    print(f"⚠️ [Audit] BERT 服务返回错误码: {response.status_code}")
                    return {
                        # 服务故障时保守阻断；此分值用于护栏，不代表模型预测。
                        "total_risk": 1.0,
                        "action_energy": None,
                        "asset_sensitivity": None,
                        "verdict": "BLOCK",
                        "error": f"AI服务异常: {response.status_code}",
                        "token_attributions": [],
                        "status": "error"
                    }
            except Exception as e:
                last_err = e
                if attempt == 0:
                    print("⚠️ [Audit] 首次调用失败，重试一次...")

        err_msg = str(last_err) if last_err else "unknown"
        if not err_msg:
            err_msg = last_err.__class__.__name__ if last_err else "unknown"
        print(f"❌ [Audit] 无法连接到 BERT 推理服务 (端口8001): {err_msg}")
        return {
            "total_risk": 1.0,
            "action_energy": None,
            "asset_sensitivity": None,
            "verdict": "BLOCK",
            "error": f"无法连接AI审计引擎: {err_msg}",
            "token_attributions": [],
            "status": "error"
        }
    
    @classmethod
    async def save_memory(cls, writeback_payload: Dict[str, Any]):
        """
        Step 12: 将本次任务的 raw_log + reflection_result 作为一组写回 RAG 记忆库。
        共享 request_id / timestamp / tags，使 reflection 能借用 raw_log 的 timestamp 做 time decay。

        writeback_payload 字段参考 orchestrator.py Step 12：
            { request_id, raw_log, reflection_result, tags }
        """
        try:
            from app.services.rag_store import RAGStore
            store = RAGStore.instance()
            result = store.write(
                request_id=writeback_payload.get("request_id", ""),
                raw_log=writeback_payload.get("raw_log") or {},
                reflection_result=writeback_payload.get("reflection_result") or {},
                tags=writeback_payload.get("tags") or [],
            )
            print(f"[MLService] 记忆写回成功: {result}")
            return result
        except Exception as e:
            print(f"[MLService] RAG 写回失败：{e}")
            return {"status": "error", "message": str(e)}

    @classmethod
    async def call_llm(cls, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
        """
        调用DeepSeek大模型，强制要求 JSON 格式返回
        """
        headers = {
            "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": settings.DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            # 某些版本的 API 也可以通过在 prompt 里强调 json 或使用 response_format
            "response_format": {"type": "json_object"},
            "thinking": {"type": "disabled"},
            "temperature": 0.1  # 低随机性，保证运维决策的稳定性
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(
                    f"{settings.DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions",
                    json=payload,
                    headers=headers
                )

                if response.status_code != 200:
                    logger.error(f"DeepSeek API Error: {response.text}")
                    return None

                result = response.json()
                content = result["choices"][0]["message"]["content"]

                # 清洗 LLM 可能返回的 Markdown 代码块标识符
                if content.startswith("```json"):
                    content = content.strip("```json").strip("```").strip()

                return json.loads(content)

        except Exception as e:
            logger.error(f"Failed to call DeepSeek: {str(e)}")
            return None
