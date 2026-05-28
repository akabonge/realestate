from app.rag.embedder import get_collection
from app.config import get_settings


def retrieve(query: str) -> tuple[str, list[str]]:
    settings = get_settings()
    collection = get_collection()

    results = collection.query(
        query_texts=[query],
        n_results=min(settings.max_retrieved_chunks, collection.count() or 1),
    )

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]

    context = "\n\n---\n\n".join(docs) if docs else ""
    sources = [m.get("source", "unknown") for m in metas]

    return context, sources
