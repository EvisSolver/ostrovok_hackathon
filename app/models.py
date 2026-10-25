from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, BigInteger
from geoalchemy2 import Geography

class Base(DeclarativeBase):
    pass

class Hotel(Base):
    __tablename__ = 'hotels'
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=True)
    stars: Mapped[int] = mapped_column(Integer, nullable=True)
    # Здесь хранится точка на карте в формате PostGIS
    location: Mapped[str] = mapped_column(Geography(geometry_type='POINT', srid=4326))

class GreenZone(Base):
    __tablename__ = 'green_zones'
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=True)
    type: Mapped[str] = mapped_column(String) # park, water, river
    location: Mapped[str] = mapped_column(Geography(geometry_type='POINT', srid=4326))

class Road(Base):
    __tablename__ = 'roads'
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=True)
    highway_type: Mapped[str] = mapped_column(String) # motorway, primary и т.д.
    # Храним как линию!
    location: Mapped[str] = mapped_column(Geography(geometry_type='LINESTRING', srid=4326))