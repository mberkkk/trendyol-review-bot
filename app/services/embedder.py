import logging
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from app.config import settings
from app.services.scraper import ScrapedProduct

logger = logging.getLogger(__name__)

# Multilingual model — handles Turkish very well
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

_client = None
_collection = None
_model = None


def _get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        Path(settings.chroma_path).mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=settings.chroma_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def _get_collection() -> chromadb.Collection:
    global _collection
    if _collection is None:
        _collection = _get_client().get_or_create_collection(
            name="trendyol_reviews",
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("Loading embedding model: %s", EMBEDDING_MODEL)
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def upsert_product(product: ScrapedProduct) -> int:
    """
    Embed and store product context + reviews into ChromaDB.

    Args:
        product: Scraped product data.

    Returns:
        Number of documents upserted.
    """
    collection = _get_collection()
    model = _get_model()

    documents: list[str] = []
    metadatas: list[dict] = []
    ids: list[str] = []

    # Store product description as context
    if product.description:
        documents.append(f"Ürün: {product.product_name}\n{product.description}")
        metadatas.append(
            {
                "product_id": product.product_id,
                "type": "description",
                "product_name": product.product_name,
                "category": product.category,
            }
        )
        ids.append(f"{product.product_id}_desc")

    # Store each review
    for idx, review in enumerate(product.reviews):
        documents.append(review)
        metadatas.append(
            {
                "product_id": product.product_id,
                "type": "review",
                "product_name": product.product_name,
                "category": product.category,
            }
        )
        ids.append(f"{product.product_id}_review_{idx}")

    if not documents:
        logger.warning("No documents to upsert for product %s", product.product_id)
        return 0

    embeddings = model.encode(documents, show_progress_bar=False).tolist()
    collection.upsert(documents=documents, embeddings=embeddings, metadatas=metadatas, ids=ids)
    logger.info("Upserted %d documents for product %s", len(documents), product.product_id)
    return len(documents)


def search_context(product_id: str, query: str, top_k: int = 5) -> list[str]:
    """
    Retrieve the most relevant context chunks for a given review query.

    Args:
        product_id: Filter results to this product.
        query: The incoming customer review text.
        top_k: Number of results to retrieve.

    Returns:
        List of relevant text chunks.
    """
    collection = _get_collection()
    model = _get_model()

    query_embedding = model.encode([query], show_progress_bar=False).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        where={"product_id": product_id},
    )

    docs = results.get("documents", [[]])[0]
    return docs


def list_products() -> list[dict]:
    """Return all unique products stored in ChromaDB."""
    collection = _get_collection()
    all_results = collection.get(include=["metadatas"])

    seen: dict[str, dict] = {}
    for meta in all_results.get("metadatas", []):
        pid = meta.get("product_id", "")
        if pid and pid not in seen:
            seen[pid] = {
                "product_id": pid,
                "product_name": meta.get("product_name", ""),
            }

    return list(seen.values())


def get_product_review_count(product_id: str) -> int:
    """Count review documents for a specific product."""
    collection = _get_collection()
    results = collection.get(where={"$and": [{"product_id": product_id}, {"type": "review"}]})
    return len(results.get("ids", []))
