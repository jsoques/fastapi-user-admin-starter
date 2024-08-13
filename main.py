from contextlib import asynccontextmanager
import time
from typing import Annotated
from fastapi import Depends, FastAPI, Form, HTTPException, Request, Response, status
from fastapi.applications import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import SQLModel, Session, select, text
from database import engine, get_session
from models.base import Role, TokenData, User, RoleTypes

from oauth import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_current_user_from_cookie,
)
from settings import get_settings
from utils import verify_password
from routes.user import userRouter
from routes.role import roleRouter
from routes.webuser import webuserRouter
from routes.webrole import webroleRouter


settings = get_settings()

menu = [{"Users": "users"}, {"Roles": "roles"}]

cookie_name = settings.COOKIE_NAME


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Startup...(code here for startup stuff...)")
    print(f"--> App Version: {app.version}")

    with Session(engine) as session:
        tables = session.exec(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        ).all()

        if not any(filter(lambda table: table.name == "role", tables)):
            try:
                SQLModel.metadata.tables["role"].create(engine)
                newRole = Role(name="Superuser")
                session.add(newRole)
                session.commit()
            except Exception as ex:
                if "already exists" not in str(ex):
                    print("lifespan Role create", ex)

        if not any(filter(lambda table: table.name == "user", tables)):
            try:
                SQLModel.metadata.tables["user"].create(engine)
            except Exception as ex:
                if "already exists" not in str(ex):
                    print("lifespan User create", ex)

    yield
    print("Shutting down...")
    with Session(engine) as session:
        session.exec(text("PRAGMA analysis_limit=400"))
        session.exec(text("PRAGMA optimize"))
        session.commit()
        engine.dispose()
    print("Shutdown")


description = "Sample FastAPI with SQLModel, Jinja2 Templating with HTMX and PICOCss"
version = "00.01.00"
devmode = True

app = FastAPI(
    title="Demo",
    description=description,
    version=f"{version}",
    lifespan=lifespan,
    debug=devmode,
)

app.mount("/static", StaticFiles(directory="www/static"), name="static")

templates = Jinja2Templates(directory="www/templates")

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=86400,
)

app.include_router(userRouter)
app.include_router(roleRouter)
app.include_router(webuserRouter)
app.include_router(webroleRouter)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """
    Middleware function that adds a process time header to the HTTP response.

    Parameters:
    - request: The incoming HTTP request object.
    - call_next: The function to call to proceed with the request handling.

    Returns:
    - The HTTP response object.

    Description:
    This function is a middleware that adds a process time header to the HTTP response. It calculates the time taken to process the request and adds it to the response headers. The function also logs the request and response details in the database.

    The function first retrieves the Authorization header from the request and extracts the user information if a Bearer token is present. It then creates a database session based on the user's tenant. If no user is found, a session with the default schema is created.

    Next, the function extracts the request headers and origin from the request. If the origin is not available, it uses the host header. It also retrieves the client IP address from the request.

    The function then processes the request details, including the request parameters and headers. It removes sensitive information from the headers and logs the request details in the database.

    After processing the request details, the function checks the client IP address. If the IP address is not localhost or a test client and does not start with "172.", it queries the database for the IP location. If the IP is not found in the database, it retrieves the IP location using an external API and saves it in the database.

    If the IP is blocked in the database, the function returns an HTTP 418 response with the "X-Big-Brother" header set to "I am watching you". Otherwise, it proceeds with the request handling.

    The function measures the time taken to process the request and adds it to the response headers. It also applies secure headers to the response.

    Finally, the function logs the response details in the database and returns the response object.
    """  # noqa: E501
    # print("Request middleware...")

    if "/static/" in request.url.path:
        response: Response = await call_next(request)
        return response

    accept = request.headers.get("accept")

    auth = str(request.headers.get("Authorization"))

    if not request.cookies.get(cookie_name):
        auth = ""
        for h in request.headers.__dict__["_list"]:
            # print(h)
            if h[0].decode("ASCII") == "authorization":
                request.headers.__dict__["_list"].remove(h)

    if "*/*" in accept:
        hxrequest = request.headers.get("hx-request")
        if hxrequest and "true" == hxrequest:
            zcookie = request.cookies.get(cookie_name)
            auth = ""
            if zcookie:
                auth = "Bearer " + zcookie

    user = ""
    if "Bearer" in auth:
        token = auth.split(" ")[1]
        if token:
            try:
                user = get_current_user(token)
            except Exception:
                user = ""
                pass

    print(user)

    hdr = str(request.headers).replace("Headers(", "")
    hdr = hdr[: len(hdr) - 1]
    origin = request.headers.get("origin")
    if not origin and request.headers.get("host"):
        origin = request.headers.get("host")

    try:
        clientIp = request.client.host
    except Exception:
        clientIp = request.headers["host"]  # request.client.host

    start_time = time.time()
    response: Response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    reqstr = f" --> request>> url.path:{request.url.path}"
    reqstr += f", method:{request.method}"
    reqstr += f", client.host:{clientIp}"
    reqstr += f", origin:{origin}"
    reqstr += f", clientIp:{clientIp}"

    # print("Response middleware")
    return response


@app.exception_handler(404)
def custom_404_handler(_, __):
    """
    Redirect all 404 to root.
    """
    return RedirectResponse("/admin")


@app.exception_handler(403)
def custom_403_handler(_, __):
    """
    Redirect all 403 to login.
    """
    return RedirectResponse("/login")


@app.get("/test", response_class=HTMLResponse, include_in_schema=False)
def test(request: Request, user: TokenData = Depends(get_current_user_from_cookie)):
    return f"{user}"


@app.get("/test2", response_class=HTMLResponse, include_in_schema=False)
def test2(request: Request):
    try:
        user: TokenData = get_current_user_from_cookie(request)
    except Exception as ex:
        errort = templates.TemplateResponse(
            request=request,
            name="error.html",
            context={"error": ex.detail},
        )
        return errort
    return f"{user}"


@app.get(
    "/favicon.ico", include_in_schema=False
)  # Prevent 404 for browser trying to get favico
def get_favico():
    return None


@app.get("/admin", response_class=HTMLResponse, include_in_schema=False)
def default(request: Request):

    cookie = None

    if request.cookies.get(cookie_name):
        cookie = request.cookies.get(cookie_name)

    loginout = "Login" if not cookie else "Logout"

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"cookie": cookie, "loginout": loginout},
    )


@app.get("/login", response_class=HTMLResponse, include_in_schema=False)
def getlogin(request: Request, session: Session = Depends(get_session)):

    stmnt = select(User, Role).join(Role, isouter=True)
    users: list[User] | None = session.exec(statement=stmnt).all()

    message = (
        ""
        if not request.query_params.get("message")
        else request.query_params.get("message")
    )

    if len(users) == 0:
        return RedirectResponse("/user/create")

    if request.cookies.get(cookie_name) is None:

        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"message": message},
            # status_code=status.HTTP_401_UNAUTHORIZED,
        )


@app.post("/login")
def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
):

    accept = request.headers.get("accept")

    stmnt = (
        select(User, Role)
        .join(Role, isouter=True)
        .where(User.email == form_data.username)
    )
    userdata: User | None = session.exec(statement=stmnt).all()

    if len(userdata) > 0:
        userdata = userdata[0]

    if len(userdata) == 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    user = userdata.User
    role = userdata.Role

    hashed_pass = user.hashed_password
    if not verify_password(form_data.password, hashed_pass):
        if "json" in accept:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )

    data = {
        "sub": str(user.id),
        "user_name": user.email,
        "organization": "",
        "orgid": 0,
        "role": role.name,
        "accepted_tc": None,
        "impersonated": False,
        "impersonated_by": None,
    }

    access_token = create_access_token(data)

    if "json" not in accept:
        if access_token:  # request.cookies.get(cookie_name):
            if request.headers.get("referer"):
                http_referer = request.headers.get("referer")
                if http_referer.endswith("login"):
                    http_referer = http_referer[0 : len(http_referer) - 5]
                response = RedirectResponse(
                    url=http_referer, status_code=status.HTTP_303_SEE_OTHER
                )
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

    response.set_cookie(
        key=cookie_name,
        value=f"{access_token}",
        max_age=settings.JWT_EXPIRE * 60,
        expires=settings.JWT_EXPIRE * 60,
        secure=False,
        samesite="strict",
        httponly=True,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": create_refresh_token(data),
    }


@app.get("/logout", response_class=HTMLResponse, include_in_schema=False)
def logout(request: Request):
    message = ""
    response = RedirectResponse(
        url="/admin", status_code=303, headers={"X-Logout-Message": message}
    )
    response.set_cookie(
        key=cookie_name,
        value="",
        max_age=-1,
        expires=-1,
        secure=False,
        samesite="strict",
        httponly=True,
    )
    return response
