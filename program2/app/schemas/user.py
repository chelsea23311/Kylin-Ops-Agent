from pydantic import BaseModel
from typing import Optional





# 1. 注册/创建用户时用：前端传给后端
class UserCreate(BaseModel):
    username: str
    password: str
    # 增加 role，允许注册时指定身份
    role: Optional[str] = "user"
    # 注册密钥（按角色校验）
    reg_key: Optional[str] = None

# 2. 登录成功后返回：后端给前端发令牌
class Token(BaseModel):
    access_token: str
    token_type: str
    # 建议加上 role，让前端能直接知道当前登录者的角色，方便切换 UI
    role: Optional[str] = None

# 3. 查询用户信息/接口返回：后端给前端展示
class UserOut(BaseModel):
    id: int
    username: str
    role: str

    class Config:
        from_attributes = True




# from pydantic import BaseModel
#
# class UserCreate(BaseModel):
#     username: str
#     password: str
#
# class Token(BaseModel):
#     access_token: str
#     token_type: str
#
# # 用于获取当前用户信息时的返回格式
# class UserOut(BaseModel):
#     id: int
#     username: str
#     role: str
#
#     class Config:
#         from_attributes = True