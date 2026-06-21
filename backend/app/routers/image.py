import datetime
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.services.image_service import ImageService
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
    Returns the latest single microscopy image record.
    Delegates database retrieval logic to ImageService.
    """
    record = ImageService.get_latest_image(db)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No images have been ingested yet."
        )
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
    Delegates database queries and calculations to ImageService.
    """
    items, total = ImageService.get_image_history(
        db=db,
        page=page,
        limit=limit,
        timeframe=timeframe,
        start_time=start_time,
        end_time=end_time
    )
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
    Fetches full details for a historical record.
    Delegates queries and transparent overlay mappings to ImageService.
    """
    record = ImageService.get_historical_image(db, image_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image record with ID '{image_id}' not found."
        )
    return record
