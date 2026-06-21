import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.database.session import engine, Base
from app.services.ingest_worker import start_worker, stop_worker
from app.routers import auth, image

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize SQLite database and tables
logger.info("Initializing database and tables...")
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: trigger client background loop
    logger.info("Application starting up...")
    start_worker()
    yield
    # Shutdown: gracefully shut down background tasks
    logger.info("Application shutting down...")
    await stop_worker()

app = FastAPI(
    title="Microscopy AI Proxy Dashboard Backend",
    version="1.0.0",
    lifespan=lifespan
)

# Set up CORS middleware for Angular client
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permits access from any origin during local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register endpoints
# /api/proxy/login and /api/proxy/refresh
app.include_router(auth.router, prefix="/api/proxy", tags=["Authentication Proxy"])
# /api/image/latest, /api/history, and /api/history/{image_id}
app.include_router(image.router, prefix="/api", tags=["Microscopy Images"])

@app.get("/")
def read_root():
    return {"status": "healthy", "service": "microscopy-caching-proxy"}
