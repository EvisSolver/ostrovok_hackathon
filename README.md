## 🛠️ Стек

- **Python** — основная логика и обработка данных
- **PostgreSQL** — база данных
- **Docker Compose** — запуск базы данных
- **FastAPI** — REST API
- **Uvicorn** — запуск API-сервера

## 🚀 Запуск

### 1. Запускаем базу данных

```bash
cd otters
docker compose up -d
```

### 2. Активируем виртуальное окружение

```bash
source .venv/bin/activate
```

Если окружение ещё не создано:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Загружаем данные в базу

```bash
cd scripts
python etl.py
```

Скрипт обрабатывает данные и загружает их в PostgreSQL.

После выполнения возвращаемся в корень проекта:

```bash
cd ..
```

### 4. Запускаем API

```bash
uvicorn app.main:app --reload
```

Сервер будет доступен по адресу:

**http://127.0.0.1:8000**
**http://127.0.0.1:8000/docs**

### 5. Проверяем, что всё работает

- http://127.0.0.1:8000/docs

В Swagger можно посмотреть доступные эндпоинты и отправить тестовые запросы прямо из браузера.

## 🛑 Остановка

Остановить контейнер с PostgreSQL:

```bash
docker compose down
```

Удалить контейнеры вместе с данными базы:

```bash
docker compose down -v
```

⚠️ **Осторожно:** `-v` удалит Docker-тома с данными PostgreSQL.

API останавливается сочетанием `Ctrl+C` в терминале.

---

**На этом всё.** Поднимаем базу, прогоняем ETL, запускаем API и проверяем результат в Swagger.