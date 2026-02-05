"""
Reddit data collector for r/romantasy.

Collects book mentions, recommendation pairs, and sentiment from Reddit
discussions using the official PRAW API.

Usage:
    python -m scripts.reddit_collector --limit 1000
    python -m scripts.reddit_collector --dry-run --limit 100
    python -m scripts.reddit_collector --subreddit romancebooks --limit 500

Environment variables:
    REDDIT_CLIENT_ID: Reddit API client ID
    REDDIT_CLIENT_SECRET: Reddit API client secret
    REDDIT_USER_AGENT: User agent string (default: romantasy-recs/1.0)
"""

import argparse
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterator

import praw
from rapidfuzz import fuzz, process
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.data.reddit_aliases import BOOK_ALIASES, get_canonical_title
from app.models.book import Book
from app.models.reddit import BookRecommendationEdge, BookRedditMetrics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Trope keywords for extraction (normalized)
TROPE_KEYWORDS = {
    "enemies-to-lovers": ["enemies to lovers", "enemies-to-lovers", "etl"],
    "slow-burn": ["slow burn", "slow-burn", "slowburn"],
    "forced-proximity": ["forced proximity", "forced-proximity"],
    "fated-mates": ["fated mates", "fated-mates", "mates"],
    "found-family": ["found family", "found-family"],
    "grumpy-sunshine": ["grumpy sunshine", "grumpy-sunshine", "grumpy/sunshine"],
    "morally-grey": ["morally grey", "morally gray", "morally-grey", "gray mmc", "grey mmc"],
    "touch-her-and-die": ["touch her and die", "thad"],
    "forbidden-love": ["forbidden love", "forbidden-love"],
    "fake-dating": ["fake dating", "fake-dating"],
    "only-one-bed": ["only one bed", "one bed"],
    "who-did-this-to-you": ["who did this to you", "wdtty"],
    "he-falls-first": ["he falls first", "hff"],
    "fae": ["fae", "faerie", "fairy"],
    "dragons": ["dragons", "dragon riders", "dragon-riders"],
    "vampires": ["vampires", "vampire"],
    "witches": ["witches", "witch"],
    "magic-academy": ["magic academy", "academy", "magic school"],
    "why-choose": ["why choose", "whychoose", "reverse harem", "rh"],
}

# Sentiment indicators
POSITIVE_INDICATORS = [
    "loved",
    "love",
    "amazing",
    "incredible",
    "fantastic",
    "highly recommend",
    "recommend",
    "favorite",
    "favourite",
    "obsessed",
    "devoured",
    "couldn't put down",
    "5 stars",
    "five stars",
    "must read",
    "chef's kiss",
    "perfection",
    "beautiful",
    "masterpiece",
    "best book",
    "loved it",
    "so good",
    "one of my favorites",
]

NEGATIVE_INDICATORS = [
    "dnf",
    "did not finish",
    "couldn't finish",
    "hated",
    "hate",
    "disappointing",
    "disappointed",
    "avoid",
    "don't recommend",
    "worst",
    "terrible",
    "boring",
    "couldn't get into",
    "not for me",
    "skip",
    "regret reading",
    "waste of time",
    "overhyped",
    "overrated",
    "1 star",
    "one star",
    "didn't like",
]

# Recommendation patterns
RECOMMENDATION_PATTERNS = [
    r"if you (?:liked?|loved?|enjoyed?) (.+?),? (?:try|read|check out|you(?:'ll| might| would) (?:like|love|enjoy)) (.+?)(?:\.|,|!|\?|$)",
    r"(?:similar to|like|reminds? me of) (.+?),? (?:try|read|check out) (.+?)(?:\.|,|!|\?|$)",
    r"(.+?) (?:fans?|lovers?) (?:will|would|should|might) (?:love|like|enjoy) (.+?)(?:\.|,|!|\?|$)",
    r"(?:loved|liked|enjoyed) (.+?)[,.]? (?:also|and) (.+?)(?:\.|,|!|\?|$)",
]


@dataclass
class BookMention:
    """A book mention extracted from Reddit text."""

    book_id: int
    title: str
    confidence: float
    sentiment: float = 0.0
    tropes: list[str] = field(default_factory=list)


@dataclass
class RecommendationPair:
    """A book recommendation pair (if you liked X, try Y)."""

    source_book_id: int
    target_book_id: int
    context: str


@dataclass
class CollectionStats:
    """Statistics from a collection run."""

    posts_processed: int = 0
    comments_processed: int = 0
    book_mentions: int = 0
    recommendation_pairs: int = 0
    tropes_found: int = 0
    books_updated: int = 0
    edges_created: int = 0


class RedditCollector:
    """
    Collects book recommendation data from Reddit.

    Uses PRAW to fetch posts and comments from romantasy-related subreddits,
    extracts book mentions and recommendation pairs, and stores aggregated
    metrics in the database.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        user_agent: str = "romantasy-recs/1.0",
    ):
        """
        Initialize the Reddit collector.

        Args:
            client_id: Reddit API client ID
            client_secret: Reddit API client secret
            user_agent: User agent string for API requests
        """
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )
        self.book_titles: dict[str, int] = {}  # title -> book_id
        self.book_titles_normalized: dict[str, int] = {}  # normalized title -> book_id
        self._load_book_titles()

    def _load_book_titles(self) -> None:
        """Load book titles from database for fuzzy matching."""
        db = SessionLocal()
        try:
            books = db.query(Book.id, Book.title).all()
            for book_id, title in books:
                self.book_titles[title] = book_id
                self.book_titles_normalized[title.lower()] = book_id

            # Add aliases
            for alias, canonical in BOOK_ALIASES.items():
                if canonical in self.book_titles:
                    self.book_titles_normalized[alias] = self.book_titles[canonical]

            logger.info(f"Loaded {len(self.book_titles)} book titles for matching")
        finally:
            db.close()

    def collect_posts(
        self,
        subreddit: str = "romantasy",
        limit: int = 1000,
        search_keywords: list[str] | None = None,
    ) -> Iterator[praw.models.Submission]:
        """
        Fetch recommendation-related posts from a subreddit.

        Args:
            subreddit: Subreddit name to collect from
            limit: Maximum number of posts to fetch
            search_keywords: Keywords to search for (default: recommendation keywords)

        Yields:
            Reddit submission objects
        """
        if search_keywords is None:
            search_keywords = [
                "recommend",
                "recommendation",
                "looking for",
                "similar to",
                "just finished",
                "what should i read",
                "suggestion",
            ]

        sub = self.reddit.subreddit(subreddit)

        # Fetch from multiple sources for better coverage
        seen_ids = set()

        # Hot posts
        for post in sub.hot(limit=min(limit // 3, 100)):
            if post.id not in seen_ids:
                seen_ids.add(post.id)
                yield post

        # New posts
        for post in sub.new(limit=min(limit // 3, 100)):
            if post.id not in seen_ids:
                seen_ids.add(post.id)
                yield post

        # Search for recommendation posts
        remaining = limit - len(seen_ids)
        if remaining > 0:
            for keyword in search_keywords:
                if len(seen_ids) >= limit:
                    break
                try:
                    for post in sub.search(keyword, limit=remaining // len(search_keywords)):
                        if post.id not in seen_ids:
                            seen_ids.add(post.id)
                            yield post
                except Exception as e:
                    logger.warning(f"Search failed for '{keyword}': {e}")

    def extract_book_mentions(self, text: str) -> list[BookMention]:
        """
        Extract book mentions from text using fuzzy matching.

        Args:
            text: Text to search for book mentions

        Returns:
            List of BookMention objects with confidence scores
        """
        mentions = []
        text_lower = text.lower()

        # First, check for exact alias matches
        for alias, book_id in self.book_titles_normalized.items():
            if alias in text_lower:
                # Check if it's a standalone word/phrase
                pattern = r"\b" + re.escape(alias) + r"\b"
                if re.search(pattern, text_lower):
                    title = next(
                        (t for t, bid in self.book_titles.items() if bid == book_id), alias
                    )
                    mentions.append(
                        BookMention(
                            book_id=book_id,
                            title=title,
                            confidence=1.0,
                        )
                    )

        # Fuzzy match against book titles for longer phrases
        words = text.split()
        for i in range(len(words)):
            for j in range(i + 2, min(i + 10, len(words) + 1)):
                phrase = " ".join(words[i:j])
                if len(phrase) < 5:
                    continue

                # Use rapidfuzz for fuzzy matching
                result = process.extractOne(
                    phrase,
                    self.book_titles.keys(),
                    scorer=fuzz.ratio,
                    score_cutoff=80,
                )

                if result:
                    matched_title, score, _ = result
                    book_id = self.book_titles[matched_title]

                    # Avoid duplicates
                    if not any(m.book_id == book_id for m in mentions):
                        mentions.append(
                            BookMention(
                                book_id=book_id,
                                title=matched_title,
                                confidence=score / 100,
                            )
                        )

        # Add sentiment and tropes to mentions
        for mention in mentions:
            mention.sentiment = self.analyze_sentiment(text, mention.title)
            mention.tropes = self.extract_tropes(text)

        return mentions

    def extract_recommendation_pairs(self, text: str) -> list[RecommendationPair]:
        """
        Extract "if you liked X, try Y" patterns from text.

        Args:
            text: Text to search for recommendation patterns

        Returns:
            List of RecommendationPair objects
        """
        pairs = []
        text_lower = text.lower()

        for pattern in RECOMMENDATION_PATTERNS:
            try:
                matches = re.finditer(pattern, text_lower, re.IGNORECASE)
                for match in matches:
                    source_text = match.group(1).strip()
                    target_text = match.group(2).strip()

                    # Resolve to book IDs
                    source_mentions = self.extract_book_mentions(source_text)
                    target_mentions = self.extract_book_mentions(target_text)

                    if source_mentions and target_mentions:
                        # Take highest confidence matches
                        source = max(source_mentions, key=lambda m: m.confidence)
                        target = max(target_mentions, key=lambda m: m.confidence)

                        if source.book_id != target.book_id:
                            # Anonymize context (remove potential usernames)
                            context = re.sub(r"u/\w+", "[user]", match.group(0))
                            context = context[:200]  # Limit length

                            pairs.append(
                                RecommendationPair(
                                    source_book_id=source.book_id,
                                    target_book_id=target.book_id,
                                    context=context,
                                )
                            )
            except re.error as e:
                logger.warning(f"Regex error with pattern: {e}")

        return pairs

    def extract_tropes(self, text: str) -> list[str]:
        """
        Extract trope mentions from text.

        Args:
            text: Text to search for trope keywords

        Returns:
            List of trope slugs found
        """
        found_tropes = []
        text_lower = text.lower()

        for trope_slug, keywords in TROPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    found_tropes.append(trope_slug)
                    break

        return found_tropes

    def analyze_sentiment(self, text: str, book_title: str) -> float:
        """
        Analyze sentiment for a book mention in context.

        Args:
            text: Full text containing the mention
            book_title: The book title mentioned

        Returns:
            Sentiment score from -1.0 (negative) to 1.0 (positive)
        """
        text_lower = text.lower()
        book_lower = book_title.lower()

        # Find context around book mention
        idx = text_lower.find(book_lower)
        if idx == -1:
            # Try alias
            canonical = get_canonical_title(book_lower)
            if canonical:
                idx = text_lower.find(canonical.lower())

        # Extract surrounding context (100 chars before/after)
        start = max(0, idx - 100)
        end = min(len(text_lower), idx + len(book_title) + 100)
        context = text_lower[start:end] if idx != -1 else text_lower

        # Count positive/negative indicators
        positive_count = sum(1 for ind in POSITIVE_INDICATORS if ind in context)
        negative_count = sum(1 for ind in NEGATIVE_INDICATORS if ind in context)

        if positive_count == 0 and negative_count == 0:
            return 0.0

        # Calculate weighted sentiment
        total = positive_count + negative_count
        sentiment = (positive_count - negative_count) / total

        return max(-1.0, min(1.0, sentiment))

    def process_and_save(
        self,
        db: Session,
        subreddit: str = "romantasy",
        limit: int = 1000,
        dry_run: bool = False,
    ) -> CollectionStats:
        """
        Main entry point - collect from Reddit and save to database.

        Args:
            db: Database session
            subreddit: Subreddit to collect from
            limit: Maximum posts to process
            dry_run: If True, don't save to database

        Returns:
            CollectionStats with run statistics
        """
        stats = CollectionStats()

        # Aggregated data
        book_data: dict[int, dict] = defaultdict(
            lambda: {
                "mention_count": 0,
                "recommendation_count": 0,
                "warning_count": 0,
                "sentiment_scores": [],
                "tropes": defaultdict(int),
                "first_seen": None,
            }
        )
        edge_data: dict[tuple[int, int], dict] = defaultdict(
            lambda: {
                "mention_count": 0,
                "contexts": [],
            }
        )

        logger.info(f"Starting collection from r/{subreddit} (limit={limit}, dry_run={dry_run})")

        for post in self.collect_posts(subreddit=subreddit, limit=limit):
            stats.posts_processed += 1

            # Process post title and selftext
            full_text = f"{post.title} {post.selftext or ''}"
            self._process_text(full_text, post.created_utc, book_data, edge_data, stats)

            # Process comments (limited depth)
            try:
                post.comments.replace_more(limit=0)
                for comment in post.comments.list()[:50]:  # Limit comments per post
                    stats.comments_processed += 1
                    self._process_text(
                        comment.body,
                        comment.created_utc,
                        book_data,
                        edge_data,
                        stats,
                    )
            except Exception as e:
                logger.warning(f"Error processing comments for post {post.id}: {e}")

            if stats.posts_processed % 100 == 0:
                logger.info(f"Processed {stats.posts_processed} posts...")

        logger.info(
            f"Collection complete: {stats.posts_processed} posts, "
            f"{stats.comments_processed} comments, "
            f"{stats.book_mentions} mentions, "
            f"{stats.recommendation_pairs} pairs"
        )

        if dry_run:
            self._print_dry_run_summary(book_data, edge_data)
        else:
            self._save_to_database(db, book_data, edge_data, stats)

        return stats

    def _process_text(
        self,
        text: str,
        created_utc: float,
        book_data: dict,
        edge_data: dict,
        stats: CollectionStats,
    ) -> None:
        """Process a piece of text and update aggregated data."""
        if not text:
            return

        post_date = datetime.fromtimestamp(created_utc).date()

        # Extract book mentions
        mentions = self.extract_book_mentions(text)
        for mention in mentions:
            stats.book_mentions += 1
            data = book_data[mention.book_id]
            data["mention_count"] += 1

            if mention.sentiment > 0.3:
                data["recommendation_count"] += 1
            elif mention.sentiment < -0.3:
                data["warning_count"] += 1

            data["sentiment_scores"].append(mention.sentiment)

            for trope in mention.tropes:
                data["tropes"][trope] += 1
                stats.tropes_found += 1

            if data["first_seen"] is None or post_date < data["first_seen"]:
                data["first_seen"] = post_date

        # Extract recommendation pairs
        pairs = self.extract_recommendation_pairs(text)
        for pair in pairs:
            stats.recommendation_pairs += 1
            key = (pair.source_book_id, pair.target_book_id)
            edge_data[key]["mention_count"] += 1
            if pair.context and len(edge_data[key]["contexts"]) < 3:
                edge_data[key]["contexts"].append(pair.context)

    def _print_dry_run_summary(self, book_data: dict, edge_data: dict) -> None:
        """Print summary for dry run mode."""
        logger.info("\n=== DRY RUN SUMMARY ===")

        # Top mentioned books
        logger.info("\nTop 20 mentioned books:")
        sorted_books = sorted(
            book_data.items(),
            key=lambda x: x[1]["mention_count"],
            reverse=True,
        )[:20]

        for book_id, data in sorted_books:
            title = next(
                (t for t, bid in self.book_titles.items() if bid == book_id), f"Book {book_id}"
            )
            avg_sentiment = (
                sum(data["sentiment_scores"]) / len(data["sentiment_scores"])
                if data["sentiment_scores"]
                else 0
            )
            logger.info(
                f"  {title}: {data['mention_count']} mentions, " f"sentiment: {avg_sentiment:.2f}"
            )

        # Top recommendation pairs
        logger.info("\nTop 10 recommendation pairs:")
        sorted_edges = sorted(
            edge_data.items(),
            key=lambda x: x[1]["mention_count"],
            reverse=True,
        )[:10]

        for (source_id, target_id), data in sorted_edges:
            source = next(
                (t for t, bid in self.book_titles.items() if bid == source_id), f"Book {source_id}"
            )
            target = next(
                (t for t, bid in self.book_titles.items() if bid == target_id), f"Book {target_id}"
            )
            logger.info(f"  {source} -> {target}: {data['mention_count']} mentions")

    def _save_to_database(
        self,
        db: Session,
        book_data: dict,
        edge_data: dict,
        stats: CollectionStats,
    ) -> None:
        """Save aggregated data to database."""
        logger.info("Saving to database...")

        # Save book metrics
        for book_id, data in book_data.items():
            metrics = (
                db.query(BookRedditMetrics).filter(BookRedditMetrics.book_id == book_id).first()
            )

            avg_sentiment = (
                sum(data["sentiment_scores"]) / len(data["sentiment_scores"])
                if data["sentiment_scores"]
                else 0.0
            )

            if metrics:
                # Update existing
                metrics.mention_count += data["mention_count"]
                metrics.recommendation_count += data["recommendation_count"]
                metrics.warning_count += data["warning_count"]
                metrics.sentiment_score = (metrics.sentiment_score + avg_sentiment) / 2
                # Merge tropes
                existing_tropes = metrics.tropes_mentioned or {}
                for trope, count in data["tropes"].items():
                    existing_tropes[trope] = existing_tropes.get(trope, 0) + count
                metrics.tropes_mentioned = existing_tropes
                metrics.last_updated = datetime.utcnow()
            else:
                # Create new
                metrics = BookRedditMetrics(
                    book_id=book_id,
                    mention_count=data["mention_count"],
                    recommendation_count=data["recommendation_count"],
                    warning_count=data["warning_count"],
                    sentiment_score=avg_sentiment,
                    tropes_mentioned=dict(data["tropes"]),
                    first_seen=data["first_seen"],
                )
                db.add(metrics)
                stats.books_updated += 1

        # Save recommendation edges
        for (source_id, target_id), data in edge_data.items():
            edge = (
                db.query(BookRecommendationEdge)
                .filter(
                    BookRecommendationEdge.source_book_id == source_id,
                    BookRecommendationEdge.target_book_id == target_id,
                )
                .first()
            )

            if edge:
                edge.mention_count += data["mention_count"]
                edge.updated_at = datetime.utcnow()
            else:
                edge = BookRecommendationEdge(
                    source_book_id=source_id,
                    target_book_id=target_id,
                    mention_count=data["mention_count"],
                    sample_context=data["contexts"][0] if data["contexts"] else None,
                )
                db.add(edge)
                stats.edges_created += 1

        db.commit()
        logger.info(
            f"Saved {stats.books_updated} book metrics, "
            f"{stats.edges_created} recommendation edges"
        )


def main():
    """Main entry point for the collector script."""
    parser = argparse.ArgumentParser(
        description="Collect book data from Reddit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--subreddit",
        default="romantasy",
        help="Subreddit to collect from (default: romantasy)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum posts to process (default: 100)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't save to database, just print results",
    )
    args = parser.parse_args()

    settings = get_settings()

    # Check for credentials
    if not settings.REDDIT_CLIENT_ID or not settings.REDDIT_CLIENT_SECRET:
        logger.error(
            "Reddit API credentials not configured. "
            "Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET environment variables."
        )
        return 1

    collector = RedditCollector(
        client_id=settings.REDDIT_CLIENT_ID,
        client_secret=settings.REDDIT_CLIENT_SECRET,
        user_agent=settings.REDDIT_USER_AGENT,
    )

    db = SessionLocal()
    try:
        stats = collector.process_and_save(
            db=db,
            subreddit=args.subreddit,
            limit=args.limit,
            dry_run=args.dry_run,
        )

        logger.info("\n=== FINAL STATISTICS ===")
        logger.info(f"Posts processed: {stats.posts_processed}")
        logger.info(f"Comments processed: {stats.comments_processed}")
        logger.info(f"Book mentions found: {stats.book_mentions}")
        logger.info(f"Recommendation pairs found: {stats.recommendation_pairs}")
        logger.info(f"Trope mentions found: {stats.tropes_found}")
        if not args.dry_run:
            logger.info(f"Books updated: {stats.books_updated}")
            logger.info(f"Edges created: {stats.edges_created}")

        return 0

    except Exception as e:
        logger.error(f"Collection failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    exit(main())
