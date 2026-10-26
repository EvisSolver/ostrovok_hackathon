import os

import pandas as pd
import psycopg
import streamlit as st

st.set_page_config(page_title="Отели — SQL", layout="wide")
st.title("Отели Москвы — таблица и SQL")
st.caption("Локальный интерфейс к PostgreSQL. Запросы выполняются только в режиме чтения.")

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql:///hotels")
DEFAULT_QUERY = """SELECT
    name,
    stars,
    phone,
    website,
    address,
    ST_Y(geom) AS latitude,
    ST_X(geom) AS longitude
FROM hotels
ORDER BY name
LIMIT 100;"""

st.subheader("SQL-запрос")
sql = st.text_area("Введите SELECT-запрос", value=DEFAULT_QUERY, height=220)

if st.button("Выполнить запрос", type="primary"):
    try:
        # Use a read-only transaction, so accidental INSERT/UPDATE/DELETE/DDL
        # statements are rejected by PostgreSQL.
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.transaction():
                conn.execute("SET TRANSACTION READ ONLY")
                with conn.cursor() as cur:
                    cur.execute(sql)
                    if cur.description is None:
                        st.info("Запрос выполнен, но не вернул таблицу результатов.")
                    else:
                        columns = [col.name for col in cur.description]
                        rows = cur.fetchmany(10000)
                        st.success(f"Получено строк: {len(rows)}" + (" (показаны первые 10 000)" if len(rows) == 10000 else ""))
                        st.dataframe(
                            pd.DataFrame(rows, columns=columns),
                            use_container_width=True,
                            hide_index=True,
                        )
    except Exception as exc:
        st.error(f"Ошибка запроса: {exc}")
        st.caption("Проверьте SQL и что PostgreSQL запущен, а DATABASE_URL указывает на базу hotels.")

st.divider()
st.caption("Открывайте интерфейс только на этом компьютере: сервер привязан к 127.0.0.1.")
