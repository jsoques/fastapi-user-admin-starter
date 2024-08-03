from pydantic import BaseModel
from sqlmodel import Field, Index, Relationship, SQLModel


class TokenData(BaseModel):
    sub: int
    user_name: str
    organization: str
    orgid: int
    role: str
    accepted_tc: bool | None = None
    tenant: str | None = None
    impersonated: bool
    impersonated_by: str | None = None


class Role(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    user: list["User"] = Relationship(back_populates="role")


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    email: str = Field(index=True)
    hashed_password: str
    role_id: int | None = Field(default=None, foreign_key="role.id")
    role: Role | None = Relationship(back_populates="user")

    __table_args__ = (Index("index_user", "email", unique=True),)


class UserCreate(SQLModel):
    name: str = Field(index=True)
    email: str = Field(index=True)
    tenant_id: int | None = Field(default=None, foreign_key="tenant.id")
