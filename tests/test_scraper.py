from unittest.mock import MagicMock, patch

import pytest

from app.services.scraper import ScrapedProduct, _extract_product_id


@pytest.fixture
def sample_product():
    return ScrapedProduct(
        product_id="123456789",
        product_name="Test Telefon",
        category="Elektronik",
        description="Harika bir akıllı telefon.",
        reviews=[
            "Çok memnun kaldım, hızlı kargo.",
            "Ürün açıklamayla birebir aynı, tavsiye ederim.",
            "Pil ömrü biraz kısa ama genel olarak iyiydi.",
        ],
    )


class TestExtractProductId:
    def test_standard_trendyol_url(self):
        url = "https://www.trendyol.com/apple/iphone-15-128-gb-siyah-p-123456789?boutiqueId=1"
        assert _extract_product_id(url) == "123456789"

    def test_url_without_p_segment(self):
        url = "https://www.trendyol.com/some-product/12345"
        pid = _extract_product_id(url)
        assert pid  # Should return something, not empty

    def test_another_valid_url(self):
        url = "https://www.trendyol.com/samsung/galaxy-s24-p-987654321"
        assert _extract_product_id(url) == "987654321"


class TestScrapedProductDataclass:
    def test_default_reviews_empty(self):
        p = ScrapedProduct(
            product_id="1", product_name="X", category="Y", description="Z"
        )
        assert p.reviews == []

    def test_reviews_populated(self, sample_product):
        assert len(sample_product.reviews) == 3
