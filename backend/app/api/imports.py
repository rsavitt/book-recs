from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.imports import ImportResult, ImportStatus
from app.services import auth_service, import_service

router = APIRouter()

# Maximum file size for CSV uploads (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024


@router.post("/library", response_model=ImportStatus)
async def import_library_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Library export CSV (Goodreads or StoryGraph)"),
    current_user=Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Import reading history from a library CSV export.

    Supports both Goodreads and StoryGraph exports. The format is automatically detected.

    **Goodreads:**
    1. Go to goodreads.com/review/import
    2. Click "Export Library"
    3. Download the CSV file
    4. Upload it here

    **StoryGraph:**
    1. Go to app.thestorygraph.com/export
    2. Click "Export"
    3. Download the CSV file
    4. Upload it here
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="File must be a CSV file",
        )

    # Read file content with size limit
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB",
        )

    # Basic validation that content is text (not binary)
    try:
        content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            content.decode("utf-8-sig")
        except UnicodeDecodeError:
            # Don't allow Latin-1 fallback for initial validation
            # This prevents binary files from being processed
            raise HTTPException(
                status_code=400,
                detail="File does not appear to be a valid text CSV file",
            ) from None

    # Validate and detect source
    try:
        import_id = import_service.validate_and_create_import(db, current_user.id, content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Process in background
    background_tasks.add_task(
        import_service.process_import,
        import_id=import_id,
        user_id=current_user.id,
        content=content,
    )

    # Get the detected source from import status
    status = import_service._import_status.get(import_id, {})
    source = status.get("source", "unknown")

    return ImportStatus(
        import_id=import_id,
        status="processing",
        message=f"Import started ({source} format detected).",
        source=source,
    )


@router.post("/goodreads", response_model=ImportStatus)
async def import_goodreads_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Goodreads library export CSV"),
    current_user=Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Import reading history from Goodreads CSV export.

    **Note:** This endpoint is an alias for `/library` and supports both Goodreads
    and StoryGraph formats. Use `/library` for new integrations.

    To get your Goodreads export:
    1. Go to goodreads.com/review/import
    2. Click "Export Library"
    3. Download the CSV file
    4. Upload it here
    """
    # Delegate to the unified endpoint
    return await import_library_csv(background_tasks, file, current_user, db)


@router.get("/status/{import_id}", response_model=ImportStatus)
async def get_import_status(
    import_id: str,
    current_user=Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
):
    """Check the status of an import job."""
    status = import_service.get_import_status(db, import_id, current_user.id)
    if not status:
        raise HTTPException(status_code=404, detail="Import not found")
    return status


@router.get("/history", response_model=list[ImportResult])
async def get_import_history(
    current_user=Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
    limit: int = 10,
):
    """Get user's import history."""
    return import_service.get_import_history(db, current_user.id, limit)
