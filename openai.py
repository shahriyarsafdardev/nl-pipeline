from config import settings
import openai
import time

openai.api_key = settings.openai_api_key


def create_embedding(text, max_retries=5):
    for i in range(max_retries):
        try:
            return openai.Embedding.create(input=[text], model="text-embedding-ada-002")['data'][0]['embedding']
        except Exception:
            time.sleep(2 ** i)
    return []
