from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from app.core.database import Base


class NotificationMessage(Base):
    __tablename__ = "notification_messages"

    id = Column(Integer, primary_key=True, index=True)
    recipient_user_id = Column(String, index=True, nullable=False)
    sender_user_id = Column(String, nullable=False)
    receiver_label = Column(String, nullable=False)
    category = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="sent")
    scheduled_for = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.now)
