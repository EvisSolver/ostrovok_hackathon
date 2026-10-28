import os
import psycopg2
import streamlit as st
import pandas as pd

st.set_page_config(page_title="SQL Playground", layout="wide")
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

# ── Коннект (креды подставь свои, как в etl.py) ──────────────
@st.cache_resource
def get_conn():
    conn = psycopg2.connect(
        dbname="otters_db",
        user="otters",
        password="hackathon",
        host="db",
        port=5432,
    )
    conn.autocommit = True       # SELECT/INSERT/UPDATE работают без явного commit
    return conn


# ── Готовые примеры для сайдбара ────────────────────────────
EXAMPLES = {
    "Отели (первые 20)": "SELECT id, name, stars FROM hotels ORDER BY id LIMIT 20;",
    "Все таблицы в БД": (
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='public' ORDER BY table_name;"
    ),
    "Вода рядом с отелем": """
        SELECT h.name AS hotel, gz.name AS water, gz.type,
               ROUND(ST_Distance(h.location, gz.location)::numeric) AS meters
        FROM hotels h
        JOIN green_zones gz
          ON gz.type IN ('water','river')
         AND ST_DWithin(h.location, gz.location, 500)
        ORDER BY meters LIMIT 50;
    """,
    "Отели + вода + достопримечательность": """
        SELECT h.name AS hotel,
               w.name AS water, ROUND(w.dist::numeric) AS water_m,
               a.name AS attraction, ROUND(a.dist::numeric) AS attr_m
        FROM hotels h
        JOIN LATERAL (
            SELECT gz.name, ST_Distance(h.location, gz.location) AS dist
            FROM green_zones gz
            WHERE gz.type IN ('water','river')
              AND ST_DWithin(h.location, gz.location, 500)
            ORDER BY gz.location <-> h.location LIMIT 1
        ) w ON true
        JOIN LATERAL (
            SELECT a.name, ST_Distance(h.location, a.location) AS dist
            FROM attraction a
            WHERE ST_DWithin(h.location, a.location, 500)
            ORDER BY a.location <-> h.location LIMIT 1
        ) a ON true
        ORDER BY water_m LIMIT 100;
    """,
}


# ── Сайдбар: список таблиц + примеры ────────────────────────
with st.sidebar:
    st.header("📋 Таблицы")
    try:
        with get_conn().cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='public' ORDER BY table_name"
            )
            tables = [r[0] for r in cur.fetchall()]
        for t in tables:
            if st.button(t, key=f"tbl_{t}", use_container_width=True):
                st.session_state.sql = f"SELECT * FROM {t} LIMIT 20;"
    except Exception as e:
        st.error(f"Не подключиться: {e}")

    st.divider()
    st.header("💡 Примеры")
    for label, q in EXAMPLES.items():
        if st.button(label, key=f"ex_{label}", use_container_width=True):
            st.session_state.sql = q


# ── Основная часть ──────────────────────────────────────────
st.title("🗄️ SQL Playground")
st.caption("Пиши запрос и жми Ctrl+Enter или кнопку ниже. SELECT → таблица, DML → сколько строк затронуто.")

default_sql = st.session_state.get("sql", "SELECT * FROM hotels LIMIT 20;")
sql = st.text_area("SQL", value=default_sql, height=220, key="sql_input")
st.session_state.sql = sql

col_run, col_clear = st.columns([1, 5])
run = col_run.button("▶ Выполнить", type="primary", use_container_width=True)
if col_clear.button("Очистить"):
    st.session_state.sql = ""
    st.rerun()

if run and sql.strip():
    try:
        with get_conn().cursor() as cur:
            cur.execute(sql)
            if cur.description:                       # SELECT
                cols = [d[0] for d in cur.description]
                rows = cur.fetchall()
                df = pd.DataFrame(rows, columns=cols)
                st.success(f"✅ {len(df)} строк")
                st.dataframe(df, use_container_width=True, height=600)
            else:                                     # INSERT/UPDATE/DELETE
                st.success(f"✅ Затронуто строк: {cur.rowcount}")
    except psycopg2.Error as e:
        st.error(f"❌ Ошибка: {e.pgerror or e}")