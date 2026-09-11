from fastapi import APIRouter
from fastapi.responses import JSONResponse
from mysql.connector import Error
from pydantic import BaseModel

from attraction_api import get_database_connection

router = APIRouter()

