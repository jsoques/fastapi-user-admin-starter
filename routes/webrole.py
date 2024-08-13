from typing import Annotated
from fastapi import (
    Depends,
    Form,
    Request,
    APIRouter,
    status,
)
from fastapi.applications import HTMLResponse
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from database import get_session
from models.base import Role, RoleTypes, TokenData, User
from oauth import get_current_user, get_current_user_from_cookie
from repository.role import create_role, delete_role, get_roles
from settings import get_settings

settings = get_settings()

cookie_name = settings.COOKIE_NAME

templates = Jinja2Templates(directory="www/templates")

webroleRouter = APIRouter(prefix="/role", tags=["Web Role"])

adminUsers = [ut.name for ut in RoleTypes][:2]


@webroleRouter.get(
    "/",
    response_class=HTMLResponse,
    include_in_schema=True,
    summary="Get list of users (html)",
)
def web_get_users(
    request: Request,
    session: Session = Depends(get_session),
    user: TokenData = Depends(get_current_user_from_cookie),
):

    adminUsers = [ut.name for ut in RoleTypes][:2]

    if user.role not in adminUsers:
        errort = templates.TemplateResponse(
            request=request,
            name="error.html",
            context={"error": "Not authorized!"},
        )
        return errort

    roles = get_roles(session)

    return templates.TemplateResponse(
        request=request,
        name="rolelist.html",
        context={"item": "Role", "list": roles},
    )


@webroleRouter.get("/create", response_class=HTMLResponse)
def get_create_role_page(request: Request, session: Session = Depends(get_session)):

    stmnt = select(User, Role).join(Role, isouter=True)
    users: list[User] | None = session.exec(statement=stmnt).all()

    if len(users) == 0:

        # Create first super duper user

        return templates.TemplateResponse(
            request=request,
            name="createuser.html",
            context={
                "title": "Create Super Duper User",
                "roles": None,
                "target": "body",
                "morejsscripts": "",
            },
        )

    # get cookie to check user
    cookie = None

    if request.cookies.get(cookie_name):
        cookie = request.cookies.get(cookie_name)

    if not cookie:
        # redirect to login
        return RedirectResponse("/login")

    user = get_current_user(cookie)

    print(user)

    # check if user is admin
    return templates.TemplateResponse(
        request=request,
        name="createrole.html",
        context={},
    )


@webroleRouter.post("/create", response_class=HTMLResponse)
def web_create_role(
    request: Request,
    rolename: Annotated[str, Form()],
    session: Session = Depends(get_session),
    user: TokenData = Depends(get_current_user_from_cookie),
):

    try:
        _ = create_role(session, rolename, user)
    except Exception as ex:
        return f"Error {ex}"

    # get cookie to check user
    cookie = None

    if request.cookies.get(cookie_name):
        cookie = request.cookies.get(cookie_name)

    if not cookie:
        # redirect to login
        return RedirectResponse("/login")

    stmnt = select(Role)
    roles = session.exec(statement=stmnt).all()

    return templates.TemplateResponse(
        request=request,
        name="rolelist.html",
        context={"item": "Role", "list": roles},
    )


@webroleRouter.delete("/{id}", response_class=HTMLResponse, include_in_schema=True)
def web_delete_role(
    id: int,
    request: Request,
    session: Session = Depends(get_session),
    user: TokenData = Depends(get_current_user_from_cookie),
):
    adminUsers = [ut.name for ut in RoleTypes][:2]

    if user.role not in adminUsers:
        errort = templates.TemplateResponse(
            request=request,
            name="error.html",
            context={"error": "Not authorized!"},
        )
        return errort

    _ = delete_role(session, id, user)

    roles = get_roles(session)

    return templates.TemplateResponse(
        request=request,
        name="rolelist.html",
        context={"item": "Role", "list": roles},
    )
