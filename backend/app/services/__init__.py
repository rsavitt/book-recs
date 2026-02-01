from app.services import auth_service
from app.services import user_service
from app.services import book_service
from app.services import import_service
from app.services import recommendation_service
from app.services.csv_parser import GoodreadsCSVParser, ParsedBook, parse_goodreads_csv
from app.services.book_dedup import BookDeduplicator, deduplicate_book
from app.services.external_apis import (
    OpenLibraryClient,
    GoogleBooksClient,
    MetadataEnricher,
    BookMetadata,
)
from app.services.classification import (
    RomantasyClassifier,
    ClassificationResult,
    classify_book,
    reclassify_all_books,
    get_classification_stats,
)
from app.services.similarity import (
    SimilarityComputer,
    BatchSimilarityComputer,
    SimilarityResult,
    compute_user_similarity,
    compute_all_similarities,
)
from app.services.password_reset import (
    create_password_reset_token,
    verify_password_reset_token,
    reset_password,
    request_password_reset,
)
from app.services.account_service import (
    export_user_data,
    delete_user_account,
    anonymize_user_data,
    update_privacy_settings,
)
from app.services.onboarding_service import (
    get_onboarding_status,
    save_preferences,
    get_starter_books,
    rate_starter_books,
    get_trope_options,
)

__all__ = [
    "auth_service",
    "user_service",
    "book_service",
    "import_service",
    "recommendation_service",
    # CSV parsing
    "GoodreadsCSVParser",
    "ParsedBook",
    "parse_goodreads_csv",
    # Deduplication
    "BookDeduplicator",
    "deduplicate_book",
    # External APIs
    "OpenLibraryClient",
    "GoogleBooksClient",
    "MetadataEnricher",
    "BookMetadata",
    # Classification
    "RomantasyClassifier",
    "ClassificationResult",
    "classify_book",
    "reclassify_all_books",
    "get_classification_stats",
    # Similarity
    "SimilarityComputer",
    "BatchSimilarityComputer",
    "SimilarityResult",
    "compute_user_similarity",
    "compute_all_similarities",
    # Password Reset
    "create_password_reset_token",
    "verify_password_reset_token",
    "reset_password",
    "request_password_reset",
    # Account Management
    "export_user_data",
    "delete_user_account",
    "anonymize_user_data",
    "update_privacy_settings",
    # Onboarding
    "get_onboarding_status",
    "save_preferences",
    "get_starter_books",
    "rate_starter_books",
    "get_trope_options",
]
