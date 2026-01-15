from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update

from app.database import get_db
from app.core.security import require_sensor_key
from app import models, schemas, websockets

router = APIRouter(prefix="/api/sensor", tags=["sensor"])

@router.post("/update")
async def update_sensor(
    data: schemas.SensorUpdate,
    db: AsyncSession = Depends(get_db),
    sensor=Depends(require_sensor_key)
):
    await db.execute(
        update(models.ParkingSpot)
        .where(models.ParkingSpot.id == data.spot_id)
        .values(status=data.status)
    )
    await db.commit()

    await websockets.manager.broadcast({
        "spot_id": data.spot_id,
        "status": data.status.value
    })

    return {"status": "ok"}
