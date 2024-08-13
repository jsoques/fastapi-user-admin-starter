from sqlmodel import Session, select

from models.base import Role, TokenData


def get_roles(session: Session):
    stmnt = select(Role)

    roles = session.exec(statement=stmnt).all()

    return roles


def create_role(session: Session, rolename: str, adminuser: TokenData | None = None):

    newrole = Role(name=rolename)

    try:
        session.add(newrole)
        session.commit()
        session.refresh(newrole)
    except Exception as ex:
        session.rollback()
        raise ex


def delete_role(session: Session, roleid: int, adminuser: TokenData):

    result = False

    stmnt = select(Role).filter(Role.id == roleid)

    role = session.exec(stmnt).first()

    if role:
        result = True
        session.delete(role)
        session.commit()

    return result
