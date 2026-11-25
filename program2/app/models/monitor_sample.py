from sqlalchemy import Column, DateTime, Float

from app.core.database import Base


class MonitorSample(Base):
    __tablename__ = "monitor_samples"

    sampled_at = Column(DateTime, primary_key=True)
    network_kbps = Column(Float, nullable=True)
    nginx_qps = Column(Float, nullable=True)
