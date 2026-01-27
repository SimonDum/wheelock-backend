from sqlalchemy import Column, Integer, String, Boolean, Index, cast, Enum as SQLEnum, ForeignKey, DateTime
from geoalchemy2 import Geography
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
    location = Column(Geography("POINT", srid=4326, spatial_index=True), nullable=False)
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
    group_id = Column(Integer, ForeignKey("docks_groups.id", ondelete="SET NULL"), nullable=True)
    group_name = Column(String, nullable=True)  # Sauvegarde du nom pour l'historique
    location = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    status = Column(String, default="pending", nullable=False)  # pending, in_progress, resolved
    
    group = relationship("DocksGroup")

class DockStatusHistory(Base):
    __tablename__ = "dock_status_history"

    id = Column(Integer, primary_key=True)
    dock_id = Column(Integer, ForeignKey("docks.id", ondelete="SET NULL"), nullable=True)
    sensor_id = Column(String, nullable=False)  # Pour garder l'historique
    dock_name = Column(String, nullable=True)  # Pour garder l'historique
    status = Column(SQLEnum(DockStatus), nullable=False)
    changed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False, index=True)
    
    dock = relationship("Dock")