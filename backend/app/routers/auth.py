"""Authentication router: register, login, me, logout."""
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.db import get_db
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    Token,
    UserResponseSafe,
    AuthError,
)
from app.services.auth import (
    AuthError,
    authenticate_user,
    create_access_token,
    get_current_user,
    get_current_user_dep,
    register_user,
    user_to_safe_response,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


@router.post("/register", response_model=UserResponseSafe, status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user."""
    try:
        user = register_user(db, user_data)
        return user_to_safe_response(user)
    except AuthError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, response: Response, db: Session = Depends(get_db)):
    """Authenticate user and return access token."""
    try:
        user = authenticate_user(db, credentials.email, credentials.password)
        access_token = create_access_token(user.id)
        return Token(access_token=access_token, token_type="bearer")
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/me", response_model=UserResponseSafe)
def me(current_user=Depends(get_current_user_dep)):
    """Get current authenticated user."""
    return current_user


@router.post("/logout")
def logout(response: Response):
    """
    Logout - client should discard the token.
    With stateless JWT, server cannot invalidate the token.
    Client should delete the token from storage.
    """
    return {"message": "Logged out. Please discard the access token on the client side."}


# Dependency for protected routes
def get_current_user_dep(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """FastAPI dependency for getting current user from Bearer token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return get_current_user(db, credentials.credentials)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )