import json, os, asyncio, httpx
from dotenv import load_dotenv
from pystyle import Colors, Write

class LLM_DATA_FETCHER:
    def __init__(self, config: dict):
        self.url_model = config["model_url"]
        self.llm_key = config["llm_key"]
        self.prompt = config["prompt"]
        super().__init__()

    async def llm_response_DATA_FETCHER(self, client: httpx.AsyncClient, user_input: str):
        try:
            user_is_asking = True
            if user_is_asking == True:
                response = (
                    f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>{self.prompt}"
                    f"<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{user_input}"
                    f"<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
                )

                answer = ""
                async with client.stream(
                    "POST", self.url_model,
                    headers = {"Authorization": f"Bearer {self.llm_key}"},
                    json = {"input": response, "stop": ["<|eot_id|>", "<|im_end|>", "<|im_sep|>"], "stream": True}
                ) as llm_response: 
                    if llm_response.status_code != 200:
                        await llm_response.aread()
                        raise RuntimeError(f"llm_1: {llm_response.status_code} {llm_response.text[:200]}")

                    async for line in llm_response.aiter_lines():
                        if line.startswith("data: "):
                            token = json.loads(line[5:])["token"]["text"]
                            answer += token
                return answer
        except Exception as e: print(f"\nllm_1|ERROR|: {e!r}")

    # TODO: async def llm_filter():
        

#     def main(self):
#         async def run():
#             async with httpx.AsyncClient(timeout = 67) as client:
#                 await self.llm_response(client)
        
#         try: asyncio.run(run())
        
#         except KeyboardInterrupt: print("exit")
#         except Exception: traceback.print_exc()


# if __name__ == "__main__":
#     LLM_REQUEST_BUILDER(model_url, llm_key).main()