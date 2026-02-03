from app.services import (
    auth_service,
    book_service,
    import_service,
    recommendation_service,
    user_service,
)
from app.services.account_service import (
    anonymize_user_data,
    delete_user_account,
    export_user_data,
    update_privacy_settings,
)
from app.services.book_dedup import BookDeduplicator, deduplicate_book
from app.services.classification import (
    ClassificationResult,
    RomantasyClassifier,
    classify_book,
    get_classification_stats,
    reclassify_all_books,
)
from app.services.csv_parser import GoodreadsCSVParser, ParsedBook, parse_goodreads_csv
from app.services.external_apis import (
    BookMetadata,
    GoogleBooksClient,
    MetadataEnricher,
    OpenLibraryClient,
)
from app.services.onboarding_service import (
    get_onboarding_status,
    get_starter_books,
    get_trope_options,
    rate_starter_books,
    save_preferences,
)
from app.services.password_reset import (
    create_password_reset_token,
    request_password_reset,
    reset_password,
    verify_password_reset_token,
)
from app.services.similarity import (
    BatchSimilarityComputer,
    SimilarityComputer,
    SimilarityResult,
    compute_all_similarities,
    compute_user_similarity,
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
