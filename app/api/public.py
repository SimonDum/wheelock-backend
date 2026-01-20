from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from geoalchemy2.shape import to_shape
from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/api/public", tags=["public"])

@router.get("/docks-groups", response_model=list[schemas.DocksGroupResponse])
async def list_parking_groups(
    lat: float | None = None,
    lon: float | None = None,
    radius_meters: int = 1000,
    db: AsyncSession = Depends(get_db),
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

        total = len(group.docks)
        available = sum(
            1 for s in group.docks if s.status == models.DockStatus.AVAILABLE
        )

        response.append({
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "image_url": group.image_url,
            "latitude": point.y,
            "longitude": point.x,
            "total_docks": total,
            "available_docks": available,
        })

    return response