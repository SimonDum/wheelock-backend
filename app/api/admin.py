from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from app.database import get_db
from app.core.security import require_admin
from app import models, schemas

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.post("/spots", response_model=schemas.ParkingSpotResponse)
async def create_spot(
    spot: schemas.ParkingSpotCreate,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin)
):
    location = from_shape(Point(spot.longitude, spot.latitude), srid=4326)
    new = models.ParkingSpot(
        name=spot.name,
        location=location
    )
    db.add(new)
    await db.commit()
    await db.refresh(new)

    return {
        "id": new.id,
        "name": new.name,
        "latitude": spot.latitude,
        "longitude": spot.longitude,
        "is_available": new.is_available
    }