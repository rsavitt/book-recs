from datetime import datetime
from pydantic import BaseModel


class ImportStatus(BaseModel):
    import_id: str
    status: str  # pending, processing, completed, failed
    message: str | None = None
    progress: float | None = None  # 0-100
    books_processed: int | None = None
    books_total: int | None = None
    errors: list[str] | None = None


class ImportResult(BaseModel):
    import_id: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    books_imported: int
    books_skipped: int
    new_books_added: int  # Books not previously in our catalog
    errors: list[str]
