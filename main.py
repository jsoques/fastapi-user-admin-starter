from contextlib import asynccontextmanager
import time
from fastapi import Depends, FastAPI, Request, Response
from fastapi.applications import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlmodel import SQLModel, Session, text
from database import engine
from models.base import Role, TokenData, User, UserCreate


# htmlgenerator (alternative)
from htmlgenerator import (
    BODY,
    DIV,
    H1,
    HEAD,
    HEADER,
    HTML,
    LI,
    LINK,
    MAIN,
    NAV,
    SCRIPT,
    STRONG,
    STYLE,
    TITLE,
    UL,
    render,
    mark_safe as s,
)

from oauth import get_current_user
from settings import get_settings

settings = get_settings()

menu = [{"Users": "users"}, {"Roles": "roles"}, {"Reports": "reports"}]


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


description = (
    "Sample FastAPI with SQLModel, HTMx, PICOCss and pure Python html generation"
)
version = "00.01.00"
devmode = True

app = FastAPI(
    title="Demo",
    description=description,
    version=f"{version}",
    lifespan=lifespan,
    debug=devmode,
)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=86400,
)


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

    if "*/*" in accept:
        hxrequest = request.headers.get("hx-request")
        if hxrequest and "true" == hxrequest:
            izcookie = request.cookies.get("iz_session")
            auth = ""
            if izcookie:
                auth = "Bearer " + izcookie

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


def getMenu():
    for m in menu:
        yield m


@app.exception_handler(404)
def custom_404_handler(_, __):
    """
    Redirect all 404 to root.
    """
    return RedirectResponse("/")


base_content = HTML(
    HEAD(
        TITLE("Main Page"),
        LINK(
            rel="stylesheet",
            href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css",
        ),
        SCRIPT(
            src="https://unpkg.com/htmx.org@2.0.1",
            integrity="sha384-QWGpdj554B4ETpJJC9z+ZHJcA/i59TyjxEPXiiUgN2WmTyV5OEZWCD6gQhgkdpB/",
            crossorigin="anonymous",
        ),
        STYLE(
            ".pointer {cursor: pointer;}",
            ".header {background-color: silver !important; padding: 30px; text-align: center; font-size: 35px;  color: blue;}",
            ".main {padding: 20px; background-color: #f1f1f1; height: 300px;}",
        ),
    ),
    BODY(
        SCRIPT(
            s(
                """document.body.addEventListener('htmx:afterOnLoad', function (evt)
                      {if(evt.detail.xhr.status == 401){
                      console.log(evt.detail.requestConfig);
                      window.location.replace('login');
                      }
                      });"""
            )
        ),
        HEADER(H1("Main Page", _class="header")),
        DIV(
            NAV(
                UL(LI(STRONG("MYAPP"))),
                UL(
                    *[
                        LI(
                            list(item.keys())[0],
                            _class="pointer",
                            hx_get=f"/item/{list(item.values())[0]}",
                            hx_target="#main",
                        )
                        for item in menu
                    ],
                    _class="menu",
                ),
            )
        ),
        _class="container",
    ),
    MAIN("Hello World", _class="main", id="main"),
    doctype=True,
)


@app.get("/", response_class=HTMLResponse)
def default():
    content = HTML(
        HEAD(
            TITLE("Main Page"),
            LINK(
                rel="stylesheet",
                href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css",
            ),
            SCRIPT(
                src="https://unpkg.com/htmx.org@2.0.1",
                integrity="sha384-QWGpdj554B4ETpJJC9z+ZHJcA/i59TyjxEPXiiUgN2WmTyV5OEZWCD6gQhgkdpB/",
                crossorigin="anonymous",
            ),
            STYLE(
                ".pointer {cursor: pointer;}",
                ".header {background-color: silver !important; padding: 30px; text-align: center; font-size: 35px;  color: blue;}",
                ".main {padding: 20px; background-color: #f1f1f1; height: 300px;}",
            ),
        ),
        BODY(
            SCRIPT(
                s(
                    """document.body.addEventListener('htmx:afterOnLoad', function (evt)
                      {if(evt.detail.xhr.status == 401){
                      console.log(evt.detail.requestConfig);
                      window.location.replace('login');
                      }
                      });"""
                )
            ),
            HEADER(H1("Main Page", _class="header")),
            DIV(
                NAV(
                    UL(LI(STRONG("MYAPP"))),
                    UL(
                        *[
                            LI(
                                list(item.keys())[0],
                                _class="pointer",
                                hx_get=f"/item/{list(item.values())[0]}",
                                hx_target="#main",
                            )
                            for item in menu
                        ],
                        _class="menu",
                    ),
                )
            ),
            _class="container",
        ),
        MAIN("Hello World", _class="main", id="main"),
        doctype=True,
    )
    return render(content, {})


@app.get("/item/{item}")
def get_item(item: str, user: TokenData = Depends(get_current_user)):

    return f"{item}"


@app.get("/login", response_class=HTMLResponse)
def login():
    return "Login"
