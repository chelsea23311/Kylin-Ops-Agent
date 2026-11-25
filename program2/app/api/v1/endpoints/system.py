from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException, Query, Request, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.user import User
from app.services.monitor import SystemMonitor
from app.services.ml_service import MLService
import psutil
import time
import os
import json
from typing import Optional

router = APIRouter()


class ResourceReportPayload(BaseModel):
    directory: str = "/var/log"
    max_depth: int = 2
    max_entries: int = 120


def _safe_dir_snapshot(directory: str, max_depth: int = 2, max_entries: int = 120) -> dict:
    base = os.path.abspath(directory or "/")
    depth_limit = max(1, min(int(max_depth or 2), 4))
    entry_limit = max(20, min(int(max_entries or 120), 300))

    if not os.path.exists(base):
        return {
            "base_dir": base,
            "entries": [],
            "errors": [f"目录不存在: {base}"],
            "truncated": False,
        }

    results = []
    errors = []
    queue = [(base, 0)]

    while queue and len(results) < entry_limit:
        cur_path, depth = queue.pop(0)
        try:
            with os.scandir(cur_path) as it:
                for entry in it:
                    if len(results) >= entry_limit:
                        break
                    try:
                        stat_info = entry.stat(follow_symlinks=False)
                        rel = os.path.relpath(entry.path, base)
                        item = {
                            "path": rel,
                            "name": entry.name,
                            "type": "dir" if entry.is_dir(follow_symlinks=False) else "file",
                            "size": int(stat_info.st_size),
                            "mtime": int(stat_info.st_mtime),
                            "depth": depth,
                        }
                        results.append(item)
                        if item["type"] == "dir" and depth + 1 < depth_limit:
                            queue.append((entry.path, depth + 1))
                    except Exception as e:
                        errors.append(f"读取条目失败 {entry.path}: {str(e)}")
        except Exception as e:
            errors.append(f"扫描目录失败 {cur_path}: {str(e)}")

    return {
        "base_dir": base,
        "entries": results,
        "errors": errors,
        "truncated": len(results) >= entry_limit,
    }


@router.post("/monitor/resource-report")
async def get_resource_report(
    payload: ResourceReportPayload,
    current_user=Depends(get_current_user),
):
    monitor_payload = SystemMonitor.get_resource_monitor_payload()
    dir_snapshot = _safe_dir_snapshot(
        payload.directory,
        max_depth=payload.max_depth,
        max_entries=payload.max_entries,
    )

    llm_system = """
你是一名资深 Linux 运维分析师。
你将收到两类实时输入：
1) 资源监控快照（CPU/内存/网络/磁盘）
2) 服务器目录快照（目录结构、文件大小与更新时间）

请输出结构化分析，并给出可执行的运维任务建议。
要求：
1. 必须结合两类输入，不得只看单一数据源。
2. 建议应优先低风险排查，再给出中风险优化。
3. 每个建议任务包含：title、reason、priority(low|medium|high)、suggested_command、risk_note。
    4. 额外输出未来风险预测，future_predictions 至少给出 1 条、最多 3 条。
    5. future_predictions 每项必须包含：
         - issue: 可能问题
         - probability: high|medium|low
         - horizon: 风险可能出现的时间窗口（如"24小时内"）
         - signal: 触发该预测的监控/目录信号
         - mitigation: 预防或缓解建议
4. 严格输出 JSON：
{
  "summary": "<总体结论>",
  "health_score": 0,
  "key_findings": ["<发现1>", "<发现2>"],
        "future_predictions": [
            {
                "issue": "<可能问题>",
                "probability": "high|medium|low",
                "horizon": "<时间窗口>",
                "signal": "<预测依据>",
                "mitigation": "<缓解建议>"
            }
        ],
  "recommended_tasks": [
    {
      "title": "<任务名>",
      "reason": "<原因>",
      "priority": "low|medium|high",
      "suggested_command": "<建议命令>",
      "risk_note": "<风险说明>"
    }
  ]
}
""".strip()

    llm_user = (
        f"role: {current_user.role}\n"
        f"monitor_snapshot: {json.dumps(monitor_payload, ensure_ascii=False)}\n"
        f"directory_snapshot: {json.dumps(dir_snapshot, ensure_ascii=False)}"
    )

    try:
        ai_report = await asyncio.wait_for(
            MLService.call_llm(system_prompt=llm_system, user_prompt=llm_user),
            timeout=35,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="AI 分析超时，请稍后重试")
    if not isinstance(ai_report, dict):
        raise HTTPException(status_code=503, detail="AI 分析服务不可用，请检查模型和 API 配置")
    else:
        # 向后兼容：确保前端渲染字段始终存在
        if not isinstance(ai_report.get("future_predictions"), list):
            ai_report["future_predictions"] = []
        if not isinstance(ai_report.get("recommended_tasks"), list):
            ai_report["recommended_tasks"] = []

    return {
        "status": "success",
        "generated_at": int(time.time()),
        "monitor_snapshot": monitor_payload,
        "directory_snapshot": dir_snapshot,
        "ai_report": ai_report,
    }

# def _get_token_from_request(request: Request, token_query: Optional[str] = None) -> Optional[str]:
#     auth_header = request.headers.get("Authorization")
#     if auth_header and auth_header.startswith("Bearer "):
#         return auth_header[7:]
#     return token_query

# ──────────────────────────────────────────────
# HTTP 快照接口（首帧 / 降级备用）
# ──────────────────────────────────────────────
# @router.get("/monitor/snapshot")
# async def get_system_snapshot(current_user=Depends(get_current_user)):
#     """
#     资源监视器首帧接口（HTTP）：
#     - 前端建立 WebSocket 前可先调用此接口渲染首帧；
#     - 或在网络不支持 WebSocket 时作为降级轮询方案。
#     """
#     payload = SystemMonitor.get_resource_monitor_payload()
#     return {
#         "status": "success",
#         "data": payload,
#         "role": current_user.role,
#     }
# @router.get("/monitor/snapshot")
# async def get_system_snapshot(current_user=Depends(get_current_user)):
#     payload = SystemMonitor.get_resource_monitor_payload()
#     # 直接展开 payload，不要包在 "data" 字段里
#     return {
#         **payload, 
#         "status": "success", 
#         "role": current_user.role
#     }
@router.get("/monitor/snapshot")
async def get_system_snapshot(
    current_user=Depends(get_current_user),
):
    """
    终极对齐版本：
    同时提供【平铺字段】和【data字段】，无论前端怎么解析都能拿到数据。
    """
    payload = SystemMonitor.get_resource_monitor_payload()
    
    # 构造响应
    response = {
        **payload,            # 平铺所有字段 (cpu_view, mem_view, disk_view)
        "data": payload,      # 额外再包一层 data 字段 (双重保险)
        "type": "monitor_frame",
        "status": "success",
        "role": current_user.role
    }
    return response

# ──────────────────────────────────────────────
# WebSocket 实时推送接口
# ──────────────────────────────────────────────
@router.websocket("/monitor/ws")
async def monitor_websocket(
    websocket: WebSocket,
    token: str = Query(..., description="JWT token，由前端在握手 URL 中携带"),
    interval: float = Query(3.0, ge=1.0, le=60.0, description="推送间隔（秒），范围 1–60"),
):
    """
    WebSocket 实时推送端点。

    连接方式：
        ws://<host>/system/monitor/ws?token=<JWT>&interval=3

    协议：
    - 服务端每隔 interval 秒主动推送一帧 JSON（ResourceMonitorPayload）；
    - 前端可发送 {"action": "ping"} 保活，服务端回复 {"type": "pong"}；
    - 连接断开（网络异常 / 主动关闭）后前端应自动重连。

    推送帧格式：
        {
          "type": "monitor_frame",
          "timestamp": "2026-04-20T08:00:00+00:00",
          "data": { /* ResourceMonitorPayload */ }
        }
    """
    # ── 1. 鉴权（WebSocket 不支持 Depends(get_current_user)，手动验证 JWT）──
    db = SessionLocal()
    try:
        payload_jwt = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        sub: str = payload_jwt.get("sub")
        if not sub:
            await websocket.close(code=4001, reason="Invalid token")
            return

        # login token currently uses user.id in sub; keep username fallback for older tokens.
        user = db.query(User).filter(User.id == sub).first()
        if not user:
            user = db.query(User).filter(User.username == sub).first()
        if not user:
            await websocket.close(code=4001, reason="User not found")
            return
    except JWTError:
        await websocket.close(code=4001, reason="Token verification failed")
        return
    finally:
        db.close()

    # ── 2. 握手成功，接受连接 ────────────────────────────────────────────────
    await websocket.accept()
    # await websocket.send_json({
    #     "type": "connected",
    #     "message": f"欢迎 {user.username}，资源监视器已连接，推送间隔 {interval}s",
    #     "role": user.role,
    # })

    # ── 3. 启动推送循环 ──────────────────────────────────────────────────────
    try:
        async for frame in SystemMonitor.stream(interval=interval):
            await websocket.send_json(frame)

            # 非阻塞地检查客户端是否发来消息（保活 ping 等）
            try:
                msg = await asyncio.wait_for(websocket.receive_json(), timeout=0.05)
                if isinstance(msg, dict) and msg.get("action") == "ping":
                    await websocket.send_json({"type": "pong"})
            except Exception:
                pass  # 没有客户端消息，继续推送

    except WebSocketDisconnect:
        pass  # 客户端主动断开，静默退出
    except Exception as e:
        try:
            await websocket.close(code=4000, reason=str(e))
        except Exception:
            pass


import asyncio  # noqa: E402（asyncio 已在 monitor.py 中使用，此处保留供 wait_for）
