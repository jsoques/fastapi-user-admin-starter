from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlmodel import Session, select

from models.base import Role, TokenData, User, UserCreate
from utils import hash_password


def get_users(session: Session):
    stmnt = (
        select(User).join(Role, isouter=True).filter(User.deleted == 0)
    )  # .where(text("deleted = 0"))

    users = session.exec(statement=stmnt).all()

    return users


def create_user(
    session: Session, newuser: UserCreate, adminuser: TokenData | None = None
):

    if newuser.password != newuser.rpassword:
        raise Exception("Passwords do not match!")

    stmnt = select(User, Role).join(Role, isouter=True)
    users: list[User] | None = session.exec(statement=stmnt).all()

    if len(users) > 0 and adminuser is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated",
        )

    # case when system is initialized with new DB
    if len(users) == 0:
        stmnt = select(Role)
        roles: list[Role] | None = session.exec(statement=stmnt).all()

        if len(roles) == 0:
            newRole = Role(name="Superuser")
            session.add(newRole)
            session.commit()
            session.refresh(newRole)
            suRole = newRole
        else:
            stmnt = select(Role).filter(Role.name == "Superuser")
            suRole: Role | None = session.exec(statement=stmnt).first()

        newUser = User(
            name=newuser.name,
            email=newuser.email,
            hashed_password=hash_password(newuser.password),
            role=suRole,
            enabled=True,
        )
        session.add(newUser)
        session.commit()
        session.refresh(newUser)
        newUser.created_by = newUser.id
        session.commit()

        return newUser

    # case there are already users in DB
    role = session.exec(select(Role).filter(Role.id == newuser.role_id)).first()

    newUser = User(
        role=role,
        name=newuser.name,
        email=newuser.email,
        hashed_password=hash_password(newuser.password),
        created_by=adminuser.sub,
    )
    session.add(newUser)

    try:
        session.commit()
        session.refresh(newUser)
        return newUser
    except Exception as ex:
        session.rollback()
        raise ex


def update_user(session: Session, user_id: int, upduser: User, adminuser: TokenData):
    stmnt = select(User).join(Role, isouter=True).filter(User.id == user_id)

    edituser = session.exec(statement=stmnt).first()

    if (
        edituser.name != upduser.name
        or edituser.email != upduser.email
        or edituser.role_id != upduser.role_id
    ):
        try:
            edituser.name = upduser.name
            edituser.email = upduser.email
            edituser.role_id = upduser.role_id
            edituser.modified_by = adminuser.sub
            edituser.modified_on = datetime.now(tz=timezone.utc)
            session.commit()
            session.refresh(edituser)
        except Exception as ex:
            session.rollback()
            raise ex

    return edituser


def delete_user(session: Session, userid: int, adminuser: TokenData):

    stmnt = select(User).filter(User.id == userid)

    user = session.exec(stmnt).first()

    if not user:
        raise Exception(f"User not found: id {userid}")

    user.deleted = True

    session.commit()
    session.refresh(user)

    return
