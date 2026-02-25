import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import chat, products, scrape
from app.services import embedder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm up ChromaDB collection and embedding model on startup."""
    logger.info("Starting up — initializing ChromaDB and embedding model...")
    embedder._get_collection()
    embedder._get_model()
    logger.info("Startup complete.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="Trendyol Review Reply Bot",
    description=(
        "Trendyol ürün yorumlarına RAG + Claude kullanarak otomatik, "
        "bağlamlı yanıtlar üreten API."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scrape.router)
app.include_router(chat.router)
app.include_router(products.router)


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "version": "1.0.0"}
