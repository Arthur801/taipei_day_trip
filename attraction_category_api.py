"""
Attraction category API
"""

from collections import Counter

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from mysql.connector import Error
from pydantic import BaseModel

from attraction_api import get_database_connection

router = APIRouter()

class ErrorResponse(BaseModel):
    error: bool
    message: str

# get and list categories in the database
def create_category_list():
    connection = None
    cursor = None
    categoryList = []
    try:
        connection = get_database_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT category FROM attractions")
        categories = [category[0] for category in cursor.fetchall()]

        categoryList = sorted(set(categories), key=Counter(categories).get, reverse=True)

        return categoryList
    except Error as e:
        print(f"Database connection error: {e}")
        return None
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()

@router.get(
    "/api/categories",
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
def get_categories():
    categoryList = create_category_list()
    if categoryList is None:
        return JSONResponse(
            status_code=500,
            content={"error": True, "message": "伺服器內部錯誤"}
        )
    return {
        "data": categoryList
    }


if __name__ == "__main__":
    pass