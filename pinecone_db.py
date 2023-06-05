import pinecone
from config import settings
from logger import getLogger

logger = getLogger()

pinecone.init(api_key=settings.pinecone_api_key,    
              environment=settings.pinecone_env)
index = pinecone.Index(settings.pinecone_index_name)

link_pattern = r'\s(https?|/[^/\s]+)'
upsert_batch_size = 90


def store_chunks(chunks):
    try:
        for i in range(0, len(chunks), upsert_batch_size):
            index.upsert(vectors=chunks[i:i + upsert_batch_size])
            logger.info(
                f"Stored {min(upsert_batch_size, len(chunks[i:i + upsert_batch_size]))} vectors to pinecone")
    except Exception as e:
        logger.error(
            f"Something went wrong while storing vectors to pinecone: {e}")