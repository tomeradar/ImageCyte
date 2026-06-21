import base64
import json
import datetime
import numpy as np
import cv2
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.database.session import Base
from app.database.models import ImageRecord
from app.services.processor import process_microscopy_image

# 1. Config Tests
def test_config():
    assert settings.UPSTREAM_URL is not None
    assert settings.POLLING_INTERVAL == 5

# 2. CV Processor Tests
def test_cv_processor():
    # Create a simple raw white image (100x100 pixels) with a dark square in the middle to detect edges
    raw_img = np.ones((100, 100, 3), dtype=np.uint8) * 255
    cv2.rectangle(raw_img, (30, 30), (70, 70), (0, 0, 0), -1) # Draw black square
    
    _, buffer = cv2.imencode('.png', raw_img)
    raw_base64 = base64.b64encode(buffer).decode('utf-8')
    
    # Process
    processed_base64 = process_microscopy_image(raw_base64)
    assert processed_base64 is not None
    
    # Decode and check if green color is present (edges should be green)
    proc_bytes = base64.b64decode(processed_base64)
    proc_arr = np.frombuffer(proc_bytes, np.uint8)
    proc_img = cv2.imdecode(proc_arr, cv2.IMREAD_COLOR)
    
    assert proc_img is not None
    # We should have some green pixels [0, 255, 0] in BGR
    # Let's count green pixels
    green_mask = (proc_img[:, :, 0] == 0) & (proc_img[:, :, 1] == 255) & (proc_img[:, :, 2] == 0)
    assert np.sum(green_mask) > 0

# 3. Database DB Insertion Tests
def test_database():
    engine = create_engine("sqlite:///:memory:")
    SessionTesting = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    db = SessionTesting()
    
    try:
        # Create record
        record = ImageRecord(
            image_id="test_img_001",
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            raw_image_base64="raw_data",
            processed_image_base64="proc_data",
            intensity_average=100.5,
            focus_score=0.92,
            classification_label="Healthy",
            histogram_json=json.dumps([0] * 256)
        )
        db.add(record)
        db.commit()
        
        # Query record
        query_record = db.query(ImageRecord).filter(ImageRecord.image_id == "test_img_001").first()
        assert query_record is not None
        assert query_record.classification_label == "Healthy"
        assert len(json.loads(query_record.histogram_json)) == 256
    finally:
        db.close()
