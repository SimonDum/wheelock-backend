from sqlalchemy import select, func, exists
from sqlalchemy.orm import selectinload
from geoalchemy2.shape import to_shape
from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.core.security import require_admin
from app import models, schemas
from app.core.storage import storage_service
from app.core.security import get_password_hash, verify_password

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


@router.post("/change-password", status_code=204)
async def change_admin_password(
    data: schemas.AdminChangePassword,
    db: AsyncSession = Depends(get_db),
    admin: models.Admin = Depends(require_admin),
):
    if not verify_password(data.old_password, admin.hashed_password):
        raise HTTPException(
            status_code=403,
            detail="Mot de passe actuel incorrect"
        )

    if verify_password(data.new_password, admin.hashed_password):
        raise HTTPException(
            status_code=400,
            detail="Le nouveau mot de passe doit être différent"
        )

    admin.hashed_password = get_password_hash(data.new_password)
    db.add(admin)
    await db.commit()

    return Response(status_code=204)