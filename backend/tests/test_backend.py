import base64
import json
import datetime
import numpy as np
# pyrefly: ignore [missing-import]
import cv2
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.database.session import Base
from app.database.models import Image, ProcessingJob, ProcessingResult
from app.services.processor import cv_processor_service
from app.services.image_service import ImageService
from app.services.queue_manager import queue_manager

# 1. Config Tests
def test_config():
    assert settings.UPSTREAM_URL is not None
    assert settings.POLLING_INTERVAL == 5

# 2. CV Processor Tests
def test_cv_processor():
    raw_img = np.ones((100, 100, 3), dtype=np.uint8) * 255
    cv2.rectangle(raw_img, (30, 30), (70, 70), (0, 0, 0), -1)
    
    _, buffer = cv2.imencode('.png', raw_img)
    raw_base64 = base64.b64encode(buffer).decode('utf-8')
    
    # Test Canny strategy
    canny_base64 = cv_processor_service.process_image(raw_base64, "canny")
    assert canny_base64 is not None
    canny_bytes = base64.b64decode(canny_base64)
    canny_arr = np.frombuffer(canny_bytes, np.uint8)
    canny_img = cv2.imdecode(canny_arr, cv2.IMREAD_UNCHANGED)
    assert canny_img.shape[2] == 4
    green_mask = (canny_img[:, :, 0] == 0) & (canny_img[:, :, 1] == 255) & (canny_img[:, :, 2] == 0) & (canny_img[:, :, 3] == 255)
    assert np.sum(green_mask) > 0
    
    # Test Otsu strategy
    otsu_base64 = cv_processor_service.process_image(raw_base64, "otsu")
    assert otsu_base64 is not None
    otsu_bytes = base64.b64decode(otsu_base64)
    otsu_arr = np.frombuffer(otsu_bytes, np.uint8)
    otsu_img = cv2.imdecode(otsu_arr, cv2.IMREAD_UNCHANGED)
    assert otsu_img.shape[2] == 4
    orange_mask = (otsu_img[:, :, 0] == 0) & (otsu_img[:, :, 1] == 100) & (otsu_img[:, :, 2] == 255) & (otsu_img[:, :, 3] == 120)
    assert np.sum(orange_mask) > 0

    # Test Thumbnail strategy
    thumb_base64 = cv_processor_service.generate_thumbnail(raw_base64, 120, 90)
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
    finally:
        db.close()

# 4. ImageService Integration Tests
def test_image_service():
    engine = create_engine("sqlite:///:memory:")
    SessionTesting = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionTesting()
    
    try:
        img = Image(
            image_id="img_service_test",
            timestamp=datetime.datetime.utcnow(),
            raw_image_base64="raw_data",
            thumbnail_base64="thumb_data",
            intensity_average=120.0,
            focus_score=0.95,
            classification_label="Healthy",
            histogram_json=json.dumps([0] * 256)
        )
        db.add(img)
        
        res = ProcessingResult(
            image_id="img_service_test",
            process_type="canny",
            processed_image_base64="canny_overlay_data"
        )
        db.add(res)
        db.commit()

        # Test latest image retrieval
        latest = ImageService.get_latest_image(db)
        assert latest is not None
        assert latest.image_id == "img_service_test"
        assert latest.overlays["canny"] == "canny_overlay_data"

        # Test history retrieval
        items, total = ImageService.get_image_history(db, page=1, limit=10)
        assert total == 1
        assert items[0]["image_id"] == "img_service_test"
        assert items[0]["thumbnail_base64"] == "thumb_data"

        # Test historical details retrieval
        detail = ImageService.get_historical_image(db, "img_service_test")
        assert detail is not None
        assert detail.overlays["canny"] == "canny_overlay_data"
    finally:
        db.close()
# 5. QueueManager Tests
@pytest.mark.asyncio
async def test_queue_manager():
    await queue_manager.push_job("img_abc")
    retrieved = await queue_manager.get_job()
    assert retrieved == "img_abc"
    queue_manager.task_done()

# 6. CV Error Decorator and Fallback Tests
from app.core.exceptions import (
    AppException,
    ErrorCode,
    ImageProcessingError,
    ImageDecodingError,
    handle_cv_errors,
    log_managed_error
)

def test_cv_errors_decorator_without_fallback():
    @handle_cv_errors()
    def failing_function(data):
        raise ValueError("Failed to decode image BGR buffer.")
        
    with pytest.raises(ImageDecodingError) as exc_info:
        failing_function("some_base64_data")
    assert "Failed to decode image" in str(exc_info.value)
    assert exc_info.value.error_code == ErrorCode.IMAGE_DECODING
    assert exc_info.value.details["arg_0"]["length"] == len("some_base64_data")

def test_generate_thumbnail_corrupt_fallback():
    # Calling generate_thumbnail with corrupt/invalid base64 input should NOT crash
    # Instead, it should trigger fallback and return the valid placeholder base64
    corrupt_input = "invalid_base64_data_!!"
    fallback_result = cv_processor_service.generate_thumbnail(corrupt_input)
    assert fallback_result is not None
    # Verify that it decodes to a valid image
    result_bytes = base64.b64decode(fallback_result)
    result_arr = np.frombuffer(result_bytes, np.uint8)
    result_img = cv2.imdecode(result_arr, cv2.IMREAD_COLOR)
    assert result_img is not None
    assert result_img.shape[0] == 90
    assert result_img.shape[1] == 120

def test_log_managed_error(caplog):
    import logging
    with caplog.at_level(logging.ERROR):
        exc = ImageDecodingError("Corrupted buffer input test", {"arg_0": "test"})
        log_managed_error(exc)
        assert len(caplog.records) == 1
        assert "[MANAGED_ERROR]" in caplog.text
        assert "ERR_IMAGE_DECODING" in caplog.text
        assert "Corrupted buffer input test" in caplog.text

