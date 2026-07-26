import logging
import asyncio
import time
from typing import Dict, Optional
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class FPSTracker:
    def __init__(self, window: int = 30):
        self.window = window
        self.timestamps = []
    
    def tick(self):
        self.timestamps.append(time.time())
        if len(self.timestamps) > self.window:
            self.timestamps.pop(0)
    
    def get(self) -> float:
        if len(self.timestamps) < 2:
            return 0.0
        
        total_time = self.timestamps[-1] - self.timestamps[0]
        if total_time <= 0:
            return 0.0
        
        return len(self.timestamps) / total_time


class StreamSession:
    def __init__(self, device_id: str):
        self.session_id = str(uuid.uuid4())
        self.device_id = device_id
        self.created_at = datetime.now()
        self.last_active = datetime.now()
        
        self.pipeline = None
        
        self.frame_count = 0
        self.fps_tracker = FPSTracker(window=30)
        
        logger.info(f"创建会话: session_id={self.session_id}, device_id={self.device_id}")
    
    async def process_frame(self, base64_image: str) -> dict:
        from backend.services.integrated_pipeline import IntegratedPipeline
        from backend.models.schemas import SensorData
        
        if self.pipeline is None:
            self.pipeline = IntegratedPipeline()
        
        self.last_active = datetime.now()
        self.frame_count += 1
        self.fps_tracker.tick()
        
        base64_image = base64_image.split(',')[-1]
        
        sensor_data = SensorData(
            device_id=self.device_id,
            timestamp=time.time() * 1000,
            video_frame=base64_image
        )
        
        result = await self.pipeline.process(sensor_data)
        
        return self._build_response(result)
    
    def _build_response(self, result) -> dict:
        blind_road_status = "not_found"
        detections = []
        
        for obs in result.vision_obstacles:
            if obs.get("class") == "blind_road":
                blind_road_status = obs.get("blind_road_status", "detected")
            detections.append(obs)
        
        warning = {"level": 0, "tts_text": "", "vibration": "none"}
        if result.warning_decision:
            wd = result.warning_decision
            warning = {
                "level": wd.get("warning_level", 0),
                "tts_text": wd.get("tts_text", ""),
                "vibration": wd.get("vibration_pattern", "none")
            }
        
        return {
            "type": "detection_result",
            "frame_id": self.frame_count,
            "fps": round(self.fps_tracker.get(), 1),
            "detections": detections,
            "blind_road_status": blind_road_status,
            "warning": warning,
            "route": result.route_plan,
            "perf": {k: round(v*1000, 1) for k, v in result.processing_time.items()},
            "timestamp": time.time() * 1000
        }
    
    def get_stats(self) -> Dict:
        return {
            "session_id": self.session_id,
            "device_id": self.device_id,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "frame_count": self.frame_count,
            "fps": round(self.fps_tracker.get(), 1)
        }
    
    def cleanup(self):
        logger.info(f"清理会话: session_id={self.session_id}, device_id={self.device_id}")
        self.pipeline = None


class SessionManager:
    def __init__(self, timeout_seconds: int = 300):
        self.sessions: Dict[str, StreamSession] = {}
        self.timeout_seconds = timeout_seconds
        self._cleanup_task = None
    
    async def get_session(self, device_id: str) -> StreamSession:
        if device_id in self.sessions:
            session = self.sessions[device_id]
            
            elapsed = (datetime.now() - session.last_active).total_seconds()
            if elapsed > self.timeout_seconds:
                logger.info(f"会话超时，重建: device_id={device_id}")
                session.cleanup()
                self.sessions[device_id] = StreamSession(device_id)
        else:
            self.sessions[device_id] = StreamSession(device_id)
        
        return self.sessions[device_id]
    
    def remove_session(self, device_id: str):
        if device_id in self.sessions:
            self.sessions[device_id].cleanup()
            del self.sessions[device_id]
            logger.info(f"移除会话: device_id={device_id}")
    
    def get_all_sessions(self) -> Dict[str, Dict]:
        return {
            device_id: session.get_stats()
            for device_id, session in self.sessions.items()
        }
    
    def start_cleanup_loop(self):
        async def cleanup():
            while True:
                await asyncio.sleep(60)
                
                now = datetime.now()
                to_remove = []
                
                for device_id, session in self.sessions.items():
                    elapsed = (now - session.last_active).total_seconds()
                    if elapsed > self.timeout_seconds:
                        to_remove.append(device_id)
                
                for device_id in to_remove:
                    self.remove_session(device_id)
        
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(cleanup())
            logger.info("会话清理循环已启动")


session_manager = SessionManager()