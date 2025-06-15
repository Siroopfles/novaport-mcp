from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pathlib import Path
from ..services import io_service
from ..db.database import get_db
from ..core.config import decode_workspace_id

router = APIRouter(prefix="/workspaces/{workspace_id_b64}/io", tags=["Import/Export"])

@router.post("/export")
def export_data(workspace_id_b64: str, export_dir: str = "conport_export", db: Session = Depends(get_db)):
    """Export all ConPort data for a workspace to a local markdown directory."""
    try:
        workspace_id = decode_workspace_id(workspace_id_b64)
        output_dir = Path(workspace_id) / export_dir
        return io_service.export_to_markdown(db, output_dir)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Export failed: {e}")

@router.post("/import")
def import_data(workspace_id_b64: str, import_dir: str = "conport_export", db: Session = Depends(get_db)):
    """Import data from a local markdown directory into a workspace."""
    try:
        workspace_id = decode_workspace_id(workspace_id_b64)
        input_dir = Path(workspace_id) / import_dir
        return io_service.import_from_markdown(db, workspace_id, input_dir)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Import failed: {e}")