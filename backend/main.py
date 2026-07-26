import logging
import numpy as np
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from backend.config import settings
from backend.websocket.router import router as websocket_router
from backend.api.auth import router as auth_router
from backend.api.system import router as system_router
from backend.db.database import engine, Base
from backend.core.pipeline import session_manager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = logging.getLogger("lifespan")
    logger.info("[Startup] 正在预热 YOLO 模型...")
    try:
        from backend.core.detector import EnhancedObstacleDetector
        detector = EnhancedObstacleDetector()
        dummy = np.zeros((320, 320, 3), dtype=np.uint8)
        detector.detect(dummy)
        logger.info("[Startup] 模型预热完成")
    except Exception as e:
        logger.warning(f"[Startup] 预热失败(可忽略): {e}")
    yield
    logger.info("[Shutdown] 清理资源")


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="盲道导航系统 v2",
    description="基于轨迹预测的碰撞风险评估和语音预警系统",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(websocket_router)
app.include_router(auth_router, prefix="/api/auth", tags=["认证"])
app.include_router(system_router, prefix="/api", tags=["系统"])

BASE_DIR = Path(__file__).parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")
app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")


@app.get("/")
async def index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/index.html")
async def index_html():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/manifest.json")
async def manifest():
    return FileResponse(str(FRONTEND_DIR / "manifest.json"))


@app.get("/sw.js")
async def sw():
    return FileResponse(
        str(FRONTEND_DIR / "sw.js"),
        media_type="application/javascript"
    )


@app.get("/favicon.ico")
async def favicon():
    favicon_path = FRONTEND_DIR / "assets" / "icons" / "favicon.ico"
    if favicon_path.exists():
        return FileResponse(str(favicon_path))
    icon_path = FRONTEND_DIR / "assets" / "icons" / "icon-192.png"
    if icon_path.exists():
        return FileResponse(str(icon_path))
    from fastapi.responses import Response
    return Response(status_code=204)


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": "2.0.0",
        "features": {
            "vision": settings.MODULE_VISION_ENABLED,
            "audio": True,
            "trajectory": settings.MODULE_TRAJECTORY_ENABLED,
            "route": settings.MODULE_ROUTE_PLANNING_ENABLED
        }
    }


@app.on_event("startup")
async def startup_event():
    session_manager.start_cleanup_loop()
    logging.info("✅ 盲道导航系统 v2 启动成功")


@app.on_event("shutdown")
async def shutdown_event():
    logging.info("🚀 盲道导航系统 v2 关闭中")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG
    )