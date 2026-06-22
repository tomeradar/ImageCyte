# ImageCyte Backend API & Processing Engine

This directory contains the FastAPI proxy backend and background computer vision ingestion service.

---

## 1. Technology Stack
- **Web Framework**: FastAPI (Uvicorn server)
- **Database**: SQLite (SQLAlchemy ORM)
- **Image Processing**: OpenCV (headless) & NumPy
- **Asynchronous Loop**: asyncio
- **Testing**: pytest & pytest-asyncio

---

## 2. Directory & Code Structure
```
backend/
├── app/
│   ├── core/
│   │   ├── config.py          → Pydantic BaseSettings config
│   │   ├── exceptions.py      → Managed exception hierarchy & decorators
│   │   ├── logging_config.py  → Centralized rich log formatting
│   │   └── upstream_client.py → Upstream API wrapper & client auth validation
│   ├── database/
│   │   ├── models.py          → Relational SQLAlchemy tables (Image, Job, Result)
│   │   └── session.py         → SQLite engine and session factory
│   ├── routers/
│   │   ├── auth.py            → Proxy login & token refresh routes
│   │   └── image.py           → Cached image retrieval routes & token auth guard
│   ├── schemas/
│   │   ├── auth.py            → Pydantic validation schemas for authentication
│   │   └── image.py           → Pydantic schemas for microscopy image records
│   ├── services/
│   │   ├── image_service.py   → Database query execution & data mapping layer
│   │   ├── ingest_worker.py   → Background upstream poller & async job consumer
│   │   ├── processor.py       → OpenCV image resizing & overlay strategies
│   │   └── queue_manager.py   → Abstract Queue interface & asyncio Queue implementation
│   └── main.py                → FastAPI entrypoint & service lifespan manager
└── tests/
    └── test_backend.py        → Backend unit & integration test suite
```

---

## 3. Main Architectural Components

### A. Background Ingestion & Decoupled Consumer
- **`ingest_worker.py`**:
  - `ingest_worker_loop`: Authenticates the client and polls the upstream server at fixed intervals (`POLLING_INTERVAL`).
  - `poll_upstream`: Ingests the latest image metadata, deduplicates against DB, saves the raw image to database, generates a `120x90` preview thumbnail, and enqueues a processing job.
  - `processing_consumer_loop`: Listens to the queue, calls `cv_processor_service` to generate overlays (Canny, Otsu) in the background, and commits results to the SQLite DB.
- **`queue_manager.py`**:
  - Implements a generic `BaseQueueManager` interface.
  - Utilizes an in-memory `asyncio.Queue` subclass `AsyncQueueManager`. This makes it completely compatible to swap out with external systems (like Celery/RabbitMQ) in production.

### B. Computer Vision Overlay Strategies (`processor.py`)
Overlays are generated as transparent PNG masks using the **Strategy Design Pattern**:
- **`CVOverlayStrategy`**: Interface defining overlay processing operations.
- **`CannyOverlayStrategy`**: Performs Dilated Canny Edge Detection and outputs transparent masks containing bright neon green boundaries.
- **`OtsuOverlayStrategy`**: Performs Otsu cell body segmentation and outputs semi-transparent neon orange masks.
- **`generate_thumbnail`**: Resizes base64 images to `120x90` BGR buffers.

---

## 4. Managed Error Architecture & Logging

### A. Traceback Suppression for Expected Failures
Anticipated runtime failures (such as corrupted upstream images or network validation timeouts) do not dump verbose stack traces in container logs.
- Custom `AppException` base exception and `ErrorCode` enum are defined in [exceptions.py](file:///backend/app/core/exceptions.py).
- `log_managed_error(exc: Exception)` detects `AppException` objects and prints a clean, single-line structured warning:
  `[MANAGED_ERROR] Code: ERR_IMAGE_DECODING | Message: ...`
- Full Python traceback dumps are suppressed unless the logger level is set to `DEBUG` or an unexpected programming error occurs (labeled as `[UNMANAGED_ERROR]`).

### B. Image Processing Decorator
Functions in `processor.py` are wrapped with `@handle_cv_errors(...)`:
- Standard ValueError/OpenCV exceptions are captured and converted into structured exceptions (`ImageDecodingError`, `ImageProcessingError`, `ThumbnailGenerationError`).
- If image buffer decoding fails (corrupted input data), the decorator catches the error, logs a managed single-line warning, and invokes `get_placeholder_thumbnail_base64()` to save a valid gray placeholder thumbnail instead of aborting the ingest cycle.

### C. Rich Logging Layout
Implemented in [logging_config.py](file:///backend/app/core/logging_config.py) and initialized at app startup. It outputs to `sys.stdout` in the format:
`%(asctime)s [%(levelname)s] (%(name)s) %(filename)s:%(lineno)d: %(message)s`
This includes the filename and exact line number of every logged operation.

---

## 5. Verification & Testing

### Running Tests Inside the Container
Verify database integration, QueueManager FIFO queues, transparent processors, and the decorator logging structure using:
```bash
docker-compose exec backend env PYTHONPATH=. pytest
```
