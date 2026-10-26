import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from LLM import LLM
from config import REQUEST_BUILDER, DATA_FETCHER, ANSWER_COMPOSER

app = FastAPI(title="LLM Multi-Agent Service", version="1.0.0")

# Инициализируем пайплайн из 3 агентов
service = LLM(REQUEST_BUILDER, DATA_FETCHER, ANSWER_COMPOSER)


class QueryRequest(BaseModel):
    message: str


class QueryResponse(BaseModel):
    response: str
    details: dict | None = None


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
        final_answer = result.get("T_F_U", "")
        return QueryResponse(
            response=final_answer,
            details={
                "request_builder": result.get("t_f_d_f"),
                "data_fetcher": result.get("t_f_a_c"),
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка генерации: {e}")
