# app/core/config.py
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = (BASE_DIR / "kylin_ops.db").as_posix()

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 改用 SQLite 方便本地直接测试运行，不依赖复杂的 PostgreSQL 服务
    DATABASE_URL: str = f"sqlite:///{DEFAULT_DB_PATH}"
    SECRET_KEY: str = Field(min_length=1)  # 部署时通过环境变量设置
    ALGORITHM: str = "HS256"
    # 角色注册密钥（建议在生产环境通过环境变量覆盖）
    OPERATOR_REGISTER_KEY: str = ""
    AUDITOR_REGISTER_KEY: str = ""
    RISK_APPROVAL_THRESHOLD: float = 0.7
    MIN_PLAN_COMMANDS: int = 3
    # 桌面弹窗审批接口的防护密钥，为空时跳过验证（开发调试用）
    APPROVE_SECRET: str = ""
    # DeepSeek大模型配置（从环境变量读取）
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-flash"
    BERT_SERVICE_URL: str = "http://127.0.0.1:8001/infer"
    # MCP C/S 网络通信配置
    MCP_SERVER_HOST: str = "127.0.0.1"
    MCP_SERVER_PORT: int = 8765
    MCP_CONNECT_TIMEOUT_SEC: float = 3.0
    MCP_REQUEST_TIMEOUT_SEC: float = 20.0

settings = Settings()
