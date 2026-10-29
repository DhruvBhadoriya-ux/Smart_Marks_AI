from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.exams import router as exams_router
from app.api.v1.students import router as students_router
from app.api.v1.activity import router as activity_router
from app.api.v1.dashboard import router as dashboard_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(health_router)
api_v1_router.include_router(dashboard_router)
api_v1_router.include_router(exams_router)
api_v1_router.include_router(students_router)
api_v1_router.include_router(activity_router)
