from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Any

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import Response
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from sqlalchemy.orm import Session

from .database import get_db
from .models import AuditLog, User, UserRole

password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET or len(JWT_SECRET.encode("utf-8")) < 32:
    raise RuntimeError("JWT_SECRET must be set to at least 32 bytes.")

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "30"))
AUTH_COOKIE_NAME = "zms_access_token"
CSRF_COOKIE_NAME = "zms_csrf_token"
COOKIE_SECURE = os.getenv("AUTH_COOKIE_SECURE", "true").strip().lower() not in {"0", "false", "no"}
COOKIE_SAMESITE = "strict"
MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
LOGIN_WINDOW_SECONDS = int(os.getenv("LOGIN_WINDOW_SECONDS", "300"))
MAX_RATE_LIMIT_IDENTIFIERS = int(os.getenv("MAX_RATE_LIMIT_IDENTIFIERS", "10000"))
MAX_AUDIT_DETAILS_BYTES = 10_000
MAX_AUDIT_DETAILS_DEPTH = 3
SENSITIVE_DETAIL_KEYS = {
    "password",
    "password_hash",
    "token",
    "access_token",
    "secret",
    "cookie",
    "authorization",
    "email",
}

# Pepper used to keep hashed IP addresses (a small, enumerable keyspace) from being
# trivially reversible via a rainbow table. Falls back to JWT_SECRET so deployments do
# not need an extra variable, but a dedicated IP_HASH_PEPPER is recommended.
IP_HASH_PEPPER = (os.getenv("IP_HASH_PEPPER") or JWT_SECRET).encode("utf-8")

PUBLIC_RATE_LIMIT = int(os.getenv("PUBLIC_RATE_LIMIT", "60"))
PUBLIC_RATE_WINDOW_SECONDS = int(os.getenv("PUBLIC_RATE_WINDOW_SECONDS", "60"))

_login_failures: dict[str, deque[float]] = {}
_revoked_tokens: dict[str, float] = {}
_public_hits: dict[str, deque[float]] = {}
_login_lock = RLock()
_revocation_lock = RLock()
_public_lock = RLock()
_last_rate_limit_cleanup_at = 0.0
_last_revocation_cleanup_at = 0.0
_last_public_cleanup_at = 0.0


def hash_password(password: str) -> str:
    validate_password_strength(password)
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not plain_password or not hashed_password:
        return False
    try:
        return password_hash.verify(plain_password, hashed_password)
    except UnknownHashError:
        return False


def validate_password_strength(password: str) -> None:
    if not password:
        raise ValueError("Password must not be empty.")
    if len(password) > 128:
        raise ValueError("Password must not be longer than 128 characters.")
    if len(password) < 10:
        raise ValueError("Password must be at least 10 characters long.")
    checks = [
        any(character.islower() for character in password),
        any(character.isupper() for character in password),
        any(character.isdigit() for character in password),
        any(not character.isalnum() for character in password),
    ]
    if not all(checks):
        raise ValueError("Password must contain uppercase, lowercase, digit, and special character.")


def create_access_token(subject: str, role: UserRole) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role.value,
        "exp": expires_at,
        "iat": now,
        "jti": secrets.token_urlsafe(24),
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_auth_cookies(response: Response, access_token: str, csrf_token: str) -> None:
    max_age = JWT_EXPIRE_MINUTES * 60
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=access_token,
        max_age=max_age,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        max_age=max_age,
        httponly=False,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
    )


def clear_auth_cookies(response: Response) -> None:
    for cookie_name in (AUTH_COOKIE_NAME, CSRF_COOKIE_NAME):
        response.delete_cookie(
            key=cookie_name,
            httponly=cookie_name == AUTH_COOKIE_NAME,
            secure=COOKIE_SECURE,
            samesite=COOKIE_SAMESITE,
        )


def check_login_rate_limit(identifier: str) -> None:
    with _login_lock:
        _check_login_rate_limit_locked(identifier, time.time())


def consume_login_attempt(identifier: str) -> None:
    now = time.time()
    with _login_lock:
        failures = _check_login_rate_limit_locked(identifier, now)
        failures.append(now)


def _check_login_rate_limit_locked(identifier: str, now: float) -> deque[float]:
    global _last_rate_limit_cleanup_at
    if now - _last_rate_limit_cleanup_at >= 60 or len(_login_failures) > MAX_RATE_LIMIT_IDENTIFIERS:
        _cleanup_login_failures_locked(now)
        _last_rate_limit_cleanup_at = now

    cutoff = now - LOGIN_WINDOW_SECONDS
    failures = _login_failures.setdefault(identifier, deque(maxlen=MAX_LOGIN_ATTEMPTS))
    while failures and failures[0] <= cutoff:
        failures.popleft()
    if len(failures) >= MAX_LOGIN_ATTEMPTS:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many login attempts")
    return failures


def _cleanup_login_failures_locked(now: float) -> None:
    cutoff = now - LOGIN_WINDOW_SECONDS
    expired = [identifier for identifier, failures in _login_failures.items() if not failures or failures[-1] <= cutoff]
    for identifier in expired:
        _login_failures.pop(identifier, None)

    if len(_login_failures) <= MAX_RATE_LIMIT_IDENTIFIERS:
        return
    oldest_identifiers = sorted(_login_failures, key=lambda key: _login_failures[key][-1] if _login_failures[key] else 0)
    for identifier in oldest_identifiers[: len(_login_failures) - MAX_RATE_LIMIT_IDENTIFIERS]:
        _login_failures.pop(identifier, None)


def clear_failed_logins(identifier: str) -> None:
    with _login_lock:
        _login_failures.pop(identifier, None)


def enforce_public_rate_limit(request: Request) -> None:
    """Sliding-window IP rate limit for unauthenticated public endpoints."""
    global _last_public_cleanup_at
    host = request.client.host if request.client else "anonymous"
    now = time.time()
    cutoff = now - PUBLIC_RATE_WINDOW_SECONDS
    with _public_lock:
        if now - _last_public_cleanup_at >= 60 or len(_public_hits) > MAX_RATE_LIMIT_IDENTIFIERS:
            stale = [key for key, hits in _public_hits.items() if not hits or hits[-1] <= cutoff]
            for key in stale:
                _public_hits.pop(key, None)
            _last_public_cleanup_at = now
        hits = _public_hits.setdefault(host, deque(maxlen=PUBLIC_RATE_LIMIT + 1))
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if len(hits) >= PUBLIC_RATE_LIMIT:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests")
        hits.append(now)


def _token_from_request(request: Request, bearer_token: str | None) -> str | None:
    if bearer_token:
        return bearer_token
    return request.cookies.get(AUTH_COOKIE_NAME)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if payload.get("type") != "access" or not payload.get("sub") or not payload.get("jti"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if is_token_revoked(str(payload["jti"])):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def revoke_token(payload: dict[str, Any]) -> None:
    jti = payload.get("jti")
    expires_at = payload.get("exp")
    if not jti or not expires_at:
        return
    expiry_timestamp = float(expires_at)
    with _revocation_lock:
        _revoked_tokens[str(jti)] = expiry_timestamp
        _cleanup_revoked_tokens_locked(time.time())


def is_token_revoked(jti: str) -> bool:
    now = time.time()
    with _revocation_lock:
        if now - _last_revocation_cleanup_at >= 60:
            _cleanup_revoked_tokens_locked(now)
        return jti in _revoked_tokens


def _cleanup_revoked_tokens_locked(now: float) -> None:
    global _last_revocation_cleanup_at
    _last_revocation_cleanup_at = now
    expired = [jti for jti, expires_at in _revoked_tokens.items() if expires_at <= now]
    for jti in expired:
        _revoked_tokens.pop(jti, None)


def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    raw_token = _token_from_request(request, token)
    if not raw_token:
        raise credentials_error

    payload = decode_access_token(raw_token)
    subject = payload.get("sub")
    if subject is None:
        raise credentials_error

    user = db.query(User).filter(User.email == subject).first()
    if user is None or not user.is_active:
        raise credentials_error
    request.state.jwt_payload = payload
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
    return hmac.new(IP_HASH_PEPPER, host.encode("utf-8"), hashlib.sha256).hexdigest()


def safe_details(details: dict[str, Any] | None) -> dict[str, Any] | None:
    if not details:
        return None
    sanitized = _sanitize_detail_value(details, depth=0)
    if not isinstance(sanitized, dict):
        return None
    encoded_size = len(str(sanitized).encode("utf-8"))
    if encoded_size > MAX_AUDIT_DETAILS_BYTES:
        return {"truncated": True, "size": encoded_size}
    return sanitized


def _sanitize_detail_value(value: Any, *, depth: int) -> Any:
    if depth > MAX_AUDIT_DETAILS_DEPTH:
        return "[max-depth]"
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, nested_value in value.items():
            key_as_text = str(key)
            if key_as_text.lower() in SENSITIVE_DETAIL_KEYS:
                continue
            clean[key_as_text[:120]] = _sanitize_detail_value(nested_value, depth=depth + 1)
        return clean
    if isinstance(value, list):
        return [_sanitize_detail_value(item, depth=depth + 1) for item in value[:50]]
    if isinstance(value, str):
        return value[:1000]
    if isinstance(value, int | float | bool) or value is None:
        return value
    return str(value)[:1000]


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
            entity_id=entity_id if entity_id is not None else None,
            details=safe_details(details),
            ip_hash=ip_hash,
        )
    )
