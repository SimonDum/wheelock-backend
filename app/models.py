from sqlalchemy import Column, Integer, String, Boolean, Enum as SQLEnum, ForeignKey, DateTime
from geoalchemy2 import Geometry
from sqlalchemy.orm import declarative_base, relationship
import enum
from datetime import datetime, UTC

Base = declarative_base()

class DockStatus(str, enum.Enum):
    OUT_OF_SERVICE = "out_of_service"
    AVAILABLE = "available"
    OCCUPIED = "occupied"

class Dock(Base):
    __tablename__ = "docks"

    id = Column(Integer, primary_key=True)
    sensor_id = Column(String, unique=True, nullable=False)  # Hardware ID du capteur
    name = Column(String, nullable=True)  # Nom assignable par l'admin
    status = Column(SQLEnum(DockStatus), default=DockStatus.AVAILABLE, nullable=False)
    group_id = Column(Integer, ForeignKey("docks_groups.id"), nullable=False)
    group = relationship("DocksGroup", back_populates="docks")

class DocksGroup(Base):
    __tablename__ = "docks_groups"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    location = Column(Geometry("POINT", srid=4326, spatial_index=True), nullable=False)
    image_url = Column(String, nullable=True)

    docks = relationship(
        "Dock",
        back_populates="group",
        cascade="all, delete-orphan"
    )

class Admin(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

class DefectReport(Base):
    __tablename__ = "defect_reports"

    id = Column(Integer, primary_key=True)
    stand_id = Column(String, nullable=False)
    location = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    status = Column(String, default="pending", nullable=False)  # pending, in_progress, resolved