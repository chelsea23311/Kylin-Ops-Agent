from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from app.core.database import Base
from datetime import datetime
from sqlalchemy import Column, String, Text, JSON
# class TaskRecord(Base):
#     __tablename__ = "task_records"
#
#     id = Column(String, primary_key=True, index=True) # 存那个 UUID
#     user_id = Column(String) # 存 admin 或 ID
#     prompt = Column(String)
#     status = Column(String)
#     # 核心：直接把整个 13 步的 context 存成 JSON
#     context_data = Column(JSON)
#     created_at = Column(DateTime, default=datetime.now)


class TaskRecord(Base):
    __tablename__ = "task_records"
    id = Column(String, primary_key=True)
    user_id = Column(String)
    task_text = Column(Text)
    host_id = Column(String, default="host_prod_01")
    status = Column(String)
    context_data = Column(JSON)
    # --- 建议补上这一行 ---
    created_at = Column(DateTime, default=datetime.now)