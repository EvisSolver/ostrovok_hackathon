import psycopg
import functools
from pathlib import Path
from psycopg.rows import dict_row

from llm_calls_config import *

def db_query(sql_filename: str):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(dict_answer: dict, *args, **kwargs):
            sql_path = Path(__file__).resolve().parent / f"{sql_path_to_sql_requests}/{sql_filename}"
            sql = sql_path.read_text(encoding="utf-8")
            
            query_params = await func(dict_answer, *args, **kwargs)

            async with await psycopg.AsyncConnection.connect(
                "postgresql://otters:hackathon@127.0.0.1:5432/otters_db",
                row_factory=dict_row
            ) as connection:
                async with connection.cursor() as cur:
                    await cur.execute(sql, query_params)
                    return await cur.fetchall()
        return wrapper
    return decorator


class LLM_Call_Functions:

    @staticmethod
    @db_query("request_for_llm.sql")
    async def get_random_hotel_with_stars(dict_answer: Union[dict, str]) -> dict:
        return {
            "hotel_price": dict_answer.get("hotel_price"),
            "hotels_stars": dict_answer.get("hotels_stars"),
            "metro_names": dict_answer.get("metro_names"),
            "distance_to_metro_meters": dict_answer.get("distance_to_metro_meters"),
            "distance_to_green_zones_meters": dict_answer.get("distance_to_green_zones_meters"),
            "distance_to_attraction_meters": dict_answer.get("distance_to_attraction_meters"),
            "distance_to_road_meters": dict_answer.get("distance_to_road_meters"),
            "distance_to_shop_meters": dict_answer.get("distance_to_shop_meters"),
            "distance_to_where_to_eat_meters": dict_answer.get("distance_to_where_to_eat_meters"),
            "roads_within_100m": dict_answer.get("roads_within_100m"),
            "shop_malls_name": dict_answer.get("shop_malls_name"),
            "where_to_eat_name": dict_answer.get("where_to_eat_name"),
            "where_to_eat_type": dict_answer.get("where_to_eat_type"),
            "main_road_name": dict_answer.get("main_road_name"),
        }