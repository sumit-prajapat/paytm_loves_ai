from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.deps import get_current_user
from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password
from app.db.models import AuditLog, User
from app.db.session import get_db

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    username: str
    password: str


class DemoTokenRequest(BaseModel):
    role: str  # merchant | traveller | ops_agent | admin
    target_id: str | None = None  # optional merchant_id (e.g. m_sunita) or customer_id


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str
    user_id: str
    username: str
    merchant_id: str | None = None
    customer_id: str | None = None


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Authenticates username and bcrypt password, returning access and refresh JWTs."""
    client_ip = request.client.host if request.client else "unknown"
    stmt = select(User).where(User.username == payload.username)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password_hash):
        # Record security event for failed login attempt
        failed_audit = AuditLog(
            case_id="AUTH_FAIL",
            actor=payload.username,
            action="login_failure",
            detail={"reason": "invalid_credentials", "username": payload.username},
            ip_address=client_ip,
        )
        db.add(failed_audit)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated",
        )

    token_data: dict[str, Any] = {
        "sub": user.id,
        "username": user.username,
        "role": user.role,
        "merchant_id": user.merchant_id,
        "customer_id": user.customer_id,
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    success_audit = AuditLog(
        case_id="AUTH_SUCCESS",
        actor=user.username,
        action="login_success",
        detail={"role": user.role, "user_id": user.id},
        ip_address=client_ip,
    )
    db.add(success_audit)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        role=user.role,
        user_id=user.id,
        username=user.username,
        merchant_id=user.merchant_id,
        customer_id=user.customer_id,
    )


@router.post("/demo-token", response_model=TokenResponse)
async def demo_token(
    payload: DemoTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """Convenience shortcut for hackathon judges & testers when DEMO_MODE=true.

    Strictly rejected with 403 when DEMO_MODE=false.
    """
    if not settings.DEMO_MODE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo token shortcut is disabled in non-demo mode",
        )

    # Map requested role or specific target_id to demo account
    username_lookup = {
        "merchant": "merchant_ramesh",
        "traveller": "traveller_arjun",
        "ops_agent": "ops_agent_1",
        "admin": "admin_user",
    }

    if payload.role == "merchant" and payload.target_id == "m_sunita":
        target_username = "merchant_sunita"
    else:
        target_username = username_lookup.get(payload.role)

    if not target_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid demo role '{payload.role}'. Choose merchant, traveller, ops_agent, admin.",
        )

    stmt = select(User).where(User.username == target_username)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Demo user for '{target_username}' not found. Run db seed first.",
        )

    token_data: dict[str, Any] = {
        "sub": user.id,
        "username": user.username,
        "role": user.role,
        "merchant_id": user.merchant_id,
        "customer_id": user.customer_id,
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        role=user.role,
        user_id=user.id,
        username=user.username,
        merchant_id=user.merchant_id,
        customer_id=user.customer_id,
    )


@router.post("/refresh")
async def refresh_token_endpoint(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Issues a new short-lived access token using a valid refresh token."""
    decoded = decode_token(payload.refresh_token)
    if not decoded or decoded.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user_id = decoded.get("sub")
    stmt = select(User).where(User.id == user_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    token_data: dict[str, Any] = {
        "sub": user.id,
        "username": user.username,
        "role": user.role,
        "merchant_id": user.merchant_id,
        "customer_id": user.customer_id,
    }
    new_access = create_access_token(token_data)
    return {"access_token": new_access, "token_type": "bearer"}


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Returns profile details of the currently authenticated user."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role,
        "merchant_id": current_user.merchant_id,
        "customer_id": current_user.customer_id,
        "is_active": current_user.is_active,
    }
