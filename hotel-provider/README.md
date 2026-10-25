# Отели России (React + Sass)

    npm install
    npm run dev

## Данные
- `public/data/hotels.json` — список отелей (сейчас 7 вымышленных примеров). Формат — в `src/data/hotelSchema.js`.
- Географические показатели (минуты пешком): `access: { metro, sea, center }`. `null` — рядом нет.
  Если `access.<ключ>` не задан, но есть `lat`/`lon` отеля и `places.<ключ>` (точки из OSM/карт),
  время считается автоматически по ближайшей точке (см. `walkMinutes` в `src/utils.js`).
- Загрузка идёт через `src/services/hotelsService.js` — менять источник нужно только там.

## Чаты
`src/services/chatApi.js` — `askAI` и `askSupport` (заглушки).

## Сервер чатов (Python + PostgreSQL)
Подробности и настройки — в шапке `server/app.py`.

Разработка (без базы, переписки хранятся в памяти процесса):

    cd server
    python -m pip install -r requirements.txt
    python -m uvicorn app:app --reload --port 8000

С PostgreSQL (таблица `chat_messages` создаётся сама; можно несколько воркеров):

    $env:DATABASE_URL="postgresql://user:password@localhost:5432/hotels"
    python -m uvicorn app:app --workers 4 --port 8000

Полный стенд (Docker): `npm run build`, затем `docker compose up --build`, сайт на http://localhost:8080.
Нейронка подключается в `stream_model()` в `server/app.py` (или переменной `MODEL_URL` для OpenAI-совместимого сервера).
Поддержка: сообщения лежат в `chat_messages` с `channel = 'support'`; сейчас на них отвечает заглушка.
