import psycopg

from pathlib import Path
from psycopg.rows import dict_row

from llm_calls_config import *


class LLM_Call_Functions:
    @staticmethod
    async def get_random_hotel_with_stars():
        sql_path = Path(__file__).resolve().parent / f"{sql_path_to_sql_requests}/get_random_hotel_with_stars.sql"
        sql = sql_path.read_text(encoding="utf-8")
        async with await psycopg.AsyncConnection.connect(
            "postgresql:///hotels",
            row_factory = dict_row
        ) as connection:
            async with connection.cursor() as cur:
                await cur.execute(sql)
                hotel = await cur.fetchone()
        return hotel