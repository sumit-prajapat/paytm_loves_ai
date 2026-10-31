from typing import Annotated
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.models import User
from app.db.session import get_db

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(security_scheme)],
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validates the Bearer JWT access token and returns the authenticated User."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    stmt = select(User).where(User.id == user_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or account deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_user_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(security_scheme)],
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Optional authentication helper for mixed public/authenticated routes."""
    if not credentials or not credentials.credentials:
        return None

    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    stmt = select(User).where(User.id == user_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    return user if user and user.is_active else None


def require_roles(allowed_roles: list[str]):
    """Role-Based Access Control (RBAC) dependency factory."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Role '{current_user.role}' is not authorized. Allowed: {allowed_roles}",
            )
        return current_user

    return role_checker


def verify_merchant_ownership(merchant_id: str, current_user: User) -> None:
    """Object-Level Authorization (IDOR Prevention):

    - Merchants may ONLY read or act on their assigned merchant_id.
    - ops_agent and admin may access across merchants.
    - Other roles are rejected with 403.
    """
    if current_user.role == "merchant":
        if current_user.merchant_id != merchant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden (IDOR Violation): You are authenticated as merchant '{current_user.merchant_id}' and cannot access data for '{merchant_id}'.",
            )
        return

    if current_user.role in ["ops_agent", "admin"]:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Forbidden: Role '{current_user.role}' cannot access merchant resources.",
    )


def verify_traveller_ownership(customer_id: str, current_user: User) -> None:
    """Object-Level Authorization (IDOR Prevention):

    - Travellers may ONLY access their own travel itinerary / session.
    - ops_agent and admin may access across users.
    - Other roles are rejected with 403.
    """
    if current_user.role == "traveller":
        if current_user.customer_id != customer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden (IDOR Violation): You are authenticated as traveller '{current_user.customer_id}' and cannot access sessions for '{customer_id}'.",
            )
        return

    if current_user.role in ["ops_agent", "admin"]:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Forbidden: Role '{current_user.role}' cannot access traveller sessions.",
    )
