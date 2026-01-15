from sqlalchemy import Column, Integer, String, Boolean
from geoalchemy2 import Geometry
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class ParkingSpot(Base):
    __tablename__ = "parking_spots"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    location = Column(Geometry("POINT", srid=4326), nullable=False)
    is_available = Column(Boolean, default=True)

class Admin(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)