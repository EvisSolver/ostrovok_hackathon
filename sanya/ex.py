import json
import httpx

from llm_calls import LLM_Call_Functions


TOOLS = [{
    "type": "function",
    "function": {
        "name": "get_random_hotel_with_stars",
        "description": "Получить случайный отель со звёздами из PostgreSQL",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}]


class LLM_DATA_FETCHER:
    def __init__(self, config: dict):
        # Оставляем вашу исходную ссылку:
        # https://api.deepinfra.com/v1/inference/<model-id>
        original_url = config["model_url"]
        prefix, marker, self.model = original_url.partition("/v1/inference/")

        if not marker or not self.model:
            raise ValueError("В model_url должен быть путь /v1/inference/<model-id>")

        # Для tool calling используем OpenAI-совместимый endpoint DeepInfra.
        self.url_model = prefix + "/v1/openai/chat/completions"
        self.llm_key = config["llm_key"]
        self.prompt = config["prompt"]

    async def llm_response_DATA_FETCHER(
        self,
        client: httpx.AsyncClient,
        user_input: str
    ):
        messages = [
            {"role": "system", "content": self.prompt},
            {"role": "user", "content": user_input},
        ]

        response = await client.post(
            self.url_model,
            headers={"Authorization": f"Bearer {self.llm_key}"},
            json={
                "model": self.model,
                "messages": messages,
                "tools": TOOLS,
                "tool_choice": "auto",
            },
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"DeepInfra: {response.status_code} {response.text[:500]}"
            )

        message = response.json()["choices"][0]["message"]
        tool_calls = message.get("tool_calls") or []

        if not tool_calls:
            return json.dumps({
                "AGENT-INPUT": user_input,
                "DATA": [],
                "status": "no_tool_call",
            }, ensure_ascii=False)

        # Запоминаем запрос инструмента, который вернула модель.
        messages.append({
            "role": "assistant",
            "content": message.get("content"),
            "tool_calls": tool_calls,
        })

        results = []

        # Python выполняет функцию. DeepInfra сам к вашей БД не подключается.
        for call in tool_calls:
            function_name = call["function"]["name"]

            if function_name == "get_random_hotel_with_stars":
                result = await LLM_Call_Functions.get_random_hotel_with_stars()
            else:
                result = None

            results.append({
                "tool": function_name,
                "result": result,
            })

        # Второй агент передаёт вопрос и фактические данные третьему.
        return json.dumps({
            "AGENT-INPUT": user_input,
            "DATA": results,
            "status": "complete" if results else "no_data",
        }, ensure_ascii=False, default=str)