import requests, json, os, asyncio
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

    async def llm_response(self):
        try:
            user_is_asking = True
            if user_is_asking == True:
                while True:
                    user_input = await asyncio.to_thread(input, "\nYou: ")#user-input-text                
                    if not user_input.strip(): continue

                    response = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>{prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{user_input}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
                    llm_response = requests.post(
                        self.url_model,
                        headers={"Authorization": f'Bearer {self.llm_key}'},
                        json={"input": response, "stop": ["<|eot_id|>", "<|im_end|>", "<|im_sep|>"], "stream": True},
                            stream=True, timeout=67
                    )#data-post

                    if llm_response: print("Assistant: ")
                    else: Write.Print("L|34|: unknown error", Colors.red, interval = 0)

                    for line in llm_response.iter_lines():
                        if line.startswith(b"data"):
                            token = json.loads(line[5:])["token"]["text"]
                            Write.Print(token, Colors.green, end = "", interval = 0, hide_cursor=False)

        except Exception as e: print(f"\n[error] {e!r}")

    # TODO: async def llm_filter():
        

    def main(self):
        asyncio.run(self.llm_response())        

llm = LLM_REQUEST_BUILDER(url_model = url_model, llm_key = llm_key)
llm.main()