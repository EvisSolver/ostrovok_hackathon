SELECT DISTINCT ON (hotels.id)
-- hotels
    hotels.id AS hotel_id,
    hotels.name AS hotel_name,
    hotels.price AS hotel_price,
    hotels.stars AS hotels_stars,
    hotels.location AS hotel_location,

-- metro
    metro.name AS metro_name,
    ROUND(ST_Distance(hotels.location, metro.location)) AS distance_to_metro_meters,

-- roads
    roads.name AS road_name,
    roads.highway_type AS road_type,
    ROUND(ST_Distance(hotels.location, roads.location)) AS distance_to_road_meters,

-- shop_malls(mall's, supermarkets)
    shop_malls.name AS shop_malls_name,
    shop_malls.type AS shop_malls_type,
    shop_malls.location AS shop_malls_location

FROM hotels

LEFT JOIN metro ON ST_DWithin(hotels.location, metro.location, 1000)
LEFT JOIN roads ON ST_DWithin(hotels.location, roads.location, 1000)
LEFT JOIN shop_malls ON ST_DWithin(hotels.location, shop_malls.location, 1000)

-- filtration
WHERE LENGTH(hotels.stars::text) = 1 
  AND metro.name IS NOT NULL

-- sort
ORDER BY 
    hotels.id ASC, 
    ST_Distance(hotels.location, metro.location) ASC, 
    ST_Distance(hotels.location, roads.location) ASC,
    ST_Distance(hotels.location, shop_malls.location) ASC



