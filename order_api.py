from datetime import date as Date
from datetime import datetime, timezone
import secrets
from typing import Annotated, Literal

from fastapi import APIRouter, Body, Header
from fastapi.responses import JSONResponse
from mysql.connector import Error, IntegrityError
from pydantic import BaseModel, ConfigDict, EmailStr, Field, ValidationError

from attraction_api import get_database_connection
from booking_api import get_authenticated_user_id, unauthorized_response

router = APIRouter()


class ErrorResponse(BaseModel):
    error: bool
    message: str


class AttractionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(gt=0)
    name: str
    address: str
    image: str | None


class TripRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attraction: AttractionRequest
    date: Date
    time: Literal["morning", "afternoon"]


class ContactRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    phone: str = Field(min_length=1, max_length=30)


class OrderDetailsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    price: int = Field(gt=0)
    trip: TripRequest
    contact: ContactRequest


class CreateOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prime: str = Field(min_length=1)
    order: OrderDetailsRequest


class OrderNumberData(BaseModel):
    number: str


class CreateOrderResponse(BaseModel):
    data: OrderNumberData


def generate_order_number() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    return f"{timestamp}{secrets.token_hex(8).upper()}"


def invalid_order_response(message: str = "訂單建立失敗，輸入資料不正確"):
    return JSONResponse(
        status_code=400,
        content={"error": True, "message": message},
    )


@router.post(
    "/api/orders",
    response_model=CreateOrderResponse,
    responses={
        400: {
            "model": ErrorResponse,
            "description": "訂單建立失敗，輸入不正確或沒有預定行程",
        },
        403: {
            "model": ErrorResponse,
            "description": "未登入系統，拒絕存取",
        },
        500: {
            "model": ErrorResponse,
            "description": "伺服器內部錯誤",
        },
    },
)
def create_order(
    order_data: Annotated[object | None, Body()] = None,
    authorization: Annotated[str | None, Header()] = None,
):
    user_id = get_authenticated_user_id(authorization)
    if user_id is None:
        return unauthorized_response()

    try:
        request = CreateOrderRequest.model_validate(order_data)
    except ValidationError:
        return invalid_order_response()

    contact_name = request.order.contact.name.strip()
    contact_email = str(request.order.contact.email).strip().lower()
    contact_phone = request.order.contact.phone.strip()
    if not request.prime.strip() or not contact_name or not contact_phone:
        return invalid_order_response()

    connection = None
    cursor = None
    try:
        connection = get_database_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT attraction_id, date, time, price "
            "FROM booking WHERE user_id = %s LIMIT 1 FOR UPDATE",
            (user_id,),
        )
        booking = cursor.fetchone()
        if booking is None:
            connection.rollback()
            return invalid_order_response("訂單建立失敗，目前沒有預定行程")

        trip = request.order.trip
        booking_date = booking["date"]
        if isinstance(booking_date, datetime):
            booking_date = booking_date.date()

        booking_matches_request = (
            booking["attraction_id"] == trip.attraction.id
            and booking_date == trip.date
            and booking["time"] == trip.time
            and booking["price"] == request.order.price
        )
        if not booking_matches_request:
            connection.rollback()
            return invalid_order_response("訂單內容與目前預定行程不相符")

        order_number = generate_order_number()
        cursor.execute(
            "INSERT INTO orders ("
            "number, user_id, attraction_id, date, time, price, "
            "contact_name, contact_email, contact_phone, status"
            ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'UNPAID')",
            (
                order_number,
                user_id,
                booking["attraction_id"],
                booking_date,
                booking["time"],
                booking["price"],
                contact_name,
                contact_email,
                contact_phone,
            ),
        )
        connection.commit()
        return {"data": {"number": order_number}}
    except IntegrityError as error:
        if connection is not None:
            connection.rollback()
        print(f"create order integrity error: {error}")
        return invalid_order_response()
    except (Error, KeyError, TypeError, ValueError) as error:
        if connection is not None:
            connection.rollback()
        print(f"create order API error: {error}")
        return JSONResponse(
            status_code=500,
            content={"error": True, "message": "伺服器內部錯誤"},
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()
