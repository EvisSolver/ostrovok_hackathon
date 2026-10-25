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
    HOTELS_FILE      путь к hotels.json
"""
import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal, Optional

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

log = logging.getLogger("chat")
logging.basicConfig(level=logging.INFO)

DATABASE_URL = os.getenv("DATABASE_URL")
MODEL_URL = os.getenv("MODEL_URL")
MODEL_NAME = os.getenv("MODEL_NAME", "default")
MODEL_API_KEY = os.getenv("MODEL_API_KEY", "")
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT", "8"))
QUEUE_WAIT = float(os.getenv("QUEUE_WAIT", "10"))
RATE_LIMIT = int(os.getenv("RATE_LIMIT", "20"))
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
    S.http = httpx.AsyncClient(timeout=httpx.Timeout(60, connect=5))
    S.slots = asyncio.Semaphore(MAX_CONCURRENT)
    yield
    await S.http.aclose()
    await S.store.close()


app = FastAPI(lifespan=lifespan)


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
    Асинхронный генератор: отдаёт ответ нейронки кусками текста по мере генерации.
    history — [{"role": "user"|"assistant", "text": "..."}], последнее — вопрос человека.
    Если MODEL_URL задан, используется любой OpenAI-совместимый сервер. Иначе — заглушка.
    """
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


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.get("/readyz")
async def readyz():
    try:
        await S.store.ping()
        return {"ok": True}
    except Exception:
        return JSONResponse({"ok": False}, status_code=503)
