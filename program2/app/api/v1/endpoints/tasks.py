# app/api/v1/endpoints/tasks.py
import uuid
import asyncio
import os
import re
from datetime import datetime
from typing import Dict, Any, List
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.api import deps
from app.core.config import settings
from app.models.task import TaskRecord
from app.models.user import User
from app.schemas.task import TaskCreate, ApprovalActionPayload, RollbackActionPayload
from app.services.orchestrator import Orchestrator
from app.services.mcp_tools import KylinMCP

router = APIRouter()


# ==========================================
# 接口 1：下发指令
# ==========================================
@router.post("/run", response_model=Dict[str, Any])
async def create_agent_task(
        task_in: TaskCreate,
        background_tasks: BackgroundTasks,
        db: Session = Depends(deps.get_db),
        current_user=Depends(deps.get_current_user)
):
    if current_user.role not in ["operator", "admin"]:
        raise HTTPException(status_code=403, detail="权限不足，无法发起运维任务")
    task_id = str(uuid.uuid4())
    orchestrator = Orchestrator(
        task_id=task_id,
        user_id=str(current_user.id),
        task_text=task_in.task_text,
        db=db,
        host_id="host_prod_01",
        current_user_role=current_user.role
    )
    background_tasks.add_task(orchestrator.run)
    return {
        "task_id": task_id,
        "status": "running",
        "message": "任务已启动，请通过 GET /tasks/status/{task_id} 轮询获取各步骤实时数据"
    }


# ==========================================
# 接口 2：获取任务详情/轮询状态
# ==========================================
@router.get("/status/{task_id}", response_model=Dict[str, Any])
async def get_task_status(
        task_id: uuid.UUID,
        db: Session = Depends(deps.get_db),
        current_user=Depends(deps.get_current_user)
):
    task = db.query(TaskRecord).filter(TaskRecord.id == str(task_id)).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 任务可见性隔离：
    # - operator 只能查看自己发起的任务
    # - admin / auditor 保留全局查看权限（用于审批与审计）
    if current_user.role == "operator" and str(task.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="无权查看该任务")

    return {
        "task_id": task.id,
        "status": task.status,
        "context_data": task.context_data,
        "history": (task.context_data or {}).get("history", [])
    }


# --- 审计模块开始 ---

@router.get("/audit/all-tasks")
def get_all_tasks_for_audit(
        db: Session = Depends(deps.get_db),
        current_user: User = Depends(deps.get_current_user),
        skip: int = 0,
        limit: int = 100
):
    if current_user.role not in ["admin", "auditor", "operator"]:
        raise HTTPException(status_code=403, detail="无权访问审计日志")
    query = db.query(TaskRecord)
    if current_user.role == "operator":
        query = query.filter(TaskRecord.user_id == str(current_user.id))
    tasks = query.order_by(TaskRecord.created_at.desc()).offset(skip).limit(limit).all()
    user_ids = {str(t.user_id) for t in tasks if t.user_id}
    users = db.query(User).filter(User.id.in_(user_ids)).all() if user_ids else []
    user_map = {str(u.id): u.username for u in users}
    return [{
        "task_id": t.id,
        "operator": user_map.get(str(t.user_id), t.user_id),
        "operator_user_id": t.user_id,
        "task_text": t.task_text,
        "status": t.status,
        "risk_score": t.context_data.get("step7_risk_audit", {}).get("total_risk", 0) if t.context_data else 0,
        "created_at": t.created_at
    } for t in tasks]


@router.get("/audit/full-trace/{task_id}")
def get_task_trace(
        task_id: str,
        db: Session = Depends(deps.get_db),
        current_user: User = Depends(deps.get_current_user)
):
    if current_user.role not in ["admin", "auditor", "operator"]:
        raise HTTPException(status_code=403, detail="无权查看溯源")
    task = db.query(TaskRecord).filter(TaskRecord.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if current_user.role == "operator" and str(task.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="无权查看该任务审计轨迹")
    context = task.context_data or {}
    step11 = context.get("step11_audit")
    if not step11:
        raise HTTPException(status_code=404, detail="该任务尚未完成审计落库（step11_audit 不存在）")
    return {
        "task_info": {
            "id": task.id,
            "operator": task.user_id,
            "status": task.status,
            "created_at": task.created_at
        },
        "step11_audit": step11,
        "step14_rollback_result": context.get("step14_rollback_result"),
    }

# --- 审计模块结束 ---


# ==========================================
# 接口 3a：获取待审批任务列表（管理员审批页面专用）
# ==========================================
@router.get("/pending-approvals", response_model=List[Dict[str, Any]])
def get_pending_approvals(
        db: Session = Depends(deps.get_db),
        current_user: User = Depends(deps.get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可查看待审批任务")
    tasks = db.query(TaskRecord).filter(
        TaskRecord.status == "awaiting_approval"
    ).order_by(TaskRecord.created_at.desc()).all()
    return [{
        "task_id": t.id,
        "operator": t.user_id,
        "task_text": t.task_text,
        "status": t.status,
        "created_at": t.created_at,
        "approval_payload": (t.context_data or {}).get("step9_approval_payload", {}),
    } for t in tasks]


# ==========================================
# 接口 3b：人工审批（管理员登录后操作，需要 JWT）
# ==========================================
@router.post("/{task_id}/approve")
async def approve_task(
        task_id: str,
        action: str,  # "approve" 或 "reject"
    payload: ApprovalActionPayload | None = Body(default=None),
        db: Session = Depends(deps.get_db),
        current_user: User = Depends(deps.get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可进行审批操作")

    task = db.query(TaskRecord).filter(TaskRecord.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    now_str = datetime.now().isoformat()
    selected_ids = (payload.selected_command_ids if payload else []) or []
    approval_info = {"action": action, "time": now_str, "selected_command_ids": selected_ids}
    ctx = dict(task.context_data)

    if action == "approve":
        existing_approval = ctx.get("approval_info") or {}
        if (
            task.status in {"approved", "success", "failed", "rejected"}
            or existing_approval.get("action") == "approve"
        ):
            return {
                "status": "success",
                "new_status": task.status,
                "detail": "already_processed",
            }

        command_options = (ctx.get("step9_approval_payload") or {}).get("command_options") or []
        if command_options and not selected_ids:
            raise HTTPException(status_code=400, detail="请至少勾选一条命令后再批准执行")

        task.status = "approved"
        ctx["approval_info"] = approval_info
        selected_count = len(selected_ids) if selected_ids else len(command_options)
        ctx.setdefault("history", []).append(
            f"[审批通过] 审计人员 {current_user.username} 批准了本次操作（命令数：{selected_count}），流程将自动恢复执行。"
        )
        task.context_data = ctx
        flag_modified(task, "context_data")
        db.commit()
        orchestrator = Orchestrator(
            task_id=str(task.id),
            user_id=str(task.user_id),
            task_text=str(task.task_text),
            db=db,
            host_id=str(task.host_id),
            current_user_role="admin",
        )
        await orchestrator.run()
        return {"status": "success", "new_status": "approved", "detail": "execution_started"}

    else:  # reject
        task.status = "rejected"
        ctx["approval_info"] = approval_info
        approval_payload = ctx.get("step9_approval_payload", {}) or {}
        command_options = approval_payload.get("command_options") or []
        rejected_commands = []
        for c in command_options:
            if not isinstance(c, dict):
                continue
            rejected_commands.append({
                "id": c.get("id"),
                "tool": c.get("tool"),
                "command": c.get("command"),
                "target": c.get("target"),
                "status": "rejected",
                "exit_code": None,
                "stdout_preview": "",
                "stderr": "审计人员拒绝，未执行",
            })
        ctx.setdefault("history", []).append(
            f"[审批拒绝] 审计人员 {current_user.username} 拒绝了本次操作，任务已终止。"
        )
        ctx["history"].append(
            f"[审计落库] 审批拒绝审计记录已写入数据库（用户：{task.user_id}，主机：{task.host_id}），最终状态：rejected。"
        )
        step7 = ctx.get("step7_risk_audit", {})
        reflection_ctx = ctx.get("step6_reflection", {})
        ctx["step11_audit"] = {
            "audit_trace": {
                "request_id": task.id,
                "user_id": task.user_id,
                "host_id": task.host_id,
                "task_text": task.task_text,
                "final_status": "rejected",
            },
            "raw_log": {
                "type": "Raw_Log",
                "request_id": task.id,
                "task": reflection_ctx.get("revised_tool", "unknown"),
                "target": reflection_ctx.get("revised_target", "unknown"),
                "status": "rejected",
                "description": f"审计人员主动拒绝，风险分 {step7.get('total_risk', 'N/A')}",
                "commands": rejected_commands,
            },
            "approval_log": {
                "approval_id": f"apv_{task.id[:8]}",
                "request_id": task.id,
                "approved": False,
                "approved_by": current_user.username,
                "reject_reason": f"审计人员主动拒绝，风险分 {step7.get('total_risk', 'N/A')}",
                "approve_time": now_str,
            },
        }
        task.context_data = ctx
        flag_modified(task, "context_data")
        db.commit()
        return {"status": "success", "new_status": "rejected", "detail": "task_rejected"}


@router.post("/{task_id}/rollback")
async def rollback_task(
        task_id: str,
        payload: RollbackActionPayload | None = Body(default=None),
        db: Session = Depends(deps.get_db),
        current_user: User = Depends(deps.get_current_user),
):
    if current_user.role not in ["operator", "admin"]:
        raise HTTPException(status_code=403, detail="仅操作员或管理员可发起回滚")

    task = db.query(TaskRecord).filter(TaskRecord.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if current_user.role == "operator" and str(task.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="无权回滚该任务")

    ctx = dict(task.context_data or {})
    execution_result = ctx.get("step10_execution_result") or {}
    command_runs = execution_result.get("command_runs") or []
    if not command_runs:
        raise HTTPException(status_code=400, detail="该任务没有可回滚的执行记录")

    selected_ids = set((payload.selected_command_ids if payload else []) or [])
    rollback_candidates = [
        i for i in command_runs
        if bool(i.get("rollback_available"))
    ]

    if selected_ids:
        rollback_candidates = [
            i for i in rollback_candidates
            if str(i.get("id")) in selected_ids
        ]

    if not rollback_candidates:
        raise HTTPException(status_code=400, detail="未选中可回滚命令，或所选命令不支持回滚")

    readonly_tools = {
        "read_file",
        "list_dir",
        "network_config_show",
        "show_service_status",
        "show_system_log",
        "list_process",
        "list_disk",
        "list_open_files",
        "show_network_connections",
    }

    def _precheck_rollback_command(cmd: str) -> tuple[bool, str]:
        c = str(cmd or "").strip()
        if not c:
            return False, "未提供回滚命令"
        parts = c.split()
        if not parts:
            return False, "回滚命令为空"
        prog = parts[0]
        if prog == "cp":
            # cp [-a] src dst，校验源文件存在
            src = ""
            for p in parts[1:]:
                if p.startswith("-"):
                    continue
                src = p
                break
            if src and not os.path.exists(src):
                return False, f"回滚源文件不存在: {src}"
        if prog == "tar" and "-xzf" in parts:
            idx = parts.index("-xzf")
            archive = parts[idx + 1] if idx + 1 < len(parts) else ""
            if archive and not os.path.exists(archive):
                return False, f"回滚归档文件不存在: {archive}"
        return True, "ok"

    def _normalize_rollback_item(item: Dict[str, Any]) -> tuple[bool, str, bool, str]:
        tool = str(item.get("tool") or "").strip()
        original_command = str(item.get("command") or "").strip()
        rollback_cmd = str(item.get("rollback_command") or "").strip()

        if tool in readonly_tools:
            return False, "", False, "只读命令不修改系统状态，无需回滚"

        # 兼容旧任务：archive_backup 回滚统一改为删除本次归档文件。
        if tool == "archive_backup":
            archive_name = ""
            m = re.search(r"tar\s+-czvf\s+(\S+)", original_command)
            if m:
                archive_name = m.group(1)
            if not archive_name and rollback_cmd:
                # 尝试从旧 tar -xzf 命令提取归档文件名
                m2 = re.search(r"-xzf\s+(\S+)", rollback_cmd)
                if m2:
                    archive_name = m2.group(1)
            if archive_name:
                rollback_cmd = f"rm -f {archive_name}"
                need_root = _rollback_need_root(item, rollback_cmd)
                return True, rollback_cmd, need_root, "删除本次归档文件，回滚归档创建操作"

        # 兼容旧任务：truncate_file 未给回滚命令时，尝试同路径 .bak 恢复
        if tool == "truncate_file" and not rollback_cmd:
            target = str(item.get("target") or "").strip()
            if target:
                rollback_cmd = f"cp -a {target}.bak {target}"

        if not rollback_cmd:
            return False, "", False, "未提供可执行回滚命令"

        ok, msg = _precheck_rollback_command(rollback_cmd)
        if not ok:
            return False, rollback_cmd, _rollback_need_root(item, rollback_cmd), msg

        return True, rollback_cmd, _rollback_need_root(item, rollback_cmd), "ok"

    def _rollback_need_root(item: Dict[str, Any], rollback_cmd: str) -> bool:
        # 优先采用反思层命令级显式标注，后端再做命令/路径兜底，避免漏判。
        explicit = bool(item.get("rollback_need_root", False))
        cmd = str(rollback_cmd or "").strip()
        target = str(item.get("target") or "").strip()

        def _path_need_root(path_val: str) -> bool:
            if not path_val or not path_val.startswith("/"):
                return False
            protected_prefixes = (
                "/root",
                "/etc",
                "/boot",
                "/proc",
                "/sys",
                "/var/log",
            )
            return any(path_val == p or path_val.startswith(p + "/") for p in protected_prefixes)

        heuristic = False
        if _path_need_root(target):
            heuristic = True

        if cmd:
            path_patterns = [
                r"(^|\s)/root(/|\s|$)",
                r"(^|\s)/etc(/|\s|$)",
                r"(^|\s)/boot(/|\s|$)",
                r"(^|\s)/proc(/|\s|$)",
                r"(^|\s)/sys(/|\s|$)",
                r"(^|\s)/var/log(/|\s|$)",
            ]
            if any(re.search(p, cmd) for p in path_patterns):
                heuristic = True

            privileged_cmd_patterns = [
                r"(^|\s)systemctl(\s|$)",
                r"(^|\s)service(\s|$)",
                r"(^|\s)iptables(\s|$)",
                r"(^|\s)ip(\s+addr|\s+route|\s+link)",
                r"(^|\s)mount(\s|$)",
                r"(^|\s)umount(\s|$)",
                r"(^|\s)chown(\s|$)",
                r"(^|\s)chmod(\s|$)",
                r"(^|\s)user(add|del|mod)(\s|$)",
                r"(^|\s)apt(-get)?(\s|$)",
            ]
            if any(re.search(p, cmd) for p in privileged_cmd_patterns):
                heuristic = True

        return explicit or heuristic

    async def _exec_rollback(command: str, need_root: bool) -> dict:
        exec_cmd = command
        if need_root and os.geteuid() != 0:
            exec_cmd = f"sudo -n {command}"
        proc = await asyncio.create_subprocess_shell(
            exec_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        out = stdout.decode("utf-8", errors="ignore") if stdout else ""
        err = stderr.decode("utf-8", errors="ignore") if stderr else ""
        return {
            "status": "success" if proc.returncode == 0 else "failed",
            "exit_code": int(proc.returncode),
            "stdout": out,
            "stderr": err,
            "executed_command": exec_cmd,
        }

    now_str = datetime.now().isoformat()
    rollback_runs = []
    for item in rollback_candidates:
        can_run, rollback_cmd, resolved_need_root, normalize_msg = _normalize_rollback_item(item)
        if not can_run:
            rollback_runs.append({
                "id": item.get("id"),
                "tool": item.get("tool"),
                "original_command": item.get("command"),
                "rollback_command": rollback_cmd,
                "status": "failed",
                "exit_code": 1,
                "stdout": "",
                "stderr": normalize_msg,
                "started_at": now_str,
                "finished_at": datetime.now().isoformat(),
            })
            continue

        started_at = datetime.now().isoformat()
        resolved_need_root = _rollback_need_root(item, rollback_cmd)
        try:
            ret = await _exec_rollback(
                rollback_cmd,
                resolved_need_root,
            )
            rollback_runs.append({
                "id": item.get("id"),
                "tool": item.get("tool"),
                "original_command": item.get("command"),
                "rollback_command": rollback_cmd,
                "rollback_need_root": resolved_need_root,
                "status": ret.get("status"),
                "exit_code": ret.get("exit_code"),
                "stdout": ret.get("stdout", ""),
                "stderr": ret.get("stderr", ""),
                "executed_command": ret.get("executed_command", rollback_cmd),
                "started_at": started_at,
                "finished_at": datetime.now().isoformat(),
            })
        except asyncio.TimeoutError:
            rollback_runs.append({
                "id": item.get("id"),
                "tool": item.get("tool"),
                "original_command": item.get("command"),
                "rollback_command": rollback_cmd,
                "rollback_need_root": resolved_need_root,
                "status": "failed",
                "exit_code": 124,
                "stdout": "",
                "stderr": "回滚命令执行超时",
                "started_at": started_at,
                "finished_at": datetime.now().isoformat(),
            })
        except Exception as e:
            rollback_runs.append({
                "id": item.get("id"),
                "tool": item.get("tool"),
                "original_command": item.get("command"),
                "rollback_command": rollback_cmd,
                "rollback_need_root": resolved_need_root,
                "status": "failed",
                "exit_code": 1,
                "stdout": "",
                "stderr": str(e),
                "started_at": started_at,
                "finished_at": datetime.now().isoformat(),
            })

    rollback_status = "success" if rollback_runs and all(r.get("status") == "success" for r in rollback_runs) else "failed"
    rollback_result = {
        "request_id": task.id,
        "selected_command_ids": [str(i.get("id")) for i in rollback_candidates],
        "status": rollback_status,
        "runs": rollback_runs,
        "started_at": now_str,
        "finished_at": datetime.now().isoformat(),
    }
    ctx["step14_rollback_result"] = rollback_result
    ctx.setdefault("history", []).append(
        f"[回滚阶段] 已执行 {len(rollback_runs)} 条回滚命令，状态：{rollback_status}。"
    )

    step11 = ctx.get("step11_audit") or {}
    raw_log = step11.get("raw_log") or {}
    raw_log["rollback"] = {
        "status": rollback_status,
        "runs": [
            {
                "id": r.get("id"),
                "tool": r.get("tool"),
                "original_command": r.get("original_command"),
                "rollback_command": r.get("rollback_command"),
                "rollback_need_root": r.get("rollback_need_root", False),
                "status": r.get("status"),
                "exit_code": r.get("exit_code"),
                "stderr": r.get("stderr", ""),
            }
            for r in rollback_runs
        ],
    }
    step11["raw_log"] = raw_log
    ctx["step11_audit"] = step11

    task.context_data = ctx
    flag_modified(task, "context_data")
    db.commit()

    return {
        "status": "success",
        "task_id": task.id,
        "rollback_result": rollback_result,
    }


# ==========================================
# 接口 4：查看所有工具
# ==========================================
@router.get("/mcp/tools", response_model=List[Dict[str, Any]])
async def get_mcp_tools():
    return KylinMCP.get_tool_list_for_ai()
