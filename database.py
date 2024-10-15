from sqlmodel import Session, create_engine, text

# from sqlalchemy.ext.compiler import compiles
# from sqlalchemy.sql.ddl import CreateTable


# @compiles(CreateTable, "sqlite")
# def tables_are_strict(create_table, compiler, **kw):
#     sqlddl = (
#         str(compiler.visit_create_table(create_table, **kw))
#         .strip()
#         .replace("VARCHAR", "TEXT")
#         .replace("BOOLEAN", "INT")
#         .replace("DATETIME", "TEXT")
#         + " STRICT"
#     )
#     return sqlddl


sqlite_file_name = "datastore/master.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
connect_args = {"check_same_thread": False}  # special case for SQLite

engine = create_engine(sqlite_url, echo=True, connect_args=connect_args)


with Session(engine) as session:
    session.exec(text("PRAGMA journal_mode = WAL"))
    session.exec(text("PRAGMA synchronous = normal"))
    session.exec(text("PRAGMA foreign_keys = on"))
    session.commit()


def get_db():
    db = Session(autoflush=False, bind=engine)
    try:
        yield db
    finally:
        db.close()


def get_session():
    with Session(engine) as session:
        yield session
