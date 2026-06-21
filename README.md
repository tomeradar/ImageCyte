# Live Microscopy Image Dashboard with Inference Overlays

This project implements a full-stack Live Microscopy Dashboard. The system behaves as a smart caching proxy to a hosted upstream microscopy server, protecting it from redundant traffic by centralizing ingestion. It features multi-overlay CV processing, a YouTube-style chronological history scrubbing bar, and a fully modular codebase.

---

## 1. Architectural Choices & Design Patterns

### Smart caching Proxy
To protect the hosted upstream server, only a single backend background ingestion task polls the upstream server. The Angular client queries the local FastAPI database cache, avoiding redundant traffic and upstream throttling.

### Decoupled Processing (Swappable Queue Manager)
CPU-intensive OpenCV processing tasks are completely decoupled from upstream fetching:
1. The **Ingestion Worker** polls upstream, inserts raw metadata into the database immediately, inserts a pending job entry, and enqueues the job.
2. An abstract **QueueManager** exposes simple `push_job` and `get_job` interfaces.
3. A background **Processing Consumer** pulls from the queue, runs Canny edge and Otsu cell boundary detection, saves transparent mask PNG overlays, and marks jobs as completed.
4. **RabbitMQ/Celery Compatibility**: The queue manager uses a clean interface design. If scaling to a production broker like RabbitMQ or Celery is required, only the `QueueManager` implementation in `queue_manager.py` needs to be replaced.

### Relational SQLite Schema
The local database uses a clean, normalized relational design containing three tables:
- **`images`**: Core ingested frame metadata, raw high-res base64, and pre-computed `120x90` thumbnails for timeline previews.
- **`processing_jobs`**: Job state tracking (`pending`, `processing`, `completed`, `failed`) and processing failure logs.
- **`processing_results`**: Base64 transparent PNG overlay masks for different CV algorithms (e.g. Canny and Otsu).

### Transparent Stackable Overlays
Overlays are generated as transparent PNG masks rather than pre-drawn on top of the original image:
- **Canny Edge Detection**: Neon green boundaries over transparent background.
- **Otsu Thresholding**: Semi-transparent neon orange cell fills over transparent background.
This enables the client to overlay them using absolute CSS layout positioning and stack multiple layers simultaneously.

### Chronological History Scrubbing Bar
The bottom drawer features a chronological scrubbing timeline bar similar to modern video players:
- Renders absolute tick marks representing frame ingestion times.
- Moving the cursor displays a floating tooltip containing the frame preview thumbnail, classification label, metrics, and timestamp.
- Clicking or releasing locks the snapshot and updates the main feed.

### Modular Client Components
To ensure single-responsibility clean code, the main `DashboardComponent` page has been split into five standalone, modular components:
1. `DashboardComponent` (Orchestrates signals, state, and HTTP polling/fetching).
2. `ViewportComponent` (Displays the raw image, stackable overlays, toggle controls, and loader states).
3. `TimelineScrubBarComponent` (Handles mouse tracking, hover coordinates mapping, and floating tooltip).
4. `HistogramComponent` (Drows pixel intensity columns on a native HTML5 canvas).
5. `MetricsComponent` (Displays KPI stats cards and classification status badges).

---

## 2. Setup & Execution

### Prerequisites
- Docker and Docker Compose installed.

### Quick Start
1. Clone the repository and navigate to the directory.
2. Build and launch the stack:
   ```bash
   docker-compose up --build
   ```
3. Open the dashboard in your browser:
   `http://localhost:4200`
4. Log in using the default upstream credentials:
   - **Username**: `tomer.adar`
   - **Password**: `chip2255`

---

## 3. Running Verification Tests

### Running Backend Pytest Suite
Run the test suite inside the backend container to verify database CRUD operations, QueueManager pushing/popping, and transparent PNG processors:
```bash
docker exec imagecyte-backend-1 env PYTHONPATH=. pytest tests
```

### Running Frontend Vitest Suite
Execute unit tests for the core Angular services and the dashboard orchestrator inside the frontend container:
```bash
docker exec imagecyte-frontend-1 npx ng test --no-watch
```
