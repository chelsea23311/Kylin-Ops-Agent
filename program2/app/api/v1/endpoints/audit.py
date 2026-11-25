from datetime import datetime
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from app.api import deps
from app.core import security
from app.core.config import settings
from app.models.notification_message import NotificationMessage
from app.models.personnel_profile import PersonnelProfile
from app.models.security_setting import SecuritySetting
from app.models.task import TaskRecord
from app.models.user import User

router = APIRouter()


AVATAR_POOL = ["#006591", "#505f76", "#8a5100", "#0ea5e9", "#ba1a1a", "#003751"]
ROLE_POSITION_MAP = {
    "admin": "高级运维工程师",
    "operator": "运维工程师",
    "auditor": "安全审计员",
    "user": "平台用户",
}
STATUS_LABELS = {
    "success": "执行成功",
    "blocked": "护栏拦截",
    "failed": "执行失败",
    "rejected": "审批拒绝",
    "awaiting_approval": "等待审批",
    "approved": "审批通过",
    "running": "执行中",
}
MESSAGE_CATEGORY_LABELS = {
    "notification": "系统通知",
    "warning": "安全警告",
    "task": "任务提醒",
    "announcement": "公告通知",
}
MAX_FILE_READ_BYTES = 1024 * 1024


class FilePathPayload(BaseModel):
    path: str


class FileWritePayload(FilePathPayload):
    content: str


def _now() -> datetime:
    return datetime.now()


def _mask_phone(raw: str) -> str:
    digits = "".join(ch for ch in str(raw or "") if ch.isdigit())
    if len(digits) != 11:
        return str(raw or "")
    return f"{digits[:3]}****{digits[-4:]}"


def _format_dt(dt: datetime | None) -> str:
    if not dt:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M")


def _default_profile_values(user: User) -> Dict[str, str]:
    idx = int(user.id) if str(user.id).isdigit() else 0
    username = (user.username or f"user{user.id}").strip() or f"user{user.id}"
    return {
        "full_name": username,
        "department": "",
        "position": ROLE_POSITION_MAP.get(user.role, "平台用户"),
        "phone": "",
        "email": "",
        "join_date": "",
        "avatar_color": AVATAR_POOL[idx % len(AVATAR_POOL)],
    }


def _ensure_profile(db: Session, user: User) -> PersonnelProfile:
    profile = db.query(PersonnelProfile).filter(PersonnelProfile.user_id == str(user.id)).first()
    if profile:
        return profile

    defaults = _default_profile_values(user)
    profile = PersonnelProfile(user_id=str(user.id), **defaults)
    db.add(profile)
    db.flush()
    return profile


def _ensure_security_setting(db: Session, user: User) -> SecuritySetting:
    row = db.query(SecuritySetting).filter(SecuritySetting.user_id == str(user.id)).first()
    if row:
        return row

    profile = _ensure_profile(db, user)
    row = SecuritySetting(
        user_id=str(user.id),
        phone_number=profile.phone,
        phone_verified=False,
        two_factor_enabled=False,
    )
    db.add(row)
    db.flush()
    return row


def _approval_attempt_count(task: TaskRecord) -> int:
    ctx = task.context_data or {}
    payload = ctx.get("step9_approval_payload") or {}
    options = payload.get("command_options") or []
    return sum(1 for item in options if isinstance(item, dict))


def _risk_analysis_text(attempts: int) -> str:
    if attempts > 10:
        return "高危指令尝试频率明显偏高，已超过日常运维基线，建议限制生产变更权限并安排专项复核。"
    return "高危指令尝试次数处于可控范围，当前行为更接近正常排障与审批流使用习惯。"


def _task_risk_score(task: TaskRecord) -> float:
    ctx = task.context_data or {}
    step7 = ctx.get("step7_risk_audit") or {}
    try:
        return float(step7.get("total_risk") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _recent_commands_for_user(tasks: List[TaskRecord]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for task in tasks:
        ctx = task.context_data or {}
        step11 = ctx.get("step11_audit") or {}
        raw_log = step11.get("raw_log") or {}
        commands = raw_log.get("commands") or []
        task_risk_score = _task_risk_score(task)
        for idx, cmd in enumerate(commands):
            if not isinstance(cmd, dict):
                continue
            status = str(cmd.get("status") or task.status or "unknown")
            rows.append({
                "id": f"{task.id}-{idx}",
                "task_id": task.id,
                "description": task.task_text,
                "command": cmd.get("command") or "",
                "tool": cmd.get("tool") or "",
                "risk_level": "high" if task_risk_score > settings.RISK_APPROVAL_THRESHOLD else "medium",
                "status": status,
                "status_label": STATUS_LABELS.get(status, status),
                "time": _format_dt(task.created_at),
            })
    return rows[:20]


def _serialize_personnel_summary(db: Session, user: User) -> Dict[str, Any]:
    profile = _ensure_profile(db, user)
    tasks = db.query(TaskRecord).filter(TaskRecord.user_id == str(user.id)).order_by(desc(TaskRecord.created_at)).all()
    attempt_count = sum(_approval_attempt_count(task) for task in tasks)
    risk_score = min(1.0, round(attempt_count / 20, 2))
    is_admin = user.role == "admin"
    return {
        "id": str(user.id),
        "employee_id": str(user.id),
        "username": user.username,
        "name": profile.full_name,
        "department": profile.department,
        "position": profile.position,
        "phone": _mask_phone(profile.phone),
        "phone_raw": profile.phone,
        "email": profile.email,
        "join_date": profile.join_date,
        "avatar_color": profile.avatar_color,
        "role": user.role,
        "role_label": "高级运维人员" if is_admin else ("普通运维人员" if user.role == "operator" else ROLE_POSITION_MAP.get(user.role, user.role)),
        "is_admin": is_admin,
        "high_risk_count": attempt_count,
        "risk_score": risk_score,
        "risk_status": "risk" if attempt_count > 10 else "normal",
        "risk_rating": "高风险" if attempt_count > 10 else "低风险",
        "risk_analysis": _risk_analysis_text(attempt_count),
    }


def _serialize_personnel_detail(db: Session, user: User) -> Dict[str, Any]:
    summary = _serialize_personnel_summary(db, user)
    tasks = db.query(TaskRecord).filter(TaskRecord.user_id == str(user.id)).order_by(desc(TaskRecord.created_at)).limit(30).all()
    summary["recent_commands"] = _recent_commands_for_user(tasks)
    return summary


def _message_receiver_label(db: Session, recipient_user_id: str) -> str:
    user = db.query(User).filter(or_(User.id == recipient_user_id, User.username == recipient_user_id)).first()
    if not user:
        return recipient_user_id
    profile = _ensure_profile(db, user)
    return profile.full_name


def _resolve_message_recipient(db: Session, recipient_key: str) -> User | None:
    key = str(recipient_key or "").strip()
    if not key:
        return None
    return db.query(User).filter(or_(User.id == key, User.username == key)).first()


def _serialize_message(db: Session, row: NotificationMessage) -> Dict[str, Any]:
    recipient = _resolve_message_recipient(db, row.recipient_user_id)
    profile = _ensure_profile(db, recipient) if recipient else None
    return {
        "id": row.id,
        "recipient_user_id": row.recipient_user_id,
        "receiver": row.receiver_label,
        "avatar_color": profile.avatar_color if profile else "#006591",
        "category": row.category,
        "category_label": MESSAGE_CATEGORY_LABELS.get(row.category, row.category),
        "content": row.content,
        "status": row.status,
        "status_label": {"sent": "已发送", "scheduled": "定时发送", "failed": "发送失败"}.get(row.status, row.status),
        "send_time": _format_dt(row.scheduled_for or row.sent_at or row.created_at),
        "is_read": bool(row.is_read),
        "created_at": _format_dt(row.created_at),
    }


def _require_auditor(current_user: User) -> None:
    if current_user.role not in ["auditor", "admin"]:
        raise HTTPException(status_code=403, detail="权限不足，只有审计员或管理员可以访问此接口")


def _require_file_manager_user(current_user: User) -> None:
    if current_user.role not in ["operator", "admin"]:
        raise HTTPException(status_code=403, detail="仅运维人员可访问文件管理")


def _resolve_existing_path(path: str) -> Path:
    target = Path(path).expanduser()
    try:
        return target.resolve(strict=True)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="路径不存在") from exc


@router.get("/logs")
def get_audit_logs(
    limit: int = Query(50, ge=1, le=200, description="返回记录数量"),
    status: Optional[str] = Query(None, description="按任务状态过滤，如 rejected, done"),
    user_id: Optional[str] = Query(None, description="按操作人ID过滤"),
    db: Session = Depends(deps.get_db),
    current_auditor: User = Depends(deps.get_current_auditor),
):
    _ = current_auditor
    query = db.query(TaskRecord)

    if status:
        query = query.filter(TaskRecord.status == status)
    if user_id:
        query = query.filter(TaskRecord.user_id == user_id)

    records = query.order_by(desc(TaskRecord.created_at)).limit(limit).all()
    audit_results = []
    for r in records:
        ctx = r.context_data or {}
        rejection_reason = None
        if r.status == "rejected" and "step11_audit" in ctx:
            rejection_reason = ctx["step11_audit"].get("raw_log", {}).get("description")

        approval_log = ctx.get("approval_log")
        audit_results.append({
            "task_id": r.id,
            "user_id": r.user_id,
            "host_id": r.host_id,
            "task_text": r.task_text,
            "status": r.status,
            "created_at": r.created_at,
            "rejection_reason": rejection_reason,
            "approval_info": approval_log,
        })

    return audit_results


@router.get("/logs/{task_id}/details")
def get_audit_log_details(
    task_id: str,
    db: Session = Depends(deps.get_db),
    current_auditor: User = Depends(deps.get_current_auditor),
):
    _ = current_auditor
    task = db.query(TaskRecord).filter(TaskRecord.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="找不到该任务记录")

    return {
        "task_id": task.id,
        "user_id": task.user_id,
        "task_text": task.task_text,
        "status": task.status,
        "created_at": task.created_at,
        "full_context": task.context_data,
    }


@router.get("/personnel")
def list_personnel(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    _require_auditor(current_user)
    users = db.query(User).order_by(User.id.asc()).all()
    rows = []
    for user in users:
        profile = _ensure_profile(db, user)
        if profile.is_deleted:
            continue
        rows.append(_serialize_personnel_summary(db, user))
    db.commit()
    return rows


@router.get("/personnel/{user_id}")
def get_personnel_detail(
    user_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    _require_auditor(current_user)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="人员不存在")
    detail = _serialize_personnel_detail(db, user)
    db.commit()
    return detail


@router.put("/personnel/{user_id}")
def update_personnel(
    user_id: str,
    payload: Dict[str, Any],
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    _require_auditor(current_user)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="人员不存在")

    profile = _ensure_profile(db, user)
    editable_fields = {
        "name": "full_name",
        "department": "department",
        "position": "position",
        "phone": "phone",
        "email": "email",
        "join_date": "join_date",
    }
    for src, dst in editable_fields.items():
        if src in payload and str(payload[src]).strip():
            setattr(profile, dst, str(payload[src]).strip())

    new_role = str(payload.get("role") or user.role).strip().lower()
    if new_role not in ["operator", "admin", "auditor", "user"]:
        raise HTTPException(status_code=400, detail="不支持的角色")
    user.role = new_role
    if new_role in ROLE_POSITION_MAP and ("position" not in payload or not str(payload.get("position") or "").strip()):
        profile.position = ROLE_POSITION_MAP[new_role]

    db.commit()
    return _serialize_personnel_detail(db, user)


@router.delete("/personnel/{user_id}")
def delete_personnel(
    user_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    _require_auditor(current_user)
    if str(current_user.id) == str(user_id):
        raise HTTPException(status_code=400, detail="不能删除当前登录账号")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="人员不存在")

    profile = _ensure_profile(db, user)
    profile.is_deleted = True
    db.commit()
    return {"status": "success"}


@router.get("/security-settings")
def get_security_settings(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    _require_auditor(current_user)
    setting = _ensure_security_setting(db, current_user)
    db.commit()
    return {
        "two_factor_enabled": False,
        "two_factor_available": False,
        "phone_number": setting.phone_number,
        "phone_verified": False,
        "password_updated_at": _format_dt(setting.password_updated_at),
        "last_code_sent_at": _format_dt(setting.last_code_sent_at),
    }


@router.post("/security-settings/send-code")
def send_security_code(
    payload: Dict[str, Any],
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    _require_auditor(current_user)
    raise HTTPException(status_code=501, detail="尚未接入短信服务，暂不支持发送验证码")


@router.put("/security-settings")
def update_security_settings(
    payload: Dict[str, Any],
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    _require_auditor(current_user)
    if payload.get("two_factor_enabled"):
        raise HTTPException(status_code=501, detail="尚未接入短信验证与登录校验，暂不支持双重验证")
    setting = _ensure_security_setting(db, current_user)

    current_password = str(payload.get("current_password") or "")
    new_password = str(payload.get("new_password") or "")
    confirm_password = str(payload.get("confirm_password") or "")

    if new_password or confirm_password or current_password:
        if not security.verify_password(current_password, current_user.hashed_password):
            raise HTTPException(status_code=400, detail="当前密钥不正确")
        if len(new_password) < 8:
            raise HTTPException(status_code=400, detail="新密钥长度不能少于 8 位")
        if new_password != confirm_password:
            raise HTTPException(status_code=400, detail="两次输入的新密钥不一致")
        current_user.hashed_password = security.get_password_hash(new_password)
        setting.password_updated_at = _now()

    phone_number = str(payload.get("phone_number") or setting.phone_number or "").strip()
    setting.two_factor_enabled = False
    setting.phone_verified = False
    if phone_number:
        setting.phone_number = phone_number

    db.commit()
    return {
        "status": "success",
        "two_factor_enabled": setting.two_factor_enabled,
        "phone_number": setting.phone_number,
        "phone_verified": setting.phone_verified,
    }


@router.get("/messages")
def list_messages(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    _require_auditor(current_user)
    rows = db.query(NotificationMessage).order_by(NotificationMessage.created_at.desc()).all()
    return [_serialize_message(db, row) for row in rows]


@router.post("/messages")
def create_message(
    payload: Dict[str, Any],
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    _require_auditor(current_user)

    recipient_user_id = str(payload.get("recipient_user_id") or "").strip()
    category = str(payload.get("category") or "").strip() or "notification"
    content = str(payload.get("content") or "").strip()
    schedule_time_raw = str(payload.get("schedule_time") or "").strip()

    if not recipient_user_id or not content:
        raise HTTPException(status_code=400, detail="接收人和消息内容不能为空")

    recipient = _resolve_message_recipient(db, recipient_user_id)
    if not recipient:
        raise HTTPException(status_code=404, detail="接收人员不存在")
    recipient_user_id = str(recipient.id)

    scheduled_for = None
    status = "sent"
    sent_at = _now()
    if schedule_time_raw:
        try:
            scheduled_for = datetime.fromisoformat(schedule_time_raw)
            status = "scheduled"
            sent_at = None
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="定时时间格式错误") from exc

    row = NotificationMessage(
        recipient_user_id=recipient_user_id,
        sender_user_id=str(current_user.id),
        receiver_label=_message_receiver_label(db, recipient_user_id),
        category=category,
        content=content,
        status=status,
        scheduled_for=scheduled_for,
        sent_at=sent_at,
        is_read=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize_message(db, row)


@router.delete("/messages/{message_id}")
def delete_message(
    message_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    _require_auditor(current_user)
    row = db.query(NotificationMessage).filter(NotificationMessage.id == message_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="消息不存在")
    db.delete(row)
    db.commit()
    return {"status": "success"}


@router.get("/messages/inbox")
def get_my_inbox(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    rows = db.query(NotificationMessage).filter(
        or_(
            NotificationMessage.recipient_user_id == str(current_user.id),
            NotificationMessage.recipient_user_id == current_user.username,
        )
    ).order_by(desc(NotificationMessage.created_at)).limit(20).all()
    items = [_serialize_message(db, row) for row in rows]
    unread_count = sum(1 for item in items if not item["is_read"])
    return {"unread_count": unread_count, "items": items}


@router.post("/messages/inbox/{message_id}/read")
def mark_inbox_message_read(
    message_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    row = db.query(NotificationMessage).filter(
        NotificationMessage.id == message_id,
        or_(
            NotificationMessage.recipient_user_id == str(current_user.id),
            NotificationMessage.recipient_user_id == current_user.username,
        ),
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="消息不存在")
    row.is_read = True
    row.read_at = _now()
    db.commit()
    return {"status": "success"}


@router.get("/files/list")
def list_server_files(
    path: str = Query(str(Path(__file__).resolve().parents[4]), description="需要浏览的目录路径"),
    current_user: User = Depends(deps.get_current_user),
):
    _require_file_manager_user(current_user)

    resolved = _resolve_existing_path(path)

    if not resolved.is_dir():
        raise HTTPException(status_code=400, detail="目标路径不是目录")

    try:
        entries = []
        for item in sorted(resolved.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            stat = item.stat()
            entries.append({
                "name": item.name,
                "is_dir": item.is_dir(),
                "size_bytes": 0 if item.is_dir() else stat.st_size,
                "size_display": "" if item.is_dir() else _human_size(stat.st_size),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "permission": _permission_string(stat.st_mode, item.is_dir()),
                "access": _access_flags(item),
            })
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="没有权限读取该目录") from exc

    return {"current_path": str(resolved), "entries": entries}


@router.post("/files/read")
def read_server_file(
    payload: FilePathPayload,
    current_user: User = Depends(deps.get_current_user),
):
    _require_file_manager_user(current_user)

    resolved = _resolve_existing_path(payload.path)
    if resolved.is_dir():
        raise HTTPException(status_code=400, detail="目录不能直接读取，请进入目录查看")

    try:
        with resolved.open("rb") as fh:
            raw = fh.read(MAX_FILE_READ_BYTES + 1)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="没有权限读取该文件") from exc

    truncated = len(raw) > MAX_FILE_READ_BYTES
    if truncated:
        raw = raw[:MAX_FILE_READ_BYTES]

    return {
        "path": str(resolved),
        "name": resolved.name,
        "content": raw.decode("utf-8", errors="replace"),
        "truncated": truncated,
    }


@router.post("/files/write")
def write_server_file(
    payload: FileWritePayload,
    current_user: User = Depends(deps.get_current_user),
):
    _require_file_manager_user(current_user)

    resolved = _resolve_existing_path(payload.path)
    if resolved.is_dir():
        raise HTTPException(status_code=400, detail="目录不能编辑内容")

    try:
        resolved.write_text(payload.content, encoding="utf-8")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="没有权限修改该文件") from exc

    return {"status": "success", "path": str(resolved)}


@router.post("/files/delete")
def delete_server_file(
    payload: FilePathPayload,
    current_user: User = Depends(deps.get_current_user),
):
    _require_file_manager_user(current_user)

    resolved = _resolve_existing_path(payload.path)
    try:
        if resolved.is_dir():
            resolved.rmdir()
        else:
            resolved.unlink()
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="没有权限删除该条目") from exc
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"删除失败：{exc}") from exc

    return {"status": "success", "path": str(resolved)}


def _human_size(size_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(size_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size_bytes} B"


def _permission_string(mode: int, is_dir: bool) -> str:
    import stat

    chars = ["d" if is_dir else "-"]
    perms = [
        (stat.S_IRUSR, "r"), (stat.S_IWUSR, "w"), (stat.S_IXUSR, "x"),
        (stat.S_IRGRP, "r"), (stat.S_IWGRP, "w"), (stat.S_IXGRP, "x"),
        (stat.S_IROTH, "r"), (stat.S_IWOTH, "w"), (stat.S_IXOTH, "x"),
    ]
    for bit, label in perms:
        chars.append(label if mode & bit else "-")
    return "".join(chars)


def _access_flags(path: Path) -> Dict[str, bool]:
    parent = path.parent
    return {
        "read": os.access(path, os.R_OK),
        "write": path.is_file() and os.access(path, os.W_OK),
        "delete": os.access(parent, os.W_OK),
    }
