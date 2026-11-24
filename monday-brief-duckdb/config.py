import os

from dotenv import load_dotenv

load_dotenv()

MODEL = "deepseek-chat"
MAX_ROUNDS = 3
MAX_CODE_ATTEMPTS = 2
ROOT = os.path.dirname(__file__)
DB_PATH = os.path.join(ROOT, "data", "sales.duckdb")
SAMPLE_CSV = os.path.join(ROOT, "data", "sample_sales.csv")


def get_llm(temperature: float = 0):
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("Set DEEPSEEK_API_KEY in a .env file next to app.py.")
    from langchain_deepseek import ChatDeepSeek

    return ChatDeepSeek(model=MODEL, api_key=key, temperature=temperature)
