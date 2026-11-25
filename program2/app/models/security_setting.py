from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.core.database import Base


class SecuritySetting(Base):
    __tablename__ = "security_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True, nullable=False)
    two_factor_enabled = Column(Boolean, nullable=False, default=False)
    phone_number = Column(String, nullable=False, default="")
    phone_verified = Column(Boolean, nullable=False, default=False)
    last_code_sent_at = Column(DateTime, nullable=True)
    password_updated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
