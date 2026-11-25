from fastapi import Depends, HTTPException, status
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.core import security
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.user import User

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(db: Session = Depends(get_db), token: str = Depends(security.oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="认证已失效，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        # 注意：这里拿到的是 str 类型的 ID
        uid: str = payload.get("sub")
        if uid is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # 这里的查询必须使用上面定义好的变量 uid
    user = db.query(User).filter(User.id == uid).first()
    if user is None:
        raise credentials_exception
    return user

# ==========================================
# 新增：专属管理员锁
# ==========================================
async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，只有管理员可以访问此接口"
        )
    return current_user

# 新增：专属审计员锁
# ==========================================
async def get_current_auditor(current_user: User = Depends(get_current_user)) -> User:
    # 允许 admin 和 auditor 都能查看审计日志
    if current_user.role not in ["auditor", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，只有审计员或管理员可以访问此接口"
        )
    return current_user

def get_user_by_token(token: str, db: Session = Depends(get_db)):
    """根据 token 字符串获取用户，不依赖 OAuth2 方案"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="认证已失效，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        uid: str = payload.get("sub")
        if uid is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == uid).first()
    if user is None:
        raise credentials_exception
    return user











# from fastapi import Depends, HTTPException, status
# from jose import jwt, JWTError
# from sqlalchemy.orm import Session
# from app.core import security
# from app.core.config import settings
# from app.core.database import SessionLocal
# from app.models.user import User
#
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()
#
# def get_current_user(db: Session = Depends(get_db), token: str = Depends(security.oauth2_scheme)):
#     credentials_exception = HTTPException(
#         status_code=status.HTTP_401_UNAUTHORIZED,
#         detail="认证已失效，请重新登录",
#         headers={"WWW-Authenticate": "Bearer"},
#     )
#     try:
#         # 解码 Token
#         payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
#         username: str = payload.get("sub")
#         if username is None:
#             raise credentials_exception
#     except JWTError:
#         raise credentials_exception
#
#     user = db.query(User).filter(User.id == user_id).first()
#     if user is None:
#         raise credentials_exception
#     return user



# def get_current_user(token: str = Depends(security.oauth2_scheme)):
#     try:
#         payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
#         username: str = payload.get("sub")
#         if username is None:
#             raise HTTPException(status_code=401, detail="无效凭证")
#         return username
#     except JWTError:
#         raise HTTPException(status_code=401, detail="Token 已过期或无效")
