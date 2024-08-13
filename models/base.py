from datetime import datetime
import enum
from pydantic import BaseModel
from sqlmodel import (
    Column,
    DateTime,
    Field,
    Index,
    Relationship,
    SQLModel,
    Session,
    func,
    text,
)
from database import engine


class TokenData(BaseModel):
    sub: int
    user_name: str
    organization: str
    orgid: int
    role: str
    accepted_tc: bool | None = None
    impersonated: bool
    impersonated_by: str | None = None


class Role(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    user: list["User"] = Relationship(back_populates="role")


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    email: str = Field(index=True, unique=True)
    enabled: bool = Field(default=False)
    deleted: bool = Field(default=False)
    change_pwd: bool = Field(default=False)
    verify_key: str | None = None
    hashed_password: str
    phone: str | None = None
    last_login: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    pwd_updated_on: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    role_id: int | None = Field(default=None, foreign_key="role.id")
    role: Role | None = Relationship(back_populates="user")
    created_on: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    created_by: int | None = Field(default=None, foreign_key="user.id")
    modified_on: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    modified_by: int | None = Field(default=None, foreign_key="user.id")
    creator: list["User"] = Relationship(
        sa_relationship_kwargs=dict(
            remote_side="User.id", primaryjoin="User.id == User.created_by"
        ),
    )
    modifier: list["User"] = Relationship(
        sa_relationship_kwargs=dict(
            remote_side="User.id", primaryjoin="User.id == User.modified_by"
        ),
    )

    __table_args__ = (Index("index_user", "email", unique=True),)


class UserShow(SQLModel):
    id: int
    name: str
    email: str
    role_id: int
    created_by: int
    enabled: bool
    created_on: datetime


class UserUpdate(SQLModel):
    name: str
    email: str
    role_id: int


class UserCreate(UserUpdate):
    password: str
    rpassword: str


with Session(engine) as session:
    names = []
    try:
        sql_role_types = """SELECT name, id FROM role ORDER BY id"""
        role_types = session.exec(text(sql_role_types)).fetchall()
        if len(role_types) == 0:
            newRole = Role(name="Superuser")
            session.add(newRole)
            session.commit()
            role_types = session.exec(text(sql_role_types)).fetchall()
        for utype in role_types:
            names.append(tuple(utype))
    except Exception:
        try:
            SQLModel.metadata.tables["role"].create(engine)
            newRole = Role(name="Superuser")
            session.add(newRole)
            session.commit()
            role_types = session.exec(text(sql_role_types)).fetchall()
            for utype in role_types:
                names.append(tuple(utype))
        except Exception:
            pass
        pass

    RoleTypes = enum.Enum("RoleTypes", names)
