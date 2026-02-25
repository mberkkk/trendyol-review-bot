import logging
from pathlib import Path

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "system_prompt.txt"
_SYSTEM_PROMPT_TEMPLATE = _PROMPT_PATH.read_text(encoding="utf-8")


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


def generate_reply(
    product_name: str,
    category: str,
    review_text: str,
    context_chunks: list[str],
) -> str:
    """
    Generate a customer service reply using Claude with RAG context.

    Args:
        product_name: Name of the reviewed product.
        category: Product category.
        review_text: The customer's review text.
        context_chunks: Retrieved relevant text chunks from ChromaDB.

    Returns:
        Generated reply string.
    """
    client = _get_client()

    retrieved_context = "\n\n".join(
        f"- {chunk}" for chunk in context_chunks
    ) if context_chunks else "Ek bağlam bulunamadı."

    system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
        product_name=product_name,
        category=category,
        retrieved_context=retrieved_context,
    )

    message = client.messages.create(
        model=settings.model_name,
        max_tokens=512,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"Müşteri yorumu:\n{review_text}",
            }
        ],
    )

    reply = message.content[0].text
    logger.info(
        "Generated reply for product '%s' | input_tokens=%d | output_tokens=%d",
        product_name,
        message.usage.input_tokens,
        message.usage.output_tokens,
    )
    return reply
