from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.database.models import ImageRecord
from app.schemas.image import ImageRecordResponse, PaginatedHistoryResponse
from app.core.upstream_client import upstream_client
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter()
security_scheme = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)):
    token = credentials.credentials
    user_info = await upstream_client.validate_client_token(token)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_info

@router.get("/image/latest", response_model=ImageRecordResponse)
def get_latest_image(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """
    Returns the latest single microscopy image record from the local database.
    """
    record = db.query(ImageRecord).order_by(ImageRecord.id.desc()).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No images have been ingested yet."
        )
    return record

@router.get("/history", response_model=PaginatedHistoryResponse)
def get_image_history(
    page: int = Query(1, ge=1),
    limit: int = Query(15, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Returns a paginated list of past records.
    Optimized to exclude heavy base64 image strings to keep the listing fast.
    """
    offset = (page - 1) * limit
    total = db.query(ImageRecord).count()
    
    # Query only the fields required for the history sidebar list
    records = db.query(
        ImageRecord.id,
        ImageRecord.image_id,
        ImageRecord.timestamp,
        ImageRecord.intensity_average,
        ImageRecord.focus_score,
        ImageRecord.classification_label
    ).order_by(ImageRecord.id.desc()).offset(offset).limit(limit).all()
    
    # Map raw SQLAlchemy tuples into dictionaries matching the HistoryItem schema
    items = []
    for r in records:
        items.append({
            "id": r.id,
            "image_id": r.image_id,
            "timestamp": r.timestamp,
            "intensity_average": r.intensity_average,
            "focus_score": r.focus_score,
            "classification_label": r.classification_label
        })
        
    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit
    }

@router.get("/history/{image_id}", response_model=ImageRecordResponse)
def get_historical_image(
    image_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Fetches full details for a historical record including the base64 raw and processed images.
    """
    record = db.query(ImageRecord).filter(ImageRecord.image_id == image_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image record with ID '{image_id}' not found."
        )
    return record
