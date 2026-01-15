from pydantic import BaseModel
from enum import Enum

class SpotStatus(str, Enum):
    HS = "HS"  # Hors service
    LIBRE = "libre"
    OCCUPE = "occupé"

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ParkingSpotCreate(BaseModel):
    name: str
    latitude: float
    longitude: float
    status: SpotStatus = SpotStatus.LIBRE
    image_url: str | None = None

class ParkingSpotResponse(BaseModel):
    id: int
    name: str
    latitude: float
    longitude: float
    status: SpotStatus
    image_url: str | None = None

class SensorUpdate(BaseModel):
    spot_id: int
    status: SpotStatus
    status: SpotStatus | None = None

class DefectReport(BaseModel):
    stand_id: str
    location: str | None = None
