from pydantic import BaseModel


class ReviewChatRequest(BaseModel):
    product_id: str
    review_text: str


class ReviewChatResponse(BaseModel):
    product_id: str
    review_text: str
    generated_reply: str
    context_used: int  # number of retrieved chunks


class ProductInfo(BaseModel):
    product_id: str
    product_name: str
    review_count: int
