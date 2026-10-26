import requests, json, os, asyncio, httpx, traceback
from dotenv import load_dotenv
from pystyle import Colors, Write

from config import *


load_dotenv()
url_model = 'https://api.deepinfra.com/v1/inference/'
llm_key = os.getenv("OPEN_ROUTER_KEY")
model_name = "google/gemini-2.5-pro"

class LLM_REQUEST_BUILDER:
    def __init__(self, url_model, llm_key, model_name):
        self.url_model = url_model
        self.llm_key = llm_key
        self.model_name = model_name
        super().__init__()

    async def llm_response(self, client: httpx.AsyncClient):
        try:
            user_is_asking = True
            if user_is_asking == True:
                while True:
                    user_input = await asyncio.to_thread(input, "\nYou: ")#user-input-text
                    if user_input == ["q", "quit", "exit", "e"]: break
                    if not user_input.strip(): continue

                    llm_body = {
                        "model": self.model_name,
                        "messages": [
                            {"role": "system", "content": prompt},
                            {"role": "user", "content": user_input},
                        ], "Temperature": 0.3, "stream": True
                    }
                    async with client.stream(
                        "POST", self.url_model, 
                        headers = {"Authorization": f"Bearer {self.llm_key}"},
                        json = llm_body
                    ) as llm_response:
                        if llm_response.status_code != 200:
                            await llm_response.aread()
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
    LLM_REQUEST_BUILDER(url_model, llm_key, model_name).main()