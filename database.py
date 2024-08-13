from sqlmodel import Session, create_engine, text

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
