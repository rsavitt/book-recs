"""
User-User Similarity Computation Service.

Computes similarity between users based on their book ratings using:
1. Pearson correlation (handles different rating scales)
2. Cosine similarity (mean-centered, as alternative)

Includes significance weighting to downweight similarities based on
small overlap counts.
"""

import math
from dataclasses import dataclass
from typing import Iterator

import numpy as np
from scipy import sparse
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from app.core.config import get_settings
from app.models.user import User
from app.models.rating import Rating
from app.models.similarity import UserSimilarity

settings = get_settings()


@dataclass
class SimilarityResult:
    """Result of computing similarity between two users."""

    user_id: int
    neighbor_id: int
    raw_similarity: float
    overlap_count: int
    adjusted_similarity: float


class SimilarityComputer:
    """
    Computes user-user similarity scores.

    Uses Pearson correlation with significance weighting:
    adjusted_sim = raw_sim * (overlap / (overlap + shrinkage))

    This downweights similarities based on small sample sizes.
    """

    def __init__(
        self,
        db: Session,
        min_overlap: int | None = None,
        shrinkage_factor: int | None = None,
        max_neighbors: int | None = None,
    ):
        self.db = db
        self.min_overlap = min_overlap or settings.MIN_OVERLAP_FOR_SIMILARITY
        self.shrinkage_factor = shrinkage_factor or settings.SIMILARITY_SHRINKAGE_FACTOR
        self.max_neighbors = max_neighbors or settings.MAX_NEIGHBORS_PER_USER

    def compute_for_user(self, user_id: int) -> list[SimilarityResult]:
        """
        Compute similarity between a user and all other users.

        Args:
            user_id: The user to compute similarities for

        Returns:
            List of SimilarityResult, sorted by adjusted_similarity descending
        """
        # Get user's ratings
        user_ratings = self._get_user_ratings(user_id)
        if len(user_ratings) < self.min_overlap:
            return []

        user_mean = np.mean(list(user_ratings.values()))
        user_books = set(user_ratings.keys())

        # Get all other users who have rated at least min_overlap of the same books
        candidate_users = self._get_candidate_users(user_id, user_books)

        results = []
        for neighbor_id in candidate_users:
            neighbor_ratings = self._get_user_ratings(neighbor_id)

            # Find overlapping books
            overlap_books = user_books & set(neighbor_ratings.keys())
            overlap_count = len(overlap_books)

            if overlap_count < self.min_overlap:
                continue

            # Compute Pearson correlation
            raw_sim = self._pearson_correlation(
                user_ratings, neighbor_ratings, overlap_books, user_mean
            )

            if raw_sim is None or math.isnan(raw_sim):
                continue

            # Apply significance weighting
            adjusted_sim = raw_sim * (overlap_count / (overlap_count + self.shrinkage_factor))

            results.append(
                SimilarityResult(
                    user_id=user_id,
                    neighbor_id=neighbor_id,
                    raw_similarity=raw_sim,
                    overlap_count=overlap_count,
                    adjusted_similarity=adjusted_sim,
                )
            )

        # Sort by adjusted similarity and limit to max_neighbors
        results.sort(key=lambda x: x.adjusted_similarity, reverse=True)
        return results[: self.max_neighbors]

    def _get_user_ratings(self, user_id: int) -> dict[int, float]:
        """Get all ratings for a user as {book_id: rating}."""
        ratings = (
            self.db.query(Rating.book_id, Rating.rating)
            .filter(Rating.user_id == user_id, Rating.rating > 0)
            .all()
        )
        return {book_id: float(rating) for book_id, rating in ratings}

    def _get_candidate_users(self, user_id: int, user_books: set[int]) -> list[int]:
        """
        Get IDs of users who might be similar (have overlap with user's books).

        Only returns users who have opted in to allow their data for recommendations.
        """
        # Find users who have rated at least some of the same books
        candidates = (
            self.db.query(Rating.user_id)
            .join(User, User.id == Rating.user_id)
            .filter(
                Rating.book_id.in_(user_books),
                Rating.user_id != user_id,
                Rating.rating > 0,
                User.allow_data_for_recs == True,
            )
            .group_by(Rating.user_id)
            .having(func.count(Rating.id) >= self.min_overlap)
            .all()
        )

        return [user_id for (user_id,) in candidates]

    def _pearson_correlation(
        self,
        user_ratings: dict[int, float],
        neighbor_ratings: dict[int, float],
        overlap_books: set[int],
        user_mean: float | None = None,
    ) -> float | None:
        """
        Compute Pearson correlation between two users on overlapping books.

        Returns:
            Correlation coefficient (-1 to 1), or None if undefined
        """
        if not overlap_books:
            return None

        # Get ratings for overlapping books
        user_vals = [user_ratings[book_id] for book_id in overlap_books]
        neighbor_vals = [neighbor_ratings[book_id] for book_id in overlap_books]

        # Compute means
        if user_mean is None:
            user_mean = np.mean(user_vals)
        neighbor_mean = np.mean(neighbor_vals)

        # Compute correlation
        numerator = sum(
            (u - user_mean) * (n - neighbor_mean)
            for u, n in zip(user_vals, neighbor_vals)
        )

        user_std = math.sqrt(sum((u - user_mean) ** 2 for u in user_vals))
        neighbor_std = math.sqrt(sum((n - neighbor_mean) ** 2 for n in neighbor_vals))

        denominator = user_std * neighbor_std

        if denominator == 0:
            return None

        return numerator / denominator

    def save_similarities(self, results: list[SimilarityResult]) -> int:
        """
        Save computed similarities to the database.

        Args:
            results: List of SimilarityResult to save

        Returns:
            Number of records saved
        """
        if not results:
            return 0

        user_id = results[0].user_id

        # Delete existing similarities for this user
        self.db.query(UserSimilarity).filter(UserSimilarity.user_id == user_id).delete()

        # Insert new similarities
        for result in results:
            similarity = UserSimilarity(
                user_id=result.user_id,
                neighbor_id=result.neighbor_id,
                similarity_score=result.raw_similarity,
                overlap_count=result.overlap_count,
                adjusted_similarity=result.adjusted_similarity,
            )
            self.db.add(similarity)

        self.db.commit()
        return len(results)


class BatchSimilarityComputer:
    """
    Batch computation of similarities for all users.

    Optimized for processing many users efficiently using sparse matrices.
    """

    def __init__(
        self,
        db: Session,
        min_overlap: int | None = None,
        shrinkage_factor: int | None = None,
        max_neighbors: int | None = None,
    ):
        self.db = db
        self.min_overlap = min_overlap or settings.MIN_OVERLAP_FOR_SIMILARITY
        self.shrinkage_factor = shrinkage_factor or settings.SIMILARITY_SHRINKAGE_FACTOR
        self.max_neighbors = max_neighbors or settings.MAX_NEIGHBORS_PER_USER

    def compute_all(self, progress_callback=None) -> dict:
        """
        Compute similarities for all users.

        Args:
            progress_callback: Optional function(current, total) for progress updates

        Returns:
            Dict with statistics about the computation
        """
        stats = {
            "users_processed": 0,
            "similarities_computed": 0,
            "users_skipped": 0,
        }

        # Get all users who have opted in and have enough ratings
        users = self._get_eligible_users()
        total_users = len(users)

        if total_users == 0:
            return stats

        # Build rating matrix
        user_ids, book_ids, ratings_matrix = self._build_rating_matrix(users)

        if ratings_matrix is None:
            return stats

        # Compute all pairwise similarities
        similarity_matrix = self._compute_similarity_matrix(ratings_matrix)

        # Save results for each user
        for i, user_id in enumerate(user_ids):
            if progress_callback:
                progress_callback(i + 1, total_users)

            similarities = self._extract_user_similarities(
                user_id, i, user_ids, similarity_matrix, ratings_matrix
            )

            if similarities:
                self._save_user_similarities(user_id, similarities)
                stats["users_processed"] += 1
                stats["similarities_computed"] += len(similarities)
            else:
                stats["users_skipped"] += 1

        self.db.commit()
        return stats

    def _get_eligible_users(self) -> list[int]:
        """Get users eligible for similarity computation."""
        users = (
            self.db.query(User.id)
            .join(Rating, Rating.user_id == User.id)
            .filter(User.allow_data_for_recs == True, Rating.rating > 0)
            .group_by(User.id)
            .having(func.count(Rating.id) >= self.min_overlap)
            .all()
        )
        return [user_id for (user_id,) in users]

    def _build_rating_matrix(
        self, user_ids: list[int]
    ) -> tuple[list[int], list[int], sparse.csr_matrix | None]:
        """
        Build a sparse user-book rating matrix.

        Returns:
            Tuple of (user_ids, book_ids, sparse_matrix)
        """
        if not user_ids:
            return [], [], None

        # Get all ratings for eligible users
        ratings = (
            self.db.query(Rating.user_id, Rating.book_id, Rating.rating)
            .filter(Rating.user_id.in_(user_ids), Rating.rating > 0)
            .all()
        )

        if not ratings:
            return [], [], None

        # Create mappings
        user_to_idx = {uid: i for i, uid in enumerate(user_ids)}
        book_ids = list(set(r.book_id for r in ratings))
        book_to_idx = {bid: i for i, bid in enumerate(book_ids)}

        # Build sparse matrix
        rows = []
        cols = []
        data = []

        for r in ratings:
            if r.user_id in user_to_idx:
                rows.append(user_to_idx[r.user_id])
                cols.append(book_to_idx[r.book_id])
                data.append(float(r.rating))

        matrix = sparse.csr_matrix(
            (data, (rows, cols)),
            shape=(len(user_ids), len(book_ids)),
        )

        return user_ids, book_ids, matrix

    def _compute_similarity_matrix(
        self, ratings_matrix: sparse.csr_matrix
    ) -> np.ndarray:
        """
        Compute pairwise cosine similarity matrix.

        Uses mean-centered ratings for better results.
        """
        # Mean-center the ratings (per user)
        row_means = np.array(ratings_matrix.sum(axis=1)).flatten()
        row_counts = np.array((ratings_matrix != 0).sum(axis=1)).flatten()
        row_means = np.divide(
            row_means, row_counts, out=np.zeros_like(row_means), where=row_counts != 0
        )

        # Subtract means (only from non-zero entries)
        centered = ratings_matrix.copy()
        for i in range(centered.shape[0]):
            start, end = centered.indptr[i], centered.indptr[i + 1]
            centered.data[start:end] -= row_means[i]

        # Compute cosine similarity
        norms = sparse.linalg.norm(centered, axis=1)
        norms[norms == 0] = 1  # Avoid division by zero

        # Normalize rows
        normalized = centered.multiply(1 / norms.reshape(-1, 1))

        # Compute similarity matrix (dot product of normalized vectors)
        similarity = normalized @ normalized.T

        return similarity.toarray()

    def _extract_user_similarities(
        self,
        user_id: int,
        user_idx: int,
        user_ids: list[int],
        similarity_matrix: np.ndarray,
        ratings_matrix: sparse.csr_matrix,
    ) -> list[SimilarityResult]:
        """Extract top neighbors for a user from the similarity matrix."""
        similarities = similarity_matrix[user_idx]

        # Get overlap counts
        user_rated = set(ratings_matrix[user_idx].indices)

        results = []
        for neighbor_idx, raw_sim in enumerate(similarities):
            if neighbor_idx == user_idx:
                continue

            if raw_sim <= 0:  # Only positive correlations
                continue

            neighbor_id = user_ids[neighbor_idx]
            neighbor_rated = set(ratings_matrix[neighbor_idx].indices)
            overlap_count = len(user_rated & neighbor_rated)

            if overlap_count < self.min_overlap:
                continue

            # Apply significance weighting
            adjusted_sim = raw_sim * (overlap_count / (overlap_count + self.shrinkage_factor))

            results.append(
                SimilarityResult(
                    user_id=user_id,
                    neighbor_id=neighbor_id,
                    raw_similarity=float(raw_sim),
                    overlap_count=overlap_count,
                    adjusted_similarity=float(adjusted_sim),
                )
            )

        # Sort and limit
        results.sort(key=lambda x: x.adjusted_similarity, reverse=True)
        return results[: self.max_neighbors]

    def _save_user_similarities(
        self, user_id: int, similarities: list[SimilarityResult]
    ):
        """Save similarities for a user."""
        # Delete existing
        self.db.query(UserSimilarity).filter(UserSimilarity.user_id == user_id).delete()

        # Insert new
        for result in similarities:
            self.db.add(
                UserSimilarity(
                    user_id=result.user_id,
                    neighbor_id=result.neighbor_id,
                    similarity_score=result.raw_similarity,
                    overlap_count=result.overlap_count,
                    adjusted_similarity=result.adjusted_similarity,
                )
            )


def compute_user_similarity(db: Session, user_id: int) -> int:
    """
    Compute and save similarity for a single user.

    Args:
        db: Database session
        user_id: User to compute similarities for

    Returns:
        Number of similarities computed
    """
    computer = SimilarityComputer(db)
    results = computer.compute_for_user(user_id)
    return computer.save_similarities(results)


def compute_all_similarities(db: Session, progress_callback=None) -> dict:
    """
    Compute similarities for all users (batch job).

    Args:
        db: Database session
        progress_callback: Optional progress callback

    Returns:
        Statistics dict
    """
    computer = BatchSimilarityComputer(db)
    return computer.compute_all(progress_callback)
