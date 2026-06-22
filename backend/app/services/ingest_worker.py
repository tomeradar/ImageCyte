from app.core.config import settings
import asyncio
import datetime
import json
import logging
from app.core.upstream_client import upstream_client
from app.database.session import SessionLocal
from app.database.models import Image, ProcessingJob, ProcessingResult
from app.services.processor import cv_processor_service
from app.services.queue_manager import queue_manager
from app.core.exceptions import AppException, log_managed_error, UpstreamMalformedDataError

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
    logger.info("Ingest Worker: Starting poll upstream cycle...")
    try:
        # 1. Fetch image from upstream
        logger.info("Ingest Worker: Fetching current microscopy image from upstream...")
        img_res = await upstream_client.request("GET", "/api/image")
        if img_res.status_code != 200:
            logger.error(f"Ingest Worker: Failed to poll upstream image: {img_res.status_code} - {img_res.text}")
            return
        
        try:
            img_data = img_res.json()
        except ValueError as je:
            raise UpstreamMalformedDataError(
                message=f"Failed to parse upstream image response JSON: {je}",
                details={"response_text_preview": img_res.text[:200]}
            ) from je
        
        image_id = img_data.get("image_id")
        if not image_id:
            logger.error("Ingest Worker: Upstream image response missing 'image_id'")
            return

        # 2. Check if deduplication criteria is met (optimized checking for bandwidth-saving upstream responses)
        latest_record = db.query(Image).order_by(Image.id.desc()).first()
        if latest_record and latest_record.image_id == image_id:
            logger.info(f"Ingest Worker: Image '{image_id}' matches the latest database record. Discarding ingestion.")
            return

        raw_base64 = img_data.get("image_data_base64")
        ts_str = img_data.get("timestamp")
        
        if not raw_base64 or not ts_str:
            logger.error(f"Ingest Worker: Upstream image response missing key data. Keys: {list(img_data.keys())}")
            return
            
        # Validate that the image data can be decoded
        if not cv_processor_service.is_valid_image(raw_base64):
            logger.warning(f"Ingest Worker: Discarding image '{image_id}' because it is corrupted/damaged.")
            return

        logger.info(f"Ingest Worker: New image detected: '{image_id}'. Fetching cell analysis results from upstream...")
        
        # 3. Fetch results
        res_res = await upstream_client.request("GET", "/api/results")
        if res_res.status_code != 200:
            logger.error(f"Ingest Worker: Failed to fetch analysis results for '{image_id}': {res_res.status_code} - {res_res.text}")
            return
            
        try:
            res_data = res_res.json()
        except ValueError as je:
            raise UpstreamMalformedDataError(
                message=f"Failed to parse upstream results response JSON: {je}",
                details={"response_text_preview": res_res.text[:200]}
            ) from je
        results_image_id = res_data.get("image_id")
        
        if results_image_id != image_id:
            logger.warning(
                f"Ingest Worker: Mismatch in image_ids: image endpoint='{image_id}', results endpoint='{results_image_id}'. "
                "Aligning on current fetched image."
            )
            
        intensity_avg = res_data.get("intensity_average", 0.0)
        focus_score = res_data.get("focus_score", 0.0)
        classification = res_data.get("classification_label", "Unknown")
        histogram_list = res_data.get("histogram", [])
        
        # Generate low-res thumbnail immediately for fast scrubbing (quick resize)
        logger.info(f"Ingest Worker: Generating 120x90 preview thumbnail for image '{image_id}'...")
        thumbnail_base64 = cv_processor_service.generate_thumbnail(raw_base64)
        logger.info(f"Ingest Worker: Thumbnail generated. Length of base64: {len(thumbnail_base64)}")

        # 4. Persist core metadata and raw image to local SQLite DB
        logger.info(f"Ingest Worker: Persisting image '{image_id}' metadata to database...")
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
        logger.info(f"Ingest Worker: Creating pending processing job record in database for image '{image_id}'...")
        job = ProcessingJob(
            image_id=image_id,
            status="pending"
        )
        db.add(job)
        db.commit()
        logger.info(f"Ingest Worker: Successfully saved image '{image_id}' and pending job to database.")
        
        # 6. Push job metadata to QueueManager for async execution
        logger.info(f"Ingest Worker: Enqueuing image '{image_id}' processing job into queue manager...")
        await queue_manager.push_job(image_id)
        logger.info(f"Ingest Worker: Ingested and enqueued image '{image_id}' successfully.")
        
    except AppException as ae:
        log_managed_error(ae)
    except Exception as e:
        logger.error(f"Ingest Worker: Error occurred in poll_upstream cycle: {e}", exc_info=True)
    finally:
        db.close()

async def processing_consumer_loop():
    logger.info("Async Job Consumer: Starting background processing consumer loop...")
    while running:
        try:
            # Await next job from QueueManager (non-blocking yield)
            logger.info("Async Job Consumer: Waiting for next enqueued job...")
            image_id = await queue_manager.get_job()
            logger.info(f"Async Job Consumer: Received job for image '{image_id}'. Starting processing...")
            
            db = SessionLocal()
            try:
                # Update status to processing
                job = db.query(ProcessingJob).filter(ProcessingJob.image_id == image_id).order_by(ProcessingJob.id.desc()).first()
                if not job:
                    logger.warning(f"Async Job Consumer: ProcessingJob for '{image_id}' not found in database.")
                    queue_manager.task_done()
                    continue
                
                logger.info(f"Async Job Consumer: Updating job status for image '{image_id}' to 'processing'...")
                job.status = "processing"
                db.commit()
                
                # Fetch raw image
                img_record = db.query(Image).filter(Image.image_id == image_id).first()
                if not img_record:
                    raise ValueError(f"Raw image metadata record for '{image_id}' missing from database.")
                
                # Compute Canny overlay
                logger.info(f"Async Job Consumer: Computing classical Canny edge overlay mask for image '{image_id}'...")
                canny_base64 = cv_processor_service.process_image(img_record.raw_image_base64, "canny")
                canny_res = ProcessingResult(
                    image_id=image_id,
                    process_type="canny",
                    processed_image_base64=canny_base64
                )
                db.add(canny_res)
                
                # Compute Otsu overlay
                logger.info(f"Async Job Consumer: Computing Otsu cell segmentation overlay mask for image '{image_id}'...")
                otsu_base64 = cv_processor_service.process_image(img_record.raw_image_base64, "otsu")
                otsu_res = ProcessingResult(
                    image_id=image_id,
                    process_type="otsu",
                    processed_image_base64=otsu_base64
                )
                db.add(otsu_res)
                
                # Mark job as completed
                logger.info(f"Async Job Consumer: Classical overlays (Canny, Otsu) generated. Completing job for image '{image_id}'...")
                job.status = "completed"
                db.commit()
                logger.info(f"Async Job Consumer: Successfully processed and completed overlays for image '{image_id}'.")
                
            except AppException as ae:
                log_managed_error(ae)
                # Rollback and save failed job state, without standard logger.error traceback
                try:
                    db.rollback()
                    job = db.query(ProcessingJob).filter(ProcessingJob.image_id == image_id).order_by(ProcessingJob.id.desc()).first()
                    if job:
                        job.status = "failed"
                        job.error_message = f"[{ae.error_code.value}] {ae.message}"
                        db.commit()
                        logger.info(f"Async Job Consumer: Job status for image '{image_id}' marked as 'failed' (Managed: {ae.error_code.value}) in database.")
                except Exception as db_err:
                    logger.error(f"Async Job Consumer: Failed to record job failure state for image '{image_id}': {db_err}")
            except Exception as e:
                logger.error(f"Async Job Consumer: Unexpected unmanaged processing failed for image '{image_id}': {e}", exc_info=True)
                # Rollback and save failed job state
                try:
                    db.rollback()
                    job = db.query(ProcessingJob).filter(ProcessingJob.image_id == image_id).order_by(ProcessingJob.id.desc()).first()
                    if job:
                        job.status = "failed"
                        job.error_message = str(e)
                        db.commit()
                        logger.info(f"Async Job Consumer: Job status for image '{image_id}' marked as 'failed' in database.")
                except Exception as db_err:
                    logger.error(f"Async Job Consumer: Failed to record job failure state for image '{image_id}': {db_err}")
            finally:
                db.close()
                queue_manager.task_done()
                
        except asyncio.CancelledError:
            logger.info("Async Job Consumer: Consumer loop task cancelled.")
            break
        except Exception as e:
            logger.error(f"Async Job Consumer: Unexpected error in processing consumer loop: {e}", exc_info=True)
            await asyncio.sleep(1)

async def ingest_worker_loop():
    global running
    logger.info("Ingest Worker: Starting central ingest background loop...")
    
    # Authenticate upstream client before starting poll loop
    logger.info("Ingest Worker: Logging in upstream client...")
    await upstream_client.login()
    
    while running:
        try:
            await poll_upstream()
        except Exception as e:
            logger.error(f"Ingest Worker: Error in ingest worker loop iteration: {e}", exc_info=True)
        await asyncio.sleep(settings.POLLING_INTERVAL)
        
    logger.info("Ingest Worker: Ingest worker loop stopped.")

def start_worker():
    global running, worker_task, consumer_task
    if not running:
        running = True
        logger.info("Ingest Worker: Spawning background ingest worker tasks...")
        worker_task = asyncio.create_task(ingest_worker_loop())
        consumer_task = asyncio.create_task(processing_consumer_loop())
        logger.info("Ingest Worker: Background tasks spawned successfully.")

async def stop_worker():
    global running, worker_task, consumer_task
    running = False
    logger.info("Ingest Worker: Stopping background worker tasks...")
    
    # Shut down tasks
    if worker_task:
        worker_task.cancel()
        worker_task = None
    if consumer_task:
        consumer_task.cancel()
        consumer_task = None
    logger.info("Ingest Worker: Ingestion and processing tasks cancelled successfully.")
