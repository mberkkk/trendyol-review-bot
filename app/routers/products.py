import logging

from fastapi import APIRouter

from app.models.review import ProductInfo
from app.services import embedder

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductInfo])
async def list_products():
    """List all products that have been scraped and stored in ChromaDB."""
    raw = embedder.list_products()
    results = []
    for p in raw:
        review_count = embedder.get_product_review_count(p["product_id"])
        results.append(
            ProductInfo(
                product_id=p["product_id"],
                product_name=p["product_name"],
                review_count=review_count,
            )
        )
    return results
