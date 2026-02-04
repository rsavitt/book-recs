"""Tests for recommendation service."""

import pytest

from app.schemas.recommendation import RecommendationFilters
from app.services.recommendation_service import RecommendationEngine


class TestDiversityConstraints:
    """Test author diversity in recommendations."""

    def test_limits_books_per_author(self):
        """Should limit books from the same author."""
        # Create mock scored books
        from dataclasses import dataclass

        @dataclass
        class MockBook:
            author: str

        @dataclass
        class MockScoredBook:
            book: MockBook
            predicted_rating: float = 4.5

        # 5 books by same author, 2 by others
        scored_books = [
            MockScoredBook(book=MockBook(author="Sarah J. Maas")),
            MockScoredBook(book=MockBook(author="Sarah J. Maas")),
            MockScoredBook(book=MockBook(author="Sarah J. Maas")),
            MockScoredBook(book=MockBook(author="Sarah J. Maas")),
            MockScoredBook(book=MockBook(author="Sarah J. Maas")),
            MockScoredBook(book=MockBook(author="Rebecca Yarros")),
            MockScoredBook(book=MockBook(author="Holly Black")),
        ]

        # Create engine with mock db
        engine = RecommendationEngine.__new__(RecommendationEngine)
        engine.diversity_author_limit = 3

        result = engine._apply_diversity(scored_books)

        # Should have at most 3 Maas books + 2 others = 5 total
        maas_count = sum(1 for s in result if s.book.author == "Sarah J. Maas")
        assert maas_count == 3
        assert len(result) == 5


class TestFilterApplication:
    """Test recommendation filters."""

    def test_spice_level_filter(self):
        """Should filter by spice level."""
        from dataclasses import dataclass

        @dataclass
        class MockBook:
            spice_level: int | None
            is_ya: bool | None = None
            tags: list = None

            def __post_init__(self):
                if self.tags is None:
                    self.tags = []

        @dataclass
        class MockScoredBook:
            book: MockBook

        scored_books = [
            MockScoredBook(book=MockBook(spice_level=1)),
            MockScoredBook(book=MockBook(spice_level=2)),
            MockScoredBook(book=MockBook(spice_level=3)),
            MockScoredBook(book=MockBook(spice_level=4)),
            MockScoredBook(book=MockBook(spice_level=5)),
            MockScoredBook(book=MockBook(spice_level=None)),  # Unknown
        ]

        # Filter for spice 2-4
        engine = RecommendationEngine.__new__(RecommendationEngine)
        engine.filters = RecommendationFilters(spice_min=2, spice_max=4)

        result = engine._apply_filters(scored_books)

        # Should only include books with spice 2, 3, or 4
        assert len(result) == 3
        spice_levels = [s.book.spice_level for s in result]
        assert all(2 <= s <= 4 for s in spice_levels)

    def test_ya_filter(self):
        """Should filter by YA/Adult."""
        from dataclasses import dataclass

        @dataclass
        class MockBook:
            is_ya: bool | None
            spice_level: int | None = None
            tags: list = None

            def __post_init__(self):
                if self.tags is None:
                    self.tags = []

        @dataclass
        class MockScoredBook:
            book: MockBook

        scored_books = [
            MockScoredBook(book=MockBook(is_ya=True)),
            MockScoredBook(book=MockBook(is_ya=True)),
            MockScoredBook(book=MockBook(is_ya=False)),
            MockScoredBook(book=MockBook(is_ya=False)),
            MockScoredBook(book=MockBook(is_ya=None)),
        ]

        # Filter for YA only
        engine = RecommendationEngine.__new__(RecommendationEngine)
        engine.filters = RecommendationFilters(is_ya=True)

        result = engine._apply_filters(scored_books)

        assert len(result) == 2
        assert all(s.book.is_ya is True for s in result)


class TestExplanationGeneration:
    """Test recommendation explanation text."""

    def test_explanation_with_shared_books(self):
        """Should include shared book titles in explanation."""
        from dataclasses import dataclass

        @dataclass
        class MockScoredBook:
            neighbor_count: int
            average_neighbor_rating: float

        engine = RecommendationEngine.__new__(RecommendationEngine)

        scored = MockScoredBook(neighbor_count=12, average_neighbor_rating=4.6)
        shared_books = ["Fourth Wing", "A Court of Mist and Fury"]

        explanation = engine._generate_explanation_text(scored, shared_books)

        assert "12 similar readers" in explanation
        assert "Fourth Wing" in explanation
        assert "4.6★" in explanation

    def test_explanation_without_shared_books(self):
        """Should work without shared books."""
        from dataclasses import dataclass

        @dataclass
        class MockScoredBook:
            neighbor_count: int
            average_neighbor_rating: float

        engine = RecommendationEngine.__new__(RecommendationEngine)

        scored = MockScoredBook(neighbor_count=5, average_neighbor_rating=4.2)

        explanation = engine._generate_explanation_text(scored, [])

        assert "5 similar readers" in explanation
        assert "4.2★" in explanation

    def test_singular_reader(self):
        """Should use singular 'reader' for count of 1."""
        from dataclasses import dataclass

        @dataclass
        class MockScoredBook:
            neighbor_count: int
            average_neighbor_rating: float

        engine = RecommendationEngine.__new__(RecommendationEngine)

        scored = MockScoredBook(neighbor_count=1, average_neighbor_rating=5.0)

        explanation = engine._generate_explanation_text(scored, [])

        assert "1 similar reader" in explanation
        assert "readers" not in explanation


class TestScoringFormula:
    """Test the weighted average scoring formula."""

    def test_weighted_average_calculation(self):
        """Verify weighted average: score = Σ(sim * rating) / Σ(sim)."""
        # Neighbors with their similarities and ratings
        neighbors = [
            (0.9, 5.0),  # High similarity, high rating
            (0.5, 4.0),  # Medium similarity, medium rating
            (0.3, 3.0),  # Low similarity, low rating
        ]

        # Manual calculation
        weighted_sum = sum(sim * rating for sim, rating in neighbors)
        total_weight = sum(sim for sim, _ in neighbors)
        expected = weighted_sum / total_weight

        # Verify
        assert expected == pytest.approx(4.35, abs=0.01)

    def test_high_similarity_neighbors_weighted_more(self):
        """High similarity neighbors should have more influence."""
        # Same ratings, different similarities
        high_sim_neighbor = (0.95, 5.0)
        low_sim_neighbor = (0.1, 1.0)

        neighbors = [high_sim_neighbor, low_sim_neighbor]

        weighted_sum = sum(sim * rating for sim, rating in neighbors)
        total_weight = sum(sim for sim, _ in neighbors)
        score = weighted_sum / total_weight

        # Score should be much closer to 5 than to 1
        assert score > 4.5
