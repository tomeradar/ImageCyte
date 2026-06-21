import asyncio
import datetime
import json
import logging
from app.core.upstream_client import upstream_client
from app.database.session import SessionLocal
from app.database.models import Image, ProcessingJob, ProcessingResult
from app.services.processor import generate_canny_overlay, generate_otsu_overlay, generate_thumbnail
from app.services.queue_manager import queue_manager

logger = logging.getLogger(__name__)

# Control flags
running = False
worker_task = None
consumer_task = None

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
        # 1. Fetch image from upstream
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
        latest_record = db.query(Image).order_by(Image.id.desc()).first()
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
        
        # Generate low-res thumbnail immediately for fast scrubbing (quick resize)
        thumbnail_base64 = generate_thumbnail(raw_base64)

        # 4. Persist core metadata and raw image to local SQLite DB
        record = Image(
            image_id=image_id,
            timestamp=parse_upstream_timestamp(ts_str),
            raw_image_base64=raw_base64,
            thumbnail_base64=thumbnail_base64,
            intensity_average=float(intensity_avg),
            focus_score=float(focus_score),
            classification_label=str(classification),
            histogram_json=json.dumps(histogram_list)
        )
        db.add(record)
        
        # 5. Create pending processing job entry
        job = ProcessingJob(
            image_id=image_id,
            status="pending"
        )
        db.add(job)
        db.commit()
        
        # 6. Push job metadata to QueueManager for async execution
        await queue_manager.push_job(image_id)
        logger.info(f"Ingested and enqueued image {image_id}")
        
    except Exception as e:
        logger.error(f"Error in poll_upstream cycle: {e}", exc_info=True)
    finally:
        db.close()

async def processing_consumer_loop():
    logger.info("Starting background processing consumer loop...")
    while running:
        try:
            # Await next job from QueueManager (non-blocking yield)
            image_id = await queue_manager.get_job()
            
            db = SessionLocal()
            try:
                # Update status to processing
                job = db.query(ProcessingJob).filter(ProcessingJob.image_id == image_id).order_by(ProcessingJob.id.desc()).first()
                if not job:
                    logger.warning(f"ProcessingJob for {image_id} not found.")
                    queue_manager.task_done()
                    continue
                
                job.status = "processing"
                db.commit()
                
                # Fetch raw image
                img_record = db.query(Image).filter(Image.image_id == image_id).first()
                if not img_record:
                    raise ValueError(f"Raw image metadata record for {image_id} missing from database.")
                
                # Compute Canny overlay
                canny_base64 = generate_canny_overlay(img_record.raw_image_base64)
                canny_res = ProcessingResult(
                    image_id=image_id,
                    process_type="canny",
                    processed_image_base64=canny_base64
                )
                db.add(canny_res)
                
                # Compute Otsu overlay
                otsu_base64 = generate_otsu_overlay(img_record.raw_image_base64)
                otsu_res = ProcessingResult(
                    image_id=image_id,
                    process_type="otsu",
                    processed_image_base64=otsu_base64
                )
                db.add(otsu_res)
                
                # Mark job as completed
                job.status = "completed"
                db.commit()
                logger.info(f"Asynchronously processed overlays (Canny, Otsu) for image {image_id}")
                
            except Exception as e:
                logger.error(f"Async processing failed for image {image_id}: {e}", exc_info=True)
                # Rollback and save failed job state
                try:
                    db.rollback()
                    job = db.query(ProcessingJob).filter(ProcessingJob.image_id == image_id).order_by(ProcessingJob.id.desc()).first()
                    if job:
                        job.status = "failed"
                        job.error_message = str(e)
                        db.commit()
                except Exception as db_err:
                    logger.error(f"Failed to record job failure state: {db_err}")
            finally:
                db.close()
                queue_manager.task_done()
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in processing consumer loop: {e}", exc_info=True)
            await asyncio.sleep(1)

async def ingest_worker_loop():
    global running
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
    global running, worker_task, consumer_task
    if not running:
        running = True
        worker_task = asyncio.create_task(ingest_worker_loop())
        consumer_task = asyncio.create_task(processing_consumer_loop())

async def stop_worker():
    global running, worker_task, consumer_task
    running = False
    
    # Shut down tasks
    if worker_task:
        worker_task.cancel()
        worker_task = None
    if consumer_task:
        consumer_task.cancel()
        consumer_task = None
    logger.info("Ingestion and processing tasks cancelled successfully.")
