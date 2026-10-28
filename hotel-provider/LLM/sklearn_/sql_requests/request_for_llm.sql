-- значения приходят из Python-словаря через параметры драйвера PostgreSQL.
-- явные типы позволяют безопасно передавать NULL и не зависят от того,
-- привязывает ли драйвер значения на стороне клиента или сервера.
WITH filters AS (
    SELECT
        CAST(%(hotel_price)s AS numeric) AS hotel_price,
        CAST(%(hotels_stars)s AS integer) AS hotels_stars,
        CAST(%(metro_names)s AS text[]) AS metro_names,
        CAST(%(distance_to_metro_meters)s AS numeric) AS distance_to_metro_meters,
        CAST(%(distance_to_green_zones_meters)s AS numeric) AS distance_to_green_zones_meters,
        CAST(%(distance_to_attraction_meters)s AS numeric) AS distance_to_attraction_meters,
        CAST(%(distance_to_road_meters)s AS numeric) AS distance_to_road_meters,
        CAST(%(distance_to_shop_meters)s AS numeric) AS distance_to_shop_meters,
        CAST(%(distance_to_where_to_eat_meters)s AS numeric) AS distance_to_where_to_eat_meters,
        CAST(%(roads_within_100m)s AS integer) AS roads_within_100m,
        CAST(%(shop_malls_name)s AS text) AS shop_malls_name,
        CAST(%(where_to_eat_name)s AS text) AS where_to_eat_name,
        CAST(%(where_to_eat_type)s AS text) AS where_to_eat_type,
        CAST(%(main_road_name)s AS text) AS main_road_name
)
SELECT json_agg(main_result) AS json_agg
FROM (
    SELECT
        -- Hotel's
        h.hotel_id,
        h.hotel_name,
        h.hotel_price,
        h.hotels_stars,

        -- metros
        h.metro_name,
        h.distance_to_metro_meters,

        -- roads and MKAD
        h.road_name,
        h.road_type,
        h.distance_to_road_meters,
        h.main_road_name,
        h.dist_to_mkad_meters,

        -- shops
        h.shop_malls_name,
        h.shop_malls_type,
        h.distance_to_shop_meters,

        -- green zones
        h.green_zones_name,
        h.type_formatted,
        h.distance_to_green_zones_meters,

        -- foodcords
        h.where_to_eat_name,
        h.where_to_eat_type,
        h.distance_to_where_to_eat_meters,

        -- attractions
        h.attraction_name,
        h.distance_to_attraction_meters,

        -- infrastructure
        h.roads_within_100m,
        h.crossings_within_100m,

        -- conditions
        NULLIF(h.attraction_name, 'Unknown') AS cleaned_attraction_name,
        h.hotel_price AS final_price,
        h.hotels_stars AS final_stars
    FROM mv_hotels_analytics AS h
    CROSS JOIN filters AS f
    WHERE

-- living-values
        (f.hotel_price IS NULL OR h.hotel_price <= f.hotel_price)
        AND (f.hotels_stars IS NULL OR h.hotels_stars = f.hotels_stars)
        AND (f.metro_names IS NULL OR h.metro_name = ANY(f.metro_names))
        AND (f.distance_to_metro_meters IS NULL OR h.distance_to_metro_meters <= f.distance_to_metro_meters)
        AND (f.distance_to_green_zones_meters IS NULL OR h.distance_to_green_zones_meters <= f.distance_to_green_zones_meters)
        AND (f.distance_to_attraction_meters IS NULL OR h.distance_to_attraction_meters <= f.distance_to_attraction_meters)
        AND (f.distance_to_road_meters IS NULL OR h.distance_to_road_meters <= f.distance_to_road_meters)
        AND (f.distance_to_shop_meters IS NULL OR h.distance_to_shop_meters <= f.distance_to_shop_meters)
        AND (f.distance_to_where_to_eat_meters IS NULL OR h.distance_to_where_to_eat_meters <= f.distance_to_where_to_eat_meters)
        AND (f.roads_within_100m IS NULL OR f.roads_within_100m = 0 OR h.roads_within_100m >= f.roads_within_100m)
        AND (f.shop_malls_name IS NULL OR h.shop_malls_name = f.shop_malls_name)
        AND (f.where_to_eat_name IS NULL OR h.where_to_eat_name = f.where_to_eat_name)
        AND (f.where_to_eat_type IS NULL OR h.where_to_eat_type = f.where_to_eat_type)
        AND (f.main_road_name IS NULL OR h.main_road_name = f.main_road_name)
    -- Без LIMIT широкий фильтр отдавал до 938 отелей одним JSON — весь список уходил
    -- в промпт ANSWER_COMPOSER. Берём случайную восьмёрку подходящих.
    ORDER BY random()
    LIMIT 8
) AS main_result;
