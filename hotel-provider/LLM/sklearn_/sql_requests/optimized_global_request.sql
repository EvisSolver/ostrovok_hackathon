
CREATE INDEX IF NOT EXISTS hotels_geo_idx ON hotels USING GIST (location);
CREATE INDEX IF NOT EXISTS metro_geo_idx ON metro USING GIST (location);
CREATE INDEX IF NOT EXISTS roads_geo_idx ON roads USING GIST (location);
CREATE INDEX IF NOT EXISTS shop_malls_geo_idx ON shop_malls USING GIST (location);
CREATE INDEX IF NOT EXISTS green_zones_geo_idx ON green_zones USING GIST(location);
CREATE INDEX IF NOT EXISTS where_to_eat_geo_idx ON where_to_eat USING GIST(location);
CREATE INDEX IF NOT EXISTS attraction_geo_idx ON attraction USING GIST(location);


SELECT 
    -- hotels
    h.id AS hotel_id,
    h.name AS hotel_name,
    h.price AS hotel_price,
    h.stars AS hotels_stars,
    h.location AS hotel_location,

    -- metro
    m.name AS metro_name,
    m.dist AS distance_to_metro_meters,

    -- roads
    r.highway_type AS road_type,
    r.dist AS distance_to_road_meters,

    -- shop_malls
    s.name AS shop_malls_name,
    s.type AS shop_malls_type,
    s.location AS shop_malls_location,
    s.dist AS distance_to_shop_meters,

    -- green_zones
    g.location AS green_zones_location,
    g.dist AS distance_to_green_zones_meters,

    -- where_to_eat
    w.type AS where_to_eat_type,
    w.location AS where_to_eat_location,
    w.dist AS distance_to_where_to_eat_meters,

    -- attraction
    a.name AS attraction_name,
    a.location AS attraction_location,
    a.location AS distance_to_attraction_meters,

NULLIF(g.type, 'Unknown') AS type_formatted,
NULLIF(a.name, 'Unknown') AS name_formatted,
NULLIF(r.name, 'Unknown') AS road_name,
NULLIF(g.name, 'Unknown') AS green_zones_name,
NULLIF(w.name, 'Unknown') AS where_to_eat_name


FROM hotels h

-- Мгновенно находим ОДНО самое близкое метро в радиусе 1000м
CROSS JOIN LATERAL (
    SELECT id, name, location, ROUND(ST_Distance(h.location, metro.location)) AS dist
    FROM metro
    WHERE ST_DWithin(h.location, metro.location, 1000)
    ORDER BY metro.location <-> h.location
    LIMIT 1
) m

-- Мгновенно находим ОДНУ самую близкую дорогу в радиусе 1000м
LEFT JOIN LATERAL (
    SELECT name, highway_type, ROUND(ST_Distance(h.location, roads.location)) AS dist
    FROM roads
    WHERE ST_DWithin(h.location, roads.location, 1000)
    ORDER BY roads.location <-> h.location
    LIMIT 1
) r ON TRUE

-- Мгновенно находим ОДИН самый близкий ТЦ в радиусе 1000м
LEFT JOIN LATERAL (
    SELECT name, type, location, ROUND(ST_Distance(h.location, shop_malls.location)) AS dist
    FROM shop_malls
    WHERE ST_DWithin(h.location, shop_malls.location, 1000)
    ORDER BY shop_malls.location <-> h.location
    LIMIT 1
) s ON TRUE

-- green_zones fast-searching
LEFT JOIN LATERAL (
    SELECT name, type, location, ROUND(ST_Distance(h.location, green_zones.location)) AS dist
    FROM green_zones
    WHERE ST_DWithin(h.location, green_zones.location, 1000)
    ORDER BY green_zones.location <-> h.location
    LIMIT 1
) g ON TRUE


-- where_to_eat fast-searching
LEFT JOIN LATERAL (
    SELECT name, type, location, ROUND(ST_Distance(h.location, where_to_eat.location)) AS dist
    FROM where_to_eat
    WHERE ST_DWithin(h.location, where_to_eat.location, 500)
    ORDER BY where_to_eat.location <-> h.location
    LIMIT 1
) w ON TRUE


-- where_to_eat fast-searching
LEFT JOIN LATERAL (
    SELECT name, location, ROUND(ST_Distance(h.location, attraction.location)) AS dist
    FROM attraction
    WHERE ST_DWithin(h.location, attraction.location, 2000)
    ORDER BY attraction.location <-> h.location
    LIMIT 1
) a ON TRUE
-- Фильтрация отелей на верхнем уровне (индекс по stars тоже поможет)
WHERE LENGTH(h.stars::text) = 1