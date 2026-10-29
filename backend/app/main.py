from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import db_instance
from app.api.v1.router import api_v1_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("smartmarks")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to MongoDB / mongomock
    logger.info("Initializing SmartMarks AI Backend Service...")
    db_instance.connect()
    yield
    # Shutdown: Clean close
    logger.info("Shutting down SmartMarks AI Backend Service...")
    db_instance.close()


app = FastAPI(
    title="SmartMarks AI API",
    description="Examination Marks Digitization and Pattern Verification System",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
origins = settings.cors_origins
if "*" not in origins:
    origins.extend(["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(set(origins)),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 Router
app.include_router(api_v1_router)

# Route alias for /api/scans/process
from app.api.v1.ocr import process_marks_strip
app.add_api_route("/api/scans/process", process_marks_strip, methods=["POST"], tags=["Scans"])


@app.get("/", tags=["Root"])
def root():
    return {
        "service": "SmartMarks AI — Examination Marks Digitization API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "health_check": "/api/v1/health",
        "status": "operational"
    }
