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
from app.database.models import Image, ProcessingJob, ProcessingResult
from app.services.processor import generate_canny_overlay, generate_otsu_overlay, generate_thumbnail
from app.services.queue_manager import queue_manager

# 1. Config Tests
def test_config():
    assert settings.UPSTREAM_URL is not None
    assert settings.POLLING_INTERVAL == 5

# 2. CV Processor Tests
def test_cv_processor():
    # Create simple raw image with a shape inside
    raw_img = np.ones((100, 100, 3), dtype=np.uint8) * 255
    cv2.rectangle(raw_img, (30, 30), (70, 70), (0, 0, 0), -1)
    
    _, buffer = cv2.imencode('.png', raw_img)
    raw_base64 = base64.b64encode(buffer).decode('utf-8')
    
    # Test Canny transparent overlay
    canny_base64 = generate_canny_overlay(raw_base64)
    assert canny_base64 is not None
    canny_bytes = base64.b64decode(canny_base64)
    canny_arr = np.frombuffer(canny_bytes, np.uint8)
    canny_img = cv2.imdecode(canny_arr, cv2.IMREAD_UNCHANGED) # Load RGBA
    assert canny_img.shape[2] == 4 # 4 channels
    
    # Check green color overlay (B=0, G=255, R=0, A=255)
    green_mask = (canny_img[:, :, 0] == 0) & (canny_img[:, :, 1] == 255) & (canny_img[:, :, 2] == 0) & (canny_img[:, :, 3] == 255)
    assert np.sum(green_mask) > 0
    
    # Test Otsu transparent overlay
    otsu_base64 = generate_otsu_overlay(raw_base64)
    assert otsu_base64 is not None
    otsu_bytes = base64.b64decode(otsu_base64)
    otsu_arr = np.frombuffer(otsu_bytes, np.uint8)
    otsu_img = cv2.imdecode(otsu_arr, cv2.IMREAD_UNCHANGED) # Load RGBA
    assert otsu_img.shape[2] == 4
    
    # Check orange color overlay (B=0, G=100, R=255, A=120)
    orange_mask = (otsu_img[:, :, 0] == 0) & (otsu_img[:, :, 1] == 100) & (otsu_img[:, :, 2] == 255) & (otsu_img[:, :, 3] == 120)
    assert np.sum(orange_mask) > 0

    # Test Thumbnail generation (120x90)
    thumb_base64 = generate_thumbnail(raw_base64, 120, 90)
    assert thumb_base64 is not None
    thumb_bytes = base64.b64decode(thumb_base64)
    thumb_arr = np.frombuffer(thumb_bytes, np.uint8)
    thumb_img = cv2.imdecode(thumb_arr, cv2.IMREAD_COLOR)
    assert thumb_img.shape[0] == 90
    assert thumb_img.shape[1] == 120

# 3. Database DB Insertion Tests
def test_database():
    engine = create_engine("sqlite:///:memory:")
    SessionTesting = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionTesting()
    
    try:
        # Create image
        img = Image(
            image_id="img_123",
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            raw_image_base64="raw_data",
            thumbnail_base64="thumb_data",
            intensity_average=100.5,
            focus_score=0.92,
            classification_label="Healthy",
            histogram_json=json.dumps([0] * 256)
        )
        db.add(img)
        
        # Create job
        job = ProcessingJob(image_id="img_123", status="completed")
        db.add(job)
        
        # Create results
        res = ProcessingResult(image_id="img_123", process_type="canny", processed_image_base64="canny_data")
        db.add(res)
        
        db.commit()
        
        # Query and assert
        q_img = db.query(Image).filter(Image.image_id == "img_123").first()
        assert q_img is not None
        assert q_img.classification_label == "Healthy"
        
        q_job = db.query(ProcessingJob).filter(ProcessingJob.image_id == "img_123").first()
        assert q_job.status == "completed"
        
        q_res = db.query(ProcessingResult).filter(ProcessingResult.image_id == "img_123").all()
        assert len(q_res) == 1
        assert q_res[0].process_type == "canny"
    finally:
        db.close()

# 4. QueueManager Tests
@pytest.mark.asyncio
async def test_queue_manager():
    await queue_manager.push_job("img_abc")
    retrieved = await queue_manager.get_job()
    assert retrieved == "img_abc"
    queue_manager.task_done()
