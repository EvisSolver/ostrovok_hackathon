## 🛠️ Стек
- **PostgreSQL + PostGIS** — база данных
- **Python 3.12** — основная логика
- **FastAPI** — REST API
- **Streamlit** — веб-интерфейс
- **Docker & Docker Compose** — контейнеризация всего проекта

## 🚀 Запуск проекта

Открой терминал в корне проекта (где лежит `docker-compose.yml`) и выполни одну команду:

```bash
docker compose up -d --build

## Что где
127.0.0.1:8000 - api
127.0.0.1:5432 - postgis
127.0.0.1:8501 - streamlit