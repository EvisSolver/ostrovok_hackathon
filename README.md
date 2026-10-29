# Ostrovok Hackathon — Сервис бронирования отелей с ИИ-помощником

Проект интерактивного сервиса подбора и бронирования отелей в России с интеграцией мультиагентной нейросети-консультанта.

---

## Видео-демонстрация проекта - https://rutube.ru/video/private/1e727013074af97e70204b9f49ea3d09/?p=Wp4GpjcAhbz58qVXV-5Efw

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

- **Nginx** на порту `8080` (балансировщик нагрузки и статика)
- **3 реплики API** (FastAPI воркеры с автомасштабированием)
- **LLM Microservice** на порту `8001` (3 взаимодействующих нейросетевых агента)
- **PostgreSQL** (хранилище истории переписок)
- **Ollama** с локальными моделями агентов 1 и 2 — модели скачиваются автоматически при первом старте (~7 ГБ) и лежат в папке проекта `hotel-provider/ollama-models/` (в git не попадают), повторные запуски ничего не перекачивают

```bash
# 1. Перейдите в папку сервиса
cd hotel-provider

# 2. Соберите фронтенд
npm run build

# 3. Установка Ollama (для Arch Linux)
sudo pacman -Sy ollama

# 4. Запуск сервера Ollama
ollama serve 

# 5. Загрузка и запуск моделей
ollama run qwen2.5-coder:7b

# 6. Llama 3.2 (3B) — легкая универсальная модель
ollama run llama3.2:3b

# 7. Ключ API для 3-го агента (файл не хранится в git)
cp LLM/.env.example LLM/.env   # и впишите OPEN_ROUTER_KEY

# 8. Поднимите все контейнеры
docker compose up -d --build
```

### Требования к машине

- **Диск:** ~7 ГБ под модели ollama + docker-образы.
- **VRAM (для любого GPU-режима): минимум 6 ГБ, рекомендуется 8–12 ГБ.** Обе локальные модели вместе — qwen2.5-coder:7b ≈ 4.7 ГБ и llama3.2:3b ≈ 2 ГБ плюс KV-кэш — занимают ~8 ГБ; на 6 ГБ они будут подгружаться по очереди, а при нехватке ollama выгрузит часть слоёв на CPU (медленнее, но работает).

Три режима запуска, отличаются только командой:

| Режим | Команда | Что нужно |
|---|---|---|
| **CPU** (по умолчанию) | `docker compose up -d --build` | ~10 ГБ свободной RAM, работает везде, ответы медленнее |
| **AMD GPU** (ROCm) | `docker compose -f docker-compose.yml -f docker-compose.amd.yml up -d --build` | карта RX 6xxx/7xxx; для RX 7xxx задайте `HSA_OVERRIDE_GFX_VERSION=11.0.0` (по умолчанию стоит 10.3.0 — под RX 6xxx) |
| **NVIDIA GPU** | `docker compose -f docker-compose.yml -f docker-compose.nvidia.yml up -d --build` | установленный [nvidia-container-toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) |

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

- **Проверка Swagger UI нейросети:** откройте в браузере `http://localhost:8001/docs`
- **Проверка запроса к нейросети напрямую:**
  ```bash
  curl -X POST http://localhost:8001/generate \
    -H "Content-Type: application/json" \
    -d '{"message": "2 + 2"}'
  ```
- **Проверка потокового чата через Nginx:**
  ```bash
  curl -N -X POST http://localhost:8080/api/chat/stream \
    -H "Content-Type: application/json" \
    -d '{"userId": "test-user-1", "channel": "ai", "message": "2 + 2"}'
  ```
- **Проверка статуса контейнеров:**
  ```bash
  docker compose ps
  ```
