import uuid
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.alert_event import AlertEvent


class AlertCenter:
    RULE_CPU_HIGH = "cpu_high_sustained"
    RULE_MEM_HIGH = "memory_high_sustained"
    RULE_DISK_HIGH = "disk_high"
    RULE_NGINX_DOWN = "nginx_down"
    RULE_MYSQL_DOWN = "mysql_down"
    RULE_REDIS_DOWN = "redis_down"

    @staticmethod
    def _now() -> datetime:
        return datetime.now()

    @classmethod
    def evaluate_rules(cls, snapshot: Dict) -> List[Dict]:
        gauges = snapshot.get("gauges", {})
        services = {s.get("name"): s.get("status") for s in snapshot.get("service_status", [])}

        cpu = float(gauges.get("cpu_percent", 0))
        mem = float(gauges.get("memory_percent", 0))
        disk = float(gauges.get("disk_percent", 0))

        rules = []
        rules.append({
            "rule_key": cls.RULE_CPU_HIGH,
            "triggered": cpu >= 90,
            "severity": "critical" if cpu >= 95 else "warning",
            "metric_name": "cpu_percent",
            "metric_value": cpu,
            "threshold": 90,
            "title": "CPU 使用率过高",
            "message": f"CPU 使用率达到 {cpu}%（阈值 90%）。",
            "task_text": "检查 CPU 异常占用进程，定位根因并给出低风险处置方案。",
        })
        rules.append({
            "rule_key": cls.RULE_MEM_HIGH,
            "triggered": mem >= 90,
            "severity": "critical" if mem >= 95 else "warning",
            "metric_name": "memory_percent",
            "metric_value": mem,
            "threshold": 90,
            "title": "内存使用率过高",
            "message": f"内存使用率达到 {mem}%（阈值 90%）。",
            "task_text": "检查内存占用异常进程，分析是否存在泄漏或缓存膨胀，并输出处置建议。",
        })
        rules.append({
            "rule_key": cls.RULE_DISK_HIGH,
            "triggered": disk >= 90,
            "severity": "critical" if disk >= 95 else "warning",
            "metric_name": "disk_percent",
            "metric_value": disk,
            "threshold": 90,
            "title": "磁盘使用率过高",
            "message": f"系统磁盘使用率达到 {disk}%（阈值 90%）。",
            "task_text": "排查磁盘占用热点目录与大文件，优先给出可回滚、低风险的空间释放方案。",
        })

        for service_name, rule_key in [
            ("Nginx", cls.RULE_NGINX_DOWN),
            ("MySQL", cls.RULE_MYSQL_DOWN),
            ("Redis", cls.RULE_REDIS_DOWN),
        ]:
            status = services.get(service_name, "DOWN")
            down = status != "UP"
            rules.append({
                "rule_key": rule_key,
                "triggered": down,
                "severity": "critical",
                "metric_name": f"{service_name.lower()}_status",
                "metric_value": 0.0 if down else 1.0,
                "threshold": 1.0,
                "title": f"{service_name} 服务异常",
                "message": f"{service_name} 当前状态为 {status}。",
                "task_text": f"排查 {service_name} 服务不可用原因，给出恢复建议并准备审批执行计划。",
            })

        return rules

    @classmethod
    def _find_open_alert(cls, db: Session, host_id: str, rule_key: str) -> Optional[AlertEvent]:
        return db.query(AlertEvent).filter(
            AlertEvent.host_id == host_id,
            AlertEvent.rule_key == rule_key,
            AlertEvent.status == "unresolved",
        ).order_by(AlertEvent.created_at.desc()).first()

    @classmethod
    def upsert_alerts_from_rules_with_events(cls, db: Session, host_id: str, rules: List[Dict]) -> List[Dict]:
        events: List[Dict] = []
        changed: List[AlertEvent] = []
        now = cls._now()

        for rule in rules:
            existing = cls._find_open_alert(db, host_id=host_id, rule_key=rule["rule_key"])

            if rule.get("triggered"):
                if existing:
                    existing.level = rule["severity"]
                    existing.message = rule["message"]
                    existing.metric_name = rule["metric_name"]
                    existing.metric_value = float(rule["metric_value"])
                    existing.threshold = float(rule["threshold"])
                    existing.updated_at = now
                    changed.append(existing)
                    events.append({
                        "event": "triggered_update",
                        "alert": existing,
                        "rule": rule,
                    })
                    continue

                alert = AlertEvent(
                    id=str(uuid.uuid4()),
                    host_id=host_id,
                    source="self-monitor",
                    rule_key=rule["rule_key"],
                    level=rule["severity"],
                    title=rule["title"],
                    message=rule["message"],
                    metric_name=rule["metric_name"],
                    metric_value=float(rule["metric_value"]),
                    threshold=float(rule["threshold"]),
                    status="unresolved",
                    agent_approval_status="pending",
                    suggested_task_text=rule.get("task_text", ""),
                    refined_task_text="",
                    linked_task_id="",
                    approved_by="",
                    resolved_by="",
                    created_at=now,
                    updated_at=now,
                )
                db.add(alert)
                changed.append(alert)
                events.append({
                    "event": "triggered_new",
                    "alert": alert,
                    "rule": rule,
                })
            else:
                if existing:
                    existing.status = "resolved"
                    existing.resolved_at = now
                    existing.updated_at = now
                    if existing.agent_approval_status == "pending":
                        existing.agent_approval_status = "rejected"
                    changed.append(existing)
                    events.append({
                        "event": "resolved_auto",
                        "alert": existing,
                        "rule": rule,
                    })

        db.commit()
        return events

    @classmethod
    def upsert_alerts_from_rules(cls, db: Session, host_id: str, rules: List[Dict]) -> List[AlertEvent]:
        events = cls.upsert_alerts_from_rules_with_events(db=db, host_id=host_id, rules=rules)
        return [e["alert"] for e in events]

    @classmethod
    def list_alerts(
        cls,
        db: Session,
        level: Optional[str] = None,
        status: Optional[str] = None,
        agent_approval_status: Optional[str] = None,
    ) -> List[AlertEvent]:
        q = db.query(AlertEvent)
        if level:
            q = q.filter(AlertEvent.level == level)
        if status:
            q = q.filter(AlertEvent.status == status)
        if agent_approval_status:
            q = q.filter(AlertEvent.agent_approval_status == agent_approval_status)
        return q.order_by(AlertEvent.created_at.desc()).all()
