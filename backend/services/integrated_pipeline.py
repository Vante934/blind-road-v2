import logging
import time
import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

from backend.config import settings
from backend.models.schemas import SensorData

from backend.core.detector import EnhancedObstacleDetector
from backend.modules.vision.classifier import EnhancedObstacleClassifier
from backend.modules.vision.depth_estimator import DepthEstimator
from backend.modules.audio.enhanced_classifier import EnhancedSoundClassifier
from backend.modules.trajectory.kalman_tracker import KalmanTracker
from backend.core.fusion_engine import BayesianFusionEngine, FusionInput
from backend.services.route_planner import EnhancedRoutePlanner

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    vision_obstacles: list = field(default_factory=list)
    sound_result: Optional[Dict] = None
    trajectories: list = field(default_factory=list)
    warning_decision: Optional[Dict] = None
    route_plan: Optional[Dict] = None
    processing_time: Dict[str, float] = field(default_factory=dict)
    total_time: float = 0.0
    success: bool = True
    error: Optional[str] = None


class IntegratedPipeline:
    def __init__(self):
        self._init_modules()
        
        self.trackers: Dict[str, KalmanTracker] = {}
        
        self._executor = None
    
    @property
    def executor(self):
        if self._executor is None:
            self._executor = asyncio.get_event_loop().run_in_executor
        return self._executor
    
    def _init_modules(self):
        logger.info("初始化完整流程组件...")
        
        if settings.MODULE_VISION_ENABLED:
            self.vision_detector = EnhancedObstacleDetector()
            self.vision_classifier = EnhancedObstacleClassifier()
            self.depth_estimator = DepthEstimator()
        else:
            self.vision_detector = None
            self.vision_classifier = None
            self.depth_estimator = None
        
        self.sound_classifier = EnhancedSoundClassifier()
        
        self.fusion_engine = BayesianFusionEngine()
        
        if settings.MODULE_ROUTE_PLANNING_ENABLED:
            self.route_planner = EnhancedRoutePlanner()
        else:
            self.route_planner = None
        
        logger.info("✅ 所有组件初始化完成")
    
    async def process(self, sensor_data: SensorData) -> PipelineResult:
        start_time = time.time()
        result = PipelineResult()
        
        try:
            if sensor_data.video_frame and self.vision_detector:
                t0 = time.time()
                
                import base64
                import cv2
                import numpy as np
                
                img_bytes = base64.b64decode(sensor_data.video_frame)
                img_array = np.frombuffer(img_bytes, dtype=np.uint8)
                image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                
                detections, blind_road_state = await self.executor(
                    None, self.vision_detector.detect, image
                )
                
                for det in detections:
                    if det.distance is None:
                        det.distance = await self.executor(
                            None, self.depth_estimator.estimate_distance,
                            det, sensor_data.tof_distance, image
                        )
                
                obstacles = await self.executor(
                    None, self.vision_classifier.classify, detections, image
                )
                
                result.vision_obstacles = []
                for obs in obstacles:
                    det_dict = obs.detection.to_dict()
                    det_dict.update({
                        "is_moving": obs.is_moving,
                        "need_trajectory": obs.need_trajectory,
                        "movement_vector": obs.movement_vector,
                        "description": obs.description,
                        "priority": obs.priority
                    })
                    result.vision_obstacles.append(det_dict)
                
                result.processing_time["vision"] = time.time() - t0
                logger.debug(f"视觉检测: {len(result.vision_obstacles)} 个障碍物")
            
            if sensor_data.audio_data:
                t0 = time.time()
                
                import base64
                audio_bytes = base64.b64decode(sensor_data.audio_data.audio_base64)
                
                sound_result = await self.executor(
                    None, self.sound_classifier.classify,
                    audio_bytes, None, sensor_data.audio_data.sample_rate
                )
                
                volume_info = await self.executor(
                    None, self.sound_classifier.classify_by_volume, audio_bytes
                )
                
                if sound_result:
                    result.sound_result = {
                        "sound_type": sound_result.sound_type,
                        "sound_label": sound_result.sound_label,
                        "confidence": sound_result.confidence,
                        "danger_score": sound_result.danger_score,
                        "urgency": sound_result.urgency,
                        "volume_info": volume_info
                    }
                
                result.processing_time["audio"] = time.time() - t0
                logger.debug(f"声音识别: {sound_result.sound_label if sound_result else 'None'}")
            
            if settings.MODULE_TRAJECTORY_ENABLED and result.vision_obstacles:
                t0 = time.time()
                
                trajectories = []
                
                for obs in result.vision_obstacles:
                    if not obs.get("is_moving"):
                        continue
                    
                    if not obs.get("distance"):
                        continue
                    
                    track_id = f"{sensor_data.device_id}_{obs['class']}_{obs['direction']}"
                    
                    if track_id not in self.trackers:
                        self.trackers[track_id] = KalmanTracker()
                    
                    tracker = self.trackers[track_id]
                    
                    bbox_center = (
                        (obs["bbox"][0] + obs["bbox"][2]) / 2,
                        (obs["bbox"][1] + obs["bbox"][3]) / 2
                    )
                    
                    prediction = tracker.update(
                        measurement=bbox_center,
                        timestamp=sensor_data.timestamp / 1000.0,
                        distance=obs["distance"]
                    )
                    
                    trajectories.append({
                        "object_id": track_id,
                        "object_class": obs["class"],
                        "speed": prediction.speed,
                        "acceleration": prediction.acceleration,
                        "direction": prediction.direction,
                        "ttc": prediction.ttc,
                        "danger_score": prediction.danger_score,
                        "confidence": prediction.confidence,
                        "predicted_positions": prediction.predicted_positions,
                        "object_direction": obs["direction"]
                    })
                
                result.trajectories = trajectories
                result.processing_time["trajectory"] = time.time() - t0
                logger.debug(f"轨迹预测: {len(trajectories)} 条轨迹")
            
            t0 = time.time()
            
            fusion_input = FusionInput(
                obstacles=result.vision_obstacles,
                trajectories=result.trajectories,
                sound_classification=result.sound_result,
                volume_info=result.sound_result.get("volume_info") if result.sound_result else None,
                distance=sensor_data.tof_distance,
                direction="center"
            )
            
            warning_decision = self.fusion_engine.decide(fusion_input)
            
            result.warning_decision = {
                "warning_level": warning_decision.warning_level,
                "warning_level_name": warning_decision.warning_level_name,
                "confidence": warning_decision.confidence,
                "tts_text": warning_decision.tts_text,
                "vibration_intensity": warning_decision.vibration_intensity,
                "vibration_pattern": warning_decision.vibration_pattern,
                "primary_threat": warning_decision.primary_threat,
                "threat_breakdown": warning_decision.threat_breakdown,
                "timestamp": warning_decision.timestamp
            }
            
            result.processing_time["fusion"] = time.time() - t0
            
            if self.route_planner:
                t0 = time.time()
                
                route_plan = self.route_planner.plan(
                    obstacles=result.vision_obstacles,
                    trajectories=result.trajectories
                )
                
                result.route_plan = {
                    "recommended": {
                        "direction": route_plan.recommended.direction.value,
                        "safety_score": route_plan.recommended.safety_score,
                        "clearance": route_plan.recommended.clearance,
                        "reason": route_plan.recommended.reason,
                        "priority": route_plan.recommended.priority
                    },
                    "alternatives": [
                        {
                            "direction": alt.direction.value,
                            "safety_score": alt.safety_score,
                            "clearance": alt.clearance,
                            "reason": alt.reason,
                            "priority": alt.priority
                        }
                        for alt in route_plan.alternatives
                    ],
                    "tts_instruction": route_plan.tts_instruction,
                    "visual_hint": route_plan.visual_hint
                }
                
                result.processing_time["route"] = time.time() - t0
            
            result.total_time = time.time() - start_time
            logger.info(f"总处理时间: {result.total_time:.3f}秒")
            
        except Exception as e:
            logger.error(f"处理过程异常: {e}")
            result.success = False
            result.error = str(e)
        
        return result