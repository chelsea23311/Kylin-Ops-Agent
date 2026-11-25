import uuid
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api import deps
from app.models.alert_event import AlertEvent
from app.models.audit import AuditLog
from app.models.task import TaskRecord
from app.models.user import User
from app.schemas.aiops import AlertApprovePayload, AlertResolvePayload
from app.services.alert_center import AlertCenter
from app.services.ml_service import MLService
from app.services.monitor_center import MonitorCenter
from app.services.orchestrator import Orchestrator

router = APIRouter()

def _now() -> datetime:
    return datetime.now()


def _upsert_single_alert_audit(
    db: Session,
    *,
    alert: AlertEvent,
    operator: str,
    action: str,
    risk_score: float,
    extra: Dict[str, Any] | None = None,
):
    # 每个告警事件（alert.id）仅维护一条审计日志记录。
    row = db.query(AuditLog).filter(
        AuditLog.task_id == alert.id,
        AuditLog.command == "ALERT_EVENT",
    ).first()

    payload = {
        "scope": "aiops_alert",
        "alert_id": alert.id,
        "host_id": alert.host_id,
        "rule_key": alert.rule_key,
        "level": alert.level,
        "status": alert.status,
        "agent_approval_status": alert.agent_approval_status,
        "title": alert.title,
        "message": alert.message,
        "metric_name": alert.metric_name,
        "metric_value": alert.metric_value,
        "threshold": alert.threshold,
        "linked_task_id": alert.linked_task_id,
        "last_action": action,
        "extra": extra or {},
    }

    if row:
        row.operator = operator
        row.risk_score = float(risk_score or 0.0)
        row.full_context = payload
        return

    db.add(AuditLog(
        task_id=alert.id,
        operator=operator,
        command="ALERT_EVENT",
        risk_score=float(risk_score or 0.0),
        full_context=payload,
    ))


async def _polish_alert_prompt(alert: AlertEvent) -> str:
    system_prompt = (
        "你是智能运维任务改写助手。"
        "请将告警内容改写成可执行、边界清晰、低风险优先的运维任务提示词。"
        "要求输出 JSON："
        "{\"refined_task_text\":\"...\",\"reason\":\"...\"}。"
        "任务文本要求："
        "1) 明确先排查再变更；2) 优先只读命令收集证据；"
        "3) 涉及变更时要强调审批和可回滚；4) 中文简洁。"
    )
    user_prompt = (
        f"alert_title: {alert.title}\n"
        f"alert_level: {alert.level}\n"
        f"alert_message: {alert.message}\n"
        f"suggested_task_text: {alert.suggested_task_text}"
    )
    llm_res = await MLService.call_llm(system_prompt=system_prompt, user_prompt=user_prompt)
    if not isinstance(llm_res, dict):
        return alert.suggested_task_text or f"请处理告警：{alert.title}，并给出可审计的修复方案。"

    refined = str(llm_res.get("refined_task_text") or "").strip()
    if not refined:
        return alert.suggested_task_text or f"请处理告警：{alert.title}，并给出可审计的修复方案。"
    return refined


@router.get("/overview", response_model=Dict[str, Any])
async def get_overview(
    auto_trigger: bool = Query(True, description="是否在查看总览时自动评估并触发告警"),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    snapshot = MonitorCenter.capture_snapshot()
    rules = AlertCenter.evaluate_rules(snapshot)

    if auto_trigger and current_user.role in ["admin", "operator"]:
        events = AlertCenter.upsert_alerts_from_rules_with_events(db=db, host_id="host_prod_01", rules=rules)
        for item in events:
            alert = item.get("alert")
            if not isinstance(alert, AlertEvent):
                continue
            if str(item.get("event")) != "triggered_new":
                continue
            rule = item.get("rule") or {}
            _upsert_single_alert_audit(
                db,
                alert=alert,
                operator="system:auto-monitor",
                action="triggered_new",
                risk_score=float(rule.get("metric_value") or 0.0),
                extra={"source_api": "GET /api/v1/aiops/overview", "auto_trigger": True},
            )
        db.commit()

    return {
        **snapshot,
        "auto_rules": [
            {
                "rule_key": r["rule_key"],
                "triggered": bool(r["triggered"]),
                "severity": r["severity"],
                "message": r["message"],
            }
            for r in rules
        ],
    }


@router.post("/alerts/evaluate", response_model=Dict[str, Any])
async def evaluate_alert_rules(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="权限不足")

    snapshot = MonitorCenter.capture_snapshot()
    rules = AlertCenter.evaluate_rules(snapshot)
    events = AlertCenter.upsert_alerts_from_rules_with_events(db=db, host_id="host_prod_01", rules=rules)
    for item in events:
        alert = item.get("alert")
        if not isinstance(alert, AlertEvent):
            continue
        if str(item.get("event")) != "triggered_new":
            continue
        rule = item.get("rule") or {}
        _upsert_single_alert_audit(
            db,
            alert=alert,
            operator=current_user.username,
            action="triggered_new",
            risk_score=float(rule.get("metric_value") or 0.0),
            extra={"source_api": "POST /api/v1/aiops/alerts/evaluate", "manual": True},
        )
    db.commit()
    changed = [item.get("alert") for item in events if isinstance(item.get("alert"), AlertEvent)]

    return {
        "status": "success",
        "changed_count": len(changed),
        "changed_alert_ids": [a.id for a in changed],
        "rules": rules,
    }


@router.get("/alerts", response_model=List[Dict[str, Any]])
async def list_alerts(
    level: str | None = Query(default=None, description="critical|warning|info"),
    status: str | None = Query(default=None, description="unresolved|resolved"),
    agent_approval_status: str | None = Query(default=None, description="pending|approved|rejected"),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    _ = current_user
    alerts = AlertCenter.list_alerts(
        db=db,
        level=level,
        status=status,
        agent_approval_status=agent_approval_status,
    )

    result = []
    for a in alerts:
        linked_task_status = None
        if a.linked_task_id:
            task = db.query(TaskRecord).filter(TaskRecord.id == a.linked_task_id).first()
            linked_task_status = task.status if task else None

        result.append({
            "id": a.id,
            "host_id": a.host_id,
            "source": a.source,
            "rule_key": a.rule_key,
            "level": a.level,
            "title": a.title,
            "message": a.message,
            "metric_name": a.metric_name,
            "metric_value": a.metric_value,
            "threshold": a.threshold,
            "status": a.status,
            "agent_approval_status": a.agent_approval_status,
            "suggested_task_text": a.suggested_task_text,
            "refined_task_text": a.refined_task_text,
            "linked_task_id": a.linked_task_id,
            "linked_task_status": linked_task_status,
            "approved_by": a.approved_by,
            "resolved_by": a.resolved_by,
            "created_at": a.created_at,
            "updated_at": a.updated_at,
            "resolved_at": a.resolved_at,
        })
    return result


@router.post("/alerts/{alert_id}/approve-agent", response_model=Dict[str, Any])
async def approve_agent_execution(
    alert_id: str,
    payload: AlertApprovePayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    if current_user.role != "operator":
        raise HTTPException(status_code=403, detail="仅 operator 可批准‘由 Agent 接手告警’；admin 仅在任务审批页批准具体执行命令")

    alert = db.query(AlertEvent).filter(AlertEvent.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")

    if alert.status == "resolved":
        raise HTTPException(status_code=400, detail="告警已恢复，无需审批执行")

    if not payload.approved:
        alert.agent_approval_status = "rejected"
        alert.updated_at = _now()
        _upsert_single_alert_audit(
            db,
            alert=alert,
            operator=current_user.username,
            action="agent_takeover_rejected_by_operator",
            risk_score=float(alert.metric_value or 0.0),
            extra={"source_api": "POST /api/v1/aiops/alerts/{alert_id}/approve-agent"},
        )
        db.commit()
        return {
            "status": "success",
            "agent_approval_status": "rejected",
            "message": "已拒绝 AI Agent 执行",
        }

    refined_text = await _polish_alert_prompt(alert)
    alert.refined_task_text = refined_text
    alert.agent_approval_status = "approved"
    alert.approved_by = current_user.username
    alert.updated_at = _now()

    task_id = str(uuid.uuid4())
    alert.linked_task_id = task_id
    _upsert_single_alert_audit(
        db,
        alert=alert,
        operator=current_user.username,
        action="agent_takeover_approved_by_operator",
        risk_score=float(alert.metric_value or 0.0),
        extra={
            "source_api": "POST /api/v1/aiops/alerts/{alert_id}/approve-agent",
            "refined_task_text": refined_text,
        },
    )
    db.commit()

    orchestrator = Orchestrator(
        task_id=task_id,
        user_id=str(current_user.id),
        task_text=refined_text,
        db=db,
        host_id=alert.host_id or "host_prod_01",
        current_user_role=current_user.role,
    )
    background_tasks.add_task(orchestrator.run)

    return {
        "status": "success",
        "agent_approval_status": "approved",
        "linked_task_id": task_id,
        "task_status": "running",
        "refined_task_text": refined_text,
        "message": "已进入 Agent 流程（含告警润色层 -> 感知层 -> 后续13步）",
    }


@router.post("/alerts/{alert_id}/rerun-agent", response_model=Dict[str, Any])
async def rerun_agent_execution(
    alert_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    if current_user.role != "operator":
        raise HTTPException(status_code=403, detail="仅 operator 可重新执行告警 Agent 任务")

    alert = db.query(AlertEvent).filter(AlertEvent.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")
    if alert.status == "resolved":
        raise HTTPException(status_code=400, detail="告警已恢复，无需重新执行")
    if alert.agent_approval_status != "approved":
        raise HTTPException(status_code=400, detail="只有已批准接手的告警任务可重新执行")

    previous_task_id = alert.linked_task_id or ""
    previous_task = db.query(TaskRecord).filter(TaskRecord.id == previous_task_id).first() if previous_task_id else None
    if previous_task and previous_task.status not in ["failed", "blocked", "rejected"]:
        raise HTTPException(status_code=400, detail="当前关联任务尚未失败，不能重复执行")

    refined_text = alert.refined_task_text or alert.suggested_task_text or await _polish_alert_prompt(alert)
    if not refined_text:
        refined_text = f"请重新排查告警：{alert.title}，优先只读收集证据，再给出可审计的处理方案。"

    task_id = str(uuid.uuid4())
    alert.linked_task_id = task_id
    alert.refined_task_text = refined_text
    alert.updated_at = _now()
    _upsert_single_alert_audit(
        db,
        alert=alert,
        operator=current_user.username,
        action="agent_takeover_rerun_by_operator",
        risk_score=float(alert.metric_value or 0.0),
        extra={
            "source_api": "POST /api/v1/aiops/alerts/{alert_id}/rerun-agent",
            "previous_task_id": previous_task_id,
            "previous_task_status": previous_task.status if previous_task else None,
            "refined_task_text": refined_text,
        },
    )
    db.commit()

    orchestrator = Orchestrator(
        task_id=task_id,
        user_id=str(current_user.id),
        task_text=refined_text,
        db=db,
        host_id=alert.host_id or "host_prod_01",
        current_user_role=current_user.role,
    )
    background_tasks.add_task(orchestrator.run)

    return {
        "status": "success",
        "agent_approval_status": alert.agent_approval_status,
        "linked_task_id": task_id,
        "previous_task_id": previous_task_id,
        "task_status": "running",
        "refined_task_text": refined_text,
        "message": "失败告警任务已重新进入 Agent 流程",
    }


@router.post("/alerts/{alert_id}/resolve", response_model=Dict[str, Any])
async def resolve_alert(
    alert_id: str,
    payload: AlertResolvePayload,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="权限不足")

    alert = db.query(AlertEvent).filter(AlertEvent.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")

    if payload.resolve:
        alert.status = "resolved"
        alert.resolved_by = current_user.username
        alert.resolved_at = _now()
        if alert.agent_approval_status == "pending":
            alert.agent_approval_status = "rejected"
    else:
        alert.status = "unresolved"

    alert.updated_at = _now()
    _upsert_single_alert_audit(
        db,
        alert=alert,
        operator=current_user.username,
        action="manual_resolve" if payload.resolve else "reopen",
        risk_score=float(alert.metric_value or 0.0),
        extra={"source_api": "POST /api/v1/aiops/alerts/{alert_id}/resolve"},
    )
    db.commit()

    return {
        "status": "success",
        "alert_id": alert_id,
        "new_status": alert.status,
        "agent_approval_status": alert.agent_approval_status,
    }


@router.get("/alerts/{alert_id}", response_model=Dict[str, Any])
async def get_alert_detail(
    alert_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    _ = current_user
    alert = db.query(AlertEvent).filter(AlertEvent.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")

    task_detail = None
    if alert.linked_task_id:
        task = db.query(TaskRecord).filter(TaskRecord.id == alert.linked_task_id).first()
        if task:
            task_detail = {
                "task_id": task.id,
                "status": task.status,
                "task_text": task.task_text,
                "created_at": task.created_at,
            }

    return {
        "id": alert.id,
        "host_id": alert.host_id,
        "source": alert.source,
        "rule_key": alert.rule_key,
        "level": alert.level,
        "title": alert.title,
        "message": alert.message,
        "metric_name": alert.metric_name,
        "metric_value": alert.metric_value,
        "threshold": alert.threshold,
        "status": alert.status,
        "agent_approval_status": alert.agent_approval_status,
        "suggested_task_text": alert.suggested_task_text,
        "refined_task_text": alert.refined_task_text,
        "linked_task_id": alert.linked_task_id,
        "approved_by": alert.approved_by,
        "resolved_by": alert.resolved_by,
        "created_at": alert.created_at,
        "updated_at": alert.updated_at,
        "resolved_at": alert.resolved_at,
        "linked_task": task_detail,
    }
