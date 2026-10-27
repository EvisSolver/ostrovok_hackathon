import psycopg
import functools
from pathlib import Path
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
            async with await psycopg.AsyncConnection.connect(
                "postgresql:///hotels",
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
    @db_query("get_random_hotel_with_stars.sql")
    async def get_random_hotel_with_stars(dict_answer: dict) -> dict:
        # Здесь мы пишем МИНИМУМ кода: только маппинг параметров для SQL
        return {"stars_number": str(dict_answer["stars"])}

    @staticmethod
    @db_query("get_meters_to_hotel.sql")
    async def get_meters_to_hotel(dict_answer: dict) -> dict:
        return {"meters_number": dict_answer["meters"]}
