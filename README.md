# FastAPI starter project with user admin using JWT, Jinja2 templates and HTMX

## Quickstart run from repo:
```
git clone https://github.com/jsoques/fastapi-user-admin-starter.git
cd fastapi-user-admin-starter
python -m venv venv
source venv/bin/activate
mkdir -p www/static
pip install fastapi[standard] sqlmodel pydantic-settings bcrypt pyjwt python-multipart
uvicorn main:app --reload --port 8888 --host 0.0.0.0
```
You can now visit http://localhost:8888

## How to setup: 

Let's assume we will create a project directory called **fastapi_htmx_demo** 

```
mkdir fastapi_htmx_demo
cd fastapi_htmx_demo
```

We need to create a Python 3 virtual environment (assuming the ve folder will be **venv**:

```
python3 -m venv venv
```

Let's activate the virtual environment:
```
source venv/bin/activate
```
or
```
. venv/bin/activate
```
Your console prompt should indicate that the ve is active with the text 'venv'

Let's check for updates (usually only pip should be installed):
```
pip list -o
```
update if necessary:
```
pip install --upgrade pip
```

Now install the necessary packages:
```
pip install fastapi[standard] sqlmodel pydantic-settings bcrypt pyjwt python-multipart
```

## How to run the project:

(assuming port **8888**):
```
uvicorn main:app --reload --port 8888 --host 0.0.0.0
```
visit http://localhost:8888/admin






