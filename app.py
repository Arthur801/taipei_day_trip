from fastapi import *
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from attraction_api import router as attraction_router
from attraction_category_api import router as attraction_category_router
from booking_api import router as booking_router
from mrt_station_api import router as mrt_router
from order_api import router as order_router
from user_api import router as user_router
from mcp_server import mcp_app

app=FastAPI(lifespan=mcp_app.lifespan)
app.include_router(attraction_router)
app.include_router(attraction_category_router)
app.include_router(mrt_router)
app.include_router(user_router)
app.include_router(booking_router)
app.include_router(order_router)
app.mount("/mcp", mcp_app)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Static Pages (Never Modify Code in this Block)
@app.get("/", include_in_schema=False)
async def index(request: Request):
	return FileResponse("./static/index.html", media_type="text/html")
@app.get("/attraction/{id}", include_in_schema=False)
async def attraction(request: Request, id: int):
	return FileResponse("./static/attraction.html", media_type="text/html")
@app.get("/booking", include_in_schema=False)
async def booking(request: Request):
	return FileResponse("./static/booking.html", media_type="text/html")
@app.get("/thankyou", include_in_schema=False)
async def thankyou(request: Request):
	return FileResponse("./static/thankyou.html", media_type="text/html")
@app.get("/member", include_in_schema=False)
async def member(request: Request):
	return FileResponse("./static/member.html", media_type="text/html")