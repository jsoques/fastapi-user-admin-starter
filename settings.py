import os
from pydantic_settings import BaseSettings
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):

    JWT_SECRET: str = os.getenv("JWT_SECRET")
    JWT_ALGO: str = os.getenv("JWT_ALGO")
    JWT_EXPIRE: int = str(os.getenv("JWT_EXPIRE", 30))
    JWT_REFRESH_SECRET_KEY: str = os.getenv("JWT_REFRESH_SECRET_KEY")
    JWT_REFRESH_TOKEN_EXPIRE_MINUTES: int = str(
        os.getenv("JWT_REFRESH_TOKEN_EXPIRE_MINUTES", 300)
    )


@lru_cache()
def get_settings():
    return Settings()
