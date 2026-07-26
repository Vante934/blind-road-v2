import logging
import numpy as np
from typing import Optional, List, Tuple
from dataclasses import dataclass
from collections import deque
import time

logger = logging.getLogger(__name__)


@dataclass
class TrajectoryState:
    x: float
    y: float
    
    vx: float
    vy: float
    
    ax: float = 0.0
    ay: float = 0.0
    
    covariance: np.ndarray = None
    
    timestamp: float = 0.0


@dataclass
class TrajectoryPrediction:
    current_state: TrajectoryState
    
    speed: float
    acceleration: float
    direction: str
    
    ttc: Optional[float]
    predicted_positions: List[Tuple[float, float]]
    
    danger_score: float
    confidence: float


class KalmanTracker:
    def __init__(
        self,
        process_noise: float = 0.01,
        measurement_noise: float = 0.1,
        pixel_to_meter: float = 0.01,
    ):
        self.process_noise = process_noise
        self.measurement_noise = measurement_noise
        self.pixel_to_meter = pixel_to_meter
        
        self.state: Optional[TrajectoryState] = None
        
        self.history: deque = deque(maxlen=30)
        
        self.initialized = False
    
    def update(
        self, 
        measurement: Tuple[float, float],
        timestamp: float,
        distance: Optional[float] = None
    ) -> TrajectoryPrediction:
        if not self.initialized:
            self._initialize(measurement, timestamp)
            return self._build_prediction()
        
        dt = timestamp - self.state.timestamp
        if dt <= 0:
            logger.warning("时间戳异常")
            return self._build_prediction()
        
        predicted_state = self._predict(dt)
        
        updated_state = self._update(predicted_state, measurement)
        
        updated_state.timestamp = timestamp
        self.state = updated_state
        
        self.history.append((timestamp, measurement[0], measurement[1]))
        
        prediction = self._build_prediction(distance)
        
        return prediction
    
    def _initialize(self, measurement: Tuple[float, float], timestamp: float):
        self.state = TrajectoryState(
            x=measurement[0],
            y=measurement[1],
            vx=0.0,
            vy=0.0,
            ax=0.0,
            ay=0.0,
            timestamp=timestamp,
            covariance=np.eye(6) * 1.0
        )
        self.initialized = True
        logger.debug("卡尔曼滤波器已初始化")
    
    def _predict(self, dt: float) -> TrajectoryState:
        F = np.array([
            [1, 0, dt, 0,  0.5*dt**2, 0],
            [0, 1, 0,  dt, 0,         0.5*dt**2],
            [0, 0, 1,  0,  dt,        0],
            [0, 0, 0,  1,  0,         dt],
            [0, 0, 0,  0,  1,         0],
            [0, 0, 0,  0,  0,         1]
        ])
        
        X = np.array([
            self.state.x,
            self.state.y,
            self.state.vx,
            self.state.vy,
            self.state.ax,
            self.state.ay
        ])
        
        X_pred = F @ X
        
        Q = np.eye(6) * self.process_noise
        P_pred = F @ self.state.covariance @ F.T + Q
        
        predicted = TrajectoryState(
            x=X_pred[0],
            y=X_pred[1],
            vx=X_pred[2],
            vy=X_pred[3],
            ax=X_pred[4],
            ay=X_pred[5],
            covariance=P_pred,
            timestamp=self.state.timestamp
        )
        
        return predicted
    
    def _update(
        self, 
        predicted: TrajectoryState, 
        measurement: Tuple[float, float]
    ) -> TrajectoryState:
        H = np.array([
            [1, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0]
        ])
        
        Z = np.array([measurement[0], measurement[1]])
        
        X_pred = np.array([
            predicted.x,
            predicted.y,
            predicted.vx,
            predicted.vy,
            predicted.ax,
            predicted.ay
        ])
        
        R = np.eye(2) * self.measurement_noise
        
        S = H @ predicted.covariance @ H.T + R
        K = predicted.covariance @ H.T @ np.linalg.inv(S)
        
        innovation = Z - H @ X_pred
        
        X_updated = X_pred + K @ innovation
        
        P_updated = (np.eye(6) - K @ H) @ predicted.covariance
        
        updated = TrajectoryState(
            x=X_updated[0],
            y=X_updated[1],
            vx=X_updated[2],
            vy=X_updated[3],
            ax=X_updated[4],
            ay=X_updated[5],
            covariance=P_updated,
            timestamp=predicted.timestamp
        )
        
        return updated
    
    def _build_prediction(self, distance: Optional[float] = None) -> TrajectoryPrediction:
        if not self.state:
            return TrajectoryPrediction(
                current_state=None,
                speed=0,
                acceleration=0,
                direction="stationary",
                ttc=None,
                predicted_positions=[],
                danger_score=0,
                confidence=0
            )
        
        vx_pixel = self.state.vx
        vy_pixel = self.state.vy
        
        speed_pixel = np.sqrt(vx_pixel**2 + vy_pixel**2)
        speed_meter = speed_pixel * self.pixel_to_meter
        
        ax_pixel = self.state.ax
        ay_pixel = self.state.ay
        
        accel_pixel = np.sqrt(ax_pixel**2 + ay_pixel**2)
        accel_meter = accel_pixel * self.pixel_to_meter
        
        if vy_pixel > 0.01:
            direction = "approaching"
        elif vy_pixel < -0.01:
            direction = "receding"
        else:
            direction = "stationary"
        
        ttc = None
        
        if distance and direction == "approaching":
            if speed_meter > 0.1:
                ttc = distance / speed_meter
                
                if accel_meter > 0.1:
                    discriminant = speed_meter**2 + 2 * accel_meter * distance
                    if discriminant > 0:
                        ttc = (-speed_meter + np.sqrt(discriminant)) / accel_meter
                
                if ttc < 0 or ttc > 30:
                    ttc = None
        
        predicted_positions = []
        
        for t in np.linspace(0.1, 1.0, 10):
            future_x = self.state.x + self.state.vx * t + 0.5 * self.state.ax * t**2
            future_y = self.state.y + self.state.vy * t + 0.5 * self.state.ay * t**2
            predicted_positions.append((future_x, future_y))
        
        danger_score = self._calculate_danger(
            speed_meter, accel_meter, ttc, direction, distance
        )
        
        if self.state.covariance is not None:
            position_variance = self.state.covariance[0, 0] + self.state.covariance[1, 1]
            confidence = 1.0 / (1.0 + position_variance)
        else:
            confidence = 0.5
        
        return TrajectoryPrediction(
            current_state=self.state,
            speed=round(speed_meter, 3),
            acceleration=round(accel_meter, 3),
            direction=direction,
            ttc=round(ttc, 2) if ttc else None,
            predicted_positions=predicted_positions,
            danger_score=round(danger_score, 3),
            confidence=round(confidence, 3)
        )
    
    def _calculate_danger(
        self,
        speed: float,
        accel: float,
        ttc: Optional[float],
        direction: str,
        distance: Optional[float]
    ) -> float:
        if direction == "receding":
            return 0.0
        
        if direction == "stationary":
            return 0.1
        
        score = 0.0
        
        if ttc is not None:
            if ttc <= 1.0:
                score += 0.6
            elif ttc <= 2.0:
                score += 0.4
            elif ttc <= 3.0:
                score += 0.25
            elif ttc <= 5.0:
                score += 0.15
        
        if speed > 3.0:
            score += 0.2
        elif speed > 1.5:
            score += 0.12
        elif speed > 0.5:
            score += 0.06
        
        if accel > 1.0:
            score += 0.15
        elif accel > 0.3:
            score += 0.08
        
        if distance:
            if distance < 1.0:
                score += 0.05
        
        return min(score, 1.0)