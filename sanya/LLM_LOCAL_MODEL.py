import httpx
import ollama


class LLM_LOCAL_DATA_FETCHER:

    def __init__(self, config: dict):
        # Сохраняем промпт в атрибуты класса
        self.config = config

    async def llm_local_model_response_DATA_FETCHER(self, agent_input: str) -> str:
        # Используем асинхронный клиент ollama для неблокирующего инференса
        response = await ollama.AsyncClient().chat(
            model="qwen2.5-coder:7b",
            messages=[
                {"role": "system", "content": self.config["prompt"]},
                {"role": "user", "content": agent_input},
            ],
            format="json",
            options={
                # СКОРОСТЬ: Отключаем случайность. Модель берет только самые вероятные токены.
                "temperature": 0.0,
                "top_p": 0.1,
                # КОНТЕКСТ: Расширяем окно под ваши 1200 строк с запасом.
                "num_ctx": 16384,
                # СКОРОСТЬ ПАРСИНГА: Ограничиваем длину ответа.
                "num_predict": 512,
                # СКОРОСТЬ: Отключаем штрафы за повторения.
                "repeat_penalty": 1.0,
                # ЖЕЛЕЗО: Выделяет под обработку контекста потоки процессора.
                "num_thread": 8,
            },
        )
        return response["message"]["content"]
