"""
3 user apis
"""
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse
from mysql.connector import Error, IntegrityError
from pydantic import BaseModel

from attraction_api import get_database_connection

router = APIRouter()
JWT_SECRET = os.getenv(
    "JWT_SECRET",
    "taipei-day-trip-development-secret-change-in-production",
)
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 7


class UserRegistration(BaseModel):
    name: str
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class SuccessResponse(BaseModel):
    ok: bool


class TokenResponse(BaseModel):
    token: str


class UserData(BaseModel):
    id: int
    name: str
    email: str


class AuthResponse(BaseModel):
    data: UserData | None


class ErrorResponse(BaseModel):
    error: bool
    message: str


def hash_password(password: str) -> str:
    iterations = 600_000
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        iterations,
    ).hex()
    return f"pbkdf2_sha256${iterations}${salt}${password_hash}"


def verify_password(password: str, stored_password: str) -> bool:
    try:
        algorithm, iterations, salt, expected_hash = stored_password.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False

        password_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt),
            int(iterations),
        ).hex()
        return hmac.compare_digest(password_hash, expected_hash)
    except (TypeError, ValueError):
        return False


def create_access_token(user: dict) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "iat": now,
        "exp": now + timedelta(days=TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        JWT_SECRET,
        algorithms=[JWT_ALGORITHM],
        options={"require": ["id", "name", "email", "exp"]},
    )


@router.post(
    "/api/user",
    response_model=SuccessResponse,
    responses={
        400: {
            "model": ErrorResponse,
            "description": "註冊失敗，重複的 Email 或其他原因",
        },
        500: {
            "model": ErrorResponse,
            "description": "伺服器內部錯誤",
        },
    },
)
def register_user(user: UserRegistration):
    connection = None
    cursor = None
    name = user.name.strip()
    email = user.email.strip().lower()

    if not name or not email or not user.password:
        return JSONResponse(
            status_code=400,
            content={"error": True, "message": "姓名、Email 和密碼皆為必填"},
        )

    if "@" not in email:
        return JSONResponse(
            status_code=400,
            content={"error": True, "message": "Email 格式不正確"},
        )

    try:
        connection = get_database_connection()
        cursor = connection.cursor()

        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
            (name, email, hash_password(user.password)),
        )
        connection.commit()
        return {"ok": True}
    except IntegrityError as error:
        if connection is not None:
            connection.rollback()

        if error.errno == 1062:
            return JSONResponse(
                status_code=400,
                content={"error": True, "message": "此 Email 已經註冊過"},
            )

        print(f"user registration integrity error: {error}")
        return JSONResponse(
            status_code=400,
            content={"error": True, "message": "註冊資料不符合要求"},
        )
    except Error as error:
        if connection is not None:
            connection.rollback()
        print(f"user registration API error: {error}")
        return JSONResponse(
            status_code=500,
            content={"error": True, "message": "伺服器內部錯誤"},
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


@router.put(
    "/api/user/auth",
    response_model=TokenResponse,
    responses={
        400: {
            "model": ErrorResponse,
            "description": "登入失敗，帳號或密碼錯誤或其他原因",
        },
        500: {
            "model": ErrorResponse,
            "description": "伺服器內部錯誤",
        },
    },
)
def login_user(user: UserLogin):
    connection = None
    cursor = None
    email = user.email.strip().lower()

    if not email or not user.password:
        return JSONResponse(
            status_code=400,
            content={"error": True, "message": "Email 和密碼皆為必填"},
        )

    try:
        connection = get_database_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, name, email, password FROM users WHERE email = %s",
            (email,),
        )
        registered_user = cursor.fetchone()

        if registered_user is None or not verify_password(
            user.password,
            registered_user["password"],
        ):
            return JSONResponse(
                status_code=400,
                content={"error": True, "message": "Email 或密碼錯誤"},
            )

        return {"token": create_access_token(registered_user)}
    except (Error, KeyError, TypeError, ValueError) as error:
        print(f"user login API error: {error}")
        return JSONResponse(
            status_code=500,
            content={"error": True, "message": "伺服器內部錯誤"},
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


@router.get("/api/user/auth", response_model=AuthResponse)
def authenticate_user(
    authorization: Annotated[str | None, Header()] = None,
):
    if authorization is None:
        return {"data": None}

    scheme, separator, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not separator or not token:
        return {"data": None}

    try:
        payload = decode_access_token(token)
        return {
            "data": {
                "id": payload["id"],
                "name": payload["name"],
                "email": payload["email"],
            }
        }
    except (jwt.InvalidTokenError, KeyError, TypeError):
        return {"data": None}
