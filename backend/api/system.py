import time
from fastapi import APIRouter

from backend.config import settings
from backend.core.pipeline import session_manager

router = APIRouter()


@router.get("/status")
async def get_system_status():
    return {
        "status": "ok",
        "version": "2.0.0",
        "modules": {
            "vision": settings.MODULE_VISION_ENABLED,
            "trajectory": settings.MODULE_TRAJECTORY_ENABLED,
            "route_planning": settings.MODULE_ROUTE_PLANNING_ENABLED,
            "environment": settings.MODULE_ENVIRONMENT_ENABLED
        },
        "uptime": time.time()
    }


@router.get("/sessions")
async def get_active_sessions():
    return session_manager.get_all_sessions()


@router.delete("/sessions/{device_id}")
async def remove_session(device_id: str):
    session_manager.remove_session(device_id)
    return {"message": f"Session for device {device_id} removed"}