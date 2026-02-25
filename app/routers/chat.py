import logging

from anthropic import APIError, AuthenticationError
from fastapi import APIRouter, HTTPException

from app.models.review import ReviewChatRequest, ReviewChatResponse
from app.services import claude_client, embedder

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ReviewChatResponse)
async def chat(request: ReviewChatRequest):
    """
    Generate an automated reply to a customer review using RAG + Claude.

    1. Retrieve top-k semantically similar chunks from ChromaDB (product-scoped).
    2. Build prompt: system role + retrieved context + customer review.
    3. Call Claude API and return the generated reply.
    """
    if not request.review_text.strip():
        raise HTTPException(status_code=400, detail="Yorum metni boş olamaz.")

    # Retrieve product metadata from ChromaDB
    products = embedder.list_products()
    product_meta = next(
        (p for p in products if p["product_id"] == request.product_id), None
    )
    if product_meta is None:
        raise HTTPException(
            status_code=404,
            detail=f"'{request.product_id}' ID'li ürün bulunamadı. Önce /scrape endpoint'ini kullanın.",
        )

    context_chunks = embedder.search_context(
        product_id=request.product_id,
        query=request.review_text,
        top_k=5,
    )

    try:
        reply = claude_client.generate_reply(
            product_name=product_meta["product_name"],
            category=product_meta.get("category", "Genel"),
            review_text=request.review_text,
            context_chunks=context_chunks,
        )
    except AuthenticationError:
        logger.error("Claude API authentication failed — check ANTHROPIC_API_KEY")
        raise HTTPException(
            status_code=401,
            detail="Claude API anahtarı geçersiz. Lütfen ANTHROPIC_API_KEY ortam değişkenini kontrol edin.",
        )
    except APIError as e:
        logger.error("Claude API error: %s", e)
        raise HTTPException(
            status_code=502,
            detail=f"Claude API hatası: {e}",
        )

    return ReviewChatResponse(
        product_id=request.product_id,
        review_text=request.review_text,
        generated_reply=reply,
        context_used=len(context_chunks),
    )
