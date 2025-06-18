from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..services import meta_service

router = APIRouter(prefix="/workspaces/{workspace_id_b64}/meta", tags=["Meta"])


@router.get("/recent-activity")
def get_recent_activity(
    workspace_id_b64: str,
    db: Session = Depends(get_db),
    since: Optional[str] = None,
    hours_ago: Optional[int] = None
):
    """Get a summary of the most recently created items of several types."""
    parsed_since = None

    if since is not None:
        try:
            # Parse ISO format timestamp (YYYY-MM-DDTHH:MM:SS)
            parsed_since = datetime.fromisoformat(
                since.replace('Z', '+00:00')
            )
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid timestamp format. Expected ISO format "
                    f"(YYYY-MM-DDTHH:MM:SS): {str(e)}"
                )
            )
    elif hours_ago is not None:
        if hours_ago < 0:
            raise HTTPException(
                status_code=400,
                detail="hours_ago must be a non-negative integer"
            )
        parsed_since = datetime.utcnow() - timedelta(hours=hours_ago)

    return meta_service.get_recent_activity(db, since=parsed_since)
