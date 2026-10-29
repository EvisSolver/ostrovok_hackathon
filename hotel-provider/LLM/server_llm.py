
import json
import logging
import os
import re
import sys
import time
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Детальные логи сервиса — в stdout, то есть прямо в `docker logs`.
# LLM_LOG_LEVEL=DEBUG печатает ответы агентов целиком, INFO — обрезанными.
logging.basicConfig(
    level=os.getenv("LLM_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("llm.api")

from LLM import LLM
from config import REQUEST_BUILDER, DATA_FETCHER, ANSWER_COMPOSER

app = FastAPI(title="LLM Multi-Agent Service", version="1.0.0")

# Стартовая сводка конфигурации: первое, что видно в docker logs.
log.info(
    "старт: ollama=%s | база отелей=%s | ключ API: %s | лог-уровень=%s",
    os.getenv("OLLAMA_HOST", "localhost:11434 (по умолчанию!)"),
    (os.getenv("HOTELS_DATABASE_URL", "postgresql://…@127.0.0.1:5432/otters_db (по умолчанию)")).split("@")[-1],
    "задан" if os.getenv("OPEN_ROUTER_KEY") else "НЕ ЗАДАН — агент 3 упадёт",
    os.getenv("LLM_LOG_LEVEL", "INFO"),
)

# Инициализируем пайплайн из 3 агентов
service = LLM(REQUEST_BUILDER, DATA_FETCHER, ANSWER_COMPOSER)


class QueryRequest(BaseModel):
    message: str


class QueryResponse(BaseModel):
    response: str
    # ID выбранных отелей из первого, JSON-ответа пайплайна.
    # Поле пустое для старых ответов, которые ещё не содержат JSON.
    hotel_ids: list[int] = Field(default_factory=list)
    details: dict | None = None


def _parse_json_response(value: Any) -> Any:
    """Parse JSON returned as an object, string, or fenced code block."""
    if not isinstance(value, str):
        return value

    text = value.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE | re.DOTALL).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Модель иногда добавляет короткий текст до или после JSON.
        start = min((i for i in (text.find("{"), text.find("[")) if i >= 0), default=-1)
        if start < 0:
            return None
        end = max(text.rfind("}"), text.rfind("]"))
        if end < start:
            return None
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None


def _hotel_ids(value: Any) -> list[int]:
    """Collect hotel IDs from the selection JSON without changing its shape."""
    found: list[int] = []
    seen: set[int] = set()
    id_keys = {"id", "hotel_id", "hotelId", "hotelID"}

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            for key, item in node.items():
                if key in id_keys and isinstance(item, (int, str)) and not isinstance(item, bool):
                    try:
                        hotel_id = int(item)
                    except (TypeError, ValueError):
                        continue
                    if hotel_id > 0 and hotel_id not in seen:
                        seen.add(hotel_id)
                        found.append(hotel_id)
                else:
                    visit(item)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(value)
    return found


def _mentioned_hotel_ids(selection: Any, answer: str) -> list[int]:
    """ID только тех отелей, чьи названия реально прозвучали в ответе: композер
    разбирает 1-2 лучших и таблицу, а в данных отелей больше — лишние ссылки запутывают."""
    pairs: list[tuple[int, str]] = []

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            raw_id = node.get("hotel_id") or node.get("id")
            name = node.get("hotel_name") or node.get("name")
            try:
                hotel_id = int(raw_id)
            except (TypeError, ValueError):
                hotel_id = 0
            if hotel_id > 0 and isinstance(name, str) and name.strip():
                pairs.append((hotel_id, name.strip()))
            for item in node.values():
                if isinstance(item, (dict, list)):
                    visit(item)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(selection)
    # Модель вольно обращается с написанием («ZNWR» -> «Z N W R»), поэтому
    # сравниваем без регистра, пробелов и пунктуации.
    def fold(value: str) -> str:
        return re.sub(r"[^0-9a-zа-яё]+", "", value.lower())

    answer_folded = fold(answer or "")
    seen: set[int] = set()
    found: list[int] = []
    for hotel_id, name in pairs:
        folded = fold(name)
        if folded and hotel_id not in seen and folded in answer_folded:
            seen.add(hotel_id)
            found.append(hotel_id)
    return found


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/generate", response_model=QueryResponse)
async def generate(req: QueryRequest):
    text = req.message.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Поле 'message' не может быть пустым")

    # Короткий id запроса связывает строки лога между собой и с ошибкой на сайте.
    log_id = uuid.uuid4().hex[:8]
    started = time.monotonic()
    try:
        result = await service.pipeline(text, log_id)
        selection_json = _parse_json_response(result.get("h_i_f_db"))
        final_answer = result.get("T_F_U", "")
        # Композер — «думающая» модель: её рассуждения <think>…</think> человеку не показываем.
        final_answer = re.sub(r"<think>.*?(?:</think>|$)", "", final_answer, flags=re.DOTALL).strip()
        # Ссылки — только на отели, названные в ответе; если имена не совпали
        # (модель перефразировала) — отдаём всё, что выбрала база.
        mentioned = _mentioned_hotel_ids(selection_json, final_answer)
        all_ids = _hotel_ids(selection_json)
        hotel_ids = mentioned or all_ids
        if not final_answer:
            log.warning("[%s] композер вернул пустой ответ (всё съел <think>?)", log_id)
        log.info("[%s] готово за %.1f с: ответ %d символов, ссылок %d (упомянуто %d из %d найденных)",
                 log_id, time.monotonic() - started, len(final_answer), len(hotel_ids),
                 len(mentioned), len(all_ids))
        return QueryResponse(
            response=final_answer,
            hotel_ids=hotel_ids,
            details={
                "request_builder": result.get("t_f_d_f"),
                "data_fetcher": result.get("t_f_a_c"),
                "hotel_ids": hotel_ids,
            },
        )
    except Exception:
        # Трейсбек этапа уже в логе пайплайна; здесь фиксируем итог и отдаём человеку
        # вежливую ошибку с кодом, по которому её легко найти в docker logs.
        log.exception("[%s] пайплайн упал через %.1f с", log_id, time.monotonic() - started)
        raise HTTPException(
            status_code=500,
            detail=f"Повторите позже. Помощник снова моет посуду. Ответит как только сможет! (код {log_id})",
        )
