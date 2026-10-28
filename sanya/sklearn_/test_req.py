import json
import psycopg2

DATABASE_URL = "postgresql://otters:hackathon@127.0.0.1:5432/otters_db"

query = """
SELECT json_agg(main_result) FROM (
    SELECT 
        *, 
        NULLIF(attraction_name, 'Unknown') AS cleaned_attraction_name,

        CASE 
            WHEN hotel_price != %(hotel_price)s THEN hotel_price
            ELSE hotel_price 
        END AS final_price,

        CASE 
            WHEN hotels_stars = %(hotels_stars)s THEN hotels_stars
            ELSE hotels_stars
        END AS final_stars

    FROM mv_hotels_analytics

    WHERE 
        (metro_name = ANY(%(metro_names)s) OR %(metro_names)s IS NULL)
        AND distance_to_metro_meters <= %(distance_to_metro_meters)s
        AND distance_to_green_zones_meters <= %(distance_to_green_zones_meters)s
        AND distance_to_attraction_meters <= %(distance_to_attraction_meters)s
        AND distance_to_road_meters <= %(distance_to_road_meters)s
        AND distance_to_shop_meters <= %(distance_to_shop_meters)s
        AND distance_to_where_to_eat_meters <= %(distance_to_where_to_eat_meters)s
        AND roads_within_100m >= %(roads_within_100Ж 
) main_result;
"""

test_params = {
    'hotel_price': 5000,
    'hotels_stars': 4,
    'metro_names': None,
    'distance_to_metro_meters': 99999,
    'distance_to_green_zones_meters': 99999,
    'distance_to_attraction_meters': 99999,
    'distance_to_road_meters': 99999,
    'distance_to_shop_meters': 99999,
    'distance_to_where_to_eat_meters': 99999,
    'roads_within_100m': 1
}

try:
    conn = psycopg2.connect(DATABASE_URL)
    with conn.cursor() as cursor:
        cursor.execute(query, test_params)
        result = cursor.fetchone()
        
        json_data = result[0] if result else None
        
        if json_data:
            print("твой запрос успешно выполнился и вернул JSON данные:")
            # Красиво печатаем полученный JSON-массив
            print(json.dumps(json_data, indent=4, ensure_ascii=False)[:2000]) # Ограничил вывод до 2000 символов
            print("\n... (вывод обрезан, чтобы не спамить консоль) ...")
        else:
            print("запрос выполнился БЕЗ ОШИБОК, но вернул 0 строк (JSON пуст).")
            print("Возможно, в таблице нет строк, где roads_within_100m = true.")
            
    conn.close()

except Exception as e:
    print("ошибка при выполнении твоего запроса:")
    print(e)
