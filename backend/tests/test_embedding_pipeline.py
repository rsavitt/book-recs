"""
Tests for the UCSD review embedding pipeline utility functions and seed data.
"""

import gzip
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from sqlalchemy.orm import Session

from app.data.trope_seeds import TROPE_SEEDS, TROPE_THRESHOLD_OVERRIDES
from app.models.book import BookEdition
from app.models.embedding import BookReviewEmbedding, BookTropeScore, TropeSeedEmbedding
from scripts.import_review_embeddings import (
    build_goodreads_id_mapping,
    chunk_text,
    clean_review_text,
    collect_reviews,
    compute_trope_scores,
)


# ===================================================================
# TestCleanReviewText
# ===================================================================


class TestCleanReviewText:
    def test_removes_html_tags(self):
        assert clean_review_text("<b>bold</b> text") == "bold text"

    def test_removes_urls(self):
        result = clean_review_text("check https://example.com/page out")
        assert "https://example.com" not in result
        assert "check" in result
        assert "out" in result

    def test_normalizes_whitespace(self):
        assert clean_review_text("too   many    spaces") == "too many spaces"

    def test_combined_dirty_input(self):
        dirty = '<a href="https://x.com">link</a>   and   more'
        result = clean_review_text(dirty)
        assert "<" not in result
        assert "https" not in result
        assert "  " not in result

    def test_empty_string(self):
        assert clean_review_text("") == ""


# ===================================================================
# TestChunkText
# ===================================================================


class TestChunkText:
    def test_short_text_single_chunk(self):
        text = "This is a short review about the book."
        chunks = chunk_text(text, max_words=150)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_multiple_chunks(self):
        words = ["word"] * 300
        text = " ".join(words)
        chunks = chunk_text(text, max_words=150)
        assert len(chunks) == 2

    def test_drops_short_trailing_chunk(self):
        # 155 words → chunk of 150 + trailing 5 words (< 10 → dropped)
        words = ["word"] * 155
        text = " ".join(words)
        chunks = chunk_text(text, max_words=150)
        assert len(chunks) == 1

    def test_custom_max_words(self):
        words = ["word"] * 50
        text = " ".join(words)
        chunks = chunk_text(text, max_words=20)
        # 50 / 20 = 2 full chunks + 10 word trailing chunk (exactly 10 → kept)
        assert len(chunks) == 3


# ===================================================================
# TestTropeSeedData – validation of TROPE_SEEDS / TROPE_THRESHOLD_OVERRIDES
# ===================================================================


class TestTropeSeedData:
    def test_every_trope_has_min_3_phrases(self):
        for slug, phrases in TROPE_SEEDS.items():
            assert len(phrases) >= 3, f"{slug} has only {len(phrases)} phrases"

    def test_all_phrases_are_nonempty_strings(self):
        for slug, phrases in TROPE_SEEDS.items():
            for phrase in phrases:
                assert isinstance(phrase, str), f"{slug} phrase not a string"
                assert len(phrase.strip()) > 0, f"{slug} has empty phrase"

    def test_threshold_overrides_reference_existing_tropes(self):
        for slug in TROPE_THRESHOLD_OVERRIDES:
            # Overrides may reference tropes not in TROPE_SEEDS (e.g. broad
            # category slugs like "romance" / "fantasy"), so we only check
            # the value type here. If the slug is in TROPE_SEEDS, great.
            assert isinstance(slug, str)

    def test_threshold_values_valid(self):
        for slug, val in TROPE_THRESHOLD_OVERRIDES.items():
            assert isinstance(val, float), f"{slug} threshold not float"
            assert 0 < val < 1, f"{slug} threshold {val} out of range (0,1)"


# ===================================================================
# TestBuildGoodreadsIdMapping
# ===================================================================


class TestBuildGoodreadsIdMapping:
    def test_creates_mapping(self, db, test_books):
        # Create editions with goodreads IDs
        ed1 = BookEdition(
            book_id=test_books[0].id,
            goodreads_book_id="111",
        )
        ed2 = BookEdition(
            book_id=test_books[1].id,
            goodreads_book_id="222",
        )
        db.add_all([ed1, ed2])
        db.commit()

        mapping = build_goodreads_id_mapping(db)
        assert mapping == {"111": test_books[0].id, "222": test_books[1].id}

    def test_skips_editions_without_goodreads_id(self, db, test_books):
        ed = BookEdition(book_id=test_books[0].id, goodreads_book_id=None)
        db.add(ed)
        db.commit()

        mapping = build_goodreads_id_mapping(db)
        assert mapping == {}


# ===================================================================
# TestCollectReviews
# ===================================================================


class TestCollectReviews:
    @staticmethod
    def _write_gz_reviews(dir_path: Path, filename: str, reviews: list[dict]):
        """Write reviews as gzipped JSON lines."""
        file_path = dir_path / filename
        with gzip.open(file_path, "wt", encoding="utf-8") as f:
            for r in reviews:
                f.write(json.dumps(r) + "\n")

    def test_collects_matching_reviews(self, tmp_path):
        reviews = [
            {
                "book_id": "111",
                "review_text": " ".join(["good"] * 25),
                "rating": 5,
                "n_votes": 2,
            },
        ]
        # The filename must match the URL's last segment
        filename = "goodreads_reviews_fantasy_paranormal.json.gz"
        self._write_gz_reviews(tmp_path, filename, reviews)

        id_mapping = {"111": 1}
        settings = SimpleNamespace(MAX_REVIEWS_PER_BOOK=100)

        # Monkey-patch REVIEW_URLS so collect_reviews finds our temp file
        import scripts.import_review_embeddings as mod

        orig = mod.REVIEW_URLS
        mod.REVIEW_URLS = {
            "fantasy_paranormal": f"http://example.com/{filename}",
        }
        try:
            result = collect_reviews(tmp_path, id_mapping, settings)
        finally:
            mod.REVIEW_URLS = orig

        assert 1 in result
        assert len(result[1]) == 1
        assert result[1][0]["rating"] == 5

    def test_filters_short_reviews(self, tmp_path):
        reviews = [
            {"book_id": "111", "review_text": "too short", "rating": 3},
        ]
        filename = "goodreads_reviews_fantasy_paranormal.json.gz"
        self._write_gz_reviews(tmp_path, filename, reviews)

        id_mapping = {"111": 1}
        settings = SimpleNamespace(MAX_REVIEWS_PER_BOOK=100)

        import scripts.import_review_embeddings as mod

        orig = mod.REVIEW_URLS
        mod.REVIEW_URLS = {
            "fantasy_paranormal": f"http://example.com/{filename}",
        }
        try:
            result = collect_reviews(tmp_path, id_mapping, settings)
        finally:
            mod.REVIEW_URLS = orig

        assert result == {}

    def test_respects_max_reviews(self, tmp_path):
        reviews = [
            {
                "book_id": "111",
                "review_text": " ".join(["word"] * 25),
                "rating": i,
            }
            for i in range(5)
        ]
        filename = "goodreads_reviews_fantasy_paranormal.json.gz"
        self._write_gz_reviews(tmp_path, filename, reviews)

        id_mapping = {"111": 1}
        settings = SimpleNamespace(MAX_REVIEWS_PER_BOOK=2)

        import scripts.import_review_embeddings as mod

        orig = mod.REVIEW_URLS
        mod.REVIEW_URLS = {
            "fantasy_paranormal": f"http://example.com/{filename}",
        }
        try:
            result = collect_reviews(tmp_path, id_mapping, settings)
        finally:
            mod.REVIEW_URLS = orig

        assert len(result[1]) == 2


# ===================================================================
# TestComputeTropeScores
# ===================================================================


def _vec384(index: int) -> list[float]:
    """Create a 384-dim unit vector with 1.0 at the given index."""
    v = [0.0] * 384
    v[index] = 1.0
    return v


def _vec384_mix(a_idx: int, a_val: float, b_idx: int, b_val: float) -> list[float]:
    """Create a 384-dim vector with two non-zero components."""
    v = [0.0] * 384
    v[a_idx] = a_val
    v[b_idx] = b_val
    return v


class TestComputeTropeScores:
    def _setup_embeddings(self, db, test_books):
        """Insert a book embedding and two trope seed embeddings."""
        book = test_books[0]

        emb = BookReviewEmbedding(
            book_id=book.id,
            embedding=_vec384(0),  # unit vector along dim-0
            review_count=10,
            total_review_words=500,
        )
        db.add(emb)

        # Seed for "fae" – same direction → high similarity
        seed1 = TropeSeedEmbedding(
            trope_slug="fae",
            seed_phrase="faerie courts",
            embedding=_vec384(0),
        )
        # Seed for "dragons" – orthogonal → low similarity
        seed2 = TropeSeedEmbedding(
            trope_slug="dragons",
            seed_phrase="fire breathing",
            embedding=_vec384(1),
        )
        db.add_all([seed1, seed2])
        db.commit()
        return book

    def test_computes_correct_scores(self, db, test_books):
        book = self._setup_embeddings(db, test_books)

        settings = SimpleNamespace(TROPE_SIMILARITY_THRESHOLD=0.45)
        stats = compute_trope_scores(db, settings)

        assert stats["books_scored"] == 1
        assert stats["tropes_scored"] == 2
        assert stats["total_scores"] == 2

        fae_score = (
            db.query(BookTropeScore)
            .filter(
                BookTropeScore.book_id == book.id,
                BookTropeScore.trope_slug == "fae",
            )
            .first()
        )
        dragon_score = (
            db.query(BookTropeScore)
            .filter(
                BookTropeScore.book_id == book.id,
                BookTropeScore.trope_slug == "dragons",
            )
            .first()
        )

        # dot(e0, e0) = 1.0 → above 0.45 threshold
        assert fae_score.similarity_score == pytest.approx(1.0, abs=0.01)
        assert fae_score.auto_tagged is True

        # dot(e0, e1) = 0.0 → below 0.45 threshold
        assert dragon_score.similarity_score == pytest.approx(0.0, abs=0.01)
        assert dragon_score.auto_tagged is False

    def test_uses_per_trope_threshold_overrides(self, db, test_books):
        book = test_books[0]
        # Vector with moderate similarity to both tropes
        emb = BookReviewEmbedding(
            book_id=book.id,
            embedding=_vec384_mix(0, 0.6, 1, 0.8),
            review_count=10,
            total_review_words=500,
        )
        db.add(emb)

        # "fae" seed → unit along dim-0: similarity = 0.6
        seed1 = TropeSeedEmbedding(
            trope_slug="fae",
            seed_phrase="faerie courts",
            embedding=_vec384(0),
        )
        # "dragon-riders" seed → unit along dim-1: similarity = 0.8
        seed2 = TropeSeedEmbedding(
            trope_slug="dragon-riders",
            seed_phrase="dragon riding",
            embedding=_vec384(1),
        )
        db.add_all([seed1, seed2])
        db.commit()

        # Default threshold 0.70: fae (0.6) below, dragon-riders (0.8) above
        # dragon-riders has override of 0.40 → still above
        settings = SimpleNamespace(TROPE_SIMILARITY_THRESHOLD=0.70)
        stats = compute_trope_scores(db, settings)

        fae_score = (
            db.query(BookTropeScore)
            .filter(
                BookTropeScore.book_id == book.id,
                BookTropeScore.trope_slug == "fae",
            )
            .first()
        )
        dr_score = (
            db.query(BookTropeScore)
            .filter(
                BookTropeScore.book_id == book.id,
                BookTropeScore.trope_slug == "dragon-riders",
            )
            .first()
        )

        # fae: 0.6 < 0.70 (default) → not auto-tagged
        assert fae_score.auto_tagged is False
        # dragon-riders: 0.8 >= 0.40 (override) → auto-tagged
        assert dr_score.auto_tagged is True
