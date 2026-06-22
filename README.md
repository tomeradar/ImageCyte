# Live Microscopy Image Dashboard with Inference Overlays

This project implements a full-stack Live Microscopy Dashboard. The system behaves as a smart caching proxy to a hosted upstream microscopy server, protecting it from redundant traffic by centralizing ingestion. It features multi-overlay CV processing, a YouTube-style chronological history scrubbing bar, and a fully modular codebase.

---

## 1. Project Directory Structure

```
ImageCyte/ (Project Root)
├── README.md             → This root architecture & setup documentation
├── docker-compose.yml    → Orchestrates frontend, backend, and dozzle services
├── spec.md               → Diagnostic specification & goals
├── data/                 → Bind-mounted directory containing the SQLite database file
│   └── microscopy.db     → SQLite database file (visible on the host)
│
├── backend/              → FastAPI proxy backend & CV processing engine
│   ├── app/              → Backend source code
│   ├── tests/            → Pytest test suite
│   └── README.md         → [Detailed Backend Documentation](backend/README.md)
│
└── frontend/             → Angular single-page application client
    ├── src/              → Frontend source code
    └── README.md         → [Detailed Frontend Documentation](frontend/README.md)
```

---

## 2. System Architecture

```
┌────────────────────────────────────────────────────────┐
│                    UPSTREAM SERVER                     │
│    (Holds live frame base64 images & analysis JSON)    │
└──────────────────────────┬─────────────────────────────┘
                           ▲
                           │ Ingestion loop (POLLING_INTERVAL = 5s)
                           ▼
┌────────────────────────────────────────────────────────┐
│                    IMAGE CYTE BACKEND                  │
│                                                        │
│ ┌──────────────────┐   Job   ┌───────────────────────┐ │
│ │ Ingest Worker    ├────────►│ Async Queue Manager   │ │
│ │ (polls upstream) │         │ (asyncio.Queue FIFO)  │ │
│ └────────┬─────────┘         └──────────┬────────────┘ │
│          │                              │              │
│          │ writes metadata              │ dequeues job │
│          ▼                              ▼              │
│ ┌──────────────────┐         ┌───────────────────────┐ │
│ │   SQLite Cache   │         │ Processing Consumer   │ │
│ │ (microscopy.db)  │◄────────┤ (OpenCV Edge/Cell)    │ │
│ └────────▲─────────┘  saves  └───────────────────────┘ │
│          │           overlays                          │
└──────────┼─────────────────────────────────────────────┘
           │
           │ queries endpoints (auth guard)
           ▼
┌────────────────────────────────────────────────────────┐
│                   IMAGE CYTE FRONTEND                  │
│         (Angular Client Dashboard at port 4200)        │
└────────────────────────────────────────────────────────┘
```

The system is decoupled into two key pipelines:
1. **The Ingestion Pipeline**: The `Ingest Worker` polls the upstream server, deduplicates frames, generates a quick `120x90` thumbnail, commits the base metadata to the relational SQLite database cache, and pushes the image ID to the FIFO queue.
2. **The Processing Pipeline**: The background `Processing Consumer` pulls jobs from the queue, runs Dilated Canny Edge Detection and Otsu Cell Segmentation strategies, and saves the resulting transparent PNG masks to the database.

Clients view metadata and stackable overlays directly from the local cache database, preventing redundant calls to the upstream server.

---

## 3. Tech Stack & Tools Overview

### Backend API
- **FastAPI**: Lightweight web server featuring ASGI routing and life cycle hooks.
- **SQLAlchemy ORM**: Handles relational SQLite mappings.
- **OpenCV & NumPy**: Decodes base64 frames, resizes thumbnails, and generates computer vision transparent PNG overlays.

### Frontend Dashboard
- **Angular standalone components**: Modular viewport, timeline player, canvas histogram, metrics, and KPI card components.
- **RxJS**: BehaviorSubjects manage active token states, coordinate history scrub positions, and throttle HTTP polling.

### Management Tools
- **Dozzle (Log Viewer)**: Integrates in docker-compose. It reads the Docker socket to provide real-time, searchable container logs via a web GUI.
- **SQLite Database Bind-Mount**: Database files are stored under `./data/microscopy.db` on the host, allowing database inspection using local tools.

---

## 4. Setup & Running the Project

### Prerequisites
- Docker and Docker Compose installed and running on the host.

### Quick Start
1. Navigate to the project root directory.
2. Build and launch the container services:
   ```bash
   docker-compose up --build
   ```
3. Open the dashboard in your browser:
   `http://localhost:4200`
4. Log in using the default upstream credentials:
   - **Username**: `tomer.adar`
   - **Password**: `chip2255`

### Log Viewer (Dozzle)
You can view rich backend logs, line numbers, database queries, and frontend console output in real-time by opening:
`http://localhost:8888`

---

## 5. Verification & Tests

### Backend Tests
Execute unit tests for database records, QueueManager queues, transparent CV strategies, decorator failures, and trace suppression inside the backend container:
```bash
docker-compose exec backend env PYTHONPATH=. pytest
```

### Frontend Tests
Execute standalone unit tests for components, services, auth interceptor refresh queues, and viewport canvas rendering:
```bash
docker-compose exec frontend npx ng test --no-watch
```
