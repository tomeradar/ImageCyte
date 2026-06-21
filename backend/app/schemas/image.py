from datetime import datetime
import json
from pydantic import BaseModel, Field, model_validator
from typing import List, Dict

class ImageRecordResponse(BaseModel):
    id: int
    image_id: str
    timestamp: datetime
    raw_image_base64: str
    intensity_average: float
    focus_score: float
    classification_label: str
    histogram: List[int]
    overlays: Dict[str, str] = Field(default_factory=dict)

    class Config:
        from_attributes = True

    @model_validator(mode='before')
    @classmethod
    def parse_histogram(cls, data):
        # Handle SQLAlchemy model conversions
        if not isinstance(data, dict):
            histogram_json = getattr(data, 'histogram_json', '[]')
            try:
                histogram = json.loads(histogram_json)
            except Exception:
                histogram = []
            
            # Map attributes
            return {
                "id": getattr(data, 'id'),
                "image_id": getattr(data, 'image_id'),
                "timestamp": getattr(data, 'timestamp'),
                "raw_image_base64": getattr(data, 'raw_image_base64'),
                "intensity_average": getattr(data, 'intensity_average'),
                "focus_score": getattr(data, 'focus_score'),
                "classification_label": getattr(data, 'classification_label'),
                "histogram": histogram,
                "overlays": getattr(data, 'overlays', {})
            }
        else:
            if 'histogram_json' in data and 'histogram' not in data:
                try:
                    data['histogram'] = json.loads(data['histogram_json'])
                except Exception:
                    data['histogram'] = []
            return data

class HistoryItem(BaseModel):
    id: int
    image_id: str
    timestamp: datetime
    intensity_average: float
    focus_score: float
    classification_label: str
    thumbnail_base64: str

    class Config:
        from_attributes = True

class PaginatedHistoryResponse(BaseModel):
    items: List[HistoryItem]
    total: int
    page: int
    limit: int
