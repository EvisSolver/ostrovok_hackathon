# LLM Pipeline — подбор отелей

Три нейросети работают цепочкой: запрос клиента → ТЗ → данные → готовый ответ.
Сейчас включены первые две ступени, третья закомментирована.

```
You → LLM_REQUEST_BUILDER → LLM_DATA_FETCHER → LLM_ANSWER_COMPOSER → ответ
      (запрос → ТЗ)         (ТЗ → данные)       (данные → текст)
```

## Файлы

| Файл | Что внутри |
|---|---|
| `LLM.py` | Фасад: класс `LLM`, цепочка `pipeline()`, REPL `chat()`, точка входа `run()` |
| `LLM_REQUEST_BUILDER.py` | `LLM_REQUEST_BUILDER` — 1-я модель, превращает реплику клиента в ТЗ |
| `LLM_DATA_FETCHER.py` | `LLM_DATA_FETCHER` — 2-я модель, собирает данные по ТЗ |
| `LLM_ANSWER_COMPOSER.py` | `LLM_ANSWER_COMPOSER` — 3-я модель, пишет ответ клиенту *(пока отключена)* |
| `config.py` | Настройки каждой ступени: `model_url`, `llm_key`, `prompt` |

## Запуск

```bash
pip install httpx python-dotenv pystyle
export OPEN_ROUTER_KEY=...     # ключ DeepInfra
python LLM.py
```

Выход: `q`, `quit`, `exit`, `e` или `Ctrl+C`.

Один запрос без REPL:

```python
from LLM import LLM
from config import REQUEST_BUILDER, DATA_FETCHER
import asyncio

print(asyncio.run(LLM(REQUEST_BUILDER, DATA_FETCHER).pipeline("нужен тихий отель 3-4 звезды")))
# {'t_f_d_f': 'ТЗ ...', 't_f_a_c': '| Отель | ...'}
```

## Настройка

Каждая ступень получает свой словарь — модель, ключ и промпт можно менять независимо:

```python
REQUEST_BUILDER = {
    "model_url": "https://api.deepinfra.com/v1/inference/deepseek-ai/DeepSeek-V4.1-Flash-1017",
    "llm_key": os.getenv("OPEN_ROUTER_KEY"),
    "prompt": "..."
}
```

Ключ хранится в `.env`:

```dotenv
OPEN_ROUTER_KEY=sk-...
```

`.env` в `.gitignore`, ключи в коде не хардкодить.

## Контракт модуля

Любая ступень — это класс с конструктором `__init__(self, config: dict)` и одним асинхронным методом:

```python
async def llm_response_XXX(self, client: httpx.AsyncClient, user_input: str) -> str
```

Внутри: собрать промпт → `client.stream(...)` → `async for line in r.aiter_lines()` → вернуть строку.
Клиент один на всю цепочку, создаётся в `LLM.pipeline()`.

## Известные проблемы / TODO

- `DATA_FETCHER["model_url"]` пустой — вторую ступень нужно включить.
- Третья ступень (`LLM_ANSWER_COMPOSER`) закомментирована в `LLM.__init__` и `pipeline`.
- `chat()` печатает только `t_f_d_f` — заменить на `T_F_U`, когда композер заработает.
- Промпты используют Llama-3 разметку (`<|begin_of_text|>`), а `model_url` указывает на DeepSeek — либо сменить URL на `NousResearch/Hermes-3-Llama-3.1-70B`, либо перейти на `https://api.deepinfra.com/v1/openai/chat/completions` с обычными `messages`.
- `user_is_asking` в `config.py` не используется.
