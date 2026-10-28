from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db import get_db
from app.models import Hotel, GreenZone

app = FastAPI(title="Otters Hackathon API")

@app.get("/")
def read_root():
    return {"status": "ok", "message": "API работает"}

@app.get("/hotels")
async def get_hotels(limit: int = 10, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Hotel).limit(limit))
    hotels = result.scalars().all()
    return [{"id": h.id, "name": h.name, "stars": h.stars} for h in hotels]

@app.get("/hotels/near-parks")
async def get_hotels_near_parks(max_dist_meters: int = 500, db: AsyncSession = Depends(get_db)):
    """
    Возвращает отели и ближайшие к ним парки в радиусе X метров.
    ST_DWithin отлично работает с типом Geography и сразу считает в метрах.
    """
    stmt = (
        select(
            Hotel.name.label("hotel_name"),
            GreenZone.name.label("park_name"),
            func.ST_Distance(Hotel.location, GreenZone.location).label("dist_meters")
        )
        .join(GreenZone, func.ST_DWithin(Hotel.location, GreenZone.location, max_dist_meters))
        .order_by(func.ST_Distance(Hotel.location, GreenZone.location))
        .limit(20)
    )
    
    result = await db.execute(stmt)
    rows = result.all()
    
    return [
        {
            "hotel": row.hotel_name,
            "park": row.park_name,
            "distance_meters": round(row.dist_meters, 1)
        }
        for row in rows
    ]

@app.get("/hotels/noise-proxy")
async def get_hotels_noise(db: AsyncSession = Depends(get_db)):
    """
    Возвращает отели и расстояние до ближайшей магистрали.
    Чем меньше расстояние, тем выше шум (шум = 10 - distance_km).
    """
    # Подзапрос: для каждого отеля ищем ближайшую дорогу
    stmt = (
        select(
            Hotel.name.label("hotel_name"),
            Road.name.label("road_name"),
            func.ST_Distance(Hotel.location, Road.location).label("dist_meters")
        )
        .join(Road, func.ST_DWithin(Hotel.location, Road.location, 1000)) # ищем в радиусе 1 км
        .order_by(Hotel.name, func.ST_Distance(Hotel.location, Road.location))
    )
    
    result = await db.execute(stmt)
    rows = result.all()
    
    # Группируем результаты (чтобы вывести только ближайшую дорогу для каждого отеля)
    hotels_noise = {}
    for row in rows:
        if row.hotel_name not in hotels_noise:
            dist = row.dist_meters
            # Простая формула: если дорога ближе 100м — шум 10, если дальше 1км — шум 1
            noise_score = max(1.0, min(10.0, 10.0 - (dist / 100.0)))
            
            hotels_noise[row.hotel_name] = {
                "hotel": row.hotel_name,
                "nearest_road": row.road_name,
                "distance_m": round(dist, 1),
                "noise_score": round(noise_score, 1)
            }
            
    return list(hotels_noise.values())