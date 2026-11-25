#!/usr/bin/env python3
"""Create a real administrator interactively; never seed demo accounts."""
import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "program2"))

from app.core.database import Base, SessionLocal, engine
from app.core.security import get_password_hash
from app.models.user import User


def main():
    parser = argparse.ArgumentParser(description="创建管理员账号（不会覆盖已有账号）")
    parser.add_argument("--username", required=True, help="管理员用户名")
    args = parser.parse_args()
    username = args.username.strip()
    if not username:
        parser.error("用户名不能为空")

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.query(User).filter(User.username == username).first():
            parser.exit(1, "用户名已存在，未修改任何账号。\n")
        password = getpass.getpass("管理员密码（至少 8 位，最多 72 个 UTF-8 字节）: ")
        if len(password) < 8 or len(password.encode("utf-8")) > 72:
            parser.exit(1, "密码长度不符合要求。\n")
        if password != getpass.getpass("再次输入密码: "):
            parser.exit(1, "两次密码不一致。\n")
        db.add(User(username=username, hashed_password=get_password_hash(password), role="admin"))
        db.commit()
    print(f"已创建管理员：{username}")


if __name__ == "__main__":
    main()
