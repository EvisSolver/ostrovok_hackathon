import json
import re
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from LLM import LLM
from config import REQUEST_BUILDER, DATA_FETCHER, ANSWER_COMPOSER

app = FastAPI(title="LLM Multi-Agent Service", version="1.0.0")

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


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/generate", response_model=QueryResponse)
async def generate(req: QueryRequest):
    text = req.message.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Поле 'message' не может быть пустым")

    try:
        result = await service.pipeline(text)
        selection_json = _parse_json_response(result.get("t_f_a_c"))
        hotel_ids = _hotel_ids(selection_json)
        final_answer = result.get("T_F_U", "")
        return QueryResponse(
            response=final_answer,
            hotel_ids=hotel_ids,
            details={
                "request_builder": result.get("t_f_d_f"),
                "data_fetcher": result.get("t_f_a_c"),
                "hotel_ids": hotel_ids,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка генерации: {e}")
