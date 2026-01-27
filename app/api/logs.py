from fastapi import APIRouter, Query, Depends
from typing import Optional
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.database import get_db
from app.core.security import require_admin
from app import models
from app import schemas

router = APIRouter(prefix="/api/admin", tags=["logs"])

@router.get("/logs", response_model=schemas.LogsResponse, summary="Récupérer l'historique des changements d'état des capteurs")
async def get_sensor_logs(
    sensor_id: Optional[str] = Query(None, description="Filtrer par sensor_id (ex: ESP32_TEST_001)"),
    status: Optional[str] = Query(None, description="Filtrer par statut (AVAILABLE, OCCUPIED, OUT_OF_SERVICE)"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre maximum de logs à retourner"),
    start_date: Optional[str] = Query(None, description="Date de début au format YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Date de fin au format YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    admin: models.Admin = Depends(require_admin)
):
    """
    Récupère l'historique des changements d'état des capteurs.
    
    **Paramètres :**
    - **sensor_id** : Filtrer par capteur spécifique (ex: ESP32_TEST_001)
    - **status** : Filtrer par statut (AVAILABLE, OCCUPIED, OUT_OF_SERVICE)
    - **limit** : Nombre maximum de logs à retourner (1-1000)
    - **start_date** : Date de début (format YYYY-MM-DD)
    - **end_date** : Date de fin (format YYYY-MM-DD)
    
    **Exemples :**
    - `/api/logs` - Tous les changements (100 derniers)
    - `/api/logs?sensor_id=ESP32_TEST_001` - Historique d'un capteur
    - `/api/logs?status=OCCUPIED` - Uniquement les passages en OCCUPIED
    - `/api/logs?start_date=2026-01-20&end_date=2026-01-22` - Sur une période
    """
    
    # Construire la requête de base avec LEFT jointure (pour inclure historique de docks supprimés)
    query = select(
        models.DockStatusHistory.id,
        func.coalesce(models.Dock.sensor_id, models.DockStatusHistory.sensor_id).label('sensor_id'),
        func.coalesce(models.Dock.name, models.DockStatusHistory.dock_name).label('name'),
        models.DockStatusHistory.dock_id,
        models.DockStatusHistory.status,
        models.DockStatusHistory.changed_at
    ).outerjoin(
        models.Dock, 
        models.DockStatusHistory.dock_id == models.Dock.id
    )
    
    # Appliquer les filtres
    filters = []
    
    if sensor_id:
        # Utiliser le sensor_id de l'historique (fonctionne même si dock supprimé)
        filters.append(models.DockStatusHistory.sensor_id == sensor_id)
    
    if status and isinstance(status, str):
        try:
            status_enum = models.DockStatus[status.upper()]
            filters.append(models.DockStatusHistory.status == status_enum)
        except KeyError:
            pass  # Ignorer les statuts invalides
    
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=ZoneInfo("UTC"))
            filters.append(models.DockStatusHistory.changed_at >= start_dt)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=ZoneInfo("UTC")) + timedelta(days=1)
            filters.append(models.DockStatusHistory.changed_at < end_dt)
        except ValueError:
            pass
    
    if filters:
        query = query.where(and_(*filters))
    
    # Compter le total
    count_query = select(func.count()).select_from(
        models.DockStatusHistory
    ).outerjoin(
        models.Dock,
        models.DockStatusHistory.dock_id == models.Dock.id
    )
    if filters:
        count_query = count_query.where(and_(*filters))
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Récupérer les logs (triés par date décroissante)
    query = query.order_by(models.DockStatusHistory.changed_at.desc()).limit(limit)
    result = await db.execute(query)
    rows = result.all()
    
    # Formater les résultats
    logs = [
        schemas.SensorLogEntry(
            id=row.id,
            sensor_id=row.sensor_id,
            sensor_name=row.name,
            dock_id=row.dock_id,
            status=row.status.value,
            changed_at=row.changed_at.strftime("%Y-%m-%d %H:%M:%S")
        )
        for row in rows
    ]
    
    return schemas.LogsResponse(total=total, logs=logs)


@router.get("/logs/sensor/{sensor_id}", summary="Historique d'un capteur spécifique")
async def get_sensor_history(
    sensor_id: str,
    limit: int = Query(50, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    admin: models.Admin = Depends(require_admin)
):
    """
    Récupère l'historique complet d'un capteur spécifique.
    
    **Exemple :**
    - `/api/logs/sensor/ESP32_TEST_001`
    """
    return await get_sensor_logs(sensor_id=sensor_id, limit=limit, db=db)

@router.get("/logs/stats", summary="Statistiques des changements d'état")
async def get_log_stats(
    db: AsyncSession = Depends(get_db),
    admin: models.Admin = Depends(require_admin)
):
    """
    Récupère des statistiques sur les changements d'état des capteurs.
    
    **Retourne :**
    - Nombre total de changements
    - Répartition par statut
    - Capteurs les plus actifs
    - Période couverte
    """
    
    # Total de changements
    total_query = select(func.count()).select_from(models.DockStatusHistory)
    total_result = await db.execute(total_query)
    total = total_result.scalar()
    
    # Répartition par statut
    status_query = select(
        models.DockStatusHistory.status,
        func.count(models.DockStatusHistory.id).label('count')
    ).group_by(models.DockStatusHistory.status)
    status_result = await db.execute(status_query)
    status_counts = {row.status.value: row.count for row in status_result}
    
    # Top capteurs les plus actifs
    top_sensors_query = select(
        models.Dock.sensor_id,
        models.Dock.name,
        func.count(models.DockStatusHistory.id).label('changes')
    ).join(
        models.DockStatusHistory,
        models.Dock.id == models.DockStatusHistory.dock_id
    ).group_by(
        models.Dock.sensor_id,
        models.Dock.name
    ).order_by(
        func.count(models.DockStatusHistory.id).desc()
    ).limit(10)
    
    top_result = await db.execute(top_sensors_query)
    top_sensors = [
        {
            "sensor_id": row.sensor_id,
            "sensor_name": row.name,
            "total_changes": row.changes
        }
        for row in top_result
    ]
    
    # Période couverte
    period_query = select(
        func.min(models.DockStatusHistory.changed_at).label('oldest'),
        func.max(models.DockStatusHistory.changed_at).label('newest')
    )
    period_result = await db.execute(period_query)
    period = period_result.first()
    
    return {
        "total_changes": total,
        "status_distribution": status_counts,
        "most_active_sensors": top_sensors,
        "period": {
            "oldest": period.oldest.strftime("%Y-%m-%d %H:%M:%S") if period.oldest else None,
            "newest": period.newest.strftime("%Y-%m-%d %H:%M:%S") if period.newest else None
        }
    }
