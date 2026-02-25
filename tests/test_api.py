from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.models.product import ScrapeResponse

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "1.0.0"}


@patch("app.routers.scrape._scrape_and_embed")
def test_scrape_endpoint_success(mock_scrape):
    mock_scrape.return_value = ScrapeResponse(
        product_id="123",
        product_name="Test",
        review_count=10,
        message="Ok",
    )
    
    response = client.post(
        "/scrape",
        json={"url": "https://www.trendyol.com/test-p-123"}
    )
    
    assert response.status_code == 200
    assert response.json()["product_id"] == "123"
    assert response.json()["review_count"] == 10


def test_scrape_endpoint_invalid_url():
    response = client.post(
        "/scrape",
        json={"url": "https://www.amazon.com/test-123"}
    )
    assert response.status_code == 400
    assert "Sadece Trendyol URL'leri" in response.json()["detail"]


@patch("app.routers.chat.embedder.list_products")
@patch("app.routers.chat.embedder.search_context")
@patch("app.routers.chat.claude_client.generate_reply")
def test_chat_endpoint_success(mock_reply, mock_search, mock_list):
    mock_list.return_value = [{"product_id": "123", "product_name": "Test Ürün", "category": "Elektronik"}]
    mock_search.return_value = ["Context 1"]
    mock_reply.return_value = "Harika bir ürün, teşekkürler."
    
    response = client.post(
        "/chat",
        json={"product_id": "123", "review_text": "Ürün elime ulaştı"}
    )
    
    assert response.status_code == 200
    assert response.json()["product_id"] == "123"
    assert response.json()["generated_reply"] == "Harika bir ürün, teşekkürler."
    assert response.json()["context_used"] == 1


@patch("app.routers.chat.embedder.list_products")
def test_chat_endpoint_product_not_found(mock_list):
    mock_list.return_value = [{"product_id": "999"}]
    
    response = client.post(
        "/chat",
        json={"product_id": "123", "review_text": "Test"}
    )
    
    assert response.status_code == 404
    assert "'123' ID'li ürün bulunamadı" in response.json()["detail"]
