from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict


class AudioData(BaseModel):
    audio_base64: str
    audio_format: str
    sample_rate: int


class SensorData(BaseModel):
    device_id: str
    timestamp: float
    tof_distance: Optional[float] = None
    tof_direction: Optional[str] = "rear"
    audio_data: Optional[AudioData] = None
    video_frame: Optional[str] = None
    session_id: Optional[str] = None


class WarningCommand(BaseModel):
    type: str
    warning_level: int
    warning_level_name: str
    tts_text: str
    vibration_intensity: int
    vibration_pattern: str
    distance: Optional[float] = None
    direction: Optional[str] = None
    timestamp: float


class PipelineResponse(BaseModel):
    success: bool
    message: str
    data: Dict


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    nickname: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    email: str
    nickname: Optional[str]
    is_active: bool


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: Optional[int] = None


class GuestLoginResponse(BaseModel):
    device_id: str
    mode: str


class LoginResponse(BaseModel):
    token: str
    user_id: int
    nickname: Optional[str]


class EmergencyContact(BaseModel):
    name: str
    phone: str


class EmergencyResponse(BaseModel):
    success: bool


class SystemStatus(BaseModel):
    status: str
    version: str
    modules: Dict[str, bool]
    uptime: float


class BlindRoadState(BaseModel):
    is_detected: bool
    direction: str
    quality: str
    anomalies: List[Dict]