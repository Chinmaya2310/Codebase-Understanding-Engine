"""JWT auth and rate limiting."""
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.core.config import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    return jwt.encode({"sub": subject, "exp": expire}, settings.secret_key, algorithm=settings.algorithm)


async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> str:
    if token is None:
        if settings.debug:
            return "anonymous"
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        subject: Optional[str] = payload.get("sub")
        if subject is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return subject
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


class _RateLimiter:
    def __init__(self):
        self._hits: dict[str, list[float]] = {}

    def check(self, key: str, limit: int, window: int = 60) -> bool:
        now = time.time()
        hits = self._hits.setdefault(key, [])
        self._hits[key] = [h for h in hits if h > now - window]
        if len(self._hits[key]) >= limit:
            return False
        self._hits[key].append(now)
        return True


_limiter = _RateLimiter()


async def rate_limit_dependency(request: Request) -> None:
    key = request.client.host if request.client else "unknown"
    if not _limiter.check(key, settings.rate_limit_per_minute):
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")
