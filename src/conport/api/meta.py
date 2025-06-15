from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..services import meta_service
from ..db.database import get_db

router = APIRouter(prefix="/meta", tags=["Meta"])

@router.get("/recent-activity")
def get_recent_activity(db: Session = Depends(get_db)):
    """Get a summary of the most recently created items of several types."""
    return meta_service.get_recent_activity(db)