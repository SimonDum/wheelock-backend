from pydantic import BaseModel

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

class ParkingSpotResponse(BaseModel):
    id: int
    name: str
    latitude: float
    longitude: float
    is_available: bool

class SensorUpdate(BaseModel):
    spot_id: int
    is_available: bool
