import requests, json, os, asyncio, httpx, traceback
from dotenv import load_dotenv
from pystyle import Colors, Write

from config import *


load_dotenv()
url_model = 'https://api.deepinfra.com/v1/inference/deepseek-ai/DeepSeek-V4.1-Flash-1017'
llm_key = os.getenv("OPEN_ROUTER_KEY")


class LLM_REQUEST_BUILDER:
    def __init__(self, url_model, llm_key):
        self.url_model = url_model
        self.llm_key = llm_key
        super().__init__()

    async def llm_response(self, client: httpx.AsyncClient):
        try:
            user_is_asking = True
            if user_is_asking == True:
                while True:
                    user_input = await asyncio.to_thread(input, "\nYou: ")#user-input-text
                    if user_input == ["q", "quit", "exit", "e"]: break
                    if not user_input.strip(): continue

                    response = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>{prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{user_input}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
                    async with client.stream(
                        "POST", self.url_model, 
                        headers = {"Authorization": f"Bearer {self.llm_key}"},
                        json = {"input": response, "stop": [], "stream": True}
                    ) as llm_response:
                        if llm_response.status_code != 200:
                            await response.aread()
                            Write.Print(f"L|35|: unknown error {llm_response.status_code} {llm_response.text[:200]}", Colors.red, interval = 0)
                            continue

                        print("Assistant: ")

                        async for line in llm_response.aiter_lines():
                            if line.startswith("data: "):
                                token = json.loads(line[5:])["token"]["text"]
                                Write.Print(token, Colors.green, end = "", interval = 0)#LLM-TEXT

        except Exception as e: print(f"\n|ERROR| {e!r}")

    # TODO: async def llm_filter():
        

    def main(self):
        async def run():
            async with httpx.AsyncClient(timeout = 67) as client:
                await self.llm_response(client)
        
        try: asyncio.run(run())
        
        except KeyboardInterrupt: print("exit")
        except Exception: traceback.print_exc()


if __name__ == "__main__":
    LLM_REQUEST_BUILDER(url_model, llm_key).main()