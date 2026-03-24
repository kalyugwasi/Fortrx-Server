from fastapi import APIRouter, Depends, Request
from app.middleware.rate_limit import limiter
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.services.auth_service import register_user, login_user
from app.schemas.user import UserCreate, UserResponse, TokenResponse
from app.database import get_db
from app.dependencies import get_active_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserResponse, status_code=201)
@limiter.limit("5/minute")
def register(
    request: Request,  
    payload: UserCreate,
    db: Session = Depends(get_db)
):
    return register_user(
        db,
        payload.username,
        payload.email,
        payload.password
    )

@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(
    request: Request,  
    payload: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    token = login_user(
        db,
        payload.username,
        payload.password
    )
    return {
        "access_token": token,
        "token_type": "bearer"
    }

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_active_user)):
    return current_user