from datetime import datetime
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
from sqlalchemy.orm import Session
from sqlmodel import select
from database import get_session

from models.base import Role, RoleTypes, TokenData, User, UserCreate, UserShow
from oauth import create_access_token, get_current_user, get_current_user_from_cookie

from repository.user import create_user, delete_user, get_users, update_user
from settings import get_settings

settings = get_settings()

cookie_name = settings.COOKIE_NAME

templates = Jinja2Templates(directory="www/templates")

webuserRouter = APIRouter(prefix="/user", tags=["Web User"])

adminUsers = [ut.name for ut in RoleTypes][:2]


@webuserRouter.get(
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

    users = get_users(session)

    # accept = request.headers.get("accept")

    return templates.TemplateResponse(
        request=request,
        name="userlist.html",
        context={"item": "User", "list": users, "morejsscripts": ""},
    )


@webuserRouter.get(
    "/edit/{id}",
    response_class=HTMLResponse,
    include_in_schema=True,
    summary="Get user edit form",
)
def web_edit_user(
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

    try:
        stmnt = select(User).join(Role, isouter=True).filter(User.id == id)

        edituser = session.exec(statement=stmnt).first()
        if not edituser:
            raise Exception("Not found")
    except Exception:
        print("fik")
        edituser: UserShow = UserShow(
            id=0,
            name="",
            email="",
            role_id=0,
            enabled=False,
            created_on=datetime.now(),
            created_by=0,
        )
        pass

    stmnt = select(Role)

    roles = session.exec(statement=stmnt).all()

    roleselect = """<select name="role" id="role">"""

    for role in roles:
        roleselect += f"""<option value="{role.id}" {"selected" if edituser.role_id == role.id else ""}>{role.name}</option>"""
    roleselect += """</select>"""

    htmledit = f"""<tr id="rowid_{edituser.id}">
                    <td><input type='text' name="username" value="{edituser.name}" required /></td>
                    <td><input type='email' name="useremail" value="{edituser.email}" required /></td>
                    <td>{roleselect}</td>
                    <td class="pointer" 
                        hx-post="user/edit/{edituser.id}" 
                        hx-target="#rowid_{edituser.id}" 
                        hx-swap="outerHTML"
                        hx-include="[name='username'],[name='useremail'],[name='role']"
                        hx-on::before-request="document.getElementById('addbutton').disabled = false">✅</td>
                    <td style="filter: grayscale(100%);" disabled>🗑</td>
                </tr>"""

    return htmledit


@webuserRouter.post(
    "/edit/{id}",
    response_class=HTMLResponse,
    include_in_schema=True,
    summary="Save a edited user",
)
def web_save_user(
    id: int,
    username: Annotated[str, Form()],
    useremail: Annotated[str, Form()],
    role: Annotated[str, Form()],
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

    updated_user: User = User(
        name=username,
        email=useremail,
        role_id=int(role),
    )

    errort = ""
    try:
        edituser = update_user(session, id, updated_user, user)
    except Exception as ex:
        print(ex)
        message = str(ex.args)
        if "UNIQUE constraint failed" in str(ex):
            message = "User email already exists! Cannot save user."
        stmnt = select(User).join(Role, isouter=True).filter(User.id == id)
        edituser = session.exec(statement=stmnt).first()
        errort = templates.TemplateResponse(
            request=request,
            name="error.html",
            context={"error": message},
        )
        errort = errort.body.decode("utf-8")

    htmledit = f"""<tr id="rowid_{edituser.id}">
                    <td>{edituser.name}</td>
                    <td>{edituser.email}</td>
                    <td>{edituser.role.name}</td>
                    <td class="pointer" 
                        hx-get="user/edit/{edituser.id}" 
                        hx-target="#rowid_{edituser.id}"
                        hx-swap="outerHTML"
                        hx-on::before-request="document.getElementById('addbutton').disabled = true">📝</td>
                    <td class="pointer">🗑</td>
                </tr>
                {errort}
                """

    return htmledit


@webuserRouter.get("/create", response_class=HTMLResponse, include_in_schema=True)
def get_create_user_page(request: Request, session: Session = Depends(get_session)):

    stmnt = select(User, Role).join(Role, isouter=True)
    users: list[User] | None = session.exec(statement=stmnt).all()

    message = (
        ""
        if not request.query_params.get("message")
        else request.query_params.get("message")
    )

    if len(users) == 0:

        # Create first super duper user

        return templates.TemplateResponse(
            request=request,
            name="createuser.html",
            context={
                "title": "Create Super Duper User",
                "roles": None,
                "message": "",
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

    stmnt = select(Role)

    roles = session.exec(statement=stmnt).all()

    # check if user is admin
    return templates.TemplateResponse(
        request=request,
        name="createuser.html",
        context={
            "title": "Create User",
            "roles": roles,
            "message": message,
            "target": "#main",
            "morejsscripts": "",
        },
    )


@webuserRouter.post("/create", response_class=HTMLResponse, include_in_schema=True)
def web_create_user(
    request: Request,
    role: Annotated[str, Form()],
    username: Annotated[str, Form()],
    useremail: Annotated[str, Form()],
    password: Annotated[str, Form()],
    rpassword: Annotated[str, Form()],
    session: Session = Depends(get_session),
):

    stmnt = select(User, Role).join(Role, isouter=True)
    users: list[User] | None = session.exec(statement=stmnt).all()

    if len(users) == 0:

        new_user: UserCreate = UserCreate(
            name=username,
            email=useremail,
            password=password,
            rpassword=rpassword,
            role_id=int(role),
        )

        errort = ""
        try:
            newUser = create_user(
                session,
                new_user,
            )
        except Exception as ex:
            message = str(ex)
            if "Passwords do not match!" in message:
                errort = templates.TemplateResponse(
                    request=request,
                    name="error.html",
                    context={"error": "Passwords do no match!"},
                )
            else:
                errort = templates.TemplateResponse(
                    request=request,
                    name="error.html",
                    context={"error": "Some error (fix me!)"},
                )

            errort = errort.body.decode("utf-8")

            return templates.TemplateResponse(
                request=request,
                name="createuser.html",
                context={
                    "title": "Create Super Duper User",
                    "roles": None,
                    "message": "",
                    "target": "body",
                    "username": username,
                    "useremail": useremail,
                    "morejsscripts": errort,
                },
            )

        data = {
            "sub": str(newUser.id),
            "user_name": newUser.email,
            "organization": "",
            "orgid": 0,
            "role": newUser.role.name,
            "accepted_tc": None,
            "impersonated": False,
            "impersonated_by": None,
        }

        access_token = create_access_token(data)

        response = RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            key=cookie_name,
            value=f"{access_token}",
            max_age=settings.JWT_EXPIRE * 60,
            expires=settings.JWT_EXPIRE * 60,
            secure=False,
            samesite="strict",
            httponly=True,
        )
        return response

    # get cookie to check user
    cookie = None

    if request.cookies.get(cookie_name):
        cookie = request.cookies.get(cookie_name)

    if not cookie:
        # redirect to login
        return RedirectResponse("/login")

    user = get_current_user(cookie)

    try:
        new_user: UserCreate = UserCreate(
            name=username,
            email=useremail,
            password=password,
            rpassword=rpassword,
            role_id=int(role),
        )
        # session.commit()
        newUser = create_user(session, new_user, user)

        errort = ""
    except Exception as ex:
        print(ex)
        if "UNIQUE constraint failed" in str(ex):
            session.rollback()
            message = "User email already exists! Cannot add user."
        errort = templates.TemplateResponse(
            request=request,
            name="error.html",
            context={"error": message},
        )

        errort = errort.body.decode("utf-8")

    stmnt = select(User).join(Role, isouter=True)

    users = session.exec(statement=stmnt).all()

    return templates.TemplateResponse(
        request=request,
        name="userlist.html",
        context={
            "item": "User",
            "list": users,
            "morejsscripts": errort,
        },
    )


@webuserRouter.delete("/{id}", response_class=HTMLResponse, include_in_schema=True)
def web_delete_user(
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

    try:
        _ = delete_user(session, id, user)
    except Exception as ex:
        errort = templates.TemplateResponse(
            request=request,
            name="error.html",
            context={"error": str(ex)},
        )
        return errort

    users = get_users(session)

    return templates.TemplateResponse(
        request=request,
        name="userlist.html",
        context={"item": "User", "list": users, "morejsscripts": ""},
    )
