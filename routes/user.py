from fastapi import (
    Depends,
    HTTPException,
    Request,
    status,
    APIRouter,
)

from sqlalchemy.orm import Session
from database import get_session
from models.base import RoleTypes, TokenData, UserShow, UserUpdate
from oauth import get_current_user

from repository.user import delete_user, get_users, update_user
from settings import get_settings

settings = get_settings()

userRouter = APIRouter(prefix="/api/user", tags=["User"])

adminUsers = [ut.name for ut in RoleTypes][:2]


@userRouter.get("/", summary="Get list of users (json)")
def api_get_users(
    request: Request,
    session: Session = Depends(get_session),
    user: TokenData = Depends(get_current_user),
):

    if user.role not in adminUsers:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not Authorized",
        )

    users = get_users(session)

    return users


@userRouter.patch(
    "/{id}", response_model=UserShow, summary="Update a user with a Pydantic model"
)
def api_save_user(
    id: int,
    upd_user: UserUpdate,
    request: Request,
    session: Session = Depends(get_session),
    user: TokenData = Depends(get_current_user),
):
    if user.role not in adminUsers:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not Authorized",
        )

    try:
        edituser = update_user(session, id, upd_user, user)
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ex),
        )

    return edituser


@userRouter.delete("/{id}", summary="Delete a user")
def api_delete_user(
    id: int,
    session: Session = Depends(get_session),
    user: TokenData = Depends(get_current_user),
):

    if user.role not in adminUsers:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not Authorized",
        )

    try:
        user = delete_user(session, id, user)
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ex),
        )

    return user
