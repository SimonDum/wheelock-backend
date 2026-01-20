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