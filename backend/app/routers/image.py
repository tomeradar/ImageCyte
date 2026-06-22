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
    logger.info("Image Router: Validating HTTP authorization credentials...")
    user_info = await upstream_client.validate_client_token(token)
    if not user_info:
        logger.warning("Image Router: Access denied. Bearer token is invalid or expired.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    logger.info(f"Image Router: Request authenticated successfully. User: '{user_info.get('username')}'")
    return user_info

@router.get("/image/latest", response_model=ImageRecordResponse)
def get_latest_image(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """
    Returns the latest single microscopy image record.
    Delegates database retrieval logic to ImageService.
    """
    logger.info(f"Image Router: User '{current_user.get('username')}' calling get_latest_image endpoint...")
    record = ImageService.get_latest_image(db)
    if not record:
        logger.warning("Image Router: Request failed. No images found in cache database.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No images have been ingested yet."
        )
    logger.info(f"Image Router: Successfully returned latest image record '{record.image_id}' to user '{current_user.get('username')}'.")
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
    logger.info(
        f"Image Router: User '{current_user.get('username')}' calling get_image_history endpoint: "
        f"page={page}, limit={limit}, timeframe={timeframe}, start_time={start_time}, end_time={end_time}"
    )
    items, total = ImageService.get_image_history(
        db=db,
        page=page,
        limit=limit,
        timeframe=timeframe,
        start_time=start_time,
        end_time=end_time
    )
    logger.info(
        f"Image Router: Returning history listing to user '{current_user.get('username')}'. "
        f"Count on current page: {len(items)}, Total records: {total}."
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
    logger.info(f"Image Router: User '{current_user.get('username')}' calling get_historical_image endpoint for image ID '{image_id}'...")
    record = ImageService.get_historical_image(db, image_id)
    if not record:
        logger.warning(f"Image Router: Request failed. Image record '{image_id}' not found.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image record with ID '{image_id}' not found."
        )
    logger.info(f"Image Router: Successfully returned historical record detail '{image_id}' to user '{current_user.get('username')}'.")
    return record
