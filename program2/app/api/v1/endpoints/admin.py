from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from typing import List
from pydantic import BaseModel
from datetime import datetime, timezone

from app.api import deps
from app.models.user import User
from app.models.task import TaskRecord
from app.models.tool_config import UserToolConfig
from app.schemas.user import UserOut

router = APIRouter()

# --- 前端传参用的局部数据模型 ---
class ApprovalRequest(BaseModel):
    approved: bool
    remark: str = None

class ToolToggleRequest(BaseModel):
    enabled: bool

# ----------------------------------------------------------------
# 所有接口都挂载了 Depends(deps.get_current_admin)
# 这确保了即使普通运维人员知道 URL，也无法绕过权限调用
# ----------------------------------------------------------------

# ==========================================
# 用户管理模块
# ==========================================
@router.get("/users", response_model=List[UserOut])
def get_all_users(
    db: Session = Depends(deps.get_db),
    current_admin: User = Depends(deps.get_current_admin)
):
    """
    管理员功能：获取系统内所有注册用户的信息列表。
    用于前端“用户管理”表格的数据填充。
    """
    return db.query(User).all()

@router.put("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    new_role: str,
    db: Session = Depends(deps.get_db),
    current_admin: User = Depends(deps.get_current_admin)
):
    """
    管理员功能：修改特定用户的角色。
    例如：将某个 operator 提升为 admin，或者将某人降权。
    """
    if new_role not in ["admin", "operator", "auditor"]:
        raise HTTPException(status_code=400, detail="无效的角色类型")
        
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="找不到该用户")
        
    user.role = new_role
    db.commit()
    return {"status": "success", "message": f"用户 {user.username} 的角色已更新为 {new_role}"}

@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(deps.get_db),
    current_admin: User = Depends(deps.get_current_admin)
):
    """
    管理员功能：从系统中删除用户。
    """
    if user_id == current_admin.id:
        raise HTTPException(status_code=400, detail="不能删除当前登录的管理员账号")
        
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="找不到该用户")
        
    db.delete(user)
    db.commit()
    return {"status": "success", "message": f"用户 {user.username} 已从系统中移除"}

@router.get("/stats")
def get_system_stats(
    db: Session = Depends(deps.get_db),
    current_admin: User = Depends(deps.get_current_admin)
):
    """
    管理员功能：获取简单的系统用户统计摘要。
    """
    total = db.query(User).count()
    admins = db.query(User).filter(User.role == "admin").count()
    operators = db.query(User).filter(User.role == "operator").count()
    auditors = db.query(User).filter(User.role == "auditor").count()
    
    return {
        "total_users": total,
        "role_distribution": {
            "admin": admins,
            "operator": operators,
            "auditor": auditors
        }
    }

# ==========================================
# 高风险动作审批模块 (步骤 8-9)
# ==========================================
@router.get("/approvals/pending")
def get_pending_approvals(
    db: Session = Depends(deps.get_db),
    current_admin: User = Depends(deps.get_current_admin)
):
    """
    管理员功能：获取所有等待审批的高风险任务。
    Orchestrator 拦截到高风险命令后，会将任务状态置为 "confirming"。
    """
    tasks = db.query(TaskRecord).filter(TaskRecord.status == "confirming").all()
    return tasks

@router.post("/approvals/{task_id}")
def process_task_approval(
    task_id: str,
    approval: ApprovalRequest,
    db: Session = Depends(deps.get_db),
    current_admin: User = Depends(deps.get_current_admin)
):
    """
    管理员功能：同意或拒绝运维人员的高风险动作
    """
    task = db.query(TaskRecord).filter(TaskRecord.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="找不到该任务")
    
    if task.status != "confirming":
        raise HTTPException(status_code=400, detail=f"任务当前状态为 {task.status}，非待审批状态")

    # 根据审批结果推进任务流：同意则进入执行排队(approved)，拒绝则终止(rejected)
    task.status = "approved" if approval.approved else "rejected"
    
    # 记录审计信息到 context_data 中，留痕操作
    if not task.context_data:
        task.context_data = {}
        
    task.context_data["approval_log"] = {
        "admin_id": current_admin.id,
        "admin_username": current_admin.username,
        "approved": approval.approved,
        "remark": approval.remark,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }
    
    # 显式告知 SQLAlchemy JSON 字段已被修改
    flag_modified(task, "context_data")
    db.commit()
    
    return {
        "status": "success", 
        "message": f"高风险任务 {task_id} 已{'通过' if approval.approved else '驳回'}"
    }

# ==========================================
# 工具管控模块
# ==========================================
@router.post("/tools/{tool_name}/toggle")
def toggle_tool_status(
    tool_name: str,
    request: ToolToggleRequest,
    db: Session = Depends(deps.get_db),
    current_admin: User = Depends(deps.get_current_admin)
):
    """
    管理员功能：全局启用/禁用某个运维工具（如高危删除命令）。
    配合前端【工具禁用管理】页面使用。
    """
    config = db.query(UserToolConfig).filter(UserToolConfig.tool_name == tool_name).first()
    
    if not config:
        config = UserToolConfig(tool_name=tool_name, is_enabled=request.enabled)
        db.add(config)
    else:
        config.is_enabled = request.enabled
        
    db.commit()
    return {"status": "success", "message": f"工具 {tool_name} 已{'启用' if request.enabled else '禁用'}"}