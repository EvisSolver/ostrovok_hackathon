# Ostrovok Hackathon — Сервис бронирования отелей с ИИ-помощником

Проект интерактивного сервиса подбора и бронирования отелей в России с интеграцией мультиагентной нейросети-консультанта.

---

## Структура репозитория

```
.
├── hotel-provider/             # Основной проект сервиса
│   ├── src/                    # Фронтенд (React 18 + Sass + Vite)
│   │   ├── components/         # Компоненты (HeroChat, HotelTicker, Filters и др.)
│   │   ├── pages/              # Страницы (HomePage, HotelPage)
│   │   └── services/           # Связь с API (chatApi, hotelsService)
│   ├── server/                 # Бэкенд на Python (FastAPI + Uvicorn)
│   │   ├── app.py              # Потоковый SSE-эндпоинт, хранилище истории, прокси к LLM
│   │   └── Dockerfile          # Докеризация бэкенда
│   ├── LLM/                    # Автономный микросервис нейросети
│   │   ├── server_llm.py       # FastAPI HTTP API (порт 8001)
│   │   ├── LLM.py              # Фасад цепочки из 3 агентов
│   │   ├── LLM_REQUEST_BUILDER/# 1-й агент: анализ запроса и формирование ТЗ
│   │   ├── LLM_DATA_FETCHER/   # 2-й агент: подбор данных под параметры
│   │   ├── LLM_ANSWER_COMPOSER/# 3-й агент: финальный вежливый ответ клиенту
│   │   └── Dockerfile          # Докеризация LLM микросервиса
│   ├── nginx.conf              # Балансировщик Nginx (раздача статики + проксирование API)
│   └── docker-compose.yml      # Полный продакшн-стенд (Nginx + 3 API + LLM + Postgres)
└── README.md                   # Документация проекта
```

---

## Быстрый старт (Docker Compose)

Полный стенд поднимается в одну команду и включает в себя:
* **Nginx** на порту `8080` (балансировщик нагрузки и статика)
* **3 реплики API** (FastAPI воркеры с автомасштабированием)
* **LLM Microservice** на порту `8001` (3 взаимодействующих нейросетевых агента)
* **PostgreSQL** (хранилище истории переписок)

```bash
# 1. Перейдите в папку сервиса
cd hotel-provider

# 2. Соберите фронтенд
npm run build

# 3. Поднимите все контейнеры
docker compose up -d --build
```

После старта перейдите в браузере:  
👉 **http://localhost:8080**

Остановка:
```bash
docker compose down
```

---

## Режим разработки (локально)

1. **Микросервис LLM:**
   ```bash
   cd hotel-provider/LLM && uvicorn server_llm:app --host 0.0.0.0 --port 8001
   ```
2. **Бэкенд:**
   ```bash
   cd hotel-provider/server && uvicorn app:app --port 8000 --reload
   ```
3. **Фронтенд:**
   ```bash
   cd hotel-provider && npm run dev
   ```
   Сайт разработки доступен на **http://localhost:5173**.

---

## Команды для тестирования

* **Проверка Swagger UI нейросети:** откройте в браузере `http://localhost:8001/docs`
* **Проверка запроса к нейросети напрямую:**
  ```bash
  curl -X POST http://localhost:8001/generate \
    -H "Content-Type: application/json" \
    -d '{"message": "2 + 2"}'
  ```
* **Проверка потокового чата через Nginx:**
  ```bash
  curl -N -X POST http://localhost:8080/api/chat/stream \
    -H "Content-Type: application/json" \
    -d '{"userId": "test-user-1", "channel": "ai", "message": "2 + 2"}'
  ```
* **Проверка статуса контейнеров:**
  ```bash
  docker compose ps
  ```
