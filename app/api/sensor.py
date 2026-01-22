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
    logger.info(f"Sensor update request received: {data.sensor_id} -> {data.status.value}")
    
    result = await db.execute(
        select(models.Dock).where(models.Dock.sensor_id == data.sensor_id)
    )
    dock = result.scalars().first()
    
    if not dock:
        logger.warning(f"Dock not found for sensor: {data.sensor_id}")
        raise HTTPException(status_code=404, detail="Dock non trouvé")
    
    if data.status == models.DockStatus.OUT_OF_SERVICE:
        raise HTTPException(
            status_code=403, 
            detail="Action non autorisée"
        )
    
    if dock.status == models.DockStatus.OUT_OF_SERVICE:
        logger.warning(f"Attempted to update OUT_OF_SERVICE dock: {data.sensor_id}")
        raise HTTPException(status_code=403, detail="Dock hors service")
    
    old_status = dock.status
    
    # Enregistrer le changement dans l'historique si le statut change
    if old_status != data.status:
        logger.info(f"Status change for {data.sensor_id}: {old_status.value} -> {data.status.value}")
        history_entry = models.DockStatusHistory(
            dock_id=dock.id,
            status=data.status
        )
        db.add(history_entry)
    else:
        logger.debug(f"No status change for {data.sensor_id}: {old_status.value}")
    
    await db.execute(
        update(models.Dock)
        .where(models.Dock.sensor_id == data.sensor_id)
        .values(status=data.status)
    )
    
    await db.commit()
    logger.info(f"Sensor {data.sensor_id} updated successfully to {data.status.value}")

    try:
        await websockets.manager.broadcast({
            "dock_id": dock.id,
            "group_id": dock.group_id,
            "sensor_id": data.sensor_id,
            "status": data.status.value
        })
        logger.debug(f"WebSocket broadcast sent for {data.sensor_id}")
    except Exception as e:
        logger.error(f"Erreur lors du broadcast pour {data.sensor_id}: {e}", exc_info=True)

    return {"status": "ok", "changed": old_status != data.status}
