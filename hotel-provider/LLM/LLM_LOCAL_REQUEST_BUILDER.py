import httpx
import ollama


class LLM_LOCAL_REQUEST_BUILDER:

    def __init__(self, config: dict):
        self.config = config
        self.client = ollama.AsyncClient(
            host="http://host.docker.internal:11434"
        )

    async def llm_local_model_response_REQUEST_BUILDER(self, user_input: str) -> str:
        response = await ollama.AsyncClient().chat(
            model="llama3.2:3b",
            messages=[
                {"role": "system", "content": self.config["prompt"]},
                {"role": "user", "content": user_input},
            ],
            format="json",
            options={
                "temperature": 0.2,
                "top_p": 0.1,
                "num_ctx": 8196,
                "num_predict": 512,
                "repeat_penalty": 1.0,
                "num_thread": 8,
            },
        )
        return response["message"]["content"]