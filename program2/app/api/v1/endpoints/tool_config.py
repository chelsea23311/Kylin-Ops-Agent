# app/api/v1/endpoints/tool_config.py
"""
工具禁用管理接口 —— 供前端"工具禁用管理页面"调用。
operator / admin 可查询和修改自己的工具禁用配置。
护栏层（_check_guardrails）会读取这张表与后端白名单合并判断。
"""
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api import deps
from app.models.tool_config import UserToolConfig
from app.services.mcp_tools import MCP_TOOLS_REGISTRY, KylinMCP

router = APIRouter()


@router.get("/", response_model=List[Dict[str, Any]])
def get_tool_config(
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user)
):
    """
    返回当前用户可见的所有 MCP 工具列表，并标注：
    - backend_allowed: 后端白名单是否允许（基于角色）
    - user_disabled:   用户是否在管理页主动关闭
    - effective:       最终是否可用（两者均通过才为 True）
    """
    role = current_user.role
    backend_allowed_tools = set(KylinMCP.get_tools_by_permission(role))

    # 查询该用户所有禁用配置
    configs = db.query(UserToolConfig).filter(
        UserToolConfig.user_id == current_user.id,
        UserToolConfig.disabled == True
    ).all()
    user_disabled_set = {c.tool_name for c in configs}

    result = []
    for tool_name, tool_info in MCP_TOOLS_REGISTRY.items():
        backend_allowed = tool_name in backend_allowed_tools
        user_disabled = tool_name in user_disabled_set
        result.append({
            "tool_name": tool_name,
            "level": tool_info.get("level"),
            "reason": tool_info.get("reason"),
            "need_root": bool(tool_info.get("need_root", 0)),
            "backend_allowed": backend_allowed,
            "user_disabled": user_disabled,
            "effective": backend_allowed and not user_disabled,
        })
    return result


@router.post("/{tool_name}/disable", response_model=Dict[str, Any])
def disable_tool(
    tool_name: str,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user)
):
    """前端工具禁用管理页：主动关闭某工具"""
    if tool_name not in MCP_TOOLS_REGISTRY:
        raise HTTPException(status_code=404, detail=f"工具 {tool_name} 不存在")

    config = db.query(UserToolConfig).filter(
        UserToolConfig.user_id == current_user.id,
        UserToolConfig.tool_name == tool_name
    ).first()
    if config:
        config.disabled = True
    else:
        config = UserToolConfig(user_id=current_user.id, tool_name=tool_name, disabled=True)
        db.add(config)
    db.commit()
    return {"tool_name": tool_name, "user_disabled": True, "effective": False}


@router.post("/{tool_name}/enable", response_model=Dict[str, Any])
def enable_tool(
    tool_name: str,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user)
):
    """前端工具禁用管理页：重新启用某工具（取消用户主动禁用）"""
    if tool_name not in MCP_TOOLS_REGISTRY:
        raise HTTPException(status_code=404, detail=f"工具 {tool_name} 不存在")

    config = db.query(UserToolConfig).filter(
        UserToolConfig.user_id == current_user.id,
        UserToolConfig.tool_name == tool_name
    ).first()
    if config:
        config.disabled = False
        db.commit()

    role = current_user.role
    backend_allowed = tool_name in set(KylinMCP.get_tools_by_permission(role))
    return {
        "tool_name": tool_name,
        "user_disabled": False,
        "effective": backend_allowed,
    }
