from datetime import datetime

from sqlalchemy import Column, DateTime, Float, String, Text

from app.core.database import Base


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id = Column(String, primary_key=True)
    host_id = Column(String, default="host_prod_01", index=True)
    source = Column(String, default="self-monitor")
    rule_key = Column(String, index=True)
    level = Column(String, default="warning", index=True)
    title = Column(String)
    message = Column(Text)
    metric_name = Column(String, default="")
    metric_value = Column(Float, default=0.0)
    threshold = Column(Float, default=0.0)
    status = Column(String, default="unresolved", index=True)
    agent_approval_status = Column(String, default="pending", index=True)
    suggested_task_text = Column(Text, default="")
    refined_task_text = Column(Text, default="")
    linked_task_id = Column(String, default="", index=True)
    approved_by = Column(String, default="")
    resolved_by = Column(String, default="")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now)
    resolved_at = Column(DateTime, nullable=True)
