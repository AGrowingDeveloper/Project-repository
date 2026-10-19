"""用户认证模块：注册、登录、密码 bcrypt 哈希校验"""
import bcrypt
from . import database as db

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))

def register(username: str, password: str):
    if not username or len(username) < 3:
        return None
    if not password or len(password) < 6:
        return None
    return db.create_user(username, hash_password(password))

def login(username: str, password: str):
    user = db.get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user
