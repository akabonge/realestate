import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from app.config import get_settings

_collection = None


def get_collection():
    global _collection
    if _collection is not None:
        return _collection

    settings = get_settings()
    ef = SentenceTransformerEmbeddingFunction(model_name=settings.embedding_model)
    client = chromadb.PersistentClient(path=settings.chroma_persist_path)
    _collection = client.get_or_create_collection(
        name=settings.chroma_collection_name,
        embedding_function=ef,
    )
    return _collection
