from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from datetime import datetime
from app.core.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, index=True)
    operator = Column(String)      # 谁执行的（Step 2）
    command = Column(String)       # 执行的命令（Step 10）
    risk_score = Column(Float)     # 风险评分（Step 7）
    full_context = Column(JSON)    # 整个 13 步的 JSON 镜像（Step 11）
    created_at = Column(DateTime, default=datetime.now)