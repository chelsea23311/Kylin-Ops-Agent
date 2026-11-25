from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AlertListQuery(BaseModel):
    level: Optional[str] = None
    status: Optional[str] = None
    agent_approval_status: Optional[str] = None


class AlertApprovePayload(BaseModel):
    approved: bool = Field(..., description="是否批准 AI Agent 执行")


class AlertResolvePayload(BaseModel):
    resolve: bool = Field(True, description="标记告警为已恢复")


class AlertRuleStatus(BaseModel):
    rule_key: str
    triggered: bool
    severity: str
    message: str


class MonitorOverviewResponse(BaseModel):
    generated_at: str
    gauges: Dict[str, Optional[float]]
    service_status: List[Dict[str, Any]]
    network_24h: List[Dict[str, Any]]
    nginx_qps_24h: List[Dict[str, Any]]
    auto_rules: List[AlertRuleStatus]


class AlertEventOut(BaseModel):
    id: str
    host_id: str
    source: str
    rule_key: str
    level: str
    title: str
    message: str
    metric_name: str
    metric_value: float
    threshold: float
    status: str
    agent_approval_status: str
    suggested_task_text: str
    refined_task_text: str
    linked_task_id: str
    approved_by: str
    resolved_by: str
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True
