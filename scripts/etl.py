import asyncio
import json
import os
from geoalchemy2.elements import WKTElement
from sqlalchemy import insert

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import engine, AsyncSessionLocal
from app.models import Base, Hotel, GreenZone, Road, Attraction, Shop_malls, Where_to_eat

def make_point(lat: float, lon: float) -> WKTElement:
    return WKTElement(f"POINT({lon} {lat})", srid=4326)

# НОВОЕ: функция для создания линии
def make_linestring(geometry_array: list) -> WKTElement | None:
    if not geometry_array or len(geometry_array) < 2:
        return None
    # Формат: LINESTRING(lon1 lat1, lon2 lat2, ...)
    coords = ", ".join([f"{p['lon']} {p['lat']}" for p in geometry_array])
    return WKTElement(f"LINESTRING({coords})", srid=4326)

def parse_stars(raw) -> int | None:
    if not raw: return None
    first = str(raw).split(";")[0].strip()
    return int(first) if first.isdigit() else None

def get_coords(el: dict):
    if "lat" in el and "lon" in el:
        return el["lat"], el["lon"]
    if "center" in el:
        return el["center"]["lat"], el["center"]["lon"]
    if el.get("geometry"):
        geom = el["geometry"]
        return sum(p["lat"] for p in geom) / len(geom), sum(p["lon"] for p in geom) / len(geom)
    if "bounds" in el:
        b = el["bounds"]
        return (b["minlat"] + b["maxlat"]) / 2, (b["minlon"] + b["maxlon"]) / 2
    return None, None

def detect_zone_type(tags: dict) -> str:
    for key in ("leisure", "natural", "waterway"):
        if key in tags:
            return tags[key]
    return "unknown"
 
def detect_shop_type(tags: dict) -> str: # ДОДЕЛАТЬДОДЕЛАТЬДОДЕЛАТЬДОДЕЛАТЬДОДЕЛАТЬДОДЕЛАТЬ
    for key in ("leisure", "natural", "waterway"):
        if key in tags:
            return tags[key]
    return "unknown"

def detect_whereeat_type(tags: dict) -> str: # ДОДЕЛАТЬДОДЕЛАТЬДОДЕЛАТЬДОДЕЛАТЬДОДЕЛАТЬДОДЕЛАТЬ
    for key in ("leisure", "natural", "waterway"):
        if key in tags:
            return tags[key]
    return "unknown"


async def main():
    # 1. Создаем таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2. Читаем отели
    print("Чтение отелей...")
    with open("../data/hotels.json", "r", encoding="utf-8") as f:
        hotels_raw = json.load(f).get("elements", [])

    hotel_rows = []
    for el in hotels_raw:
        lat, lon = get_coords(el)
        if lat is None: continue
        tags = el.get("tags", {})
        hotel_rows.append({
            "id": el["id"],
            "name": tags.get("name", "Unknown"),
            "stars": parse_stars(tags.get("stars")),
            "location": make_point(lat, lon),
        })

    # 3. Читаем парки
    print("Чтение парков...")
    with open("../data/park_water_moscow.json", "r", encoding="utf-8") as f:
        zones_raw = json.load(f).get("elements", [])

    zone_rows = []
    for el in zones_raw:
        lat, lon = get_coords(el)
        if lat is None: continue
        tags = el.get("tags", {})
        zone_rows.append({
            "id": el["id"],
            "name": tags.get("name", "Unknown"),
            "type": detect_zone_type(tags),
            "location": make_point(lat, lon),
        })

    #Читаем дороги
    print("Чтение дорог...")
    with open("../data/roads_moscow.json", "r", encoding="utf-8") as f:
        roads_raw = json.load(f).get("elements", [])

    road_rows = []
    for el in roads_raw:
        geom = el.get("geometry") # у дорог всегда есть geometry, если делали out geom
        line = make_linestring(geom)
        if not line: continue
        
        tags = el.get("tags", {})
        road_rows.append({
            "id": el["id"],
            "name": tags.get("name", "Unknown"),
            "highway_type": tags.get("highway", "unknown"),
            "location": line,
        })

###МОЙ ГОВНО КОД НЕ НЕЙРОНКА ДАЖЕ КЛЯНГУСЬ67

    print("Чтение shop_malls...")
    with open("../data/shop_malls.json", "r", encoding="utf-8") as f:
        shop_malls_raw = json.load(f).get("elements", [])

    shop_malls_rows = []
    for el in shop_malls_raw:
        lat, lon = get_coords(el)
        if lat is None: continue
        tags = el.get("tags", {})
        shop_malls_rows.append({
            "id": el["id"],
            "name": tags.get("name", "Unknown"),
            "type": detect_shop_type(tags),
            "location": make_point(lat, lon),
        })


    print("Чтение attraction...")
    with open("../data/attraction.json", "r", encoding="utf-8") as f:
        attraction_raw = json.load(f).get("elements", [])

    attraction_rows = []
    for el in attraction_raw:
        lat, lon = get_coords(el)
        if lat is None: continue
        tags = el.get("tags", {})
        attraction_rows.append({
            "id": el["id"],
            "name": tags.get("name", "Unknown"),
            "location": make_point(lat, lon),
        })

    print("Чтение where_to_eat...")
    with open("../data/where_to_eat.json", "r", encoding="utf-8") as f:
        where_to_eat_raw = json.load(f).get("elements", [])

    where_to_eat_rows = []
    for el in where_to_eat_raw:
        lat, lon = get_coords(el)
        if lat is None: continue
        tags = el.get("tags", {})
        where_to_eat_rows.append({
            "id": el["id"],
            "name": tags.get("name", "Unknown"),
            "type": detect_whereeat_type(tags),
            "location": make_point(lat, lon),
        })


    # 4. Заливаем в базу
    print(
        f"Заливка: {len(hotel_rows)} отелей, {len(zone_rows)} зон, {len(road_rows)} дорог, "
        f"{len(attraction_rows)} достопримечательностей, {len(shop_malls_rows)} ТЦ, "
        f"{len(where_to_eat_rows)} точек еды"
    )
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Очистка перед заливкой
            await session.execute(Hotel.__table__.delete())
            await session.execute(GreenZone.__table__.delete())
            await session.execute(Road.__table__.delete()) 
            await session.execute(Attraction.__table__.delete())
            await session.execute(Shop_malls.__table__.delete())
            await session.execute(Where_to_eat.__table__.delete())

            # Быстрый bulk insert
            if hotel_rows:
                await session.execute(insert(Hotel), hotel_rows)
            if zone_rows:
                await session.execute(insert(GreenZone), zone_rows)
            if road_rows: 
                await session.execute(insert(Road), road_rows)
            if road_rows: 
                await session.execute(insert(Attraction), attraction_rows)
            if road_rows: 
                await session.execute(insert(Shop_malls), shop_malls_rows)
            if road_rows: 
                await session.execute(insert(Where_to_eat), where_to_eat_rows)
    
    print("✅ ETL успешно завершен!")

if __name__ == "__main__":
    asyncio.run(main())