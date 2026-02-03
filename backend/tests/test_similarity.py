"""Tests for similarity computation service."""


import pytest

from app.services.similarity import SimilarityComputer


class TestPearsonCorrelation:
    """Test Pearson correlation calculation."""

    def test_perfect_positive_correlation(self):
        """Identical ratings should have correlation 1.0."""
        user_ratings = {1: 5.0, 2: 4.0, 3: 3.0, 4: 2.0, 5: 1.0}
        neighbor_ratings = {1: 5.0, 2: 4.0, 3: 3.0, 4: 2.0, 5: 1.0}
        overlap = set(user_ratings.keys())

        # Create a mock computer just to access the method
        computer = SimilarityComputer.__new__(SimilarityComputer)
        correlation = computer._pearson_correlation(
            user_ratings, neighbor_ratings, overlap
        )

        assert correlation == pytest.approx(1.0, abs=0.001)

    def test_perfect_negative_correlation(self):
        """Opposite ratings should have correlation -1.0."""
        user_ratings = {1: 5.0, 2: 4.0, 3: 3.0, 4: 2.0, 5: 1.0}
        neighbor_ratings = {1: 1.0, 2: 2.0, 3: 3.0, 4: 4.0, 5: 5.0}
        overlap = set(user_ratings.keys())

        computer = SimilarityComputer.__new__(SimilarityComputer)
        correlation = computer._pearson_correlation(
            user_ratings, neighbor_ratings, overlap
        )

        assert correlation == pytest.approx(-1.0, abs=0.001)

    def test_no_correlation(self):
        """Unrelated ratings should have correlation near 0."""
        user_ratings = {1: 5.0, 2: 1.0, 3: 5.0, 4: 1.0}
        neighbor_ratings = {1: 3.0, 2: 3.0, 3: 3.0, 4: 3.0}  # All same rating
        overlap = set(user_ratings.keys())

        computer = SimilarityComputer.__new__(SimilarityComputer)
        correlation = computer._pearson_correlation(
            user_ratings, neighbor_ratings, overlap
        )

        # When one user has constant ratings, std dev is 0, correlation is undefined
        assert correlation is None

    def test_partial_overlap(self):
        """Correlation should only use overlapping books."""
        user_ratings = {1: 5.0, 2: 4.0, 3: 3.0, 100: 1.0}  # 100 not in neighbor
        neighbor_ratings = {1: 5.0, 2: 4.0, 3: 3.0, 200: 5.0}  # 200 not in user
        overlap = {1, 2, 3}

        computer = SimilarityComputer.__new__(SimilarityComputer)
        correlation = computer._pearson_correlation(
            user_ratings, neighbor_ratings, overlap
        )

        assert correlation == pytest.approx(1.0, abs=0.001)


class TestSignificanceWeighting:
    """Test significance weighting formula."""

    def test_low_overlap_reduces_similarity(self):
        """Low overlap should significantly reduce adjusted similarity."""
        shrinkage = 10  # Default
        raw_sim = 0.9

        # With only 5 books overlap
        overlap_5 = 5
        adjusted_5 = raw_sim * (overlap_5 / (overlap_5 + shrinkage))
        assert adjusted_5 == pytest.approx(0.3, abs=0.01)

        # With 20 books overlap
        overlap_20 = 20
        adjusted_20 = raw_sim * (overlap_20 / (overlap_20 + shrinkage))
        assert adjusted_20 == pytest.approx(0.6, abs=0.01)

        # With 100 books overlap
        overlap_100 = 100
        adjusted_100 = raw_sim * (overlap_100 / (overlap_100 + shrinkage))
        assert adjusted_100 == pytest.approx(0.82, abs=0.01)

    def test_high_overlap_preserves_similarity(self):
        """Very high overlap should preserve most of the similarity."""
        shrinkage = 10
        raw_sim = 0.8
        overlap = 200

        adjusted = raw_sim * (overlap / (overlap + shrinkage))

        # Should be close to raw similarity
        assert adjusted > 0.75
        assert adjusted < raw_sim


class TestSimilarityResult:
    """Test SimilarityResult data class."""

    def test_result_fields(self):
        """SimilarityResult should store all required fields."""
        from app.services.similarity import SimilarityResult

        result = SimilarityResult(
            user_id=1,
            neighbor_id=2,
            raw_similarity=0.85,
            overlap_count=25,
            adjusted_similarity=0.607,
        )

        assert result.user_id == 1
        assert result.neighbor_id == 2
        assert result.raw_similarity == 0.85
        assert result.overlap_count == 25
        assert result.adjusted_similarity == 0.607
