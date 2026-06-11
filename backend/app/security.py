from __future__ import annotations

import hashlib
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from sqlalchemy.orm import Session

from .database import get_db
from .models import AuditLog, User, UserRole

password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-change-me-for-local-mvp-32-bytes")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))
MAX_LOGIN_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 300

_login_failures: dict[str, list[float]] = {}


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("Password must not be empty.")
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not plain_password or not hashed_password:
        return False
    try:
        return password_hash.verify(plain_password, hashed_password)
    except UnknownHashError:
        return False


def create_access_token(subject: str, role: UserRole) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload: dict[str, Any] = {"sub": subject, "role": role.value, "exp": expires_at}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def check_login_rate_limit(identifier: str) -> None:
    now = time.time()
    failures = [entry for entry in _login_failures.get(identifier, []) if now - entry < LOGIN_WINDOW_SECONDS]
    _login_failures[identifier] = failures
    if len(failures) >= MAX_LOGIN_ATTEMPTS:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many login attempts")


def register_failed_login(identifier: str) -> None:
    failures = _login_failures.setdefault(identifier, [])
    failures.append(time.time())


def clear_failed_logins(identifier: str) -> None:
    _login_failures.pop(identifier, None)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        subject = payload.get("sub")
        if subject is None:
            raise credentials_error
    except jwt.PyJWTError as exc:
        raise credentials_error from exc

    user = db.query(User).filter(User.email == subject).first()
    if user is None or not user.is_active:
        raise credentials_error
    return user


def require_roles(*roles: UserRole):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return current_user

    return dependency


def request_ip_hash(request: Request) -> str | None:
    host = request.client.host if request.client else None
    if not host:
        return None
    digest = hashlib.sha256(host.encode("utf-8")).hexdigest()
    return digest[:24]


def safe_details(details: dict[str, Any] | None) -> dict[str, Any] | None:
    if not details:
        return None
    blocked = {"password", "password_hash", "token", "access_token", "secret", "cookie", "authorization"}
    return {key: value for key, value in details.items() if key.lower() not in blocked}


def write_audit_log(
    db: Session,
    actor: User | None,
    action: str,
    entity_type: str,
    entity_id: int | str | None = None,
    details: dict[str, Any] | None = None,
    ip_hash: str | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_user_id=actor.id if actor else None,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            details=safe_details(details),
            ip_hash=ip_hash,
        )
    )
