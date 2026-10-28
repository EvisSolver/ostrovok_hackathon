import asyncio, httpx, traceback, json, sys
from pystyle import Colors, Write


from config import *

from LLM_LOCAL_MODEL import LLM_LOCAL_DATA_FETCHER
from LLM_LOCAL_REQUEST_BUILDER import LLM_LOCAL_REQUEST_BUILDER

from LLM_ANSWER_COMPOSER import llm_3_response

from llm_calls import LLM_Call_Functions


class LLM:
    def __init__(self, request_builder: dict, data_fetcher: dict, answer_composer: dict):
        self.request_builder = LLM_LOCAL_REQUEST_BUILDER(request_builder)
        self.data_fetcher = LLM_LOCAL_DATA_FETCHER(data_fetcher)
        self.answer_composer = llm_3_response.LLM_ANSWER_COMPOSER(answer_composer)

        self.llm_call = LLM_Call_Functions

    async def pipeline(self, user_text: str) -> dict:
        async with httpx.AsyncClient(timeout = 67) as llm_client:
            hotel = "Eleon"
            text_for_data_fetcher = await self.request_builder.llm_local_model_response_REQUEST_BUILDER(user_text)
            if text_for_data_fetcher == '{"command": "stop"}': return await self.pipeline(user_text)
            print(text_for_data_fetcher)
            text_for_answer_composer = await self.data_fetcher.llm_local_model_response_DATA_FETCHER(text_for_data_fetcher)

            dict_answer = json.loads(text_for_answer_composer)
            hotel_info_from_db = await LLM_Call_Functions.get_random_hotel_with_stars(dict_answer)
            print(hotel_info_from_db)

            final_output_text = ""
            try:
                if isinstance(hotel_info_from_db, list) and len(hotel_info_from_db) > 0:
                    hotels_list = hotel_info_from_db[0].get('json_agg')
                    
                    if hotels_list and len(hotels_list) > 0:
                        lines = []
                        lines.append(f"🎉 Найдено отелей: {len(hotels_list)}")
                        lines.append("=" * 50)
                        
                        for hotel in hotels_list:
                            lines.append(f"Отель: «{hotel.get('hotel_name')}» ({hotel.get('final_stars', hotel.get('hotels_stars'))})")
                            lines.append(f"Цена: {hotel.get('final_price', hotel.get('hotel_price'))} руб/ночь")
                            
                            if hotel.get('metro_name'):
                                lines.append(f"Метро: {hotel.get('metro_name')} ({hotel.get('distance_to_metro_meters')} м)")
                            
                            info_parts = []
                            if hotel.get('shop_malls_name') and hotel.get('shop_malls_name') != 'Unknown':
                                info_parts.append(f"Магазин «{hotel.get('shop_malls_name')}» ({hotel.get('distance_to_shop_meters')} м)")
                            
                            if hotel.get('where_to_eat_name'):
                                info_parts.append(f"🍴 Заведение «{hotel.get('where_to_eat_name')}» ({hotel.get('distance_to_where_to_eat_meters')} м)")
                            
                            if hotel.get('cleaned_attraction_name') or (hotel.get('attraction_name') and hotel.get('attraction_name') != 'Unknown'):
                                attr_name = hotel.get('cleaned_attraction_name') or hotel.get('attraction_name')
                                lines.append(f"Достопримечательность: {attr_name} ({hotel.get('distance_to_attraction_meters')} м)")

                            if info_parts:
                                lines.append("Рядом: " + ", ".join(info_parts))
                            
                            if hotel.get('main_road_name'):
                                lines.append(f"Трасса: {hotel.get('main_road_name')} (до неё {hotel.get('dist_to_mkad_meters')} м)")
                            
                            lines.append("-" * 50)
                            
                        final_output_text = "\n".join(lines)
                    else:
                        final_output_text = "Извините, но по вашему запросу ничего не найдено в базе данных отелей. Пожалуйста, измените параметры поиска."
                else:
                    final_output_text = "Извините, но по вашему запросу ничего не найдено в базе данных отелей. Пожалуйста, измените параметры поиска."
            except Exception as e:
                final_output_text = f"Произошла ошибка при чтении данных из базы отелей: {e}"

            answer_for_LLM_ANSWER_COMPOSER = f"""

            |AGENT-QUESTION|{text_for_data_fetcher} 
            |DATA|{final_output_text}
            """
            
            Text_For_User = await self.answer_composer.llm_response_ANSWER_COMPOSER(llm_client, answer_for_LLM_ANSWER_COMPOSER)

            return {
                "h_i_f_db": hotel_info_from_db,
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
                # print(result["t_f_d_f"])
                # print(result["t_f_a_c"])
                print(result["T_F_U"])
            except Exception as e: print(f"\n|ERROR| {e!r}")

    def run(self):
        try: asyncio.run(self.chat())
        except KeyboardInterrupt: print("\nexit")
        except Exception: traceback.print_exc()

if __name__ == "__main__": LLM(REQUEST_BUILDER, DATA_FETCHER, ANSWER_COMPOSER).run()