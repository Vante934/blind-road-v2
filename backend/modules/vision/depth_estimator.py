import logging
import numpy as np
from typing import Optional, Dict
from backend.core.detector import Detection
from backend.config import settings

logger = logging.getLogger(__name__)


class DepthEstimator:
    OBJECT_HEIGHTS = {
        "person": 1.7,
        "child": 1.2,
        "car": 1.5,
        "truck": 2.8,
        "bus": 3.2,
        "bicycle": 1.1,
        "motorcycle": 1.3,
        "dog": 0.6,
        "cat": 0.3,
        "traffic_light": 3.5,
        "stop_sign": 2.0,
        "fire_hydrant": 0.8,
        "bench": 0.8,
        "chair": 1.0,
    }
    
    def __init__(
        self,
        focal_length: float = None,
        camera_height: float = None,
        image_height: int = 480,
        use_monocular_depth: bool = False
    ):
        self.focal_length = focal_length or settings.CAMERA_FOCAL_LENGTH
        self.camera_height = camera_height or settings.CAMERA_HEIGHT
        self.image_height = image_height
        self.use_monocular_depth = use_monocular_depth
        
        self.depth_model = None
        if use_monocular_depth:
            self._load_depth_model()
    
    def _load_depth_model(self):
        try:
            import torch
            self.depth_model = torch.hub.load('intel-isl/MiDaS', 'MiDaS_small')
            self.depth_model.eval()
            logger.info("✅ MiDaS深度估计模型加载成功")
        except Exception as e:
            logger.warning(f"⚠️ 深度模型加载失败: {e}")
            self.depth_model = None
    
    def estimate_distance(
        self,
        detection: Detection,
        tof_distance: Optional[float] = None,
        image: np.ndarray = None
    ) -> Optional[float]:
        if tof_distance is not None and tof_distance > 0:
            vision_dist = self._estimate_by_bbox_height(detection)
            if vision_dist:
                fused = 0.7 * tof_distance + 0.3 * vision_dist
                logger.debug(f"ToF融合: ToF={tof_distance:.2f}, Vision={vision_dist:.2f}, Fused={fused:.2f}")
                return fused
            else:
                return tof_distance
        
        if self.depth_model and image is not None:
            depth_map = self._estimate_by_model(image)
            if depth_map is not None:
                x1, y1, x2, y2 = detection.bbox_pixels
                roi_depth = depth_map[y1:y2, x1:x2].mean()
                return self._depth_to_distance(roi_depth)
        
        dist_height = self._estimate_by_bbox_height(detection)
        if dist_height:
            return dist_height
        
        dist_bottom = self._estimate_by_bbox_bottom(detection)
        
        return dist_bottom
    
    def _estimate_by_bbox_height(self, detection: Detection) -> Optional[float]:
        real_height = self.OBJECT_HEIGHTS.get(detection.class_name)
        if not real_height:
            return None
        
        bbox_height_norm = detection.bbox[3] - detection.bbox[1]
        bbox_height_pixels = bbox_height_norm * self.image_height
        
        if bbox_height_pixels < 10:
            return None
        
        distance = (real_height * self.focal_length) / bbox_height_pixels
        
        if distance < 0.3 or distance > 50:
            logger.debug(f"距离异常: {distance:.2f}m, 使用兜底方法")
            return None
        
        return distance
    
    def _estimate_by_bbox_bottom(self, detection: Detection) -> float:
        y_bottom = detection.bbox[3]
        
        if y_bottom > 0.95:
            return 0.5
        elif y_bottom > 0.85:
            return 1.0
        elif y_bottom > 0.75:
            return 1.5
        elif y_bottom > 0.65:
            return 2.5
        elif y_bottom > 0.55:
            return 3.5
        elif y_bottom > 0.45:
            return 5.0
        else:
            return 8.0
    
    def _estimate_by_model(self, image: np.ndarray) -> Optional[np.ndarray]:
        if self.depth_model is None:
            return None
        
        try:
            import torch
            import cv2
            
            img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            img_input = torch.from_numpy(img_rgb).float() / 255.0
            img_input = img_input.permute(2, 0, 1).unsqueeze(0)
            
            with torch.no_grad():
                depth_map = self.depth_model(img_input)
            
            depth_map = depth_map.squeeze().cpu().numpy()
            
            return depth_map
        except Exception as e:
            logger.error(f"深度模型推理失败: {e}")
            return None
    
    def _depth_to_distance(self, depth_value: float) -> float:
        max_depth = 10.0
        min_depth = 0.5
        
        distance = max_depth - (depth_value / 255.0) * (max_depth - min_depth)
        
        return max(distance, 0.3)