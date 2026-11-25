from sqlalchemy import Column, Integer, String, Boolean
from app.core.database import Base

# class User(Base):
#     __tablename__ = "users"
#     id = Column(Integer, primary_key=True, index=True)
#     username = Column(String, unique=True, index=True)
#     hashed_password = Column(String)
#     role = Column(String, default="operator") # 区分管理员与普通运维


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    # --- 新增字段 ---
    role = Column(String, default="user")