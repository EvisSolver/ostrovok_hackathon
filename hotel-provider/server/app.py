"""
Сервер чатов: stateless-воркеры + PostgreSQL + стриминг ответа.

Разработка (без базы, память процесса, ОДИН воркер):
    pip install -r requirements.txt
    python -m uvicorn app:app --reload --port 8000
С PostgreSQL (можно несколько воркеров):
    $env:DATABASE_URL="postgresql://user:password@localhost:5432/hotels"
    python -m uvicorn app:app --workers 4 --port 8000
Полный стенд (nginx + 3 копии API + Postgres): см. docker-compose.yml.

Переменные окружения:
    DATABASE_URL     postgresql://user:pass@host:5432/db   (нет = память процесса)
    MODEL_URL        OpenAI-совместимый сервер (vLLM, Ollama, облачный API), MODEL_NAME, MODEL_API_KEY
    MAX_CONCURRENT   одновременных генераций на воркер (по умолчанию 8)
    QUEUE_WAIT       сколько секунд ждать свободный слот (по умолчанию 10)
    RATE_LIMIT       сообщений на пользователя за 60 с (по умолчанию 20)
    HOTELS_FILE      путь к hotels.json (используется текущим AI-контуром)
    HOTELS_DATABASE_URL  PostgreSQL с каталогом отелей (опционально)
"""
import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from collections import OrderedDict
from typing import Literal, Optional

from fastapi import Query

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field


log = logging.getLogger("chat")
logging.basicConfig(level=logging.INFO)

DATABASE_URL = os.getenv("DATABASE_URL")
HOTELS_DATABASE_URL = os.getenv("HOTELS_DATABASE_URL")
LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL")
MODEL_URL = os.getenv("MODEL_URL")
MODEL_NAME = os.getenv("MODEL_NAME", "default")
MODEL_API_KEY = os.getenv("MODEL_API_KEY", "")
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT", "8"))
QUEUE_WAIT = float(os.getenv("QUEUE_WAIT", "10"))
RATE_LIMIT = int(os.getenv("RATE_LIMIT", "20"))
HOTELS_PAGE_SIZE = 25
HOTELS_CACHE_SIZE = 128
HOTELS_CACHE_TTL = 60
MODEL_HISTORY = 20      # сколько последних сообщений видит модель
UI_HISTORY = 50         # сколько сообщений отдаём в окно чата при открытии
HOTELS_FILE = Path(os.getenv("HOTELS_FILE", Path(__file__).resolve().parent.parent / "public" / "data" / "hotels.json"))


# ======================= хранилище переписок =======================
# role: "user" | "assistant" (ИИ) | "operator" (человек из поддержки) | "system" (заглушки)
class MemoryStore:
    """Только для разработки: данные живут в одном процессе и пропадают при перезапуске."""
    def __init__(self):
        self.rows: dict[tuple[str, str], list[dict]] = {}

    async def init(self): pass
    async def close(self): pass
    async def ping(self): return True

    async def append(self, user_id, channel, role, text):
        self.rows.setdefault((user_id, channel), []).append({"role": role, "text": text})

    async def history(self, user_id, channel, limit):
        return list(self.rows.get((user_id, channel), []))[-limit:]


class PostgresStore:
    def __init__(self, dsn):
        self.dsn = dsn
        self.pool = None

    async def init(self):
        import asyncpg
        # max_size небольшой: воркеров много, а у Postgres ограничено число соединений (по умолчанию 100)
        self.pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=5)
        async with self.pool.acquire() as c:
            await c.execute("SELECT pg_advisory_lock(7351)")      # воркеры стартуют одновременно — создаём таблицу по очереди
            try:
                await c.execute("""
                    CREATE TABLE IF NOT EXISTS chat_messages (
                        id         BIGSERIAL PRIMARY KEY,
                        user_id    TEXT NOT NULL,
                        channel    TEXT NOT NULL,
                        role       TEXT NOT NULL,
                        text       TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    );
                    CREATE INDEX IF NOT EXISTS chat_messages_user_idx ON chat_messages (user_id, channel, id);
                """)
            finally:
                await c.execute("SELECT pg_advisory_unlock(7351)")

    async def close(self):
        await self.pool.close()

    async def ping(self):
        return await self.pool.fetchval("SELECT 1")

    async def append(self, user_id, channel, role, text):
        await self.pool.execute(
            "INSERT INTO chat_messages (user_id, channel, role, text) VALUES ($1, $2, $3, $4)",
            user_id, channel, role, text)

    async def history(self, user_id, channel, limit):
        rows = await self.pool.fetch(
            """SELECT role, text FROM (
                   SELECT id, role, text FROM chat_messages
                   WHERE user_id = $1 AND channel = $2 ORDER BY id DESC LIMIT $3
               ) t ORDER BY id""",
            user_id, channel, limit)
        return [dict(r) for r in rows]


class RateLimiter:
    """Счётчик в памяти процесса: при N воркерах реальный лимит до N раз выше. Жёсткий лимит — в nginx (limit_req)."""
    def __init__(self):
        self.hits: dict[str, tuple[int, float]] = {}

    def allow(self, key, limit, window):
        now = time.time()
        n, until = self.hits.get(key, (0, 0))
        if now > until:
            n, until = 0, now + window
            if len(self.hits) > 50000:          # защита от разрастания словаря
                self.hits.clear()
        self.hits[key] = (n + 1, until)
        return n + 1 <= limit


class State:
    store = None
    hotels_pool = None
    limiter = RateLimiter()
    http: httpx.AsyncClient = None
    slots: asyncio.Semaphore = None


S = State()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if DATABASE_URL:
        S.store = PostgresStore(DATABASE_URL)
    else:
        S.store = MemoryStore()
        log.warning("DATABASE_URL не задан: переписки хранятся в памяти процесса. Только для разработки, один воркер!")
    await S.store.init()
    if not HOTELS_DATABASE_URL:
        raise RuntimeError("HOTELS_DATABASE_URL не задан: каталог отелей недоступен")
    import asyncpg
    S.hotels_pool = await asyncpg.create_pool(HOTELS_DATABASE_URL, min_size=1, max_size=5)
    async with S.hotels_pool.acquire() as connection:
        await connection.execute("ALTER TABLE hotels ADD COLUMN IF NOT EXISTS description TEXT")
    S.http = httpx.AsyncClient(timeout=httpx.Timeout(60, connect=5))
    S.slots = asyncio.Semaphore(MAX_CONCURRENT)
    yield
    await S.http.aclose()
    await S.hotels_pool.close()
    await S.store.close()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ======================= формат запроса =======================
class Context(BaseModel):
    path: str = "/"
    hotelSlug: Optional[str] = None   # заполнен, если человек на странице отеля


class ChatRequest(BaseModel):
    userId: str = Field(min_length=8, max_length=64)   # постоянный id посетителя (позже — id аккаунта)
    channel: str                                       # "ai" | "support"
    message: str = Field(min_length=1, max_length=2000)
    context: Context = Context()                       # историю хранит сервер (по userId)


# ======================= данные об отелях =======================
_hotels_cache = {"mtime": 0, "data": []}
_catalog_cache: OrderedDict[str, tuple[float, dict]] = OrderedDict()


def load_hotels() -> list[dict]:
    mtime = HOTELS_FILE.stat().st_mtime
    if mtime != _hotels_cache["mtime"]:                      # перечитываем только при изменении файла
        _hotels_cache.update(mtime=mtime, data=json.loads(HOTELS_FILE.read_text(encoding="utf-8")))
    return _hotels_cache["data"]


def mentioned_hotels(text: str, hotels: list[dict]) -> list[dict]:
    """Отели, названные в ответе, — фронт покажет на них ссылки."""
    return [{"slug": h["slug"], "name": h["name"]} for h in hotels if h["name"] in text][:3]


# ======================= ЗДЕСЬ РАБОТАЕТ НЕЙРОНКА =======================
def build_system_prompt(current_hotel: Optional[dict], hotels: list[dict]) -> str:
    prompt = (
        "Ты помощник сервиса по подбору отелей в России. Отвечай по-русски, коротко, "
        "используй только данные каталога ниже, ничего не выдумывай. "
        "access — минуты пешком до метро/моря/центра (null = рядом нет). "
        "Называй отели в точности как в поле name.\n\n"
        f"Каталог:\n{json.dumps(hotels, ensure_ascii=False)}"
    )
    if current_hotel:
        prompt += f"\n\nЧеловек сейчас смотрит отель:\n{json.dumps(current_hotel, ensure_ascii=False)}"
    return prompt


async def stream_model(system_prompt: str, history: list[dict]):
    """
    Асинхронный генератор: отдаёт ответ нейронки.
    history — [{"role": "user"|"assistant", "text": "..."}], последнее — вопрос человека.
    Если задан LLM_SERVICE_URL, используется Docker-микросервис LLM.
    Иначе, если MODEL_URL задан, используется OpenAI-совместимый сервер. Иначе — заглушка.
    """
    if LLM_SERVICE_URL:
        user_message = history[-1]["text"]
        try:
            r = await S.http.post(
                f"{LLM_SERVICE_URL.rstrip('/')}/generate",
                json={"message": user_message},
                timeout=75.0,
            )
            r.raise_for_status()
            data = r.json()
            yield data.get("response", "")
            return
        except Exception as e:
            log.error(f"Ошибка обращения к LLM_SERVICE_URL: {e}")
            yield f"Ошибка сервиса нейросети: {e}"
            return

    if not MODEL_URL:
        for word in f"Заглушка ИИ. Вы написали: «{history[-1]['text']}»".split(" "):
            await asyncio.sleep(0.05)
            yield word + " "
        return

    payload = {
        "model": MODEL_NAME,
        "stream": True,
        "messages": [{"role": "system", "content": system_prompt}]
        + [{"role": m["role"], "content": m["text"]} for m in history],
    }
    headers = {"Authorization": f"Bearer {MODEL_API_KEY}"} if MODEL_API_KEY else {}
    for attempt in (1, 2):                                   # один повтор, если модель не ответила до первого токена
        started = False
        try:
            async with S.http.stream("POST", f"{MODEL_URL}/chat/completions", json=payload, headers=headers) as r:
                r.raise_for_status()
                async for line in r.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        return
                    delta = json.loads(data)["choices"][0]["delta"].get("content")
                    if delta:
                        started = True
                        yield delta
            return
        except (httpx.TransportError, httpx.HTTPStatusError):
            if started or attempt == 2:
                raise
            await asyncio.sleep(0.5)


# ======================= вспомогательное =======================
def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() or (request.client.host if request.client else "?")


def check_rate(req: ChatRequest, request: Request):
    ok = S.limiter.allow(f"u:{req.userId}", RATE_LIMIT, 60) and S.limiter.allow(f"ip:{client_ip(request)}", RATE_LIMIT * 5, 60)
    if not ok:
        raise HTTPException(429, "Слишком много сообщений", headers={"Retry-After": "10"})


# ======================= эндпоинты =======================
@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest, request: Request):
    check_rate(req, request)
    hotels = load_hotels()
    current = next((h for h in hotels if h["slug"] == req.context.hotelSlug), None)

    async def events():
        try:
            # очередь: ждём свободный слот; не дождались — клиент повторит позже
            try:
                await asyncio.wait_for(S.slots.acquire(), QUEUE_WAIT)
            except asyncio.TimeoutError:
                yield sse("busy", {"retryAfter": 3})
                return
            try:
                await S.store.append(req.userId, "ai", "user", req.message)
                history = await S.store.history(req.userId, "ai", MODEL_HISTORY)
                parts = []
                async for chunk in stream_model(build_system_prompt(current, hotels), history):
                    parts.append(chunk)
                    yield sse("token", {"t": chunk})
                full = "".join(parts)
                await S.store.append(req.userId, "ai", "assistant", full)
                yield sse("done", {"hotels": mentioned_hotels(full, hotels)})
            finally:
                S.slots.release()          # срабатывает и при обрыве соединения клиентом
        except Exception:
            log.exception("chat stream failed")
            yield sse("error", {"message": "Не удалось получить ответ"})

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


SUPPORT_STUB = "Заглушка. Здесь должны быть реальные люди."


@app.post("/api/support")
async def support(req: ChatRequest, request: Request):
    check_rate(req, request)
    # Сообщение остаётся в таблице chat_messages (channel='support') — оттуда его будут брать операторы.
    await S.store.append(req.userId, "support", "user", req.message)
    await S.store.append(req.userId, "support", "system", SUPPORT_STUB)
    return {"reply": SUPPORT_STUB}


@app.get("/api/history")
async def history(channel: Literal["ai", "support"], x_user_id: str = Header(min_length=8, max_length=64)):
    """Переписка пользователя — чтобы окно чата восстановилось после перезапуска браузера."""
    return {"messages": await S.store.history(x_user_id, channel, UI_HISTORY)}


HOTEL_SORTS = {
    "stars": "stars DESC NULLS LAST, id ASC",
    "price-asc": "price ASC NULLS LAST, id ASC",
    "price-desc": "price DESC NULLS LAST, id ASC",
    "id": "id ASC",
}


def _catalog_cache_key(q, stars, max_price, sort, page, page_size, proximity):
    return json.dumps(
        [q, stars, max_price, sort, page, page_size, proximity],
        ensure_ascii=False,
    )


HOTEL_NAME_PREDICATE = "name IS NOT NULL AND btrim(name) <> '' AND lower(btrim(name)) <> 'unknown'"


def _catalog_cache_get(key):
    cached = _catalog_cache.get(key)
    if cached is None:
        return None
    created, value = cached
    if time.monotonic() - created > HOTELS_CACHE_TTL:
        _catalog_cache.pop(key, None)
        return None
    _catalog_cache.move_to_end(key)
    return value


def _catalog_cache_put(key, value):
    _catalog_cache[key] = (time.monotonic(), value)
    _catalog_cache.move_to_end(key)
    while len(_catalog_cache) > HOTELS_CACHE_SIZE:
        _catalog_cache.popitem(last=False)


@app.get("/api/hotels")
async def get_hotels(
    q: str = Query("", max_length=120),
    stars: Optional[str] = Query(None, max_length=20),
    max_price: Optional[int] = Query(None, ge=0),
    sort: str = Query("stars", max_length=20),
    page: int = Query(1, ge=1),
    page_size: int = Query(HOTELS_PAGE_SIZE, ge=1, le=HOTELS_PAGE_SIZE),
    park_distance_m: Optional[int] = Query(None, ge=1, le=50000),
    water_distance_m: Optional[int] = Query(None, ge=1, le=50000),
    river_distance_m: Optional[int] = Query(None, ge=1, le=50000),
    road_distance_m: Optional[int] = Query(None, ge=1, le=50000),
    attraction_distance_m: Optional[int] = Query(None, ge=1, le=50000),
    mall_distance_m: Optional[int] = Query(None, ge=1, le=50000),
    food_distance_m: Optional[int] = Query(None, ge=1, le=50000),
):
    """Return one bounded, database-filtered catalog page."""
    if sort not in HOTEL_SORTS:
        raise HTTPException(400, "Неизвестная сортировка")
    try:
        selected_stars = sorted({int(value) for value in (stars or "").split(",") if value})
    except ValueError as exc:
        raise HTTPException(400, "Некорректный фильтр звёзд") from exc
    if any(value < 1 or value > 5 for value in selected_stars):
        raise HTTPException(400, "Некорректный фильтр звёзд")

    normalized_q = q.strip()
    proximity = {
        "park": park_distance_m,
        "water": water_distance_m,
        "river": river_distance_m,
        "road": road_distance_m,
        "attraction": attraction_distance_m,
        "mall": mall_distance_m,
        "food": food_distance_m,
    }
    key = _catalog_cache_key(
        normalized_q, selected_stars, max_price, sort, page, page_size, proximity
    )
    cached = _catalog_cache_get(key)
    if cached is not None:
        return cached

    predicates = [HOTEL_NAME_PREDICATE]
    params = []
    if normalized_q:
        params.append(f"%{normalized_q}%")
        predicates.append(f"name ILIKE ${len(params)}")
    if selected_stars:
        params.append(selected_stars)
        predicates.append(f"stars = ANY(${len(params)}::int[])")
    if max_price is not None:
        params.append(max_price)
        predicates.append(f"price <= ${len(params)}")

    def add_exists(table, distance, condition=""):
        if distance is None:
            return
        params.append(distance)
        distance_param = len(params)
        predicates.append(
            f"EXISTS (SELECT 1 FROM {table} nearby "
            f"WHERE ST_DWithin(hotels.location, nearby.location, ${distance_param})"
            f"{condition})"
        )

    add_exists("green_zones", park_distance_m, " AND nearby.type = 'park'")
    add_exists("green_zones", water_distance_m, " AND nearby.type = 'water'")
    add_exists("green_zones", river_distance_m, " AND nearby.type = 'river'")
    add_exists("roads", road_distance_m)
    add_exists("attraction", attraction_distance_m)
    add_exists("shop_malls", mall_distance_m)
    add_exists("where_to_eat", food_distance_m)

    where = f" WHERE {' AND '.join(predicates)}"
    offset = (page - 1) * page_size
    count_sql = f"SELECT count(*) FROM hotels{where}"
    rows_sql = f"""
        SELECT id, name, stars, price,
               ST_Y(location::geometry) AS latitude,
               ST_X(location::geometry) AS longitude
        FROM hotels{where}
        ORDER BY {HOTEL_SORTS[sort]}
        LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
    """
    try:
        async with S.hotels_pool.acquire() as connection:
            async with connection.transaction():
                total = await connection.fetchval(count_sql, *params)
                rows = await connection.fetch(rows_sql, *params, page_size, offset)
    except Exception as exc:
        log.exception("Failed to load hotel catalog from PostgreSQL")
        raise HTTPException(503, "Каталог отелей временно недоступен") from exc

    result = {
        "items": [_hotel_for_site(row) for row in rows],
        "total": total,
        "page": page,
        "pageSize": page_size,
        "totalPages": (total + page_size - 1) // page_size,
    }
    _catalog_cache_put(key, result)
    return result


@app.get("/api/hotels/{slug}")
async def get_hotel(slug: str):
    try:
        hotel_id = int(slug.removeprefix("hotel-"))
    except ValueError:
        # The database catalog uses numeric IDs; legacy demo links are not DB slugs.
        raise HTTPException(404, "Отель не найден")
    try:
        row = await S.hotels_pool.fetchrow(f"""
            SELECT id, name, stars, price, description,
                   ST_Y(location::geometry) AS latitude,
                   ST_X(location::geometry) AS longitude
            FROM hotels
            WHERE id = $1
              AND {HOTEL_NAME_PREDICATE}
        """, hotel_id)
    except Exception as exc:
        log.exception("Failed to load hotel %s from PostgreSQL", hotel_id)
        raise HTTPException(503, "Каталог отелей временно недоступен") from exc
    if row is None:
        raise HTTPException(404, "Отель не найден")

    nearby = await _hotel_nearby(hotel_id)
    return _hotel_for_site(row, nearby=nearby)


async def _hotel_nearby(hotel_id: int) -> list[dict]:
    """Return the nearest named OSM features for a hotel."""
    queries = (
        ("park", "green_zones", "nearby.type = 'park'"),
        ("water", "green_zones", "nearby.type = 'water'"),
        ("river", "green_zones", "nearby.type = 'river'"),
        ("road", "roads", "TRUE"),
        ("attraction", "attraction", "TRUE"),
        ("mall", "shop_malls", "TRUE"),
        ("food", "where_to_eat", "TRUE"),
    )
    nearby = []
    async with S.hotels_pool.acquire() as connection:
        for category, table, condition in queries:
            rows = await connection.fetch(
                f"""
                SELECT nearby.name, {('nearby.type' if table == 'green_zones' else 'NULL')} AS object_type,
                       ROUND(ST_Distance(h.location, nearby.location)::numeric) AS distance_m
                FROM hotels h
                CROSS JOIN {table} nearby
                WHERE h.id = $1
                  AND {condition}
                  AND nearby.name IS NOT NULL
                  AND btrim(nearby.name) <> ''
                  AND lower(btrim(nearby.name)) <> 'unknown'
                ORDER BY nearby.location <-> h.location
                LIMIT 2
                """,
                hotel_id,
            )
            nearby.extend(
                {
                    "category": category,
                    "type": row["object_type"],
                    "name": row["name"],
                    "distanceM": int(row["distance_m"]),
                    "distance": _format_distance(row["distance_m"]),
                }
                for row in rows
            )
    return nearby


def _format_distance(distance_m) -> str:
    meters = int(distance_m)
    return f"{meters} м" if meters < 1000 else f"{meters / 1000:.1f} км"


def _hotel_for_site(row, nearby=None) -> dict:
    hotel_id = row["id"]
    latitude = row["latitude"]
    longitude = row["longitude"]
    location = None
    if latitude is not None and longitude is not None:
        location = {"lat": latitude, "lng": longitude, "address": ""}
        if nearby is not None:
            location["nearby"] = nearby
    description = row.get("description") if hasattr(row, "get") else None
    return {
        "id": hotel_id,
        "slug": f"hotel-{hotel_id}",
        "name": row["name"] or f"Отель {hotel_id}",
        "city": "",
        "region": "",
        "country": "Россия",
        "stars": row["stars"] or 0,
        "priceFrom": row["price"],
        "priceIsMock": row["price"] is not None,
        "priceSource": "synthetic-mock" if row["price"] is not None else None,
        "description": [description] if description else [],
        "currency": "RUB",
        "location": location,
        "lat": latitude,
        "lon": longitude,
    }


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.get("/readyz")
async def readyz():
    try:
        await S.store.ping()
        await S.hotels_pool.fetchval("SELECT 1")
        return {"ok": True}
    except Exception:
        return JSONResponse({"ok": False}, status_code=503)
