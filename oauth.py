from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional
import jwt
from sqlmodel import Session, select

from models.base import TokenData, User
from settings import get_settings
from database import engine

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def create_access_token(data: dict, expires_delta: Optional[int] = None) -> str:

    if expires_delta is not None:
        expires_delta = datetime.now(tz=timezone.utc) + expires_delta
    else:
        expires_delta = datetime.now(tz=timezone.utc) + timedelta(
            minutes=settings.JWT_EXPIRE
        )

    to_encode = data.copy()
    to_encode.update({"iat": datetime.now(tz=timezone.utc)})
    to_encode.update({"exp": expires_delta})
    to_encode.update({"iss": "emphasys-software.com"})
    to_encode.update({"aud": "izlottery.com"})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, settings.JWT_ALGO)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[int] = None) -> str:

    if expires_delta is not None:
        expires_delta = datetime.now(tz=timezone.utc) + expires_delta
    else:
        expires_delta = datetime.now(tz=timezone.utc) + timedelta(
            minutes=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES
        )

    to_encode = data.copy()
    to_encode.update({"iat": datetime.now(tz=timezone.utc)})
    to_encode.update({"exp": expires_delta})
    to_encode.update({"iss": "emphasys-software.com"})
    to_encode.update({"aud": "izlottery.com"})
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_REFRESH_SECRET_KEY, settings.JWT_ALGO
    )
    return encoded_jwt


def validate_access_token(token: str):
    """Convenience function just to validate a JWT token\nReturn Frue or False"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGO],
            audience="izlottery.com",
        )
        user_id = payload.get("sub")
        if user_id is None:
            return False

    except Exception as ex:
        print(ex)
        return False

    return True


def verify_access_token(token: str, credentials_exception, credentials_expired):
    """Verify a JWT token for endpoints"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGO],
            audience="izlottery.com",
        )

        user_id = payload.get("sub")

        if user_id is None:
            raise credentials_exception
        organization = payload.get("organization")
        orgid = payload.get("orgid")
        role = payload.get("role")
        user_name = payload.get("user_name")
        accepted_tc = payload.get("accepted_tc")
        tenant = payload.get("tenant")
        iztc = payload.get("iztc")
        impersonated = payload.get("impersonated")
        impersonated_by = payload.get("impersonated_by")
        token_data = TokenData(
            sub=user_id,
            user_name=user_name,
            organization=organization,
            orgid=orgid,
            role=role,
            accepted_tc=accepted_tc,
            tenant=tenant,
            iztc=iztc,
            impersonated=impersonated,
            impersonated_by=impersonated_by,
        )
        with Session(engine) as session:
            stmnt = select(User).where(User.email == user_name)
            user = session.exec(stmnt).first()

        if user is None:
            token_data = None
    except Exception as JWTError:

        if JWTError.args:
            if JWTError.args[0]:
                if "Signature verification failed" in str(JWTError.args[0]):
                    raise credentials_exception
                if "expired" in str(JWTError.args[0]):
                    raise credentials_expired
            raise credentials_exception
        raise credentials_exception

    return token_data


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> TokenData:
    """Returns current user from JWT"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    credentials_expired = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credentials have expired",
        headers={"WWW-Authenticate": "Bearer"},
    )
    return verify_access_token(token, credentials_exception, credentials_expired)
