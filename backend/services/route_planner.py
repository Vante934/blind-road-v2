import logging
import numpy as np
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class Direction(str, Enum):
    STOP = "stop"
    FORWARD = "forward"
    LEFT = "left"
    RIGHT = "right"
    SLOW = "slow"
    BACK = "back"


@dataclass
class RouteOption:
    direction: Direction
    safety_score: float
    clearance: float
    reason: str
    priority: int


@dataclass
class RoutePlan:
    recommended: RouteOption
    alternatives: List[RouteOption]
    tts_instruction: str
    visual_hint: Optional[Dict] = None


class OccupancyGrid:
    def __init__(
        self,
        grid_size: Tuple[int, int] = (3, 3),
        cell_size: float = 1.5,
    ):
        self.grid_size = grid_size
        self.cell_size = cell_size
        
        self.grid = np.zeros(grid_size)
        self.confidence = np.ones(grid_size) * 0.5
    
    def update(
        self, 
        obstacles: List[Dict],
        trajectories: List[Dict] = None
    ):
        self.grid.fill(0)
        self.confidence.fill(0.5)
        
        for obs in obstacles:
            self._mark_obstacle(obs)
        
        if trajectories:
            for traj in trajectories:
                self._mark_trajectory(traj)
    
    def _mark_obstacle(self, obs: Dict):
        distance = obs.get("distance", 5.0)
        direction = obs.get("direction", "center")
        obs_type = obs.get("type", "static")
        
        if distance < 1.5:
            row = 0
        elif distance < 3.0:
            row = 1
        else:
            row = 2
        
        if direction == "left":
            col = 0
        elif direction == "center":
            col = 1
        else:
            col = 2
        
        if row < self.grid_size[1] and col < self.grid_size[0]:
            self.grid[col, row] = 1.0
            
            if obs_type == "dynamic":
                self.confidence[col, row] = 0.9
            else:
                self.confidence[col, row] = 0.8
            
            self._spread_occupation(col, row, 0.5)
    
    def _mark_trajectory(self, traj: Dict):
        predicted_positions = traj.get("predicted_positions", [])
        
        for pos in predicted_positions:
            if pos[0] < -0.2:
                col = 0
            elif pos[0] < 0.2:
                col = 1
            else:
                col = 2
            
            if pos[1] > 0.6:
                row = 0
            elif pos[1] > 0.4:
                row = 1
            else:
                row = 2
            
            if row < self.grid_size[1] and col < self.grid_size[0]:
                self.grid[col, row] = max(self.grid[col, row], 0.7)
                self.confidence[col, row] = max(self.confidence[col, row], 0.6)
    
    def _spread_occupation(self, col: int, row: int, value: float):
        for dc in [-1, 0, 1]:
            for dr in [-1, 0, 1]:
                if dc == 0 and dr == 0:
                    continue
                
                nc, nr = col + dc, row + dr
                
                if 0 <= nc < self.grid_size[0] and 0 <= nr < self.grid_size[1]:
                    if self.grid[nc, nr] < value:
                        self.grid[nc, nr] = value
                        self.confidence[nc, nr] = 0.5
    
    def is_free(self, col: int, row: int, threshold: float = 0.3) -> bool:
        if not (0 <= col < self.grid_size[0] and 0 <= row < self.grid_size[1]):
            return False
        
        return self.grid[col, row] < threshold
    
    def get_zone_status(self, zone: str) -> Dict:
        col_map = {"left": 0, "center": 1, "right": 2}
        col = col_map.get(zone, 1)
        
        occupied_cells = 0
        total_cells = self.grid_size[1]
        
        for row in range(total_cells):
            if self.grid[col, row] > 0.3:
                occupied_cells += 1
        
        occupation_rate = occupied_cells / total_cells
        
        min_distance = None
        for row in range(total_cells):
            if self.grid[col, row] > 0.5:
                if row == 0:
                    dist = 0.75
                elif row == 1:
                    dist = 2.25
                else:
                    dist = 4.0
                
                if min_distance is None or dist < min_distance:
                    min_distance = dist
        
        return {
            "zone": zone,
            "occupation_rate": occupation_rate,
            "is_free": occupation_rate < 0.33,
            "is_blocked": occupation_rate > 0.66,
            "min_distance": min_distance,
            "clearance": min_distance if min_distance else 5.0
        }


class EnhancedRoutePlanner:
    def __init__(self):
        self.grid = OccupancyGrid()
    
    def plan(
        self,
        obstacles: List[Dict],
        trajectories: List[Dict] = None,
        current_direction: str = "forward"
    ) -> RoutePlan:
        self.grid.update(obstacles, trajectories)
        
        left_status = self.grid.get_zone_status("left")
        center_status = self.grid.get_zone_status("center")
        right_status = self.grid.get_zone_status("right")
        
        logger.debug(
            f"区域状态: Left={left_status['occupation_rate']:.2f}, "
            f"Center={center_status['occupation_rate']:.2f}, "
            f"Right={right_status['occupation_rate']:.2f}"
        )
        
        options = []
        
        if center_status["is_free"]:
            options.append(RouteOption(
                direction=Direction.FORWARD,
                safety_score=self._calc_safety_score(center_status, obstacles, "center"),
                clearance=center_status["clearance"],
                reason="前方道路畅通",
                priority=3
            ))
        
        if left_status["is_free"]:
            options.append(RouteOption(
                direction=Direction.LEFT,
                safety_score=self._calc_safety_score(left_status, obstacles, "left"),
                clearance=left_status["clearance"],
                reason=f"左侧通行空间{left_status['clearance']:.1f}米",
                priority=2
            ))
        
        if right_status["is_free"]:
            options.append(RouteOption(
                direction=Direction.RIGHT,
                safety_score=self._calc_safety_score(right_status, obstacles, "right"),
                clearance=right_status["clearance"],
                reason=f"右侧通行空间{right_status['clearance']:.1f}米",
                priority=2
            ))
        
        if not center_status["is_blocked"]:
            options.append(RouteOption(
                direction=Direction.SLOW,
                safety_score=0.6,
                clearance=center_status["clearance"],
                reason="前方有障碍物，建议减速通过",
                priority=1
            ))
        
        options.append(RouteOption(
            direction=Direction.STOP,
            safety_score=0.3,
            clearance=0.0,
            reason="前方拥挤，请停止前进",
            priority=5 if not options else 1
        ))
        
        options = self._apply_special_rules(
            options, obstacles, trajectories, 
            left_status, center_status, right_status
        )
        
        if not options:
            recommended = RouteOption(
                direction=Direction.STOP,
                safety_score=0.2,
                clearance=0.0,
                reason="无安全通行路径",
                priority=5
            )
            alternatives = []
        else:
            options.sort(key=lambda x: (x.safety_score, x.clearance), reverse=True)
            recommended = options[0]
            alternatives = options[1:4]
        
        tts = self._generate_instruction(recommended, obstacles)
        
        visual_hint = {
            "grid": self.grid.grid.tolist(),
            "recommended_direction": recommended.direction.value,
            "arrow_angle": self._direction_to_angle(recommended.direction),
            "clearance_zones": {
                "left": left_status["clearance"],
                "center": center_status["clearance"],
                "right": right_status["clearance"]
            }
        }
        
        return RoutePlan(
            recommended=recommended,
            alternatives=alternatives,
            tts_instruction=tts,
            visual_hint=visual_hint
        )
    
    def _calc_safety_score(
        self, 
        zone_status: Dict, 
        obstacles: List[Dict],
        zone: str
    ) -> float:
        base_score = 1.0 - zone_status["occupation_rate"]
        
        clearance = zone_status["clearance"]
        if clearance > 3.0:
            clearance_bonus = 0.2
        elif clearance > 2.0:
            clearance_bonus = 0.1
        elif clearance > 1.0:
            clearance_bonus = 0.05
        else:
            clearance_bonus = 0.0
        
        dynamic_penalty = 0.0
        for obs in obstacles:
            if obs.get("direction") == zone and obs.get("type") == "dynamic":
                if obs.get("distance", 5.0) < 2.0:
                    dynamic_penalty += 0.15
        
        ground_penalty = 0.0
        for obs in obstacles:
            if obs.get("direction") == zone and obs.get("type") == "ground":
                ground_penalty += 0.1
        
        total_score = base_score + clearance_bonus - dynamic_penalty - ground_penalty
        
        return max(0.0, min(1.0, total_score))
    
    def _apply_special_rules(
        self,
        options: List[RouteOption],
        obstacles: List[Dict],
        trajectories: List[Dict],
        left_status: Dict,
        center_status: Dict,
        right_status: Dict
    ) -> List[RouteOption]:
        if trajectories:
            for traj in trajectories:
                ttc = traj.get("ttc")
                direction = traj.get("direction")
                obj_dir = traj.get("object_direction", "center")
                
                if ttc and ttc < 2.0 and direction == "approaching":
                    if obj_dir == "left":
                        options = [o for o in options if o.direction != Direction.LEFT]
                    elif obj_dir == "right":
                        options = [o for o in options if o.direction != Direction.RIGHT]
                    elif obj_dir == "center":
                        options = [o for o in options if o.direction != Direction.FORWARD]
        
        if left_status["is_blocked"] and right_status["is_blocked"]:
            options = [o for o in options if o.direction not in [Direction.LEFT, Direction.RIGHT]]
            
            for opt in options:
                if opt.direction == Direction.STOP:
                    opt.priority = 5
                    opt.reason = "左右两侧均不可通行，请停止"
        
        center_ground_hazards = [
            o for o in obstacles
            if o.get("direction") == "center" and o.get("type") == "ground"
        ]
        if center_ground_hazards:
            for opt in options:
                if opt.direction == Direction.FORWARD:
                    opt.safety_score *= 0.5
                    opt.reason = "前方有地面异常，建议绕行"
        
        return options
    
    def _generate_instruction(
        self, 
        option: RouteOption, 
        obstacles: List[Dict]
    ) -> str:
        direction_map = {
            Direction.STOP: "请立即停止",
            Direction.FORWARD: "可以继续前进",
            Direction.LEFT: "请向左绕行",
            Direction.RIGHT: "请向右绕行",
            Direction.SLOW: "请放慢脚步",
            Direction.BACK: "请后退"
        }
        
        action = direction_map.get(option.direction, "请注意")
        
        if option.reason:
            instruction = f"{action}，{option.reason}。"
        else:
            instruction = f"{action}。"
        
        if option.clearance > 0 and option.clearance < 3.0:
            instruction = instruction.rstrip("。")
            instruction += f"，通行空间约{option.clearance:.1f}米。"
        
        return instruction
    
    def _direction_to_angle(self, direction: Direction) -> int:
        angle_map = {
            Direction.FORWARD: 0,
            Direction.LEFT: -45,
            Direction.RIGHT: 45,
            Direction.BACK: 180,
            Direction.STOP: 0,
            Direction.SLOW: 0
        }
        return angle_map.get(direction, 0)