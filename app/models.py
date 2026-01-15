from sqlalchemy import Column, Integer, String, Boolean, Enum as SQLEnum
from geoalchemy2 import Geometry
from sqlalchemy.orm import declarative_base
import enum

Base = declarative_base()

class SpotStatus(str, enum.Enum):
    HS = "HS"  
    LIBRE = "libre"
    OCCUPE = "occupé"

class ParkingSpot(Base):
    __tablename__ = "parking_spots"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    location = Column(Geometry("POINT", srid=4326), nullable=False)
    status = Column(SQLEnum(SpotStatus), default=SpotStatus.LIBRE, nullable=False)
    image_url = Column(String, nullable=True)

class Admin(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)