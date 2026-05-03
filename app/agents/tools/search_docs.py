"""
Search documents tool.
Uses ChromaDB's default embedding function (local, no API key needed).
"""
import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

from app.settings import settings


async def search_docs(query: str, k: int = 5, product_area: str | None = None) -> list[dict]:
    """
    Search documents from the vector store.

    Args:
        query: The search query text
        k: Number of results to return
        product_area: Optional filter by product area

    Returns:
        List of dicts with chunk_id, score, content, source_file, heading
    """
    chroma_client = chromadb.PersistentClient(path=settings.chroma_persist_dir)

    try:
        collection = chroma_client.get_collection(
            "helix_docs",
            embedding_function=DefaultEmbeddingFunction(),
        )
    except Exception:
        return []

    where_filter = {"product_area": product_area} if product_area else None

    results = collection.query(
        query_texts=[query],
        n_results=k,
        where=where_filter,
    )

    output = []
    if results and results.get("ids") and results["ids"][0]:
        ids = results["ids"][0]
        distances = results.get("distances", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        documents = results.get("documents", [[]])[0]

        for i, chunk_id in enumerate(ids):
            distance = distances[i] if i < len(distances) else 1.0
            score = max(0.0, min(1.0, 1.0 - distance))
            metadata = metadatas[i] if i < len(metadatas) else {}
            content = documents[i] if i < len(documents) else ""

            output.append({
                "chunk_id": chunk_id,
                "score": score,
                "content": content,
                "source_file": metadata.get("source_file", ""),
                "heading": metadata.get("heading", ""),
            })

    return output