import cv2
import numpy as np
import logging
import os
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
from collections import deque

logger = logging.getLogger(__name__)

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    logger.error("ultralytics未安装")

from backend.config import settings


@dataclass
class Detection:
    class_name: str
    class_id: int
    confidence: float
    bbox: List[float]
    bbox_pixels: List[int]
    
    center: List[float] = None
    area: float = 0.0
    aspect_ratio: float = 0.0
    direction: str = "center"
    distance: Optional[float] = None
    
    velocity: Optional[List[float]] = None
    track_id: Optional[int] = None
    
    danger_level: str = "medium"
    
    class_name_cn: str = ""
    obstacle_type: str = "static"
    is_blind_road: bool = False
    blind_road_status: str = ""
    
    def to_dict(self) -> dict:
        def to_float(v):
            if hasattr(v, 'tolist'):
                return v.tolist()
            if isinstance(v, (list, tuple)):
                return [float(x) for x in v]
            return float(v) if isinstance(v, (int, float)) else v

        return {
            "class": self.class_name,
            "class_cn": self.class_name_cn,
            "confidence": round(float(self.confidence), 3),
            "bbox": [float(x) for x in self.bbox],
            "bbox_pixels": [int(x) for x in self.bbox_pixels] if self.bbox_pixels else [],
            "direction": self.direction,
            "distance": round(float(self.distance), 2) if self.distance else None,
            "danger_level": self.danger_level,
            "obstacle_type": self.obstacle_type,
            "is_blind_road": self.is_blind_road,
            "blind_road_status": self.blind_road_status,
            "track_id": self.track_id
        }


@dataclass
class BlindRoadState:
    is_detected: bool
    status: str
    alert: Optional[str]


class EnhancedObstacleDetector:
    CRITICAL_CLASSES = {
        "car", "truck", "bus", "motorcycle", "bicycle",
        "person", "dog", "cat", "pole", "construction", "step", "pothole"
    }
    
    CLASS_NAMES = {
        0: "blind_road",
        1: "person",
        2: "bicycle",
        3: "car",
        4: "pole",
        5: "trash_bin",
        6: "construction",
        7: "step",
        8: "pothole",
    }
    
    CHINESE_NAMES = {
        "blind_road": "盲道",
        "person": "行人",
        "bicycle": "自行车",
        "car": "车辆",
        "pole": "障碍柱",
        "trash_bin": "垃圾桶",
        "construction": "施工障碍",
        "step": "台阶",
        "pothole": "坑洞",
        "truck": "卡车",
        "bus": "公交车",
        "motorcycle": "摩托车",
        "dog": "动物",
        "cat": "动物",
    }
    
    DANGER_LEVELS = {
        "person": "medium",
        "bicycle": "high",
        "car": "high",
        "pole": "high",
        "trash_bin": "medium",
        "construction": "high",
        "step": "high",
        "pothole": "high",
        "blind_road": "low",
        "truck": "high",
        "bus": "high",
        "motorcycle": "high",
        "dog": "medium",
        "cat": "medium",
    }
    
    REFERENCE_HEIGHTS = {
        "person": 1.7,
        "bicycle": 1.0,
        "car": 1.5,
        "pole": 3.0,
        "trash_bin": 0.8,
        "construction": 1.0,
        "step": 0.15,
        "pothole": 0.3,
        "truck": 2.8,
        "bus": 3.2,
        "motorcycle": 1.3,
        "dog": 0.6,
        "cat": 0.3,
    }
    
    LEFT_THRESHOLD = 0.33
    RIGHT_THRESHOLD = 0.67
    
    FRAME_QUALITY_THRESHOLD = 50
    
    def __init__(
        self,
        model_path: str = None,
        device: str = "cpu",
        conf_threshold: float = 0.5,
        conf_critical: float = 0.3,
        iou_threshold: float = 0.5,
        history_size: int = 5
    ):
        if not YOLO_AVAILABLE:
            raise RuntimeError("请安装 ultralytics")
        
        self.model_path = model_path or settings.YOLO_MODEL_PATH
        self.device = device or settings.YOLO_DEVICE
        self.conf_threshold = conf_threshold
        self.conf_critical = conf_critical
        self.iou_threshold = iou_threshold
        
        resolved_path = self._ensure_model(self.model_path)
        logger.info(f"加载YOLO模型: {resolved_path}")
        self.model = YOLO(resolved_path)
        
        self.history = deque(maxlen=history_size)
        self.frame_count = 0
        
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        
        logger.info(f"✅ YOLO模型加载完成")
    
    def _ensure_model(self, model_path: str) -> str:
        path = Path(model_path)
        if not path.exists():
            hf_repo = os.getenv("HF_REPO_ID")
            if hf_repo:
                from huggingface_hub import hf_hub_download
                path.parent.mkdir(parents=True, exist_ok=True)
                hf_hub_download(hf_repo, "best.pt", local_dir=str(path.parent))
            else:
                raise FileNotFoundError(f"模型文件不存在: {model_path}，请设置HF_REPO_ID环境变量")
        return str(path)
    
    def _check_frame_quality(self, image: np.ndarray) -> bool:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = laplacian.var()
        
        if variance < self.FRAME_QUALITY_THRESHOLD:
            logger.debug(f"帧质量过低，跳过: variance={variance:.2f}")
            return False
        
        return True
    
    def _preprocess_clahe(self, image: np.ndarray) -> np.ndarray:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b_ch = cv2.split(lab)
        l_enhanced = self.clahe.apply(l)
        enhanced = cv2.cvtColor(cv2.merge([l_enhanced, a, b_ch]), cv2.COLOR_LAB2BGR)
        return enhanced
    
    def detect(self, image: np.ndarray) -> Tuple[List[Detection], BlindRoadState]:
        h, w = image.shape[:2]
        self.frame_count += 1
        
        if not self._check_frame_quality(image):
            return [], BlindRoadState(is_detected=False, status="lost", alert="帧质量过低")
        
        enhanced = self._preprocess_clahe(image)
        
        results = self.model.predict(
            source=enhanced,
            conf=self.conf_critical,
            iou=self.iou_threshold,
            device=self.device,
            verbose=False,
            imgsz=settings.YOLO_IMGSZ
        )
        
        raw_detections = []
        blind_road_detections = []
        
        for result in results:
            boxes = result.boxes
            
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0].cpu().numpy())
                cls_id = int(box.cls[0].cpu().numpy())
                cls_name = self.CLASS_NAMES.get(cls_id, self.model.names.get(cls_id, f"unknown_{cls_id}"))
                
                if cls_name in self.CRITICAL_CLASSES:
                    if conf < self.conf_critical:
                        continue
                else:
                    if conf < self.conf_threshold:
                        continue
                
                cx = (x1 + x2) / 2
                cy = (y1 + y2) / 2
                
                bbox_norm = [x1/w, y1/h, x2/w, y2/h]
                
                area = (x2 - x1) * (y2 - y1) / (w * h)
                aspect_ratio = (x2 - x1) / (y2 - y1 + 1e-6)
                
                center_x_norm = cx / w
                if center_x_norm < self.LEFT_THRESHOLD:
                    direction = "left"
                elif center_x_norm < self.RIGHT_THRESHOLD:
                    direction = "center"
                else:
                    direction = "right"
                
                height_ratio = (y2 - y1) / h
                distance = self._estimate_distance(height_ratio, cls_name)
                
                danger_level = self.DANGER_LEVELS.get(cls_name, "medium")
                class_name_cn = self.CHINESE_NAMES.get(cls_name, cls_name)
                
                is_blind_road = (cls_name == "blind_road")
                obstacle_type = "blind_road" if is_blind_road else "static"
                
                if cls_name in ["car", "truck", "bus", "motorcycle", "bicycle", "person", "dog", "cat"]:
                    obstacle_type = "dynamic"
                elif cls_name in ["pothole", "step", "curb"]:
                    obstacle_type = "ground_hazard"
                
                detection = Detection(
                    class_name=cls_name,
                    class_id=cls_id,
                    confidence=conf,
                    bbox=bbox_norm,
                    bbox_pixels=[int(x1), int(y1), int(x2), int(y2)],
                    center=[cx/w, cy/h],
                    area=area,
                    aspect_ratio=aspect_ratio,
                    direction=direction,
                    distance=distance,
                    danger_level=danger_level,
                    class_name_cn=class_name_cn,
                    obstacle_type=obstacle_type,
                    is_blind_road=is_blind_road,
                    blind_road_status=""
                )
                
                if is_blind_road:
                    blind_road_detections.append((detection, center_x_norm))
                else:
                    raw_detections.append(detection)
        
        for det in raw_detections:
            if det.direction == "center":
                det.confidence *= 1.1
        
        for det in raw_detections:
            if det.area < 0.01 and det.confidence > 0.7:
                logger.debug(f"小目标增强: {det.class_name}, area={det.area:.4f}")
        
        if self.history:
            smoothed = self._temporal_smooth(raw_detections)
        else:
            smoothed = raw_detections
        
        self.history.append(smoothed)
        
        blind_road_state = self._analyze_blind_road(blind_road_detections)
        
        for det, _ in blind_road_detections:
            det.blind_road_status = blind_road_state.status
            smoothed.append(det)
        
        logger.debug(f"检测到 {len(smoothed)} 个目标")
        
        return smoothed, blind_road_state
    
    def _temporal_smooth(self, current: List[Detection]) -> List[Detection]:
        if not self.history:
            return current
        
        prev_detections = self.history[-1]
        
        smoothed = []
        
        for det in current:
            has_history = False
            for prev in prev_detections:
                if (det.class_name == prev.class_name and
                    self._iou(det.bbox_pixels, prev.bbox_pixels) > 0.3):
                    has_history = True
                    break
            
            if has_history:
                smoothed.append(det)
            else:
                det.confidence *= 0.8
                if det.confidence > 0.3:
                    smoothed.append(det)
        
        return smoothed
    
    def _iou(self, box1: List[int], box2: List[int]) -> float:
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        
        union = area1 + area2 - inter
        
        return inter / (union + 1e-6)
    
    def _estimate_distance(self, height_ratio: float, class_name: str) -> Optional[float]:
        ref_height = self.REFERENCE_HEIGHTS.get(class_name)
        if ref_height is None or height_ratio < 0.01:
            return None
        
        focal_factor = 0.8
        estimated = (ref_height * focal_factor) / height_ratio
        
        return max(0.5, min(estimated, 20.0))
    
    def _analyze_blind_road(self, blind_road_detections: List[Tuple[Detection, float]]) -> BlindRoadState:
        if not blind_road_detections:
            return BlindRoadState(
                is_detected=False,
                status="not_found",
                alert="未检测到盲道"
            )
        
        detection, center_x = blind_road_detections[0]
        
        if 0.35 < center_x < 0.65:
            return BlindRoadState(
                is_detected=True,
                status="on_track",
                alert=None
            )
        elif center_x <= 0.35:
            return BlindRoadState(
                is_detected=True,
                status="deviated_right",
                alert="您已偏离盲道，请向左调整"
            )
        else:
            return BlindRoadState(
                is_detected=True,
                status="deviated_left",
                alert="您已偏离盲道，请向右调整"
            )
    
    def get_chinese_name(self, class_name: str) -> str:
        return self.CHINESE_NAMES.get(class_name, class_name)