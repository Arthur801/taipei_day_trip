"""FastMCP server for searching attractions and creating bookings."""

from datetime import date as Date
import re
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.dependencies import CurrentAccessToken, CurrentRequest
from fastmcp.server.auth import AccessToken, TokenVerifier
from mysql.connector import Error
from pydantic import Field, ValidationError
from starlette.requests import Request

from attraction_api import get_database_connection
from booking_api import (
    BookingPrice,
    BookingRequest,
    BookingStorageError,
    BookingTime,
    BookingValidationError,
    replace_booking,
)

MCP_SCOPE = "mcp:access"
API_TOKEN_PATTERN = re.compile(r"[0-9a-f]{64}")


def find_member_id_by_api_token(token: str) -> int | None:
    if API_TOKEN_PATTERN.fullmatch(token) is None:
        return None

    connection = None
    cursor = None
    try:
        connection = get_database_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT id FROM users WHERE BINARY api_token = %s LIMIT 1",
            (token,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        member_id = row[0]
        if isinstance(member_id, bool) or not isinstance(member_id, int) or member_id < 1:
            return None
        return member_id
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


class DatabaseTokenVerifier(TokenVerifier):
    def __init__(self) -> None:
        super().__init__(required_scopes=[MCP_SCOPE])

    async def verify_token(self, token: str) -> AccessToken | None:
        member_id = find_member_id_by_api_token(token)
        if member_id is None:
            return None
        return AccessToken(
            token=token,
            client_id=f"member-{member_id}",
            subject=str(member_id),
            scopes=[MCP_SCOPE],
            claims={"member_id": member_id},
        )


mcp = FastMCP(name="台北一日遊", auth=DatabaseTokenVerifier())


@mcp.tool(
    name="search",
    title="搜尋台北市景點",
    description="透過關鍵字和捷運站名搜尋台北一日遊的景點",
)
def search_attractions(keyword: str) -> dict[str, object]:
    normalized_keyword = keyword.strip()
    if not normalized_keyword or len(normalized_keyword) > 255:
        return {"error": True}

    connection = None
    cursor = None
    try:
        connection = get_database_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, name, description FROM attractions "
            "WHERE INSTR(name, %s) > 0 OR mrt = %s ORDER BY id",
            (normalized_keyword, normalized_keyword),
        )
        rows = cursor.fetchall()
        return {
            "data": [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "description": row["description"],
                }
                for row in rows
            ]
        }
    except (Error, KeyError, TypeError) as error:
        print(f"MCP attraction search error: {error}")
        return {"error": True}
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


@mcp.tool(
    name="add_to_cart",
    title="預定景點導覽行程",
    description="根據景點編號、日期、時間、價格，預定一個景點導覽行程。",
)
def add_to_cart(
    attractionId: Annotated[int, Field(gt=0)],
    date: Date,
    time: BookingTime,
    price: BookingPrice,
    access_token: AccessToken = CurrentAccessToken(),
    request: Request = CurrentRequest(),
) -> dict[str, object]:
    member_id = access_token.claims.get("member_id")
    if isinstance(member_id, bool) or not isinstance(member_id, int) or member_id < 1:
        return {"error": True}

    try:
        booking = BookingRequest.model_validate(
            {
                "attractionId": attractionId,
                "date": date,
                "time": time,
                "price": price,
            }
        )
        replace_booking(member_id, booking)
    except (ValidationError, BookingValidationError, BookingStorageError) as error:
        print(f"MCP booking error: {error}")
        return {"error": True}

    booking_url = str(request.url.replace(path="/booking", query=""))
    return {
        "ok": True,
        "message": f"台北導覽行程，預定成功，請到 {booking_url} 完成付款。",
    }


mcp_app = mcp.http_app(path="/", json_response=True)
