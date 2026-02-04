#!/usr/bin/env python3
"""
Import UCSD Goodreads review data, embed reviews with sentence-transformers,
and compute trope similarity scores using pgvector.

Pipeline steps:
1. Download UCSD review files (fantasy_paranormal + romance)
2. Build Goodreads ID -> book_id mapping from book_editions table
3. Collect and filter reviews per book
4. Compute per-book aggregated embeddings
5. Embed trope seed phrases
6. Compute book-trope similarity scores

Usage:
    python -m scripts.import_review_embeddings
    python -m scripts.import_review_embeddings --skip-download
    python -m scripts.import_review_embeddings --step embeddings
    python -m scripts.import_review_embeddings --step tropes
    python -m scripts.import_review_embeddings --step scores
"""

import argparse
import gzip
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_settings
from app.data.trope_seeds import TROPE_SEEDS, TROPE_THRESHOLD_OVERRIDES
from app.models.book import BookEdition
from app.models.embedding import BookReviewEmbedding, BookTropeScore, TropeSeedEmbedding

# UCSD Goodreads review dataset URLs
REVIEW_URLS = {
    "fantasy_paranormal": "https://datarepo.eng.ucsd.edu/mcauley_group/gdrive/goodreads/byGenre/goodreads_reviews_fantasy_paranormal.json.gz",
    "romance": "https://datarepo.eng.ucsd.edu/mcauley_group/gdrive/goodreads/byGenre/goodreads_reviews_romance.json.gz",
}

DATA_DIR = Path(__file__).parent / "data"


def download_file(url: str, dest_path: Path) -> bool:
    """Download a file with progress indication."""
    import urllib.request

    if dest_path.exists():
        print(f"  Already downloaded: {dest_path.name}")
        return True

    print(f"  Downloading: {url}")
    try:

        def reporthook(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                percent = min(100, downloaded * 100 / total_size)
                mb_downloaded = downloaded / (1024 * 1024)
                mb_total = total_size / (1024 * 1024)
                print(
                    f"\r    {percent:.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)",
                    end="",
                    flush=True,
                )

        urllib.request.urlretrieve(url, dest_path, reporthook)
        print()
        return True
    except Exception as e:
        print(f"\n  Error downloading: {e}")
        return False


def read_gzip_json_lines(file_path: Path):
    """Stream gzipped JSON lines without loading full file into memory."""
    with gzip.open(file_path, "rt", encoding="utf-8") as f:
        for line in f:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def clean_review_text(text: str) -> str:
    """Strip HTML tags, URLs, and normalize whitespace."""
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Remove URLs
    text = re.sub(r"https?://\S+", " ", text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def chunk_text(text: str, max_words: int = 150) -> list[str]:
    """Split text into chunks of approximately max_words words."""
    words = text.split()
    if len(words) <= max_words:
        return [text]
    chunks = []
    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i : i + max_words])
        if len(chunk.split()) >= 10:  # Skip very short trailing chunks
            chunks.append(chunk)
    return chunks


def build_goodreads_id_mapping(session) -> dict[str, int]:
    """Build mapping of goodreads_book_id -> book_id from book_editions table."""
    print("  Building Goodreads ID mapping...")
    editions = (
        session.query(BookEdition.goodreads_book_id, BookEdition.book_id)
        .filter(BookEdition.goodreads_book_id.isnot(None))
        .all()
    )
    mapping = {str(gr_id): book_id for gr_id, book_id in editions}
    print(f"  Found {len(mapping)} books with Goodreads IDs")
    return mapping


def collect_reviews(data_dir: Path, id_mapping: dict[str, int], settings) -> dict[int, list[dict]]:
    """
    Stream reviews from gzipped files and collect for books in our DB.

    Returns: {book_id: [{"text": ..., "rating": ..., "n_votes": ...}, ...]}
    """
    max_reviews = settings.MAX_REVIEWS_PER_BOOK
    book_reviews: dict[int, list[dict]] = {}
    total_processed = 0
    matched = 0

    for genre, url in REVIEW_URLS.items():
        filename = url.split("/")[-1]
        file_path = data_dir / filename

        if not file_path.exists():
            print(f"  Skipping {genre} reviews - file not found: {file_path}")
            continue

        print(f"  Processing {genre} reviews...")

        for review in read_gzip_json_lines(file_path):
            total_processed += 1
            if total_processed % 500000 == 0:
                print(
                    f"    Processed {total_processed} reviews, "
                    f"matched {matched} for {len(book_reviews)} books..."
                )

            book_gr_id = str(review.get("book_id", ""))
            if book_gr_id not in id_mapping:
                continue

            book_id = id_mapping[book_gr_id]

            # Skip if already have max reviews for this book
            if book_id in book_reviews and len(book_reviews[book_id]) >= max_reviews:
                continue

            review_text = review.get("review_text", "")
            if not review_text:
                continue

            # Clean and filter
            cleaned = clean_review_text(review_text)
            word_count = len(cleaned.split())
            if word_count < 20:
                continue

            rating = review.get("rating", 0)
            n_votes = review.get("n_votes", 0)

            if book_id not in book_reviews:
                book_reviews[book_id] = []

            book_reviews[book_id].append(
                {
                    "text": cleaned,
                    "rating": rating,
                    "n_votes": n_votes,
                    "word_count": word_count,
                }
            )
            matched += 1

    print(
        f"  Collected {matched} reviews for {len(book_reviews)} books "
        f"(from {total_processed} total reviews)"
    )
    return book_reviews


def compute_book_embeddings(session, book_reviews: dict[int, list[dict]], settings) -> int:
    """
    Compute aggregated embeddings per book and store in DB.

    Uses weighted average of review chunk embeddings, where weight = 1 + log(1 + n_votes).
    """
    from sentence_transformers import SentenceTransformer

    min_reviews = settings.MIN_REVIEWS_FOR_EMBEDDING
    model_name = settings.EMBEDDING_MODEL

    print(f"  Loading model: {model_name}...")
    model = SentenceTransformer(model_name)

    # Filter books with enough reviews
    eligible_books = {bid: revs for bid, revs in book_reviews.items() if len(revs) >= min_reviews}
    print(
        f"  {len(eligible_books)} books have >= {min_reviews} reviews "
        f"(skipping {len(book_reviews) - len(eligible_books)} books)"
    )

    # Clear existing embeddings
    session.query(BookReviewEmbedding).delete()
    session.commit()

    embedded_count = 0
    batch_size = 50  # Process 50 books at a time for periodic commits

    book_ids = list(eligible_books.keys())
    for batch_start in range(0, len(book_ids), batch_size):
        batch_book_ids = book_ids[batch_start : batch_start + batch_size]

        for book_id in batch_book_ids:
            reviews = eligible_books[book_id]

            # Collect all chunks with their weights
            all_chunks = []
            all_weights = []

            for review in reviews:
                chunks = chunk_text(review["text"], max_words=150)
                weight = 1.0 + math.log(1.0 + review["n_votes"])
                all_chunks.extend(chunks)
                all_weights.extend([weight] * len(chunks))

            if not all_chunks:
                continue

            # Encode all chunks in one batch
            chunk_embeddings = model.encode(
                all_chunks, batch_size=256, normalize_embeddings=True, show_progress_bar=False
            )

            # Weighted average
            weights = np.array(all_weights, dtype=np.float32)
            weights = weights / weights.sum()  # Normalize weights
            aggregated = np.average(chunk_embeddings, axis=0, weights=weights)

            # L2 normalize
            norm = np.linalg.norm(aggregated)
            if norm > 0:
                aggregated = aggregated / norm

            # Compute stats
            total_words = sum(r["word_count"] for r in reviews)
            ratings = [r["rating"] for r in reviews if r["rating"] > 0]
            avg_rating = sum(ratings) / len(ratings) if ratings else None

            # Store
            embedding_record = BookReviewEmbedding(
                book_id=book_id,
                embedding=aggregated.tolist(),
                review_count=len(reviews),
                total_review_words=total_words,
                avg_review_rating=avg_rating,
            )
            session.add(embedding_record)
            embedded_count += 1

        session.commit()
        print(f"    Embedded {embedded_count}/{len(eligible_books)} books...")

    session.commit()
    print(f"  Stored embeddings for {embedded_count} books")
    return embedded_count


def embed_trope_seeds(session, settings) -> int:
    """Embed all trope seed phrases and store in DB."""
    from sentence_transformers import SentenceTransformer

    model_name = settings.EMBEDDING_MODEL
    print(f"  Loading model: {model_name}...")
    model = SentenceTransformer(model_name)

    # Clear existing seed embeddings
    session.query(TropeSeedEmbedding).delete()
    session.commit()

    seed_count = 0
    for trope_slug, phrases in TROPE_SEEDS.items():
        embeddings = model.encode(phrases, normalize_embeddings=True, show_progress_bar=False)

        for phrase, embedding in zip(phrases, embeddings, strict=True):
            record = TropeSeedEmbedding(
                trope_slug=trope_slug,
                seed_phrase=phrase,
                embedding=embedding.tolist(),
            )
            session.add(record)
            seed_count += 1

    session.commit()
    print(f"  Stored {seed_count} seed phrase embeddings for {len(TROPE_SEEDS)} tropes")
    return seed_count


def compute_trope_scores(session, settings) -> dict:
    """
    Compute cosine similarity between each book embedding and each trope centroid.
    Store results in book_trope_scores table.
    """
    default_threshold = settings.TROPE_SIMILARITY_THRESHOLD

    print("  Computing trope centroids...")
    # Build trope centroids from seed embeddings
    trope_centroids: dict[str, np.ndarray] = {}
    seed_records = session.query(TropeSeedEmbedding).all()

    # Group by trope_slug
    trope_embeddings: dict[str, list[list[float]]] = {}
    for record in seed_records:
        if record.trope_slug not in trope_embeddings:
            trope_embeddings[record.trope_slug] = []
        trope_embeddings[record.trope_slug].append(record.embedding)

    for trope_slug, embeddings in trope_embeddings.items():
        centroid = np.mean(embeddings, axis=0)
        norm = np.linalg.norm(centroid)
        if norm > 0:
            centroid = centroid / norm
        trope_centroids[trope_slug] = centroid

    print(f"  Computed centroids for {len(trope_centroids)} tropes")

    # Clear existing scores
    session.query(BookTropeScore).delete()
    session.commit()

    # Fetch all book embeddings
    book_embeddings = session.query(BookReviewEmbedding).all()
    print(f"  Scoring {len(book_embeddings)} books against {len(trope_centroids)} tropes...")

    total_scores = 0
    auto_tagged_count = 0
    batch_count = 0

    for be in book_embeddings:
        book_emb = np.array(be.embedding, dtype=np.float32)

        for trope_slug, centroid in trope_centroids.items():
            # Cosine similarity (vectors are already normalized)
            similarity = float(np.dot(book_emb, centroid))

            # Determine auto-tag threshold
            threshold = TROPE_THRESHOLD_OVERRIDES.get(trope_slug, default_threshold)
            auto_tagged = similarity >= threshold

            score = BookTropeScore(
                book_id=be.book_id,
                trope_slug=trope_slug,
                similarity_score=round(similarity, 4),
                auto_tagged=auto_tagged,
            )
            session.add(score)
            total_scores += 1
            if auto_tagged:
                auto_tagged_count += 1

        batch_count += 1
        if batch_count % 100 == 0:
            session.commit()
            print(f"    Scored {batch_count}/{len(book_embeddings)} books...")

    session.commit()
    stats = {
        "total_scores": total_scores,
        "auto_tagged": auto_tagged_count,
        "books_scored": len(book_embeddings),
        "tropes_scored": len(trope_centroids),
    }
    print(
        f"  Stored {total_scores} scores, {auto_tagged_count} auto-tagged "
        f"({len(book_embeddings)} books x {len(trope_centroids)} tropes)"
    )
    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Import UCSD Goodreads review embeddings for trope classification"
    )
    parser.add_argument(
        "--skip-download", action="store_true", help="Skip downloading review files"
    )
    parser.add_argument(
        "--step",
        choices=["download", "embeddings", "tropes", "scores", "all"],
        default="all",
        help="Run only a specific pipeline step",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("UCSD Review Embedding Pipeline for Trope Classification")
    print("=" * 60)

    settings = get_settings()

    # Create data directory
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Download review files
    if args.step in ("download", "all") and not args.skip_download:
        print("\n1. Downloading UCSD review files...")
        for name, url in REVIEW_URLS.items():
            filename = url.split("/")[-1]
            dest = DATA_DIR / filename
            if not download_file(url, dest):
                print(f"  Warning: Failed to download {name}")
    else:
        print("\n1. Skipping download step")

    if args.step == "download":
        print("\nDownload complete.")
        return

    # Connect to database
    print("\n2. Connecting to database...")
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        if args.step in ("embeddings", "all"):
            # Step 2: Build ID mapping
            print("\n3. Building Goodreads ID mapping...")
            id_mapping = build_goodreads_id_mapping(session)

            if not id_mapping:
                print("  No books with Goodreads IDs found. Run import_goodreads_dataset.py first.")
                return

            # Step 3: Collect reviews
            print("\n4. Collecting and filtering reviews...")
            book_reviews = collect_reviews(DATA_DIR, id_mapping, settings)

            if not book_reviews:
                print("  No reviews matched. Check that review files are downloaded.")
                return

            # Step 4: Compute book embeddings
            print("\n5. Computing per-book embeddings...")
            compute_book_embeddings(session, book_reviews, settings)

        if args.step in ("tropes", "all"):
            # Step 5: Embed trope seed phrases
            print("\n6. Embedding trope seed phrases...")
            embed_trope_seeds(session, settings)

        if args.step in ("scores", "all"):
            # Step 6: Compute book-trope similarity scores
            print("\n7. Computing book-trope similarity scores...")
            compute_trope_scores(session, settings)

        # Summary
        print("\n" + "=" * 60)
        print("PIPELINE COMPLETE")
        print("=" * 60)

        # Query final counts
        embedding_count = session.query(func.count(BookReviewEmbedding.id)).scalar()
        seed_count = session.query(func.count(TropeSeedEmbedding.id)).scalar()
        score_count = session.query(func.count(BookTropeScore.id)).scalar()
        auto_tagged = (
            session.query(func.count(BookTropeScore.id))
            .filter(BookTropeScore.auto_tagged.is_(True))
            .scalar()
        )

        print(f"  Book embeddings:      {embedding_count}")
        print(f"  Trope seed phrases:   {seed_count}")
        print(f"  Book-trope scores:    {score_count}")
        print(f"  Auto-tagged entries:  {auto_tagged}")

    except Exception as e:
        session.rollback()
        print(f"\nError during pipeline: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
