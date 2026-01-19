from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, admin, public, sensor, websocket, defect, image
from app import models
from app.database import engine

app = FastAPI(title="Wheelock API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(public.router)
app.include_router(sensor.router)
app.include_router(websocket.router)
app.include_router(defect.router)
app.include_router(image.router)