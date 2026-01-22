from sqlalchemy import select, func, exists
from sqlalchemy.orm import selectinload
from geoalchemy2.shape import to_shape
from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.core.security import require_admin
from app import models, schemas
from app.core.storage import storage_service
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/docks", response_model=list[schemas.DocksGroupWithDocksResponse])
async def get_docks(
    lat: float | None = None,
    lon: float | None = None,
    radius_meters: int = 1000,
    db: AsyncSession = Depends(get_db),
    admin: models.Admin = Depends(require_admin),
):
    query = select(models.DocksGroup).options(selectinload(models.DocksGroup.docks))

    if lat is not None and lon is not None:
        user_point = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
        query = query.where(
            func.ST_DWithin(
                models.DocksGroup.location,
                user_point,
                radius_meters
            )
        )

    result = await db.execute(query)
    groups = result.scalars().all()

    response = []

    for group in groups:
        point = to_shape(group.location)
        docks = [
            schemas.DockResponse(
                id=dock.id,
                status=dock.status,
                name=dock.name,
                sensor_id=dock.sensor_id
            ) for dock in group.docks
        ]
        response.append({
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "image_url": group.image_url,
            "latitude": point.y,
            "longitude": point.x,
            "docks": docks
        })

    return response

@router.post("/docks-groups", response_model=schemas.DocksGroupWithDocksResponse)
async def create_docks_group(
    data: schemas.DocksGroupCreate,
    db: AsyncSession = Depends(get_db),
    admin: models.Admin = Depends(require_admin),
):
    location = func.ST_SetSRID(func.ST_MakePoint(data.longitude, data.latitude), 4326)

    group = models.DocksGroup(
        name=data.name,
        description=data.description,
        image_url=data.image_url,
        location=location,
    )

    db.add(group)
    await db.commit()
    await db.refresh(group)

    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "image_url": group.image_url,
        "latitude": data.latitude,
        "longitude": data.longitude,
        "docks": [],
    }


@router.post("/docks", response_model=schemas.DockResponse)
async def create_dock(
    data: schemas.DockCreate,
    db: AsyncSession = Depends(get_db),
    admin: models.Admin = Depends(require_admin),
):
    group = await db.get(models.DocksGroup, data.group_id)
    if not group:
        raise HTTPException(
            status_code=404,
            detail="Dock group not found"
        )
    sensor_query = select(exists().where(models.Dock.sensor_id == data.sensor_id))
    sensor_result = await db.execute(sensor_query)
    if sensor_result.scalar():
        raise HTTPException(status_code=400, detail="Dock with this sensor assigned already exists")
    dock = models.Dock(group_id=data.group_id, sensor_id=data.sensor_id, name=data.name)
    db.add(dock)
    await db.commit()
    await db.refresh(dock)
    return dock


@router.put("/docks-groups/{group_id}", response_model=schemas.DocksGroupWithDocksResponse)
async def update_docks_group(
    group_id: int,
    data: schemas.DocksGroupUpdate,
    db: AsyncSession = Depends(get_db),
    admin: models.Admin = Depends(require_admin),
):
    stmt = select(models.DocksGroup).options(selectinload(models.DocksGroup.docks)).where(models.DocksGroup.id == group_id)
    result = await db.execute(stmt)
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(status_code=404, detail="Docks group not found")

    if data.name is not None:
        group.name = data.name
    if data.description is not None:
        group.description = data.description
    if data.image_url is not None:
        group.image_url = data.image_url

    if data.latitude is not None and data.longitude is not None:
        group.location = func.ST_SetSRID(func.ST_MakePoint(data.longitude, data.latitude), 4326)
    
    await db.commit()
    await db.refresh(group)

    point = to_shape(group.location)
    docks = group.docks

    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "image_url": group.image_url,
        "latitude": point.y,
        "longitude": point.x,
        "docks": docks,
    }

@router.put("/docks/{dock_id}", response_model=schemas.DockResponse)
async def update_dock(
    dock_id: int,
    data: schemas.DockUpdate,
    db: AsyncSession = Depends(get_db),
    admin: models.Admin = Depends(require_admin),
):
    dock = await db.get(models.Dock, dock_id)
    if not dock:
        raise HTTPException(status_code=404, detail="Dock not found")

    if data.group_id is not None:
        group = await db.get(models.DocksGroup, data.group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Target Dock Group not found")
        dock.group_id = data.group_id

    if data.sensor_id is not None and data.sensor_id != dock.sensor_id:
        sensor_query = select(exists().where(models.Dock.sensor_id == data.sensor_id))
        sensor_result = await db.execute(sensor_query)
        if sensor_result.scalar():
            raise HTTPException(status_code=400, detail="Dock with this sensor assigned already exists")
        dock.sensor_id = data.sensor_id

    if data.name is not None:
        dock.name = data.name
        
    if data.status is not None:
        dock.status = data.status

    await db.commit()
    await db.refresh(dock)
    return dock

@router.delete("/docks-groups/{group_id}", status_code=204)
async def delete_docks_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    admin: models.Admin = Depends(require_admin),
):
    group = await db.get(models.DocksGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Docks group not found")

    if group.image_url:
        try:
            storage_service.delete_image(group.image_url)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Image delete failed: {str(e)}")

    await db.delete(group)
    await db.commit()
    
    return Response(status_code=204)

@router.delete("/docks/{dock_id}", status_code=204)
async def delete_dock(
    dock_id: int,
    db: AsyncSession = Depends(get_db),
    admin: models.Admin = Depends(require_admin),
):
    dock = await db.get(models.Dock, dock_id)
    if not dock:
        raise HTTPException(status_code=404, detail="Dock not found")

    await db.delete(dock)
    await db.commit()
    
    return Response(status_code=204)


@router.post("/docks-groups/{group_id}/image", status_code=204)
async def upload_docks_group_image(
    group_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin: models.Admin = Depends(require_admin),
):
    group = await db.get(models.DocksGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Docks group not found")
    
    if group.image_url:
        storage_service.delete_image(group.image_url)
    
    try:
        image_url = await storage_service.upload_image(
            file=file,
            folder="docks-groups"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image upload failed: {str(e)}")
    
    group.image_url = image_url
    await db.commit()
    await db.refresh(group)
    
    return Response(status_code=204)

@router.delete("/docks-groups/{group_id}/image", status_code=204)
async def delete_docks_group_image_only(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    admin: models.Admin = Depends(require_admin),
):
    group = await db.get(models.DocksGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Docks group not found")
        
    if group.image_url:
        storage_service.delete_image(group.image_url)
        group.image_url = None
        await db.commit()
    
    return Response(status_code=204)

@router.get("/stats/sensors", response_model=schemas.SensorStatsResponse)
async def get_sensors_statistics(db: AsyncSession = Depends(get_db)):
    """
    ## Statistiques globales des capteurs
    
    Retourne le nombre total de capteurs ainsi que leur répartition par statut.
    
    ### Retourne
    - **total** : Nombre total de capteurs installés
    - **available** : Nombre de capteurs libres (disponibles pour utilisation)
    - **occupied** : Nombre de capteurs actuellement occupés
    - **out_of_service** : Nombre de capteurs hors service
    
    ### Exemple d'utilisation
    ```
    GET /api/public/stats/sensors
    ```
    """
    # Requête pour compter tous les capteurs par statut
    query = select(
        models.Dock.status,
        func.count(models.Dock.id).label("count")
    ).group_by(models.Dock.status)
    
    result = await db.execute(query)
    status_counts = {row.status: row.count for row in result}
    
    # Calculer le total
    total = sum(status_counts.values())
    
    return {
        "total": total,
        "available": status_counts.get(models.DockStatus.AVAILABLE, 0),
        "occupied": status_counts.get(models.DockStatus.OCCUPIED, 0),
        "out_of_service": status_counts.get(models.DockStatus.OUT_OF_SERVICE, 0)
    }


@router.get(
    "/stats/usage-by-day",
    response_model=list[schemas.SensorUsageResponse],
    responses={
        200: {
            "description": "Liste des statistiques d'utilisation par capteur et par jour",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "sensor_id": "ESP32_001",
                            "sensor_name": "Capteur Dock A1",
                            "dock_id": 1,
                            "daily_usage": [
                                {
                                    "date": "2026-01-14",
                                    "occupied_seconds": 7200,
                                    "occupied_hours": 2.0
                                },
                                {
                                    "date": "2026-01-15",
                                    "occupied_seconds": 10800,
                                    "occupied_hours": 3.0
                                }
                            ]
                        },
                        {
                            "sensor_id": "ESP32_002",
                            "sensor_name": "Capteur Dock B2",
                            "dock_id": 2,
                            "daily_usage": [
                                {
                                    "date": "2026-01-14",
                                    "occupied_seconds": 3600,
                                    "occupied_hours": 1.0
                                },
                                {
                                    "date": "2026-01-15",
                                    "occupied_seconds": 5400,
                                    "occupied_hours": 1.5
                                }
                            ]
                        }
                    ]
                }
            }
        }
    }
)
async def get_usage_by_day(
    start_date: str | None = Query(
        None,
        description="Date de début au format YYYY-MM-DD. Par défaut : 7 jours avant aujourd'hui",
        example="2026-01-14"
    ),
    end_date: str | None = Query(
        None,
        description="Date de fin au format YYYY-MM-DD. Par défaut : aujourd'hui",
        example="2026-01-20"
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    ## Temps d'utilisation de chaque capteur par jour
    
    Calcule le temps d'occupation (statut OCCUPIED) de chaque capteur pour chaque jour de la période spécifiée.
    
    ### Paramètres
    - **start_date** *(optionnel)* : Date de début de la période au format YYYY-MM-DD  
      *(par défaut : 7 jours avant aujourd'hui)*
    - **end_date** *(optionnel)* : Date de fin de la période au format YYYY-MM-DD  
      *(par défaut : aujourd'hui)*
    
    ### Retourne
    Une liste d'objets contenant pour chaque capteur :
    - **sensor_id** : Identifiant unique du capteur (ex: ESP32_001)
    - **sensor_name** : Nom attribué au capteur
    - **dock_id** : Identifiant du dock associé
    - **daily_usage** : Liste des statistiques quotidiennes
      - **date** : Date au format YYYY-MM-DD
      - **occupied_seconds** : Temps total d'occupation en secondes
      - **occupied_hours** : Temps total d'occupation en heures (arrondi à 2 décimales)
    
    ### Exemples d'utilisation
    ```
    # 7 derniers jours (par défaut)
    GET /api/public/stats/usage-by-day
    
    # Période personnalisée
    GET /api/public/stats/usage-by-day?start_date=2026-01-01&end_date=2026-01-20
    
    # Depuis une date spécifique jusqu'à aujourd'hui
    GET /api/public/stats/usage-by-day?start_date=2026-01-01
    ```
    
    ### Notes
    - L'historique des changements de statut est enregistré automatiquement à chaque mise à jour du capteur
    - Le calcul prend en compte les périodes qui chevauchent plusieurs jours
    - Les capteurs sans historique retournent des valeurs à 0
    """
    # Parser les dates
    if start_date:
        start = datetime.fromisoformat(start_date)
    else:
        start = datetime.now() - timedelta(days=7)
    
    if end_date:
        end = datetime.fromisoformat(end_date)
    else:
        end = datetime.now()
    
    # Récupérer tous les capteurs
    docks_result = await db.execute(select(models.Dock))
    docks = docks_result.scalars().all()
    
    response = []
    
    for dock in docks:
        # Récupérer l'historique pour ce capteur dans la plage de dates
        history_query = select(models.DockStatusHistory).where(
            models.DockStatusHistory.dock_id == dock.id,
            models.DockStatusHistory.changed_at >= start,
            models.DockStatusHistory.changed_at <= end
        ).order_by(models.DockStatusHistory.changed_at)
        
        history_result = await db.execute(history_query)
        history = history_result.scalars().all()
        
        # Calculer l'utilisation par jour
        daily_usage = {}
        current_date = start.date()
        end_date_obj = end.date()
        
        while current_date <= end_date_obj:
            daily_usage[current_date] = 0
            current_date += timedelta(days=1)
        
        # Parcourir l'historique pour calculer le temps d'occupation
        previous_status = dock.status  # Statut actuel ou par défaut
        previous_time = start
        
        for entry in history:
            # Si le statut précédent était OCCUPIED, ajouter le temps
            if previous_status == models.DockStatus.OCCUPIED:
                time_diff = (entry.changed_at - previous_time).total_seconds()
                entry_date = previous_time.date()
                
                # Si le changement de statut chevauche plusieurs jours
                current_time = previous_time
                while current_time.date() <= entry.changed_at.date():
                    day_end = datetime.combine(current_time.date(), datetime.max.time())
                    day_end = day_end.replace(hour=23, minute=59, second=59)
                    
                    segment_end = min(entry.changed_at, day_end)
                    segment_seconds = (segment_end - current_time).total_seconds()
                    
                    if current_time.date() in daily_usage:
                        daily_usage[current_time.date()] += segment_seconds
                    
                    current_time = day_end + timedelta(seconds=1)
            
            previous_status = entry.status
            previous_time = entry.changed_at
        
        # Ajouter le temps jusqu'à maintenant si le statut actuel est OCCUPIED
        if previous_status == models.DockStatus.OCCUPIED and previous_time < end:
            time_diff = (end - previous_time).total_seconds()
            
            current_time = previous_time
            while current_time.date() <= end.date():
                day_end = datetime.combine(current_time.date(), datetime.max.time())
                day_end = day_end.replace(hour=23, minute=59, second=59)
                
                segment_end = min(end, day_end)
                segment_seconds = (segment_end - current_time).total_seconds()
                
                if current_time.date() in daily_usage:
                    daily_usage[current_time.date()] += segment_seconds
                
                current_time = day_end + timedelta(seconds=1)
        
        # Formater la réponse
        daily_usage_list = [
            {
                "date": date.isoformat(),
                "occupied_seconds": int(seconds),
                "occupied_hours": round(seconds / 3600, 2)
            }
            for date, seconds in sorted(daily_usage.items())
        ]
        
        response.append({
            "sensor_id": dock.sensor_id,
            "sensor_name": dock.name or dock.sensor_id,
            "dock_id": dock.id,
            "daily_usage": daily_usage_list
        })
    
    return response