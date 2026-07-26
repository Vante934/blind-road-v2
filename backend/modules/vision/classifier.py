import logging
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional
import numpy as np

from backend.core.detector import Detection

logger = logging.getLogger(__name__)


class ObstacleType(str, Enum):
    DYNAMIC = "dynamic"
    STATIC = "static"
    GROUND_HAZARD = "ground"


@dataclass
class ClassifiedObstacle:
    detection: Detection
    obstacle_type: ObstacleType
    danger_level: float
    priority: int
    description: str
    
    is_moving: bool = False
    need_trajectory: bool = False
    
    movement_vector: Optional[List[float]] = None
    predicted_position: Optional[List[float]] = None


class EnhancedObstacleClassifier:
    CLASSIFICATION_RULES = {
        "car": {
            "type": ObstacleType.DYNAMIC,
            "danger": 0.9,
            "priority": 5,
            "desc": "汽车",
            "track": True,
            "speed_threshold": 0.01
        },
        "truck": {
            "type": ObstacleType.DYNAMIC,
            "danger": 0.95,
            "priority": 5,
            "desc": "卡车",
            "track": True,
            "speed_threshold": 0.01
        },
        "bus": {
            "type": ObstacleType.DYNAMIC,
            "danger": 0.95,
            "priority": 5,
            "desc": "公交车",
            "track": True,
            "speed_threshold": 0.01
        },
        "motorcycle": {
            "type": ObstacleType.DYNAMIC,
            "danger": 0.85,
            "priority": 5,
            "desc": "摩托车",
            "track": True,
            "speed_threshold": 0.02
        },
        "bicycle": {
            "type": ObstacleType.DYNAMIC,
            "danger": 0.7,
            "priority": 4,
            "desc": "自行车",
            "track": True,
            "speed_threshold": 0.015
        },
        "person": {
            "type": ObstacleType.DYNAMIC,
            "danger": 0.6,
            "priority": 4,
            "desc": "行人",
            "track": True,
            "speed_threshold": 0.01
        },
        "dog": {
            "type": ObstacleType.DYNAMIC,
            "danger": 0.5,
            "priority": 3,
            "desc": "动物",
            "track": True,
            "speed_threshold": 0.02
        },
        "cat": {
            "type": ObstacleType.DYNAMIC,
            "danger": 0.4,
            "priority": 3,
            "desc": "动物",
            "track": True,
            "speed_threshold": 0.02
        },
        "traffic_light": {
            "type": ObstacleType.STATIC,
            "danger": 0.3,
            "priority": 2,
            "desc": "红绿灯",
            "track": False
        },
        "stop_sign": {
            "type": ObstacleType.STATIC,
            "danger": 0.4,
            "priority": 3,
            "desc": "停止标志",
            "track": False
        },
        "fire_hydrant": {
            "type": ObstacleType.STATIC,
            "danger": 0.6,
            "priority": 3,
            "desc": "消防栓",
            "track": False
        },
        "bench": {
            "type": ObstacleType.STATIC,
            "danger": 0.5,
            "priority": 2,
            "desc": "长椅",
            "track": False
        },
        "chair": {
            "type": ObstacleType.STATIC,
            "danger": 0.5,
            "priority": 2,
            "desc": "椅子",
            "track": False
        },
        "pothole": {
            "type": ObstacleType.GROUND_HAZARD,
            "danger": 0.75,
            "priority": 4,
            "desc": "坑洞",
            "track": False
        },
        "stairs": {
            "type": ObstacleType.GROUND_HAZARD,
            "danger": 0.85,
            "priority": 5,
            "desc": "台阶",
            "track": False
        },
        "curb": {
            "type": ObstacleType.GROUND_HAZARD,
            "danger": 0.65,
            "priority": 3,
            "desc": "路缘",
            "track": False
        },
    }
    
    def __init__(self):
        self.prev_detections: List[Detection] = []
    
    def classify(
        self, 
        detections: List[Detection],
        image: np.ndarray = None
    ) -> List[ClassifiedObstacle]:
        classified = []
        
        for det in detections:
            rule = self.CLASSIFICATION_RULES.get(
                det.class_name,
                {
                    "type": ObstacleType.STATIC,
                    "danger": 0.5,
                    "priority": 2,
                    "desc": det.class_name,
                    "track": False,
                    "speed_threshold": 0.01
                }
            )
            
            is_moving = False
            movement_vector = None
            
            if self.prev_detections:
                movement = self._detect_movement(det, self.prev_detections)
                if movement:
                    movement_vector = movement
                    speed = np.linalg.norm(movement)
                    
                    if speed > rule.get("speed_threshold", 0.01):
                        is_moving = True
                        
                        if rule["type"] == ObstacleType.STATIC:
                            logger.debug(f"{det.class_name} 检测到运动，重新分类为动态")
                            rule = {**rule, "type": ObstacleType.DYNAMIC, "track": True}
            
            if self._is_ground_level(det):
                if rule["type"] == ObstacleType.STATIC:
                    logger.debug(f"{det.class_name} 位于地面，可能是地面异常")
                    rule = {**rule, "type": ObstacleType.GROUND_HAZARD}
            
            danger_level = rule["danger"]
            
            if det.distance:
                if det.distance < 1.0:
                    danger_level *= 1.3
                elif det.distance < 2.0:
                    danger_level *= 1.1
            
            if det.direction == "center":
                danger_level *= 1.2
            
            if is_moving:
                danger_level *= 1.15
            
            danger_level = min(danger_level, 1.0)
            
            obstacle = ClassifiedObstacle(
                detection=det,
                obstacle_type=rule["type"],
                danger_level=danger_level,
                priority=rule["priority"],
                description=rule["desc"],
                is_moving=is_moving or rule.get("track", False),
                need_trajectory=rule.get("track", False),
                movement_vector=movement_vector
            )
            
            classified.append(obstacle)
        
        self.prev_detections = detections
        classified.sort(key=lambda x: (x.priority, x.danger_level), reverse=True)
        
        return classified
    
    def _detect_movement(
        self, 
        current: Detection, 
        prev_list: List[Detection]
    ) -> Optional[List[float]]:
        best_match = None
        best_iou = 0.0
        
        for prev in prev_list:
            if prev.class_name != current.class_name:
                continue
            
            iou = self._calc_iou(current.bbox, prev.bbox)
            if iou > best_iou:
                best_iou = iou
                best_match = prev
        
        if best_match and best_iou > 0.3:
            dx = current.center[0] - best_match.center[0]
            dy = current.center[1] - best_match.center[1]
            return [dx, dy]
        
        return None
    
    def _is_ground_level(self, det: Detection) -> bool:
        bottom_y = det.bbox[3]
        return bottom_y > 0.7
    
    def _calc_iou(self, box1: List[float], box2: List[float]) -> float:
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        
        union = area1 + area2 - inter
        
        return inter / (union + 1e-6)
    
    def filter_by_distance(
        self, 
        obstacles: List[ClassifiedObstacle], 
        max_distance: float = 5.0
    ) -> List[ClassifiedObstacle]:
        return [
            obs for obs in obstacles
            if obs.detection.distance is None or obs.detection.distance <= max_distance
        ]