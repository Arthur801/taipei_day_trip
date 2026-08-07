from fastapi import *
from fastapi.responses import FileResponse

from attraction_api import router as attraction_router
from attraction_category_api import router as attraction_category_router
from mrt_station_api import router as mrt_router

app=FastAPI()
app.include_router(attraction_router)
app.include_router(attraction_category_router)
app.include_router(mrt_router)

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
