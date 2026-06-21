import asyncio
import datetime
import json
import logging
from app.core.upstream_client import upstream_client
from app.database.session import SessionLocal
from app.database.models import ImageRecord
from app.services.processor import process_microscopy_image

logger = logging.getLogger(__name__)

# Control flags
running = False
worker_task = None

def parse_upstream_timestamp(ts_str: str) -> datetime.datetime:
    """
    Parses ISO-8601 UTC timestamp safely (compatible across Python versions).
    """
    if ts_str.endswith('Z'):
        ts_str = ts_str[:-1] + '+00:00'
    return datetime.datetime.fromisoformat(ts_str)

async def poll_upstream():
    db = SessionLocal()
    try:
        # 1. Fetch image
        img_res = await upstream_client.request("GET", "/api/image")
        if img_res.status_code != 200:
            logger.error(f"Failed to poll upstream image: {img_res.status_code} - {img_res.text}")
            return
        
        img_data = img_res.json()
        image_id = img_data.get("image_id")
        raw_base64 = img_data.get("image_data_base64")
        ts_str = img_data.get("timestamp")
        
        if not image_id or not raw_base64 or not ts_str:
            logger.error(f"Upstream image response missing key data. Keys: {list(img_data.keys())}")
            return
            
        # 2. Check if deduplication criteria is met
        latest_record = db.query(ImageRecord).order_by(ImageRecord.id.desc()).first()
        if latest_record and latest_record.image_id == image_id:
            logger.debug(f"Image {image_id} matches the latest record in database. Discarding ingestion.")
            return
            
        logger.info(f"New image detected: {image_id}. Fetching results from upstream...")
        
        # 3. Fetch results
        res_res = await upstream_client.request("GET", "/api/results")
        if res_res.status_code != 200:
            logger.error(f"Failed to fetch results for {image_id}: {res_res.status_code} - {res_res.text}")
            return
            
        res_data = res_res.json()
        results_image_id = res_data.get("image_id")
        
        if results_image_id != image_id:
            logger.warning(
                f"Mismatch in image_ids: image endpoint={image_id}, results endpoint={results_image_id}. "
                "Aligning on current fetched image."
            )
            
        intensity_avg = res_data.get("intensity_average", 0.0)
        focus_score = res_data.get("focus_score", 0.0)
        classification = res_data.get("classification_label", "Unknown")
        histogram_list = res_data.get("histogram", [])
        
        # 4. Trigger classical CV processing pipeline
        logger.info(f"Processing microscopy image {image_id}...")
        processed_base64 = process_microscopy_image(raw_base64)
        
        # 5. Persist record to local SQLite DB
        record = ImageRecord(
            image_id=image_id,
            timestamp=parse_upstream_timestamp(ts_str),
            raw_image_base64=raw_base64,
            processed_image_base64=processed_base64,
            intensity_average=float(intensity_avg),
            focus_score=float(focus_score),
            classification_label=str(classification),
            histogram_json=json.dumps(histogram_list)
        )
        db.add(record)
        db.commit()
        logger.info(f"Successfully processed and stored new record for image {image_id}")
        
    except Exception as e:
        logger.error(f"Error in poll_upstream cycle: {e}", exc_info=True)
    finally:
        db.close()

async def ingest_worker_loop():
    global running
    running = True
    logger.info("Starting central ingest background loop...")
    
    # Authenticate upstream client before starting poll loop
    await upstream_client.login()
    
    while running:
        try:
            await poll_upstream()
        except Exception as e:
            logger.error(f"Error in ingest worker loop iteration: {e}", exc_info=True)
        await asyncio.sleep(5)
        
    logger.info("Ingest worker loop stopped.")

def start_worker():
    global running, worker_task
    if not running:
        worker_task = asyncio.create_task(ingest_worker_loop())

async def stop_worker():
    global running, worker_task
    running = False
    if worker_task:
        # Wait for task to finish or cancel it
        try:
            await asyncio.wait_for(worker_task, timeout=10.0)
        except asyncio.TimeoutError:
            worker_task.cancel()
        except Exception as e:
            logger.error(f"Exception during worker shutdown: {e}")
        worker_task = None
