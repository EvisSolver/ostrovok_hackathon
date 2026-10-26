# LLM Pipeline & Microservice — Подбор отелей

Цепочка из трёх специализированных нейросетей-агентов, работающих последовательно:
запрос клиента → ТЗ (фильтры/пожелания) → данные из каталога → финальный вежливый ответ.

```
Пользователь ─► LLM_REQUEST_BUILDER ─► LLM_DATA_FETCHER ─► LLM_ANSWER_COMPOSER ─► Ответ
                  запрос → ТЗ            ТЗ → данные          данные → текст
```

Сервис упакован в автономный Docker-микросервис с HTTP API на базе FastAPI, готовый к горизонтальному масштабированию.

---

## Архитектура файлов

| Файл | Назначение |
|---|---|
| `server_llm.py` | FastAPI HTTP-микросервис (`POST /generate`, `GET /health`) для вызова извне и Docker |
| `LLM.py` | Фасад пайплайна: класс `LLM`, метод `pipeline()`, консольный REPL `chat()` |
| `LLM_REQUEST_BUILDER/` | 1-я ступень: анализ запроса пользователя и формирование структуры ТЗ |
| `LLM_DATA_FETCHER/` | 2-я ступень: подбор подходящих данных под параметры запроса |
| `LLM_ANSWER_COMPOSER/` | 3-я ступень: компоновка финального текста ответа пользователю |
| `config.py` | Конфигурация ступеней: URL модели, API-ключ, системные промпты |
| `Dockerfile` | Сборка легковесного контейнера на `python:3.12-slim` с Uvicorn |
| `requirements.txt` | Минимальные продакшн-зависимости (`fastapi`, `uvicorn`, `httpx`, `python-dotenv`, `pydantic`, `pystyle`) |

---

## Способы запуска

### Способ 1. Запуск в Docker (Рекомендуемый)

Сборка и запуск контейнера:
```bash
# 1. Сборка образа
docker build -t hotel-llm .

# 2. Запуск контейнера
docker run -d --name hotel-llm -p 8001:8001 --env-file .env hotel-llm
```

Проверка через интерактивную документацию Swagger UI:
Откройте в браузере: **http://localhost:8001/docs**

### Способ 2. Запуск локально через Python

```bash
pip install -r requirements.txt
export OPEN_ROUTER_KEY=ваш_ключ   # или задайте в .env

# Запуск HTTP API:
uvicorn server_llm:app --host 0.0.0.0 --port 8001

# Или запуск интерактивного консольного REPL:
python LLM.py
```

---

## API Микросервиса

### 1. Проверка состояния: `GET /health`
```bash
curl http://localhost:8001/health
```
**Ответ:** `{"status": "ok"}`

### 2. Генерация ответа: `POST /generate`
```bash
curl -X POST http://localhost:8001/generate \
  -H "Content-Type: application/json" \
  -d '{"message": "Подбери отель в Сочи у моря"}'
```
**Ответ:**
```json
{
  "response": "Финальный текст ответа...",
  "details": {
    "request_builder": "ТЗ от первого агента...",
    "data_fetcher": "Данные от второго агента..."
  }
}
```

---

## Использование в Python-коде

```python
import asyncio
from LLM import LLM
from config import REQUEST_BUILDER, DATA_FETCHER, ANSWER_COMPOSER

async def main():
    service = LLM(REQUEST_BUILDER, DATA_FETCHER, ANSWER_COMPOSER)
    result = await service.pipeline("Отель в центре Москвы до 10 000 рублей")
    print("ТЗ:", result["t_f_d_f"])
    print("Данные:", result["t_f_a_c"])
    print("Ответ клиенту:", result["T_F_U"])

asyncio.run(main())
```
