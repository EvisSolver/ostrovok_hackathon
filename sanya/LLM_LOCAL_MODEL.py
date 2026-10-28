import httpx
import ollama


class LLM_LOCAL_DATA_FETCHER:

    def __init__(self, config: dict):
        self.config = config

    async def llm_local_model_response_DATA_FETCHER(self, agent_input: str) -> str:
        response = await ollama.AsyncClient().chat(
            model="qwen2.5-coder:7b",
            messages=[
                {"role": "system", "content": self.config["prompt"]},
                {"role": "user", "content": agent_input},
            ],
            format="json",
            options={

                "temperature": 0.0,
                "top_p": 0.1,
                "num_ctx": 16384,
                "num_predict": 512,
                "repeat_penalty": 1.0,
                "num_thread": 8,
            },
        )
        return response["message"]["content"]
