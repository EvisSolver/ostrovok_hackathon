import os
import geopandas as gpd
from sqlalchemy import create_engine, text

# 1. Параметры подключения к базе данных Docker
DATABASE_URL = "postgresql://otters:hackathon@localhost:5432/otters_db"
engine = create_engine(DATABASE_URL)

# 2. Имя вашего файла
geojson_path = "export.geojson"

if not os.path.exists(geojson_path):
    print(f"❌ Ошибка: Файл '{geojson_path}' не найден в текущей директории!")
    print("Пожалуйста, положите файл 'export.geojson' рядом с этим скриптом.")
    exit()

print("1/4 Чтение и парсинг GeoJSON файла...")
gdf = gpd.read_file(geojson_path)

# Выставляем стандартную GPS проекцию (WGS84)
if gdf.crs is None:
    gdf.set_crs(epsg=4326, inplace=True)
else:
    gdf = gdf.to_crs(epsg=4326)

print(f"   Успешно прочитано пешеходных объектов: {len(gdf)}")

print("2/4 Создание таблицы 'pedestrian_crossings' в вашей БД (без изменения других таблиц)...")
with engine.begin() as conn:
    conn.execute(text("DROP MATERIALIZED VIEW IF EXISTS mv_hotels_analytics CASCADE;"))

gdf.to_postgis(
    name="pedestrian_crossings", 
    con=engine, 
    if_exists="replace", 
    index=False
)

print("3/4 Создание пространственного GIST-индекса для моментальной скорости в Streamlit...")
with engine.begin() as conn:
    conn.execute(text("CREATE INDEX IF NOT EXISTS crossings_geo_idx ON pedestrian_crossings USING GIST (geometry);"))

print("4/4 Создание/Обновление материализованного представления mv_hotels_analytics...")
# SQL-запрос сборки всей аналитики хакатона в одну быструю таблицу
mv_sql = """
DROP MATERIALIZED VIEW IF EXISTS mv_hotels_analytics CASCADE;

CREATE MATERIALIZED VIEW mv_hotels_analytics AS
SELECT 
    -- 1. ДАННЫЕ ОТЕЛЯ
    NULLIF(h.name, 'Unknown') AS hotel_name,
    h.id AS hotel_id,
    h.price AS hotel_price,
    h.stars AS hotels_stars,
    h.location AS hotel_location,
 
    -- 2. МЕТРО (CROSS JOIN)
    m.name AS metro_name,
    m.dist AS distance_to_metro_meters,

    -- 3. БЛИЖАЙШАЯ ОБЩАЯ ДОРОГА
    NULLIF(r.name, 'Unknown') AS road_name,
    r.highway_type AS road_type,
    r.dist AS distance_to_road_meters,

    -- 4. ТРАССЫ И МКАД
    NULLIF(main_road.name, 'Unknown') AS main_road_name, 
    main_road.highway_type AS main_road_type, 
    main_road.dist AS dist_to_main_road_meters, 
    mkad.dist AS dist_to_mkad_meters,

    -- 5. ТОРГОВЫЕ ЦЕНТРЫ И СУПЕРМАРКЕТЫ
    s.name AS shop_malls_name,
    s.type AS shop_malls_type,
    s.location AS shop_malls_location,
    s.dist AS distance_to_shop_meters,

    -- 6. ПАРКИ И ЗЕЛЕНЫЕ ЗОНЫ
    NULLIF(g.name, 'Unknown') AS green_zones_name,
    NULLIF(g.type, 'Unknown') AS type_formatted,
    g.location AS green_zones_location,
    g.dist AS distance_to_green_zones_meters,

    -- 7. ТОЧКИ ОБЩЕСТВЕННОГО ПИТАНИЯ (Кафе, Рестораны)
    NULLIF(w.name, 'Unknown') AS where_to_eat_name,
    NULLIF(w.type, 'Unknown') AS where_to_eat_type,
    w.location AS where_to_eat_location,
    w.dist AS distance_to_where_to_eat_meters,

    -- 8. ДОСТОПРИМЕЧАТЕЛЬНОСТИ
    NULLIF(a.name, 'Unknown') AS name_formatted,
    a.name AS attraction_name,
    a.location AS attraction_location,
    a.dist AS distance_to_attraction_meters,

    -- 9. ПЕШЕХОДНАЯ И ДОРОЖНАЯ ИНФРАСТРУКТУРА
    COALESCE(r_cnt.roads_count, 0) AS roads_within_100m,
    COALESCE(p_cnt.crossings_count, 0) AS crossings_within_100m

FROM hotels h

-- [МЕТРО] Ближайшее в радиусе 1000м
CROSS JOIN LATERAL (
    SELECT id, name, location, ROUND(ST_Distance(h.location, metro.location)) AS dist
    FROM metro
    WHERE ST_DWithin(h.location, metro.location, 1000)
    ORDER BY metro.location <-> h.location
    LIMIT 1
) m

-- [ДОРОГА ОБЩАЯ] Ближайшая в радиусе 1000м
LEFT JOIN LATERAL (
    SELECT name, highway_type, ROUND(ST_Distance(h.location, roads.location)) AS dist
    FROM roads
    WHERE ST_DWithin(h.location, roads.location, 1000)
    ORDER BY roads.location <-> h.location
    LIMIT 1
) r ON TRUE

-- [ГЛАВНАЯ ТРАССА] Магистраль (motorway или trunk)
LEFT JOIN LATERAL (
    SELECT name, highway_type, ROUND(ST_Distance(h.location, roads.location)) AS dist
    FROM roads 
    WHERE highway_type IN ('motorway', 'trunk') 
    ORDER BY roads.location <-> h.location 
    LIMIT 1
) main_road ON TRUE 

-- [МКАД] Ближайшая точка МКАД по названию
LEFT JOIN LATERAL (
    SELECT ROUND(ST_Distance(h.location, roads.location)) AS dist 
    FROM roads 
    WHERE name LIKE '%%МКАД%%'
    ORDER BY roads.location <-> h.location 
    LIMIT 1
) mkad ON TRUE 

-- [ТОРГОВЫЕ ЦЕНТРЫ] Ближайший в радиусе 1000м
LEFT JOIN LATERAL (
    SELECT name, type, location, ROUND(ST_Distance(h.location, shop_malls.location)) AS dist
    FROM shop_malls
    WHERE ST_DWithin(h.location, shop_malls.location, 1000)
    ORDER BY shop_malls.location <-> h.location
    LIMIT 1
) s ON TRUE

-- [ПАРКИ / ЗЕЛЕНЫЕ ЗОНЫ] Ближайшая в радиусе 1000м
LEFT JOIN LATERAL (
    SELECT name, type, location, ROUND(ST_Distance(h.location, green_zones.location)) AS dist
    FROM green_zones
    WHERE ST_DWithin(h.location, green_zones.location, 1000)
    ORDER BY green_zones.location <-> h.location
    LIMIT 1
) g ON TRUE

-- [ЕДА] Ближайшая точка общепита в радиусе 500м
LEFT JOIN LATERAL (
    SELECT name, type, location, ROUND(ST_Distance(h.location, where_to_eat.location)) AS dist
    FROM where_to_eat
    WHERE ST_DWithin(h.location, where_to_eat.location, 500)
    ORDER BY where_to_eat.location <-> h.location
    LIMIT 1
) w ON TRUE

-- [ДОСТОПРИМЕЧАТЕЛЬНОСТИ] Ближайшая в радиусе 2000м
LEFT JOIN LATERAL (
    SELECT name, location, ROUND(ST_Distance(h.location, attraction.location)) AS dist
    FROM attraction
    WHERE ST_DWithin(h.location, attraction.location, 2000)
    ORDER BY attraction.location <-> h.location
    LIMIT 1
) a ON TRUE

-- [ПОДСЧЕТ ДОРОГ] Количество линий дорог в радиусе 100м
LEFT JOIN LATERAL (
    SELECT COUNT(*) AS roads_count
    FROM roads
    WHERE ST_DWithin(h.location, roads.location, 100)
) r_cnt ON TRUE

-- [ПОДСЧЕТ ПЕРЕХОДОВ] Количество переходов в радиусе 100м
LEFT JOIN LATERAL (
    SELECT COUNT(*) AS crossings_count
    FROM pedestrian_crossings
    WHERE ST_DWithin(h.location, pedestrian_crossings.geometry, 100)
) p_cnt ON TRUE

WHERE h.name IS DISTINCT FROM 'Unknown' 
  AND h.name IS NOT NULL
  AND LENGTH(h.stars::text) = 1;

-- Создаем быстрые b-tree индексы поверх материализованной таблицы
CREATE UNIQUE INDEX IF NOT EXISTS mv_hotels_id_idx ON mv_hotels_analytics (hotel_id);
CREATE INDEX IF NOT EXISTS mv_hotels_price_idx ON mv_hotels_analytics (hotel_price);
CREATE INDEX IF NOT EXISTS mv_hotels_stars_idx ON mv_hotels_analytics (hotels_stars);
"""

with engine.begin() as conn:
    conn.execute(text(mv_sql))

print("✅ Данные и материализованное представление 'mv_hotels_analytics' успешно загружены!")
print("💡 В коде Streamlit теперь достаточно делать простейший: SELECT * FROM mv_hotels_analytics;")
