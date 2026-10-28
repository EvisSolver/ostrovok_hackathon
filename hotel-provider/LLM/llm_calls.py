import os
import psycopg
import functools
from pathlib import Path
from typing import Union
from psycopg.rows import dict_row

from llm_calls_config import *

# 1. Создаем декоратор для автоматизации работы с PostgreSQL и файлами запросов
def db_query(sql_filename: str):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(dict_answer: dict, *args, **kwargs):
            # Автоматически находим и читаем нужный SQL-файл
            sql_path = Path(__file__).resolve().parent / f"{sql_path_to_sql_requests}/{sql_filename}"
            sql = sql_path.read_text(encoding="utf-8")
            
            # Вызываем декорируемую функцию, чтобы получить словарь параметров запроса
            # Сама функция теперь занимается ТОЛЬКО подготовкой данных
            query_params = await func(dict_answer, *args, **kwargs)
            
            # Управляем подключением к базе данных в одном месте
            # В Docker 127.0.0.1 — это сам контейнер; адрес базы задаётся переменной окружения.
            async with await psycopg.AsyncConnection.connect(
                os.getenv("HOTELS_DATABASE_URL", "postgresql://otters:hackathon@127.0.0.1:5432/otters_db"),
                row_factory=dict_row
            ) as connection:
                async with connection.cursor() as cur:
                    await cur.execute(sql, query_params)
                    return await cur.fetchall()
        return wrapper
    return decorator


class LLM_Call_Functions:
    
    # 2. Применяем декоратор и передаем имя файла. На вход метод ждет только dict_answer.
    @staticmethod
    @db_query("request_for_llm.sql")
    async def get_random_hotel_with_stars(dict_answer: Union[dict, str]) -> dict:
        return {
            "hotel_price": dict_answer.get("hotel_price"),
            "hotels_stars": dict_answer.get("hotels_stars"),
            # Текущий промпт metro_names не формирует, но список можно передать отдельно.
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