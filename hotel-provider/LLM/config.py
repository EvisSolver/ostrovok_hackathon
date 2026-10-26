import os
from dotenv import load_dotenv
load_dotenv()


user_is_asking = None

REQUEST_BUILDER = {
    "model_url": "https://api.deepinfra.com/v1/inference/deepseek-ai/DeepSeek-V4.1-Flash-1017",
    "llm_key": os.getenv("OPEN_ROUTER_KEY"),
    "prompt": "ОТВЕТЬ КРАТКО | даю тебе пример а ты решаешь его"
}
DATA_FETCHER = {
    "model_url": "https://api.deepinfra.com/v1/inference/deepseek-ai/DeepSeek-V4.1-Flash-1017",
    "llm_key": os.getenv("OPEN_ROUTER_KEY"),
    "prompt": "ОТВЕТЬ КРАТКО | а если еще прибавить + 10?"
}
ANSWER_COMPOSER = {
    "model_url": "https://api.deepinfra.com/v1/inference/deepseek-ai/DeepSeek-V4.1-Flash-1017",
    "llm_key": os.getenv("OPEN_ROUTER_KEY"),
    "prompt": "ОТВЕТЬ КРАТКО | УМНОЖЬ ЧИСЛОВОЙ ОТВЕТ на 0"
}
