import os
from datetime import date as Date
from datetime import datetime
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

import requests
from fastapi import APIRouter, Body, Header
from fastapi.responses import JSONResponse
from mysql.connector import Error, IntegrityError
from pydantic import BaseModel, ConfigDict, EmailStr, Field, ValidationError

from attraction_api import get_database_connection, parse_images
from booking_api import get_authenticated_user_id, unauthorized_response

router = APIRouter()
TAPPAY_PARTNER_KEY = os.getenv("TAPPAY_PARTNER_KEY")
TAPPAY_MERCHANT_ID = os.getenv("TAPPAY_MERCHANT_ID")
TAPPAY_PAY_BY_PRIME_URL = "https://sandbox.tappaysdk.com/tpc/payment/pay-by-prime"
TAPPAY_TIMEOUT_SECONDS = 30


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


class PaymentResult(BaseModel):
    status: Literal[0, 1]
    message: str


class OrderPaymentData(BaseModel):
    number: str
    payment: PaymentResult


class CreateOrderResponse(BaseModel):
    data: OrderPaymentData


class OrderRecordData(BaseModel):
    number: str
    price: int
    trip: TripRequest
    contact: ContactRequest
    status: Literal[0, 1]


class GetOrderResponse(BaseModel):
    data: OrderRecordData | None


class TapPayRequestError(Exception):
    pass


def generate_order_number() -> str:
    return datetime.now(ZoneInfo("Asia/Taipei")).strftime("%Y%m%d%H%M%S")


def pay_by_prime(
    prime: str,
    order_number: str,
    amount: int,
    attraction_name: str,
    contact_name: str,
    contact_email: str,
    contact_phone: str,
) -> tuple[int, str]:
    if not TAPPAY_PARTNER_KEY or not TAPPAY_MERCHANT_ID:
        raise TapPayRequestError("TapPay backend credentials are not configured")

    payload = {
        "prime": prime,
        "partner_key": TAPPAY_PARTNER_KEY,
        "merchant_id": TAPPAY_MERCHANT_ID,
        "details": attraction_name[:100],
        "amount": amount,
        "order_number": order_number,
        "cardholder": {
            "phone_number": contact_phone,
            "name": contact_name,
            "email": contact_email,
        },
        "remember": False,
    }

    try:
        response = requests.post(
            TAPPAY_PAY_BY_PRIME_URL,
            headers={
                "Content-Type": "application/json",
                "x-api-key": TAPPAY_PARTNER_KEY,
            },
            json=payload,
            timeout=TAPPAY_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        result = response.json()
    except (requests.RequestException, ValueError) as error:
        raise TapPayRequestError("TapPay Pay by Prime request failed") from error

    if not isinstance(result, dict):
        raise TapPayRequestError("TapPay returned an invalid response")

    status = result.get("status")
    message = result.get("msg")
    if not isinstance(status, int) or not isinstance(message, str):
        raise TapPayRequestError("TapPay returned an invalid response")

    return status, message


def invalid_order_response(message: str = "訂單建立失敗，輸入資料不正確"):
    return JSONResponse(
        status_code=400,
        content={"error": True, "message": message},
    )


@router.get(
    "/api/order/{orderNumber}",
    response_model=GetOrderResponse,
    responses={
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
def get_order(
    orderNumber: str,
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
            "SELECT o.number, o.price, o.date, o.time, "
            "o.contact_name, o.contact_email, o.contact_phone, o.status, "
            "a.id AS attraction_id, a.name AS attraction_name, "
            "a.address AS attraction_address, a.images AS attraction_images "
            "FROM orders AS o "
            "INNER JOIN attractions AS a ON a.id = o.attraction_id "
            "WHERE o.number = %s AND o.user_id = %s LIMIT 1",
            (orderNumber, user_id),
        )
        row = cursor.fetchone()

        if row is None:
            return {"data": None}

        images = parse_images(row["attraction_images"])
        order_date = row["date"]
        if hasattr(order_date, "isoformat"):
            order_date = order_date.isoformat()

        return {
            "data": {
                "number": row["number"],
                "price": row["price"],
                "trip": {
                    "attraction": {
                        "id": row["attraction_id"],
                        "name": row["attraction_name"],
                        "address": row["attraction_address"],
                        "image": images[0] if images else None,
                    },
                    "date": order_date,
                    "time": row["time"],
                },
                "contact": {
                    "name": row["contact_name"],
                    "email": row["contact_email"],
                    "phone": row["contact_phone"],
                },
                "status": 1 if row["status"] == "PAID" else 0,
            }
        }
    except (Error, KeyError, TypeError, ValueError) as error:
        print(f"get order API error: {error}")
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
            "SELECT b.attraction_id, b.date, b.time, b.price, "
            "a.name AS attraction_name "
            "FROM booking AS b "
            "JOIN attractions AS a ON a.id = b.attraction_id "
            "WHERE b.user_id = %s LIMIT 1 FOR UPDATE",
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

        cursor.execute(
            "SELECT id, number FROM orders "
            "WHERE user_id = %s AND attraction_id = %s "
            "AND date = %s AND time = %s AND price = %s "
            "AND status = 'UNPAID' "
            "ORDER BY id DESC LIMIT 1 FOR UPDATE",
            (
                user_id,
                booking["attraction_id"],
                booking_date,
                booking["time"],
                booking["price"],
            ),
        )
        unpaid_order = cursor.fetchone()

        if unpaid_order is not None:
            order_id = unpaid_order["id"]
            order_number = unpaid_order["number"]
        else:
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
            order_id = cursor.lastrowid
        connection.commit()

        try:
            payment_status, payment_message = pay_by_prime(
                prime=request.prime,
                order_number=order_number,
                amount=booking["price"],
                attraction_name=booking["attraction_name"],
                contact_name=contact_name,
                contact_email=contact_email,
                contact_phone=contact_phone,
            )
        except TapPayRequestError as error:
            print(f"TapPay payment error: {error}")
            payment_status = 1
            payment_message = str(error)

        if payment_status != 0:
            print(
                "TapPay payment declined: "
                f"status={payment_status}, message={payment_message}"
            )
            return {
                "data": {
                    "number": order_number,
                    "payment": {"status": 1, "message": "付款失敗"},
                }
            }

        cursor.execute(
            "UPDATE orders SET status = 'PAID', contact_name = %s, "
            "contact_email = %s, contact_phone = %s "
            "WHERE id = %s AND status = 'UNPAID'",
            (contact_name, contact_email, contact_phone, order_id),
        )
        if cursor.rowcount != 1:
            raise ValueError("Unable to mark paid order")
        connection.commit()

        return {
            "data": {
                "number": order_number,
                "payment": {"status": 0, "message": "付款成功"},
            }
        }
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
