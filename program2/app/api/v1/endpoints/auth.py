from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.api import deps
from app.core import security
from app.core.config import settings
from app.core.security import get_password_hash, create_access_token
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserOut  # 记得在 schemas/user.py 定义这两个

router = APIRouter()


@router.post("/register", response_model=UserOut)
def register(user_in: UserCreate, db: Session = Depends(deps.get_db)):
    """
    用户注册接口：
    1. 检查用户名冲突
    2. 哈希处理密码
    3. 保存用户信息（包含角色 role）
    """
    role = (user_in.role or "user").strip().lower()
    username = (user_in.username or "").strip()

    if not username:
        raise HTTPException(status_code=400, detail="用户名不能为空")

    # 0. 禁止前端自行注册管理员账号
    if role == "admin":
        raise HTTPException(
            status_code=403,
            detail="不允许自行注册管理员账号"
        )

    # 0.1 角色白名单
    if role not in ["user", "operator", "auditor"]:
        raise HTTPException(status_code=400, detail="不支持的注册角色")

    # 0.2 角色密钥校验
    reg_key = (user_in.reg_key or "").strip()
    if role == "operator":
        if not settings.OPERATOR_REGISTER_KEY:
            raise HTTPException(status_code=503, detail="运维角色注册尚未配置")
        if not reg_key:
            raise HTTPException(status_code=400, detail="请提供运维角色密钥")
        if reg_key != settings.OPERATOR_REGISTER_KEY:
            raise HTTPException(status_code=403, detail="运维角色密钥错误")
    if role == "auditor":
        if not settings.AUDITOR_REGISTER_KEY:
            raise HTTPException(status_code=503, detail="审计角色注册尚未配置")
        if not reg_key:
            raise HTTPException(status_code=400, detail="请提供审计人员角色密钥")
        if reg_key != settings.AUDITOR_REGISTER_KEY:
            raise HTTPException(status_code=403, detail="审计人员角色密钥错误")

    # 1. 检查用户是否已存在
    user = db.query(User).filter(User.username == username).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="该用户名已被注册"
        )

    # 2. 创建新用户实例
    # 注意：这里的 user_in.role 就是从前端传过来的 (operator/auditor/user)
    new_user = User(
        username=username,
        hashed_password=get_password_hash(user_in.password),
        role=role
    )

    # 3. 写入数据库
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post("/admin/create-user", response_model=UserOut)
def admin_create_user(
    user_in: UserCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    管理员专用：创建任意角色的账号（包括 admin）。
    需要 JWT 且 role=admin。
    """
    # 0. 鉴权：必须是管理员
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可以创建账号")

    # 1. 检查用户名是否重复
    username = (user_in.username or "").strip()
    if not username:
        raise HTTPException(status_code=400, detail="用户名不能为空")

    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(status_code=400, detail="该用户名已被注册")

    # 2. 创建用户
    new_user = User(
        username=username,
        hashed_password=get_password_hash(user_in.password),
        role=user_in.role if user_in.role else "user"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
def login(
        db: Session = Depends(deps.get_db),
        form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Step 0: 用户登录
    关键点：必须在 Token 中包含 role，Orchestrator 靠它来决定执行权限
    """
    # 1. 查找用户
    username = (form_data.username or "").strip()
    user = db.query(User).filter(User.username == username).first()

    # 2. 验证密码
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    # 3. 创建 Token (Payload 中包含 sub 和 role)
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": str(user.id), "role": user.role},
        expires_delta=access_token_expires
    )

    # 4. 返回给前端（前端会把这个 token 存在 localStorage 里）
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role
    }
# @router.post("/register", response_model=dict)
# def register(user_in: UserCreate, db: Session = Depends(deps.get_db)):
#     # 1. 检查用户是否已存在
#     user = db.query(User).filter(User.username == user_in.username).first()
#     if user:
#         raise HTTPException(status_code=400, detail="该用户名已被注册")
#
#     # 2. 创建新用户（加密密码）
#     new_user = User(
#         username=user_in.username,
#         hashed_password=security.get_password_hash(user_in.password),
#         role="operator"
#     )
#     db.add(new_user)
#     db.commit()
#     return {"msg": "注册成功"}

# @router.post("/login/access-token", response_model=Token)
# def login_access_token(
#     db: Session = Depends(deps.get_db),
#     form_data: OAuth2PasswordRequestForm = Depends()
# ):
#     # 1. 验证用户 (这里直接查库，不用担心 authenticate 引用报错)
#     user = db.query(User).filter(User.username == form_data.username).first()
#     if not user or not security.verify_password(form_data.password, user.hashed_password):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="用户名或密码错误"
#         )
#
#     # 2. 生成 Token：必须把角色 (role) 塞进 Payload
#     access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
#     access_token = security.create_access_token(
#         data={"sub": str(user.id), "role": user.role}, # <-- 关键：加密角色
#         expires_delta=access_token_expires
#     )
#
#     # 3. 返回：必须符合 Token Schema，带上 role
#     return {
#         "access_token": access_token,
#         "token_type": "bearer",
#         "role": user.role # <-- 关键：让前端能直接看到角色
#     }
#
# @router.post("/login", response_model=Token)
# def login(db: Session = Depends(deps.get_db), form_data: OAuth2PasswordRequestForm = Depends()):
#     # 1. 查找用户
#     user = db.query(User).filter(User.username == form_data.username).first()
#     if not user or not security.verify_password(form_data.password, user.hashed_password):
#         raise HTTPException(status_code=400, detail="用户名或密码错误")
#
#     # 2. 签发 Token
#     access_token = security.create_access_token(data={"sub": user.username})
#     return {"access_token": access_token, "token_type": "bearer"}
