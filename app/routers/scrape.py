import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.models.product import ScrapeRequest, ScrapeResponse
from app.services import embedder, scraper

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scrape", tags=["scrape"])


def _scrape_and_embed(url: str) -> ScrapeResponse:
    """Run scraper + embedder synchronously (runs in background task)."""
    product = scraper.scrape_product(url)
    count = embedder.upsert_product(product)
    return ScrapeResponse(
        product_id=product.product_id,
        product_name=product.product_name,
        review_count=count,
        message=f"{count} belge ChromaDB'ye kaydedildi.",
    )


@router.post("", response_model=ScrapeResponse)
async def scrape_product(request: ScrapeRequest, background_tasks: BackgroundTasks):
    """
    Scrape a Trendyol product URL and embed its reviews into ChromaDB.

    The scraping runs synchronously for simplicity. For production use,
    consider Celery or FastAPI background tasks with status polling.
    """
    url = str(request.url)
    if "trendyol.com" not in url:
        raise HTTPException(status_code=400, detail="Sadece Trendyol URL'leri desteklenmektedir.")

    try:
        result = _scrape_and_embed(url)
        return result
    except Exception as exc:
        logger.exception("Scrape failed for URL: %s", url)
        raise HTTPException(status_code=500, detail=f"Scrape başarısız: {exc}") from exc
