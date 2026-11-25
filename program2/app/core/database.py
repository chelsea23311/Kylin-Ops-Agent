# app/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# 适配 SQLite 设置
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

# 创建引擎
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 所有数据库模型的父类
Base = declarative_base()

# 获取数据库连接的依赖项 (给接口用的)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()