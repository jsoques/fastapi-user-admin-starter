from fastapi import (
    Depends,
    HTTPException,
    Request,
    status,
    APIRouter,
)
from sqlmodel import Session

from database import get_session
from models.base import RoleTypes, TokenData
from oauth import get_current_user
from repository.role import delete_role, get_roles
from settings import get_settings

settings = get_settings()

roleRouter = APIRouter(prefix="/api/role", tags=["Role"])

adminUsers = [ut.name for ut in RoleTypes][:2]


@roleRouter.get("/", summary="Get list of roles (json)")
def api_get_roles(
    session: Session = Depends(get_session),
    user: TokenData = Depends(get_current_user),
):
    if user.role not in adminUsers:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not Authorized",
        )

    roles = get_roles(session)

    return roles


@roleRouter.delete("/{id}", summary="Delete a role")
def api_delete_role(
    id: int,
    session: Session = Depends(get_session),
    user: TokenData = Depends(get_current_user),
):
    if user.role not in adminUsers:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not Authorized",
        )

    role = delete_role(session, id, user)

    return role
