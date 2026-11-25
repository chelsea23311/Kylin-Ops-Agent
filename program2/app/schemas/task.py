from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# ==========================================
# 1. 前端创建任务的输入模型 (POST /tasks/run)
# ==========================================
class TaskCreate(BaseModel):
    # 统一字段名为 task_text，与数据库 Model 对齐
    task_text: str = Field(..., example="清理 /var/log 目录下的过大日志文件")
    host_id: Optional[str] = Field(default="host_prod_01")


# ==========================================
# 2. 任务状态响应模型 (用于接口统一返回)
# ==========================================
class TaskResponse(BaseModel):
    id: str
    user_id: str
    task_text: str
    host_id: str
    status: str
    context_data: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


# 3. 审批操作模型 (可选：如果以后审批需要传参)
# ==========================================
class TaskApprove(BaseModel):
    approved: bool = True
    remark: Optional[str] = None


class ApprovalActionPayload(BaseModel):
    selected_command_ids: List[str] = []


class RollbackActionPayload(BaseModel):
    selected_command_ids: List[str] = []
'''
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# MCP 动作定义（对应你的工具表）
class ActionDraft(BaseModel):
    tool_name: str
    command: str
    risk_level: float
    audit_reason: str

#
# # 核心：13步流程中的上下文大对象
# class TaskContext(BaseModel):
#     task_id: str
#     user_id: str
#     prompt: str
#     status: str = "init"  # init, perceiving, reflecting, confirming, executing, done, failed
#
#     # 阶段性数据存储
#     perception_data: Optional[Dict] = None  # Step 3 环境感知结果
#     memory_recall: Optional[Dict] = None  # Step 4 RAG 检索结果
#     action: Optional[ActionDraft] = None  # Step 5 & 6 LLM 决策结果
#     risk_report: Optional[Dict] = None  # Step 7 ML 风险评估结果
#
#     execution_result: Optional[str] = None  # Step 10 执行输出
#     error_msg: Optional[str] = None
#     created_at: datetime = Field(default_factory=datetime.now)
#
#
# # 前端提交请求的模型
# class TaskCreate(BaseModel):
#     user_id: str
#     prompt: str


# 1. 前端提交请求的模型 (Step 1)
class TaskCreate(BaseModel):
    task_text: str  # 对应 MD 的需求描述
    host_id: str = "host_prod_01"
    session_id: Optional[str] = None


# 2. 完整的任务详情模型 (用于 GET /tasks/{id} 或 Step 2 返回)
class TaskContext(BaseModel):
    request_id: str  # 对应数据库 id
    session_id: Optional[str] = None
    user_id: str
    host_id: str
    task_text: str
    status: str = "accepted"
    request_time: datetime = Field(default_factory=datetime.now)

    # 【黑匣子】对应 13 步流程中的 context_data
    # 包含了感知、RAG、决策、执行的所有中间过程
    context_data: Dict[str, Any] = {
        "steps": {},  # 存储每一波的具体数据 (perception, rag, decision)
        "history": [],  # 状态流转时间轴
        "pending_action": {}  # 等待确认的动作
    }

    class Config:
        from_attributes = True  # 允许从 SQLAlchemy 对象直接转换
'''