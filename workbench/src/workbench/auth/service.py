"""认证业务：bcrypt 哈希 + JWT 签发/校验（secret 单源，供 bridge 依赖注入）。"""

import datetime as dt
import uuid
from dataclasses import dataclass, field

import bcrypt
import jwt

from workbench.auth.repository import User, UserRepository


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


# 「记住我」会话 TTL：30 天免登录（默认 1 小时，见 AuthService.ttl_seconds）
REMEMBER_TTL_SECONDS = 30 * 24 * 3600


@dataclass
class AuthService:
    db_path: str
    secret: bytes
    ttl_seconds: int = 3600
    repo: UserRepository = field(init=False)

    def __post_init__(self):
        self.repo = UserRepository(self.db_path)

    def _issue(self, username: str, ttl_seconds: int | None = None) -> str:
        ttl = self.ttl_seconds if ttl_seconds is None else ttl_seconds
        now = dt.datetime.now(dt.timezone.utc)
        payload = {
            "sub": username,
            "iat": now,
            "exp": now + dt.timedelta(seconds=ttl),
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(payload, self.secret, algorithm="HS256")

    def verify_token(self, token: str) -> dict:
        """校验 token 并返回 payload；无效/过期抛 ValueError。bridge 鉴权统一走这里。"""
        try:
            payload = jwt.decode(token, self.secret, algorithms=["HS256"])
        except jwt.PyJWTError as e:
            raise ValueError(f"invalid token: {e}") from e
        if not isinstance(payload, dict) or "sub" not in payload:
            raise ValueError("invalid token payload")
        return payload

    def register(self, username: str, password: str, remember: bool = False) -> str:
        if len(password) < 6:
            raise ValueError("password too short (min 6)")
        self.repo.create_user(username, hash_password(password))
        return self._issue(username, self._ttl(remember))

    def authenticate(self, username: str, password: str) -> User:
        user = self.repo.get_by_username(username)
        if user is None or not verify_password(password, user.password_hash):
            raise ValueError("invalid credentials")
        return user

    def login(self, username: str, password: str, remember: bool = False) -> str:
        self.authenticate(username, password)
        return self._issue(username, self._ttl(remember))

    def _ttl(self, remember: bool) -> int:
        return REMEMBER_TTL_SECONDS if remember else self.ttl_seconds
