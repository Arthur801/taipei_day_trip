"""
3 Booking APIs
"""
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse
from mysql.connector import Error, IntegrityError
from pydantic import BaseModel

from attraction_api import get_database_connection

router = APIRouter()

class ErrorResponse(BaseModel):
    error: bool
    message: str

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
            }
        },
        )
def get_booking():
    pass


@router.post(
        "/api/booking",
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
            }
        },
        )
def create_new_booking():
    pass

@router.delete(
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
            }
        },
        )
def delete_current_booking():
    pass