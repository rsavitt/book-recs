from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.imports import ImportStatus, ImportResult
from app.services import auth_service, import_service

router = APIRouter()


@router.post("/goodreads", response_model=ImportStatus)
async def import_goodreads_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Goodreads library export CSV"),
    current_user=Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Import reading history from Goodreads CSV export.

    To get your export:
    1. Go to goodreads.com/review/import
    2. Click "Export Library"
    3. Download the CSV file
    4. Upload it here
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="File must be a CSV file",
        )

    # Read file content
    content = await file.read()

    # Validate it's a Goodreads export
    try:
        import_id = import_service.validate_and_create_import(db, current_user.id, content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Process in background
    background_tasks.add_task(
        import_service.process_import,
        import_id=import_id,
        user_id=current_user.id,
        content=content,
    )

    return ImportStatus(
        import_id=import_id,
        status="processing",
        message="Import started. This may take a few minutes.",
    )


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
