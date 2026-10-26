import asyncio, httpx, traceback

from config import *

from LLM_REQUEST_BUILDER import llm_1_response
from LLM_DATA_FETCHER import llm_2_response
from LLM_ANSWER_COMPOSER import llm_3_response

from llm_calls import LLM_Call_Functions


class LLM:
    def __init__(self, request_builder: dict, data_fetcher: dict, answer_composer: dict):
        self.request_builder = llm_1_response.LLM_REQUEST_BUILDER(request_builder)
        self.data_fetcher = llm_2_response.LLM_DATA_FETCHER(data_fetcher)
        self.answer_composer = llm_3_response.LLM_ANSWER_COMPOSER(answer_composer)

        self.llm_call = LLM_Call_Functions

    async def pipeline(self, user_text: str) -> dict:
        async with httpx.AsyncClient(timeout = 67) as llm_client:
            hotel = await LLM_Call_Functions.get_random_hotel_with_stars()
            text_for_data_fetcher = await self.request_builder.llm_response_REQUEST_BUILDER(llm_client, user_text)
            text_data = f"|AGENT-DATA|: {text_for_data_fetcher}. |DATA|: {hotel}"
            text_for_answer_composer = await self.data_fetcher.llm_response_DATA_FETCHER(llm_client, text_data)
            Text_For_User = await self.answer_composer.llm_response_ANSWER_COMPOSER(llm_client, text_for_answer_composer)

            return {
                "t_f_d_f": text_for_data_fetcher,
                "t_f_a_c": text_for_answer_composer,
                "T_F_U": Text_For_User
            }

    async def chat(self):
        while True:
            user_text = await asyncio.to_thread(input, "\nYou: ")
            if user_text.strip().lower() in ["q", "quit", "exit", "e"]: break
            if not user_text.strip(): continue
            print("assistant: ", end = "", flush = True)

            try:
                result = await self.pipeline(user_text)
                print(result["t_f_d_f"])
                print(result["t_f_a_c"])
                print(result["T_F_U"])
            except Exception as e: print(f"\n|ERROR| {e!r}")

    def run(self):
        try: asyncio.run(self.chat())
        except KeyboardInterrupt: print("\nexit")
        except Exception: traceback.print_exc()

if __name__ == "__main__": LLM(REQUEST_BUILDER, DATA_FETCHER, ANSWER_COMPOSER).run()