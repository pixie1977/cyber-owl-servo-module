from fastapi import APIRouter

from app.core.low_level_controllers.servo_controller_manager import get_servo_controller

router = APIRouter(tags=["health"])

@router.get("/health")
async def health_check():
    try:
        ctrl = get_servo_controller()
        stats = ctrl.get_connection_stats()
        return {
            "status": "healthy" if stats["current_status"] == "connected" else "degraded",
            "servo": stats
        }
    except Exception:
        return {"status": "unhealthy", "servo": None}