from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pathlib import Path
from ..services import io_service
from ..db.database import get_db

router = APIRouter(prefix="/io", tags=["Import/Export"])

@router.post("/export")
def export_data(export_dir: str = "conport_export", db: Session = Depends(get_db)):
    """Export all ConPort data to a local markdown directory."""
    try:
        return io_service.export_to_markdown(db, Path(export_dir))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Export failed: {e}")


@router.post("/import")
def import_data(import_dir: str = "conport_export", db: Session = Depends(get_db)):
    """Import data from a local markdown directory. (Simplified implementation)"""
    try:
        return io_service.import_from_markdown(db, Path(import_dir))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Import failed: {e}")