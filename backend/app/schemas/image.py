from datetime import datetime
import json
from pydantic import BaseModel, model_validator
from typing import List

class ImageRecordResponse(BaseModel):
    id: int
    image_id: str
    timestamp: datetime
    raw_image_base64: str
    processed_image_base64: str
    intensity_average: float
    focus_score: float
    classification_label: str
    histogram: List[int]

    class Config:
        from_attributes = True

    @model_validator(mode='before')
    @classmethod
    def parse_histogram(cls, data):
        # Check if the data is a SQLAlchemy object
        if not isinstance(data, dict):
            histogram_json = getattr(data, 'histogram_json', '[]')
            try:
                histogram = json.loads(histogram_json)
            except Exception:
                histogram = []
            
            return {
                "id": getattr(data, 'id'),
                "image_id": getattr(data, 'image_id'),
                "timestamp": getattr(data, 'timestamp'),
                "raw_image_base64": getattr(data, 'raw_image_base64'),
                "processed_image_base64": getattr(data, 'processed_image_base64'),
                "intensity_average": getattr(data, 'intensity_average'),
                "focus_score": getattr(data, 'focus_score'),
                "classification_label": getattr(data, 'classification_label'),
                "histogram": histogram
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

    class Config:
        from_attributes = True

class PaginatedHistoryResponse(BaseModel):
    items: List[HistoryItem]
    total: int
    page: int
    limit: int
