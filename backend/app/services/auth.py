"""Authentication service: password hashing and JWT handling."""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import get_settings
from app.db import get_db
from app.models import User
from app.schemas.auth import Token, UserLogin, UserRegister, UserResponseSafe


# Password hashing with Argon2id
ph = PasswordHasher()

# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)


class AuthError(Exception):
    """Authentication error with safe message."""
    def __init__(self, message: str = "Invalid credentials"):
        self.message = message
        super().__init__(self.message)


def hash_password(password: str) -> str:
    """Hash a password using Argon2id."""
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        ph.verify(hashed_password, plain_password)
        return True
    except VerifyMismatchError:
        return False


def validate_password_strength(password: str) -> None:
    """Validate password meets minimum requirements."""
    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters")
    if len(password) > 128:
        raise ValueError("Password must not exceed 128 characters")


def create_access_token(user_id: int, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    settings = get_settings()
    secret = settings.JWT_SECRET_KEY
    if not secret or len(secret) < 32:
        raise RuntimeError("JWT_SECRET_KEY must be at least 32 characters")

    algorithm = "HS256"
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))

    to_encode = {"sub": str(user_id), "exp": expire, "iat": datetime.now(timezone.utc)}
    return jwt.encode(to_encode, secret, algorithm=algorithm)


def decode_token(token: str) -> Optional[int]:
    """Decode and validate a JWT token, returning user_id if valid."""
    settings = get_settings()
    secret = settings.JWT_SECRET_KEY
    if not secret:
        raise AuthError("JWT secret not configured")

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise AuthError("Invalid token: missing subject")
        return int(user_id_str)
    except JWTError as e:
        # Log the specific error category for debugging (without token)
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"JWT validation failed: {type(e).__name__}")
        raise AuthError("Invalid or expired token")


def authenticate_user(db: Session, email: str, password: str) -> User:
    """Authenticate a user by email and password."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise AuthError("Invalid credentials")
    if not user.hashed_password:
        raise AuthError("Account not initialized. Use the setup command to set a password.")
    if not user.is_active:
        raise AuthError("Account is disabled")
    if not verify_password(password, user.hashed_password):
        raise AuthError("Invalid credentials")
    return user


def register_user(db: Session, user_data: UserRegister) -> User:
    """Register a new user."""
    # Check for existing email
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise AuthError("Email already registered")

    hashed = hash_password(user_data.password)
    user = User(
        email=user_data.email,
        hashed_password=hashed,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_current_user(db: Session, token: str) -> User:
    """Get the current user from a JWT token. Returns SQLAlchemy User model."""
    user_id = decode_token(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AuthError("User not found")
    if not user.is_active:
        raise AuthError("Account is disabled")
    return user


def get_current_user_dep(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency for getting current user from Bearer token. Returns SQLAlchemy User model."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return get_current_user(db, credentials.credentials)
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user_safe_dep(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> UserResponseSafe:
    """FastAPI dependency for getting current user safe response from Bearer token. Returns UserResponseSafe."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user = get_current_user(db, credentials.credentials)
        return user_to_safe_response(user)
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def user_to_safe_response(user: User) -> UserResponseSafe:
    """Convert User model to safe response (no password hash)."""
    return UserResponseSafe(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        created_at=user.created_at,
    )