import datetime
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.database.models import Image, ProcessingResult
from app.schemas.image import ImageRecordResponse, PaginatedHistoryResponse
from app.core.upstream_client import upstream_client
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

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
    Returns the latest single microscopy image record from the local database,
    including any associated processed overlays.
    """
    record = db.query(Image).order_by(Image.id.desc()).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No images have been ingested yet."
        )
    
    # Load associated overlays
    overlays_db = db.query(ProcessingResult).filter(ProcessingResult.image_id == record.image_id).all()
    overlays = {item.process_type: item.processed_image_base64 for item in overlays_db}
    
    # Inject dynamically into transient property parsed by pydantic validator
    record.overlays = overlays
    return record

@router.get("/history", response_model=PaginatedHistoryResponse)
def get_image_history(
    page: int = Query(1, ge=1),
    limit: int = Query(15, ge=1, le=500),
    timeframe: str = Query(None, description="Time slice filters: 10m, 30m, 1h, 1d, custom"),
    start_time: datetime.datetime = Query(None, description="Custom start UTC datetime"),
    end_time: datetime.datetime = Query(None, description="Custom end UTC datetime"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Returns a filtered, paginated list of past records.
    Includes low-res thumbnails and filters by timeframe or custom start/end time.
    """
    query = db.query(Image)
    
    # Apply Timeframe filters (using UTC comparison)
    if timeframe:
        now = datetime.datetime.utcnow()
        if timeframe == "10m":
            start = now - datetime.timedelta(minutes=10)
            query = query.filter(Image.timestamp >= start)
        elif timeframe == "30m":
            start = now - datetime.timedelta(minutes=30)
            query = query.filter(Image.timestamp >= start)
        elif timeframe == "1h":
            start = now - datetime.timedelta(hours=1)
            query = query.filter(Image.timestamp >= start)
        elif timeframe == "1d":
            start = now - datetime.timedelta(days=1)
            query = query.filter(Image.timestamp >= start)
        elif timeframe == "custom":
            if start_time:
                query = query.filter(Image.timestamp >= start_time)
            if end_time:
                query = query.filter(Image.timestamp <= end_time)
                
    total = query.count()
    offset = (page - 1) * limit
    
    # Query records including thumbnail_base64
    records = query.order_by(Image.id.desc()).offset(offset).limit(limit).all()
    
    items = []
    for r in records:
        items.append({
            "id": r.id,
            "image_id": r.image_id,
            "timestamp": r.timestamp,
            "intensity_average": r.intensity_average,
            "focus_score": r.focus_score,
            "classification_label": r.classification_label,
            "thumbnail_base64": r.thumbnail_base64
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
    Fetches full details for a historical record including the base64 raw image
    and all completed transparent processed overlays.
    """
    record = db.query(Image).filter(Image.image_id == image_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image record with ID '{image_id}' not found."
        )
        
    # Load associated overlays
    overlays_db = db.query(ProcessingResult).filter(ProcessingResult.image_id == image_id).all()
    overlays = {item.process_type: item.processed_image_base64 for item in overlays_db}
    
    record.overlays = overlays
    return record
