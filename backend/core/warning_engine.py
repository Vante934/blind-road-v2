import logging
import time
from typing import Dict, Any, Optional

from backend.models.schemas import WarningCommand

logger = logging.getLogger(__name__)


class WarningEngine:
    def __init__(self):
        self._device_states = {}
        self._last_warning_time = {}
        self.DEBOUNCE_SECONDS = {1: 2.0, 2: 3.0, 3: 5.0}
    
    async def process_legacy(self, sensor_data) -> Optional[WarningCommand]:
        distance = sensor_data.tof_distance
        
        if distance and distance < 0.5:
            return WarningCommand(
                type="warning",
                warning_level=1,
                warning_level_name="一级危险",
                tts_text=f"危险！前方距离{distance:.1f}米，请立即避让！",
                vibration_intensity=3,
                vibration_pattern="sos",
                distance=distance,
                direction=sensor_data.tof_direction,
                timestamp=time.time() * 1000
            )
        
        return None
    
    async def process_fusion_data(
        self, 
        device_id: str, 
        fusion_data: Dict[str, Any]
    ) -> Optional[WarningCommand]:
        obstacles = fusion_data.get("obstacles", [])
        sound_class = fusion_data.get("sound_classification")
        trajectories = fusion_data.get("trajectories", [])
        distance = fusion_data.get("distance")
        direction = fusion_data.get("direction", "center")
        
        vision_score = self._calc_vision_score(obstacles)
        
        sound_score = 0.0
        if sound_class:
            sound_score = sound_class.get("danger_score", 0) * sound_class.get("confidence", 0)
        
        trajectory_score = 0.0
        if trajectories:
            max_danger = max(t.get("danger_score", 0) for t in trajectories)
            trajectory_score = max_danger
        
        distance_score = self._distance_to_score(distance)
        
        if obstacles:
            weights = {
                "vision": 0.40,
                "trajectory": 0.25,
                "sound": 0.20,
                "distance": 0.15
            }
        else:
            weights = {
                "vision": 0.0,
                "trajectory": 0.30,
                "sound": 0.30,
                "distance": 0.40
            }
        
        total_score = (
            vision_score * weights["vision"] +
            trajectory_score * weights["trajectory"] +
            sound_score * weights["sound"] +
            distance_score * weights["distance"]
        )
        
        if distance and distance < 0.5:
            warning_level = 1
        elif any(t.get("ttc") and t["ttc"] <= 1.0 for t in trajectories):
            warning_level = 1
        else:
            warning_level = self._score_to_level(total_score)
        
        if not self._should_trigger(device_id, warning_level):
            return None
        
        if warning_level == 0:
            return None
        
        tts_text = self._build_tts(
            warning_level, distance, direction, obstacles, sound_class, trajectories
        )
        
        command = WarningCommand(
            type="warning",
            warning_level=warning_level,
            warning_level_name=self._get_level_name(warning_level),
            tts_text=tts_text,
            vibration_intensity=self._get_vibration(warning_level),
            vibration_pattern=self._get_vibration_pattern(warning_level),
            distance=distance,
            direction=direction,
            timestamp=time.time() * 1000
        )
        
        self._update_state(device_id, distance, warning_level)
        self._last_warning_time[f"{device_id}_{warning_level}"] = time.time()
        
        return command
    
    def _calc_vision_score(self, obstacles: list) -> float:
        if not obstacles:
            return 0.0
        
        max_danger = 0.0
        for obs in obstacles:
            danger = obs.get("danger_level", 0)
            dist = obs.get("distance", 5.0)
            
            if dist < 1.0:
                dist_factor = 1.0
            elif dist < 2.0:
                dist_factor = 0.7
            else:
                dist_factor = 0.4
            
            if obs.get("direction") == "center":
                dir_factor = 1.0
            else:
                dir_factor = 0.7
            
            score = danger * dist_factor * dir_factor
            max_danger = max(max_danger, score)
        
        return max_danger
    
    def _distance_to_score(self, distance: Optional[float]) -> float:
        if not distance:
            return 0.0
        
        if distance <= 0.5:
            return 1.0
        elif distance <= 1.5:
            return 0.7
        elif distance <= 3.0:
            return 0.4
        else:
            return 0.1
    
    def _score_to_level(self, score: float) -> int:
        if score >= 0.7:
            return 1
        elif score >= 0.45:
            return 2
        elif score >= 0.25:
            return 3
        else:
            return 0
    
    def _should_trigger(self, device_id: str, level: int) -> bool:
        if level == 0:
            return True
        
        key = f"{device_id}_{level}"
        last_time = self._last_warning_time.get(key, 0)
        debounce = self.DEBOUNCE_SECONDS.get(level, 3.0)
        
        return time.time() - last_time >= debounce
    
    def _build_tts(
        self, level, distance, direction, obstacles, sound, trajectories
    ) -> str:
        direction_map = {"center": "前方", "left": "左侧", "right": "右侧", "rear": "后方"}
        dir_text = direction_map.get(direction, "附近")
        
        obs_text = ""
        if obstacles:
            primary = obstacles[0]
            obs_text = f"有{primary['class']}"
            if primary.get("distance"):
                obs_text += f"，距离{primary['distance']:.1f}米"
        
        sound_text = ""
        if sound:
            sound_text = f"，检测到{sound['label']}"
        
        traj_text = ""
        if trajectories:
            for t in trajectories:
                if t.get("trend") == "approaching" and t.get("ttc") and t["ttc"] < 3:
                    traj_text = f"，{t['ttc']:.0f}秒内将到达"
                    break
        
        if level == 1:
            tts = f"危险！{dir_text}{obs_text}{sound_text}{traj_text}，请立即避让！"
        elif level == 2:
            tts = f"注意！{dir_text}{obs_text}{sound_text}{traj_text}，请注意安全。"
        elif level == 3:
            tts = f"提醒：{dir_text}{obs_text}{sound_text}。"
        else:
            tts = ""
        
        return tts
    
    def _get_level_name(self, level: int) -> str:
        return {1: "一级危险", 2: "二级警告", 3: "三级提醒", 0: "安全"}.get(level, "")
    
    def _get_vibration(self, level: int) -> int:
        return {1: 3, 2: 2, 3: 1, 0: 0}.get(level, 0)
    
    def _get_vibration_pattern(self, level: int) -> str:
        return {1: "sos", 2: "continuous", 3: "single", 0: "none"}.get(level, "none")
    
    def _update_state(self, device_id, distance, level):
        self._device_states[device_id] = {
            "last_distance": distance,
            "last_level": level,
            "last_time": time.time()
        }