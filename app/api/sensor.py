from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, select
import logging
from app.database import get_db
from app.core.security import require_sensor_key
from app import models, schemas, websockets

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sensor", tags=["sensor"])

@router.post("/update")
async def update_sensor(
    data: schemas.SensorUpdate,
    db: AsyncSession = Depends(get_db),
    sensor=Depends(require_sensor_key)
):
    result = await db.execute(
        select(models.Dock).where(models.Dock.sensor_id == data.sensor_id)
    )
    dock = result.scalars().first()
    
    if not dock:
        raise HTTPException(status_code=404, detail="Dock non trouvé")
    if dock.status == models.DockStatus.OUT_OF_SERVICE:
        raise HTTPException(status_code=403, detail="Dock hors service")
    
    # Enregistrer le changement dans l'historique si le statut change
    if dock.status != data.status and data.status != models.DockStatus.OUT_OF_SERVICE:
        history_entry = models.DockStatusHistory(
            dock_id=dock.id,
            status=data.status
        )
        db.add(history_entry)
    
        await db.execute(
            update(models.Dock)
            .where(models.Dock.sensor_id == data.sensor_id)
            .values(status=data.status)
        )
        await db.commit()

        try:
            await websockets.manager.broadcast({
                "dock_id": dock.id,
                "group_id": dock.group_id,
                "sensor_id": data.sensor_id,
                "status": data.status.value
            })
        except Exception as e:
            logger.error(f"Erreur lors du broadcast: {e}")

    return {"status": "ok"}
