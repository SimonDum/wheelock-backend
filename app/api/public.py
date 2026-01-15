from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from geoalchemy2.shape import to_shape

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/api/public", tags=["public"])

@router.get("/spots", response_model=list[schemas.ParkingSpotResponse])
async def get_spots(
    lat: float | None = None,
    lon: float | None = None,
    radius_meters: int = 1000,
    db: AsyncSession = Depends(get_db),
):
    query = select(models.ParkingSpot)

    if lat and lon:
        center = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
        query = query.filter(
            func.ST_DWithin(models.ParkingSpot.location, center, radius_meters)
        )

    result = await db.execute(query)
    spots = result.scalars().all()

    return [{
        "id": s.id,
        "name": s.name,
        "latitude": to_shape(s.location).y,
        "longitude": to_shape(s.location).x,
        "status": s.status,
        "image_url": s.image_url
    } for s in spots]
