# app/main.py
from pathlib import Path
import asyncio
from contextlib import asynccontextmanager, suppress

import uvicorn
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints import admin
from app.core.database import engine, Base
from app.api.v1.endpoints import auth, tasks
from app.api import deps
from app.api.v1.endpoints import audit

# ==========================================
# 1. 数据库初始化 (核心：确保所有 Model 都已导入)
# ==========================================
# 导入所有模型以确保 Base.metadata 能识别到它们
from app.models.user import User
from app.models.task import TaskRecord
from app.models.audit import AuditLog
from app.models.tool_config import UserToolConfig  # 工具禁用管理
from app.models.alert_event import AlertEvent
from app.models.notification_message import NotificationMessage
from app.models.personnel_profile import PersonnelProfile
from app.models.security_setting import SecuritySetting
from app.models.monitor_sample import MonitorSample
from app.services.monitor_center import MonitorCenter

try:
    # 这一步会根据上面导入的类，在数据库中创建/更新表结构
    Base.metadata.create_all(bind=engine)
    print("🚀 [Kylin Agent] 数据库表初始化/更新成功！")
except Exception as e:
    print(f"❌ [Kylin Agent] 数据库初始化失败: {e}")

# ==========================================
# 2. FastAPI 实例配置
# ==========================================
@asynccontextmanager
async def lifespan(app):
    await asyncio.to_thread(MonitorCenter.load_history)
    collector = asyncio.create_task(MonitorCenter.run_collector())
    try:
        yield
    finally:
        collector.cancel()
        with suppress(asyncio.CancelledError):
            await collector


app = FastAPI(
    lifespan=lifespan,
    title="Kylin Ops Agent",
    description="基于 13 步编排流程的工业级 AI 运维助手",
    version="2.0.0"
)

# ==========================================
# 3. 跨域配置 (CORS) - 解决前端调用审批接口报错
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 生产环境建议改为具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 4. 路由挂载 (对齐 v1 目录结构)
# ==========================================
# 认证模块 (登录、注册)
app.include_router(auth.router, prefix="/auth", tags=["用户认证"])

# 核心：AI 运维任务模块 (对应你刚才修改的 tasks.py)
app.include_router(tasks.router, prefix="/tasks", tags=["AI 运维编排"])

app.include_router(admin.router, prefix="/api/v1/admin", tags=["管理员业务"])

app.include_router(audit.router, prefix="/api/v1/audit", tags=["审计员"])

# 资源监视器（HTTP 快照 + WebSocket 实时推送）
from app.api.v1.endpoints import system
app.include_router(system.router, prefix="/system", tags=["资源监视器"])

# 工具禁用管理（前端工具禁用管理页面对接）
from app.api.v1.endpoints import tool_config
app.include_router(tool_config.router, prefix="/tools/config", tags=["工具禁用管理"])

# 知识库（银河麒麟 FAQ 检索）
from app.api.v1.endpoints import knowledge
app.include_router(knowledge.router, prefix="/knowledge", tags=["知识库"])

# 智能监控与告警中心（自研，无 Prometheus/Zabbix 依赖）
from app.api.v1.endpoints import aiops
app.include_router(aiops.router, prefix="/api/v1/aiops", tags=["智能监控与告警"])

# 前端静态资源由后端同源托管，避免本地浏览器和远程端口转发之间来回打架。
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "operations-and-maintenance" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="frontend-assets")


def frontend_index_response():
    return FileResponse(
        FRONTEND_DIST / "index.html",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )

# ==========================================
# 5. 基础状态检查接口
# ==========================================
@app.get("/")
def root():
    if FRONTEND_DIST.exists():
        return frontend_index_response()
    return {
        "status": "online",
        "system": "Kylin Ops Agent",
        "version": "2.0.0",
        "features": ["ContextBundle", "Reflection", "GuardrailTree", "ML_Audit"]
    }


@app.get("/health", tags=["健康检查"])
def health():
    return {"status": "ok", "system": "Kylin Ops Agent"}


@app.get("/users/me")
def read_user_me(current_user = Depends(deps.get_current_user)):
    """受保护接口，用于测试登录态"""
    return {
        "username": current_user.username,
        "role": current_user.role,
        "permissions": current_user.role # 对应 Orchestrator 里的身份护栏
    }


@app.get("/{full_path:path}", include_in_schema=False)
def frontend_spa(full_path: str):
    if FRONTEND_DIST.exists() and not full_path.startswith(("auth/", "tasks/", "api/", "system/", "tools/", "knowledge/", "users/")):
        return frontend_index_response()
    raise HTTPException(status_code=404, detail="接口不存在")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
