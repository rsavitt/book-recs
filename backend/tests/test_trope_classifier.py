"""
Tests for VectorTropeClassifier service and /books/{id}/tropes API endpoint.
"""

import pytest
from sqlalchemy.orm import Session

from app.models.book import BookTag
from app.models.embedding import BookReviewEmbedding, BookTropeScore
from app.services.trope_classifier import (
    VectorTropeClassifier,
    apply_vector_tags_to_all_books,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_trope_score(
    db: Session,
    book_id: int,
    trope_slug: str,
    similarity_score: float,
    auto_tagged: bool = False,
) -> BookTropeScore:
    score = BookTropeScore(
        book_id=book_id,
        trope_slug=trope_slug,
        similarity_score=similarity_score,
        auto_tagged=auto_tagged,
    )
    db.add(score)
    db.commit()
    db.refresh(score)
    return score


_DUMMY_384 = [0.0] * 384


def _create_embedding(
    db: Session,
    book_id: int,
    review_count: int = 10,
) -> BookReviewEmbedding:
    emb = BookReviewEmbedding(
        book_id=book_id,
        embedding=_DUMMY_384,
        review_count=review_count,
        total_review_words=review_count * 50,
    )
    db.add(emb)
    db.commit()
    db.refresh(emb)
    return emb


# ===================================================================
# TestClassify – VectorTropeClassifier.classify()
# ===================================================================


class TestClassify:
    def test_no_scores_returns_empty(self, db, test_books):
        classifier = VectorTropeClassifier(db)
        result = classifier.classify(test_books[0].id)

        assert result.book_id == test_books[0].id
        assert result.trope_scores == []
        assert result.auto_tagged == []
        assert result.review_count == 0
        assert result.confidence == 0.0

    def test_scores_sorted_descending(self, db, test_books):
        book = test_books[0]
        _create_embedding(db, book.id, review_count=10)
        _create_trope_score(db, book.id, "slow-burn", 0.3)
        _create_trope_score(db, book.id, "enemies-to-lovers", 0.7)
        _create_trope_score(db, book.id, "fae", 0.5)

        classifier = VectorTropeClassifier(db)
        result = classifier.classify(book.id)

        slugs = [ts.trope_slug for ts in result.trope_scores]
        assert slugs == ["enemies-to-lovers", "fae", "slow-burn"]

    def test_auto_tagged_list_populated(self, db, test_books):
        book = test_books[0]
        _create_embedding(db, book.id, review_count=10)
        _create_trope_score(db, book.id, "fae", 0.6, auto_tagged=True)
        _create_trope_score(db, book.id, "slow-burn", 0.3, auto_tagged=False)

        classifier = VectorTropeClassifier(db)
        result = classifier.classify(book.id)

        assert result.auto_tagged == ["fae"]

    # --- confidence tiers ---

    def test_confidence_zero_reviews(self, db, test_books):
        book = test_books[0]
        _create_embedding(db, book.id, review_count=0)
        _create_trope_score(db, book.id, "fae", 0.5)

        result = VectorTropeClassifier(db).classify(book.id)
        assert result.confidence == 0.0

    def test_confidence_3_reviews(self, db, test_books):
        book = test_books[0]
        _create_embedding(db, book.id, review_count=3)
        _create_trope_score(db, book.id, "fae", 0.5)

        result = VectorTropeClassifier(db).classify(book.id)
        assert result.confidence == 0.2

    def test_confidence_10_reviews(self, db, test_books):
        book = test_books[0]
        _create_embedding(db, book.id, review_count=10)
        _create_trope_score(db, book.id, "fae", 0.5)

        result = VectorTropeClassifier(db).classify(book.id)
        assert result.confidence == 0.5

    def test_confidence_15_reviews(self, db, test_books):
        book = test_books[0]
        _create_embedding(db, book.id, review_count=15)
        _create_trope_score(db, book.id, "fae", 0.5)

        result = VectorTropeClassifier(db).classify(book.id)
        # 0.5 + (15-10)*0.0225 = 0.6125 → rounded to 0.613
        assert result.confidence == pytest.approx(0.613, abs=0.001)

    def test_confidence_30_plus_reviews(self, db, test_books):
        book = test_books[0]
        _create_embedding(db, book.id, review_count=30)
        _create_trope_score(db, book.id, "fae", 0.5)

        result = VectorTropeClassifier(db).classify(book.id)
        assert result.confidence == 0.95


# ===================================================================
# TestApplyAutoTags – VectorTropeClassifier.apply_auto_tags()
# ===================================================================


class TestApplyAutoTags:
    def test_adds_matching_tags(self, db, test_books, test_tags):
        book = test_books[0]
        _create_embedding(db, book.id, review_count=10)
        _create_trope_score(db, book.id, "enemies-to-lovers", 0.7, auto_tagged=True)

        classifier = VectorTropeClassifier(db)
        added = classifier.apply_auto_tags(book.id)

        assert "enemies-to-lovers" in added
        db.refresh(book)
        tag_slugs = {t.slug for t in book.tags}
        assert "enemies-to-lovers" in tag_slugs

    def test_skips_existing_tags(self, db, test_books, test_tags):
        book = test_books[0]
        # Pre-assign the tag
        etl_tag = db.query(BookTag).filter(BookTag.slug == "enemies-to-lovers").first()
        book.tags.append(etl_tag)
        db.commit()

        _create_embedding(db, book.id, review_count=10)
        _create_trope_score(db, book.id, "enemies-to-lovers", 0.7, auto_tagged=True)

        classifier = VectorTropeClassifier(db)
        added = classifier.apply_auto_tags(book.id)

        assert added == []

    def test_dry_run_returns_but_does_not_commit(self, db, test_books, test_tags):
        book = test_books[0]
        _create_embedding(db, book.id, review_count=10)
        _create_trope_score(db, book.id, "fae", 0.7, auto_tagged=True)

        classifier = VectorTropeClassifier(db)
        added = classifier.apply_auto_tags(book.id, dry_run=True)

        assert "fae" in added
        db.refresh(book)
        tag_slugs = {t.slug for t in book.tags}
        assert "fae" not in tag_slugs

    def test_nonexistent_book_returns_empty(self, db, test_books, test_tags):
        _create_trope_score(db, 9999, "fae", 0.7, auto_tagged=True)

        classifier = VectorTropeClassifier(db)
        added = classifier.apply_auto_tags(9999)
        assert added == []


# ===================================================================
# TestGetTopTropes – VectorTropeClassifier.get_top_tropes()
# ===================================================================


class TestGetTopTropes:
    def test_respects_limit(self, db, test_books):
        book = test_books[0]
        _create_embedding(db, book.id, review_count=10)
        for i, slug in enumerate(["fae", "slow-burn", "enemies-to-lovers", "dragons", "spicy"]):
            _create_trope_score(db, book.id, slug, 0.9 - i * 0.1)

        classifier = VectorTropeClassifier(db)
        top = classifier.get_top_tropes(book.id, limit=3)

        assert len(top) == 3

    def test_returns_sorted(self, db, test_books):
        book = test_books[0]
        _create_embedding(db, book.id, review_count=10)
        _create_trope_score(db, book.id, "slow-burn", 0.3)
        _create_trope_score(db, book.id, "fae", 0.8)

        classifier = VectorTropeClassifier(db)
        top = classifier.get_top_tropes(book.id, limit=10)

        assert top[0].trope_slug == "fae"
        assert top[1].trope_slug == "slow-burn"


# ===================================================================
# TestApplyVectorTagsToAllBooks – bulk function
# ===================================================================


class TestApplyVectorTagsToAllBooks:
    def test_processes_all_books_with_embeddings(self, db, test_books, test_tags):
        book_a, book_b = test_books[0], test_books[1]
        _create_embedding(db, book_a.id, review_count=10)
        _create_embedding(db, book_b.id, review_count=10)

        _create_trope_score(db, book_a.id, "enemies-to-lovers", 0.7, auto_tagged=True)
        _create_trope_score(db, book_b.id, "fae", 0.6, auto_tagged=True)

        stats = apply_vector_tags_to_all_books(db)

        assert stats["books_processed"] == 2
        assert stats["total_tags_added"] == 2
        assert stats["books_with_new_tags"] == 2


# ===================================================================
# TestTropesAPIEndpoint – GET /api/v1/books/{id}/tropes
# ===================================================================


class TestTropesAPIEndpoint:
    def test_returns_trope_scores(self, client, db, test_books):
        book = test_books[0]
        _create_embedding(db, book.id, review_count=10)
        _create_trope_score(db, book.id, "fae", 0.6, auto_tagged=True)
        _create_trope_score(db, book.id, "slow-burn", 0.3)

        resp = client.get(f"/api/v1/books/{book.id}/tropes")
        assert resp.status_code == 200

        data = resp.json()
        assert data["book_id"] == book.id
        assert data["review_count"] == 10
        assert len(data["trope_scores"]) == 2
        assert data["auto_tagged"] == ["fae"]

    def test_404_for_nonexistent_book(self, client, db):
        resp = client.get("/api/v1/books/99999/tropes")
        assert resp.status_code == 404

    def test_empty_for_book_without_scores(self, client, db, test_books):
        book = test_books[0]
        resp = client.get(f"/api/v1/books/{book.id}/tropes")
        assert resp.status_code == 200

        data = resp.json()
        assert data["trope_scores"] == []
        assert data["auto_tagged"] == []

    def test_respects_limit_param(self, client, db, test_books):
        book = test_books[0]
        _create_embedding(db, book.id, review_count=10)
        for i, slug in enumerate(["fae", "slow-burn", "enemies-to-lovers", "dragons", "spicy"]):
            _create_trope_score(db, book.id, slug, 0.9 - i * 0.1)

        resp = client.get(f"/api/v1/books/{book.id}/tropes?limit=2")
        assert resp.status_code == 200
        assert len(resp.json()["trope_scores"]) == 2
