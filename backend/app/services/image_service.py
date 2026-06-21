import datetime
import logging
from sqlalchemy.orm import Session
from app.database.models import Image, ProcessingResult

logger = logging.getLogger(__name__)

class ImageService:
    """
    Service layer separating database interactions and query calculations from routers.
    """
    @staticmethod
    def get_latest_image(db: Session) -> Image:
        record = db.query(Image).order_by(Image.id.desc()).first()
        if not record:
            return None
        
        # Load and map associated overlays
        overlays_db = db.query(ProcessingResult).filter(ProcessingResult.image_id == record.image_id).all()
        record.overlays = {item.process_type: item.processed_image_base64 for item in overlays_db}
        return record

    @staticmethod
    def get_image_history(
        db: Session,
        page: int,
        limit: int,
        timeframe: str = None,
        start_time: datetime.datetime = None,
        end_time: datetime.datetime = None
    ) -> tuple[list[dict], int]:
        query = db.query(Image)
        
        # Apply Timeframe logic using UTC timezone
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
            
        return items, total

    @staticmethod
    def get_historical_image(db: Session, image_id: str) -> Image:
        record = db.query(Image).filter(Image.image_id == image_id).first()
        if not record:
            return None
            
        # Load and map associated overlays
        overlays_db = db.query(ProcessingResult).filter(ProcessingResult.image_id == image_id).all()
        record.overlays = {item.process_type: item.processed_image_base64 for item in overlays_db}
        return record
