"""JWT authentication for FloorMind API."""
from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

try:
    import jwt
except ImportError:
    import PyJWT as jwt  # type: ignore[no-redef]

from api.schemas import LoginRequest, TokenResponse, UserInfo

router = APIRouter(prefix="/api/auth", tags=["auth"])

SECRET_KEY = os.getenv("FLOORMIND_JWT_SECRET", "floormind-dev-secret-change-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("FLOORMIND_TOKEN_EXPIRE_MIN", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Default credentials (override via env in production)
DEFAULT_USERNAME = os.getenv("FLOORMIND_ADMIN_USER", "admin")
DEFAULT_PASSWORD_HASH = os.getenv("FLOORMIND_ADMIN_PASS_HASH", "")

security = HTTPBearer(auto_error=False)


def _hash_password(password: str) -> str:
    """SHA-256 hash for password comparison."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str) -> bool:
    """Verify password against configured hash or plain-text env var."""
    plain = os.getenv("FLOORMIND_ADMIN_PASSWORD", "")
    if plain:
        return hmac.compare_digest(password, plain)

    if DEFAULT_PASSWORD_HASH:
        return hmac.compare_digest(_hash_password(password), DEFAULT_PASSWORD_HASH)

    # Dev mode: accept any password when no credentials configured
    return True


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return jwt.encode({**data, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """Dependency that extracts and validates the JWT from the Authorization header."""
    if credentials is None:
        # Dev mode: allow unauthenticated access when no password is set
        if not os.getenv("FLOORMIND_ADMIN_PASSWORD") and not DEFAULT_PASSWORD_HASH:
            return {"sub": "dev", "role": "admin"}
        raise HTTPException(status_code=401, detail="Not authenticated")

    return decode_token(credentials.credentials)


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    """Authenticate and return a JWT access token."""
    if not verify_password(request.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": request.username, "role": "admin"})
    return TokenResponse(
        access_token=token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(user: dict = Depends(get_current_user)) -> TokenResponse:
    """Refresh an existing token."""
    token = create_access_token({"sub": user["sub"], "role": user.get("role", "admin")})
    return TokenResponse(
        access_token=token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserInfo)
async def me(user: dict = Depends(get_current_user)) -> UserInfo:
    """Return the current authenticated user."""
    return UserInfo(username=user["sub"], role=user.get("role", "admin"))
