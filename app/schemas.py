from pydantic import BaseModel, Field
from typing import Optional

from app.models import DockStatus

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=255)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class DockCreate(BaseModel):
    group_id: int
    sensor_id: str = Field(..., min_length=1, max_length=50)
    name: Optional[str] = Field(None, max_length=255)


class DockResponse(BaseModel):
    id: int
    sensor_id: str
    name: Optional[str]
    status: DockStatus

    class Config:
        from_attributes = True

class DocksGroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    image_url: Optional[str] = Field(None, max_length=2048)

class DocksGroupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    image_url: Optional[str]
    latitude: float
    longitude: float
    total_docks: int
    available_docks: int

    class Config:
        from_attributes = True


class DocksGroupWithDocksResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    image_url: Optional[str]
    latitude: float
    longitude: float
    docks: list[DockResponse]

    class Config:
        from_attributes = True

class SensorUpdate(BaseModel):
    sensor_id: str = Field(..., min_length=1, max_length=50)
    status: DockStatus

class DocksGroupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    image_url: Optional[str] = Field(None, max_length=2048)

class DockUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    group_id: Optional[int] = None
    sensor_id: Optional[str] = Field(None, min_length=1, max_length=50)
    status: Optional[DockStatus] = None

class DefectReport(BaseModel):
    stand_id: str = Field(..., min_length=1, max_length=255)
    location: str | None = Field(None, max_length=500)

class DailyUsage(BaseModel):
    """Utilisation quotidienne d'un capteur"""
    date: str = Field(..., description="Date au format YYYY-MM-DD", example="2026-01-15")
    occupied_seconds: int = Field(..., description="Temps d'occupation en secondes", example=7200, ge=0)
    occupied_hours: float = Field(..., description="Temps d'occupation en heures (arrondi à 2 décimales)", example=2.0, ge=0)

class SensorUsageResponse(BaseModel):
    """Statistiques d'utilisation d'un capteur par jour"""
    sensor_id: str = Field(..., description="Identifiant unique du capteur", example="ESP32_001")
    sensor_name: str = Field(..., description="Nom du capteur", example="Capteur Dock A1")
    dock_id: int = Field(..., description="Identifiant du dock", example=1)
    daily_usage: list[DailyUsage] = Field(..., description="Liste des usages quotidiens")

    class Config:
        json_schema_extra = {
            "example": {
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
            }
        }

class SensorStatsResponse(BaseModel):
    """Statistiques globales des capteurs"""
    total: int = Field(..., description="Nombre total de capteurs", example=10, ge=0)
    available: int = Field(..., description="Nombre de capteurs libres", example=7, ge=0)
    occupied: int = Field(..., description="Nombre de capteurs occupés", example=2, ge=0)
    out_of_service: int = Field(..., description="Nombre de capteurs hors service", example=1, ge=0)

    class Config:
        json_schema_extra = {
            "example": {
                "total": 10,
                "available": 7,
                "occupied": 2,
                "out_of_service": 1
            }
        }