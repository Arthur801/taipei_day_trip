"""
mrt station api
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from mysql.connector import Error
from pydantic import BaseModel

from attraction_api import get_database_connection

router = APIRouter()

class ErrorResponse(BaseModel):
    error: bool
    message: str


@router.get(
    "/api/mrts",
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
def get_mrts():
    connection = None
    cursor = None
    try:
        connection = get_database_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT mrt, COUNT(mrt) AS mrt_count FROM attractions GROUP BY mrt ORDER BY mrt_count DESC")
        mrtList = [mrt[0] for mrt in cursor.fetchall()]
        mrtList.remove(None)

        return {
            "data": mrtList
        }
    except Error as e:
        print(f"mrt API error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": True, "message": f"伺服器內部錯誤: {e}"},
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()

if __name__ == "__main__":
    pass