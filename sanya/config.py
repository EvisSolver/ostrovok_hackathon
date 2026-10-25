import os
from dotenv import load_dotenv
load_dotenv()


user_is_asking = None

REQUEST_BUILDER = {
    "model_url": "https://api.deepinfra.com/v1/inference/deepseek-ai/DeepSeek-V4.1-Flash-1017",
    "llm_key": os.getenv("OPEN_ROUTER_KEY"),
    "prompt": "+1 | ты первая модель"
}
DATA_FETCHER = {
    "model_url": "", #TODO пофиксить и определиться с моделью(до этого стояла Gemini-2.5-Pro)
    "llm_key": os.getenv("OPEN_ROUTER_KEY"),
    "prompt": "+1 | ты вторая модель"
}
ANSWER_COMPOSER = {
    "model_url": "https://api.deepinfra.com/v1/inference/deepseek-ai/DeepSeek-V4.1-Flash-1017",
    "llm_key": os.getenv("OPEN_ROUTER_KEY"),
    "prompt": "+1"
}