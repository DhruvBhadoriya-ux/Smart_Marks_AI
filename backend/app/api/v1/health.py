import time
from fastapi import APIRouter
from app.core.config import settings
from app.core.database import db_instance, get_db

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
def check_health():
    db = get_db()
    start_time = time.time()
    db_status = "ok"
    ping_ms = 0.0
    
    try:
        # Check database responsiveness
        if not db_instance.is_mock and db_instance.client:
            db_instance.client.admin.command("ping")
        else:
            db.command("ping")
        ping_ms = round((time.time() - start_time) * 1000, 2)
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy",
        "service": "SmartMarks AI Core Engine",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "database": {
            "status": db_status,
            "is_mock": db_instance.is_mock,
            "database_name": settings.MONGODB_DB_NAME,
            "ping_latency_ms": ping_ms
        }
    }
