"""
Attraction list API.
"""

import mysql.connector
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from mysql.connector import Error
from pydantic import BaseModel

router = APIRouter()
PAGE_SIZE = 8

class ErrorResponse(BaseModel):
    error: bool
    message: str

def get_database_connection():
    return mysql.connector.connect(
        host="localhost",
        user="admin",
        password="Password1234!",
        database="attractionDB",
    )


def parse_images(images: str) -> list[str]:
    return [f"/imgs/{image}" for image in images.split("/imgs/") if image]


@router.get(
        "/api/attractions",
        responses={
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
            }
        },
        )
def get_attractions(
    page: int = Query(..., ge=0),
    category: str | None = None,
    keyword: str | None = None,
):
    # Return one page of attractions with optional category and keyword filters.
    connection = None
    cursor = None

    try:
        conditions = []
        parameters = []

        if category is not None:
            conditions.append("category = %s")
            parameters.append(category)
        if keyword is not None:
            conditions.append("(mrt = %s OR name LIKE %s)")
            parameters.extend([keyword, f"%{keyword}%"])

        whereClause = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        query = (
            "SELECT id, name, category, description, address, transport, mrt, lat, lng, images "
            f"FROM attractions{whereClause} ORDER BY id LIMIT %s OFFSET %s"
        )
        parameters.extend([PAGE_SIZE + 1, page * PAGE_SIZE])

        connection = get_database_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, parameters)
        rows = cursor.fetchall()

        nextPage = page + 1 if len(rows) > PAGE_SIZE else None
        attractions = [
            {
                "id": row["id"],
                "name": row["name"],
                "category": row["category"],
                "description": row["description"],
                "address": row["address"],
                "transport": row["transport"],
                "mrt": row["mrt"],
                "lat": float(row["lat"]),
                "lng": float(row["lng"]),
                "images": parse_images(row["images"]),
            }
            for row in rows[:PAGE_SIZE]
        ]
        return {"nextPage": nextPage, "data": attractions}
    except (Error, TypeError, ValueError) as error:
        print(f"attraction API error: {error}")
        return JSONResponse(
            status_code=500,
            content={"error": True, "message": f"伺服器內部錯誤: {error}"},
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

@router.get(
        "/api/attractions/{attractionId}",
        responses={
            400: {
                "model": ErrorResponse,
                "description": "景點編號不正確",
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
            }
        },
        )
def get_attraction_by_id(attractionId: str):
    connection = None
    cursor = None

    if not attractionId.isascii() or not attractionId.isdecimal() or int(attractionId) < 1:
        return JSONResponse(
            status_code=400,
            content={"error": True, "message": "景點編號不正確: 輸入型態錯誤"},
        )

    try:
        connection = get_database_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, name, category, description, address, transport, mrt, lat, lng, images "
            "FROM attractions WHERE id = %s",
            (int(attractionId),),
        )
        row = cursor.fetchone()

        if row is None:
            return JSONResponse(
                status_code=400,
                content={"error": True, "message": "景點編號不正確: 不存在的編號"},
            )

        return {
            "data": {
                "id": row["id"],
                "name": row["name"],
                "category": row["category"],
                "description": row["description"],
                "address": row["address"],
                "transport": row["transport"],
                "mrt": row["mrt"],
                "lat": float(row["lat"]),
                "lng": float(row["lng"]),
                "images": parse_images(row["images"]),
            }
        }
    except (Error, KeyError, TypeError, ValueError) as error:
        print(f"attraction id api error: {error}")
        return JSONResponse(
            status_code=500,
            content={"error": True, "message": "伺服器內部錯誤"},
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()
