"""
3 Booking APIs
"""
from datetime import date as Date
from typing import Annotated, Literal

import jwt
from fastapi import APIRouter, Body, Header
from fastapi.responses import JSONResponse
from mysql.connector import Error, IntegrityError
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from attraction_api import get_database_connection, parse_images
from user_api import decode_access_token

router = APIRouter()


class ErrorResponse(BaseModel):
    error: bool
    message: str


class SuccessResponse(BaseModel):
    ok: bool


class BookingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attraction_id: int = Field(alias="attractionId", gt=0)
    date: Date
    time: Literal["morning", "afternoon"]
    price: int = Field(gt=0)


def get_authenticated_user_id(authorization: str | None) -> int | None:
    if authorization is None:
        return None

    scheme, separator, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not separator or not token:
        return None

    try:
        payload = decode_access_token(token)
        user_id = payload["id"]
        if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id < 1:
            return None
        return user_id
    except (jwt.InvalidTokenError, KeyError, TypeError):
        return None


def unauthorized_response():
    return JSONResponse(
        status_code=403,
        content={"error": True, "message": "未登入系統，拒絕存取"},
    )


@router.get(
    "/api/booking",
    responses={
        403: {
            "model": ErrorResponse,
            "description": "未登入系統，拒絕存取",
            "content": {
                "application/json": {
                    "example": {
                        "error": True,
                        "message": "請按照情境提供對應的錯誤訊息",
                    }
                }
            },
        },
        500: {
            "model": ErrorResponse,
            "description": "伺服器內部錯誤",
        },
    },
)
def get_booking(
    authorization: Annotated[str | None, Header()] = None,
):
    user_id = get_authenticated_user_id(authorization)
    if user_id is None:
        return unauthorized_response()

    connection = None
    cursor = None
    try:
        connection = get_database_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT a.id AS attraction_id, a.name, a.address, a.images, "
            "b.date, b.time, b.price "
            "FROM booking AS b "
            "INNER JOIN attractions AS a ON a.id = b.attraction_id "
            "WHERE b.user_id = %s LIMIT 1",
            (user_id,),
        )
        row = cursor.fetchone()

        if row is None:
            return {"data": None}

        images = parse_images(row["images"])
        booking_date = row["date"]
        if hasattr(booking_date, "isoformat"):
            booking_date = booking_date.isoformat()

        return {
            "data": {
                "attraction": {
                    "id": row["attraction_id"],
                    "name": row["name"],
                    "address": row["address"],
                    "image": images[0] if images else None,
                },
                "date": booking_date,
                "time": row["time"],
                "price": row["price"],
            }
        }
    except (Error, KeyError, TypeError, ValueError) as error:
        print(f"get booking API error: {error}")
        return JSONResponse(
            status_code=500,
            content={"error": True, "message": "伺服器內部錯誤"},
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


@router.post(
    "/api/booking",
    response_model=SuccessResponse,
    responses={
        400: {
            "model": ErrorResponse,
            "description": "建立失敗，輸入不正確或其他原因",
            "content": {
                "application/json": {
                    "example": {
                        "error": True,
                        "message": "請按照情境提供對應的錯誤訊息",
                    }
                }
            },
        },
        403: {
            "model": ErrorResponse,
            "description": "未登入系統，拒絕存取",
            "content": {
                "application/json": {
                    "example": {
                        "error": True,
                        "message": "請按照情境提供對應的錯誤訊息",
                    }
                }
            },
        },
        500: {
            "model": ErrorResponse,
            "description": "伺服器內部錯誤",
            "content": {
                "application/json": {
                    "example": {
                        "error": True,
                        "message": "請按照情境提供對應的錯誤訊息",
                    }
                }
            },
        },
    },
)
def create_new_booking(
    booking_data: Annotated[object | None, Body()] = None,
    authorization: Annotated[str | None, Header()] = None,
):
    user_id = get_authenticated_user_id(authorization)
    if user_id is None:
        return unauthorized_response()

    try:
        booking = BookingRequest.model_validate(booking_data)
    except ValidationError:
        return JSONResponse(
            status_code=400,
            content={"error": True, "message": "建立失敗，輸入資料不正確"},
        )

    expected_price = 2000 if booking.time == "morning" else 2500
    if booking.price != expected_price:
        return JSONResponse(
            status_code=400,
            content={"error": True, "message": "建立失敗，時段與費用不相符"},
        )

    connection = None
    cursor = None
    try:
        connection = get_database_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT id FROM attractions WHERE id = %s",
            (booking.attraction_id,),
        )
        if cursor.fetchone() is None:
            return JSONResponse(
                status_code=400,
                content={"error": True, "message": "建立失敗，景點不存在"},
            )

        cursor.execute("DELETE FROM booking WHERE user_id = %s", (user_id,))
        cursor.execute(
            "INSERT INTO booking (user_id, attraction_id, date, time, price) "
            "VALUES (%s, %s, %s, %s, %s)",
            (
                user_id,
                booking.attraction_id,
                booking.date,
                booking.time,
                booking.price,
            ),
        )
        connection.commit()
        return {"ok": True}
    except IntegrityError as error:
        if connection is not None:
            connection.rollback()
        print(f"create booking integrity error: {error}")
        return JSONResponse(
            status_code=400,
            content={"error": True, "message": "建立失敗，輸入資料不正確"},
        )
    except Error as error:
        if connection is not None:
            connection.rollback()
        print(f"create booking API error: {error}")
        return JSONResponse(
            status_code=500,
            content={"error": True, "message": "伺服器內部錯誤"},
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


@router.delete(
    "/api/booking",
    response_model=SuccessResponse,
    responses={
        403: {
            "model": ErrorResponse,
            "description": "未登入系統，拒絕存取",
            "content": {
                "application/json": {
                    "example": {
                        "error": True,
                        "message": "請按照情境提供對應的錯誤訊息",
                    }
                }
            },
        },
        500: {
            "model": ErrorResponse,
            "description": "伺服器內部錯誤",
        },
    },
)
def delete_current_booking(
    authorization: Annotated[str | None, Header()] = None,
):
    user_id = get_authenticated_user_id(authorization)
    if user_id is None:
        return unauthorized_response()

    connection = None
    cursor = None
    try:
        connection = get_database_connection()
        cursor = connection.cursor()
        cursor.execute("DELETE FROM booking WHERE user_id = %s", (user_id,))
        connection.commit()
        return {"ok": True}
    except Error as error:
        if connection is not None:
            connection.rollback()
        print(f"delete booking API error: {error}")
        return JSONResponse(
            status_code=500,
            content={"error": True, "message": "伺服器內部錯誤"},
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()
