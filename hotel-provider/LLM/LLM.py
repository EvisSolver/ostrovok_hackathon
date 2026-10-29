import asyncio, httpx, logging, time, traceback, json, sys
from pystyle import Colors, Write

# Логи пайплайна: видны в stdout контейнера (docker logs <llm>).
log = logging.getLogger("llm.pipeline")


def _short(value, limit: int = 500) -> str:
    """Обрезает длинные тексты в логах; LLM_LOG_LEVEL=DEBUG печатает целиком."""
    text = str(value)
    if log.isEnabledFor(logging.DEBUG) or len(text) <= limit:
        return text
    return f"{text[:limit]}… [обрезано, всего {len(text)} символов]"


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

    async def pipeline(self, user_text: str, log_id: str = "-") -> dict:
        async with httpx.AsyncClient(timeout = 67) as llm_client:
            hotel = "Eleon"
            log.info("[%s] вопрос пользователя: %s", log_id, _short(user_text, 300))

            # --- Агент 1: REQUEST_BUILDER (локальная модель) ---
            started = time.monotonic()
            try:
                text_for_data_fetcher = await self.request_builder.llm_local_model_response_REQUEST_BUILDER(user_text)
            except Exception:
                log.exception("[%s] агент 1 REQUEST_BUILDER упал (ollama доступна? модель скачана?)", log_id)
                raise
            log.info("[%s] агент 1 REQUEST_BUILDER: %.1f с, ответ: %s",
                     log_id, time.monotonic() - started, _short(text_for_data_fetcher))
            if text_for_data_fetcher == '{"command": "stop"}': return await self.pipeline(user_text, log_id)

            # --- Агент 2: DATA_FETCHER (локальная модель) ---
            started = time.monotonic()
            try:
                text_for_answer_composer = await self.data_fetcher.llm_local_model_response_DATA_FETCHER(text_for_data_fetcher)
            except Exception:
                log.exception("[%s] агент 2 DATA_FETCHER упал (ollama доступна? модель скачана?)", log_id)
                raise
            log.info("[%s] агент 2 DATA_FETCHER: %.1f с, фильтры: %s",
                     log_id, time.monotonic() - started, _short(text_for_answer_composer))

            try:
                dict_answer = json.loads(text_for_answer_composer)
            except json.JSONDecodeError:
                log.exception("[%s] агент 2 вернул не-JSON, разбор невозможен. Сырой ответ: %s",
                              log_id, _short(text_for_answer_composer, 1500))
                raise

            # --- База: подбор отелей по фильтрам ---
            started = time.monotonic()
            try:
                hotel_info_from_db = await LLM_Call_Functions.get_random_hotel_with_stars(dict_answer)
            except Exception:
                log.exception("[%s] запрос к базе отелей упал (HOTELS_DATABASE_URL верный? витрина mv_hotels_analytics есть?)", log_id)
                raise
            db_hotels = (hotel_info_from_db or [{}])[0].get("json_agg") or []
            log.info("[%s] база: %.1f с, подобрано отелей: %d%s",
                     log_id, time.monotonic() - started, len(db_hotels),
                     "" if not db_hotels else " — " + _short(", ".join(str(h.get("hotel_name")) for h in db_hotels), 300))

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

            # --- Агент 3: ANSWER_COMPOSER (API) ---
            started = time.monotonic()
            try:
                Text_For_User = await self.answer_composer.llm_response_ANSWER_COMPOSER(llm_client, answer_for_LLM_ANSWER_COMPOSER)
            except Exception:
                log.exception("[%s] агент 3 ANSWER_COMPOSER упал (ключ OPEN_ROUTER_KEY в .env? сервис доступен?)", log_id)
                raise
            log.info("[%s] агент 3 ANSWER_COMPOSER: %.1f с, длина ответа: %d символов",
                     log_id, time.monotonic() - started, len(Text_For_User or ""))

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