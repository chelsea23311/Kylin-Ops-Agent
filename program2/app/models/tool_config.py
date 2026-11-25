# app/models/tool_config.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from app.core.database import Base


class UserToolConfig(Base):
    """
    用户维度的工具禁用配置表。
    每条记录代表某个用户主动关闭了某个 MCP 工具。
    护栏层会将此表与后端白名单合并判断，任一禁止则工具不可用。
    """
    __tablename__ = "user_tool_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)          # 对应 users.id
    tool_name = Column(String, nullable=False, index=True)         # MCP_TOOLS_REGISTRY key
    disabled = Column(Boolean, default=True, nullable=False)       # True = 用户主动禁用
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
