from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, admin, public, sensor, websocket, defect, logs, stats
from app import models
from app.database import engine
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Wheelock API")

# CORS middleware
import os

# Pour la prod, restreindre les origines autorisées via une variable d'environnement
origins = os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    logger.info("Wheelock API started successfully")

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(public.router)
app.include_router(sensor.router)
app.include_router(websocket.router)
app.include_router(defect.router)
app.include_router(logs.router)
app.include_router(stats.router)