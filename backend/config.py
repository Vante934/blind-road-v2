from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = True
    
    DATABASE_URL: str = "sqlite:///./backend.db"
    
    BAIDU_APP_ID: str = ""
    BAIDU_API_KEY: str = ""
    BAIDU_SECRET_KEY: str = ""
    AUDIO_ENGINE: str = "baidu"
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             
    DISTANCE_LEVEL1: float = 0.5
    DISTANCE_LEVEL2: float = 1.5
    DISTANCE_LEVEL3: float = 3.0
    
    MODULE_VISION_ENABLED: bool = True
    YOLO_MODEL_PATH: str = "models/best.pt"
    YOLO_DEVICE: str = "cpu"
    YOLO_CONFIDENCE: float = 0.5
    YOLO_CONF: float = 0.25
    YOLO_IMGSZ: int = 320
    
    MODULE_TRAJECTORY_ENABLED: bool = False
    TRAJECTORY_WINDOW_SIZE: int = 20
    
    MODULE_ENVIRONMENT_ENABLED: bool = False
    
    MODULE_ROUTE_PLANNING_ENABLED: bool = False
    
    CAMERA_FOCAL_LENGTH: float = 1000.0
    CAMERA_HEIGHT: float = 1.5
    ENABLE_MONOCULAR_DEPTH: bool = False
    
    FRAME_SKIP_INTERVAL: int = 0
    IMAGE_DOWNSAMPLE: bool = False
    IMAGE_TARGET_SIZE: tuple = (640, 480)
    
    SECRET_KEY: str = "your-secret-key-here"
    JWT_SECRET_KEY: str = "your-secret-key-change-this"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    class Config:
        env_file = ".env"


settings = Settings()