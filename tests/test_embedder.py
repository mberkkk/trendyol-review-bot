from unittest.mock import MagicMock, patch

import pytest

from app.services.scraper import ScrapedProduct


class TestEmbedder:
    @patch("app.services.embedder._get_collection")
    @patch("app.services.embedder._get_model")
    def test_upsert_product(self, mock_model, mock_collection):
        """Verify upsert calls collection.upsert with correct document count."""
        from app.services.embedder import upsert_product

        mock_model.return_value.encode.return_value = [[0.1, 0.2]] * 4  # desc + 3 reviews
        mock_coll = MagicMock()
        mock_collection.return_value = mock_coll

        product = ScrapedProduct(
            product_id="test_123",
            product_name="Test Ürün",
            category="Test",
            description="Açıklama",
            reviews=["Yorum 1", "Yorum 2", "Yorum 3"],
        )

        count = upsert_product(product)
        assert count == 4  # 1 description + 3 reviews
        mock_coll.upsert.assert_called_once()

    @patch("app.services.embedder._get_collection")
    @patch("app.services.embedder._get_model")
    def test_search_context_returns_documents(self, mock_model, mock_collection):
        """Verify search_context returns document list from ChromaDB."""
        from app.services.embedder import search_context

        mock_model.return_value.encode.return_value = [[0.1, 0.2]]
        mock_coll = MagicMock()
        mock_coll.query.return_value = {
            "documents": [["İlgili yorum 1", "İlgili yorum 2"]],
        }
        mock_collection.return_value = mock_coll

        results = search_context("test_123", "Ürün kalitesi nasıl?", top_k=2)
        assert len(results) == 2
        assert "İlgili yorum 1" in results

    @patch("app.services.embedder._get_collection")
    def test_upsert_empty_product_returns_zero(self, mock_collection):
        """Products with no description and no reviews should upsert 0 docs."""
        from app.services.embedder import upsert_product

        mock_coll = MagicMock()
        mock_collection.return_value = mock_coll

        product = ScrapedProduct(
            product_id="empty_123",
            product_name="Boş Ürün",
            category="Test",
            description="",  # empty
            reviews=[],
        )
        count = upsert_product(product)
        assert count == 0
        mock_coll.upsert.assert_not_called()
