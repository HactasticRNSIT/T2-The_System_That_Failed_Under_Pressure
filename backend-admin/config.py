"""
Urban Resilience Platform — Core Configuration
Part 1: Core Backend Foundation
"""

from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import List, Optional
from functools import lru_cache
import secrets


class Settings(BaseSettings):
    # ─── Application ───────────────────────────────────────────
    APP_NAME: str = "Urban Resilience Platform"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = Field(default="development", env="APP_ENV")
    DEBUG: bool = Field(default=False, env="DEBUG")
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_hex(32))
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_HOSTS: List[str] = ["*"]

    # ─── Database ──────────────────────────────────────────────
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/urban_resilience",
        env="DATABASE_URL"
    )
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600

    # ─── Redis ─────────────────────────────────────────────────
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    REDIS_CACHE_DB: int = 1
    REDIS_SESSION_DB: int = 2
    REDIS_QUEUE_DB: int = 3
    REDIS_PUBSUB_DB: int = 4
    REDIS_TTL_DEFAULT: int = 3600
    REDIS_TTL_SESSION: int = 86400

    # ─── JWT Authentication ─────────────────────────────────────
    JWT_SECRET_KEY: str = Field(default_factory=lambda: secrets.token_hex(64))
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    JWT_ISSUER: str = "urban-resilience-platform"

    # ─── Security ──────────────────────────────────────────────
    BCRYPT_ROUNDS: int = 12
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 30
    OTP_EXPIRE_MINUTES: int = 10
    API_KEY_PREFIX: str = "urp_"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]

    # ─── Rate Limiting ─────────────────────────────────────────
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_AUTH: str = "10/minute"
    RATE_LIMIT_GPS: str = "300/minute"
    RATE_LIMIT_VOICE: str = "30/minute"

    # ─── Google APIs ───────────────────────────────────────────
    GOOGLE_MAPS_API_KEY: str = Field(default="", env="GOOGLE_MAPS_API_KEY")
    GOOGLE_SPEECH_API_KEY: str = Field(default="", env="GOOGLE_SPEECH_API_KEY")
    GOOGLE_TTS_API_KEY: str = Field(default="", env="GOOGLE_TTS_API_KEY")
    GOOGLE_DIRECTIONS_API_KEY: str = Field(default="", env="GOOGLE_DIRECTIONS_API_KEY")

    # ─── OpenAI ────────────────────────────────────────────────
    OPENAI_API_KEY: str = Field(default="", env="OPENAI_API_KEY")
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # ─── Firebase ──────────────────────────────────────────────
    FIREBASE_CREDENTIALS_PATH: str = Field(default="", env="FIREBASE_CREDENTIALS_PATH")
    FIREBASE_PROJECT_ID: str = Field(default="", env="FIREBASE_PROJECT_ID")

    # ─── Celery (Task Queue) ───────────────────────────────────
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/3", env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/3", env="CELERY_RESULT_BACKEND")
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"

    # ─── WebSocket ─────────────────────────────────────────────
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_MAX_CONNECTIONS_PER_USER: int = 5
    WS_PING_TIMEOUT: int = 60

    # ─── Simulation Engine ─────────────────────────────────────
    SIMULATION_TICK_INTERVAL_MS: int = 1000
    SIMULATION_MAX_STEPS: int = 10000
    SIMULATION_BUFFER_SIZE: int = 100

    # ─── Bangalore GIS ─────────────────────────────────────────
    BANGALORE_CENTER_LAT: float = 12.9716
    BANGALORE_CENTER_LNG: float = 77.5946
    BANGALORE_RADIUS_KM: float = 30.0
    BANGALORE_DISTRICTS_COUNT: int = 18
    BANGALORE_WARDS_COUNT: int = 198

    # ─── AI / ML ───────────────────────────────────────────────
    FATIGUE_MODEL_VERSION: str = "v1.0"
    RESILIENCE_SCORING_INTERVAL_MINUTES: int = 15
    PREDICTION_CONFIDENCE_THRESHOLD: float = 0.75
    ANOMALY_DETECTION_SENSITIVITY: float = 0.85

    # ─── Logging ───────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE_PATH: str = "logs/app.log"
    LOG_ROTATION: str = "1 day"
    LOG_RETENTION: str = "30 days"

    # ─── Monitoring ────────────────────────────────────────────
    PROMETHEUS_ENABLED: bool = True
    PROMETHEUS_PORT: int = 9090
    OTLP_ENDPOINT: str = Field(default="http://localhost:4317", env="OTLP_ENDPOINT")

    # ─── Storage ───────────────────────────────────────────────
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 50
    AUDIO_MAX_DURATION_SECONDS: int = 300

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


# ─── Role Definitions ──────────────────────────────────────────
class Roles:
    SUPER_ADMIN = "super_admin"
    CITY_OPERATIONS_HEAD = "city_operations_head"
    DISTRICT_COORDINATOR = "district_coordinator"
    WARD_SUPERVISOR = "ward_supervisor"
    SANITATION_WORKER = "sanitation_worker"
    EMERGENCY_CREW = "emergency_crew"
    TRAFFIC_OFFICER = "traffic_officer"
    ROUTE_MANAGER = "route_manager"
    DISASTER_OPERATOR = "disaster_operator"
    AI_ANALYST = "ai_analyst"

    ALL = [
        SUPER_ADMIN, CITY_OPERATIONS_HEAD, DISTRICT_COORDINATOR,
        WARD_SUPERVISOR, SANITATION_WORKER, EMERGENCY_CREW,
        TRAFFIC_OFFICER, ROUTE_MANAGER, DISASTER_OPERATOR, AI_ANALYST
    ]

    ADMIN_ROLES = [SUPER_ADMIN, CITY_OPERATIONS_HEAD]
    COORDINATOR_ROLES = [DISTRICT_COORDINATOR, WARD_SUPERVISOR, ROUTE_MANAGER]
    FIELD_ROLES = [SANITATION_WORKER, EMERGENCY_CREW, TRAFFIC_OFFICER, DISASTER_OPERATOR]
    ANALYST_ROLES = [AI_ANALYST]


# ─── Permission Matrix ──────────────────────────────────────────
ROLE_PERMISSIONS = {
    Roles.SUPER_ADMIN: ["*"],  # All permissions
    Roles.CITY_OPERATIONS_HEAD: [
        "workers:read", "workers:write", "workers:delete",
        "tasks:read", "tasks:write", "tasks:delete",
        "events:read", "events:write",
        "simulation:read", "simulation:write",
        "analytics:read", "reports:export",
        "alerts:manage", "leaderboard:read",
    ],
    Roles.DISTRICT_COORDINATOR: [
        "workers:read", "workers:write",
        "tasks:read", "tasks:write",
        "events:read", "events:write",
        "analytics:read", "leaderboard:read",
        "alerts:read",
    ],
    Roles.WARD_SUPERVISOR: [
        "workers:read", "tasks:read", "tasks:write",
        "events:read", "alerts:read",
    ],
    Roles.SANITATION_WORKER: [
        "tasks:read", "tasks:update_own",
        "voice:submit", "gps:submit", "sos:trigger",
    ],
    Roles.EMERGENCY_CREW: [
        "tasks:read", "tasks:update_own",
        "voice:submit", "gps:submit", "sos:trigger",
        "emergency:respond",
    ],
    Roles.TRAFFIC_OFFICER: [
        "tasks:read", "tasks:update_own",
        "voice:submit", "gps:submit", "events:report",
    ],
    Roles.ROUTE_MANAGER: [
        "workers:read", "tasks:read", "tasks:write",
        "routes:manage", "gps:read",
    ],
    Roles.DISASTER_OPERATOR: [
        "tasks:read", "tasks:write",
        "voice:submit", "gps:submit", "sos:trigger",
        "emergency:respond", "alerts:read",
    ],
    Roles.AI_ANALYST: [
        "analytics:read", "reports:export",
        "simulation:read", "predictions:read",
        "leaderboard:read",
    ],
}


# ─── Bangalore Districts ────────────────────────────────────────
BANGALORE_DISTRICTS = [
    {"id": 1, "name": "Yelahanka", "lat": 13.1005, "lng": 77.5963},
    {"id": 2, "name": "Dasarahalli", "lat": 13.0437, "lng": 77.5141},
    {"id": 3, "name": "Rajarajeshwari Nagar", "lat": 12.9200, "lng": 77.5194},
    {"id": 4, "name": "Bommanahalli", "lat": 12.9064, "lng": 77.6121},
    {"id": 5, "name": "BTM Layout", "lat": 12.9166, "lng": 77.6101},
    {"id": 6, "name": "JP Nagar", "lat": 12.9063, "lng": 77.5857},
    {"id": 7, "name": "Mahadevapura", "lat": 12.9955, "lng": 77.6990},
    {"id": 8, "name": "KR Puram", "lat": 13.0121, "lng": 77.6931},
    {"id": 9, "name": "Shivajinagar", "lat": 12.9814, "lng": 77.5980},
    {"id": 10, "name": "Gandhinagar", "lat": 12.9784, "lng": 77.5722},
    {"id": 11, "name": "Shanti Nagar", "lat": 12.9626, "lng": 77.6009},
    {"id": 12, "name": "Pulakeshi Nagar", "lat": 12.9868, "lng": 77.6208},
    {"id": 13, "name": "Sarvagna Nagar", "lat": 13.0007, "lng": 77.6438},
    {"id": 14, "name": "Hebbal", "lat": 13.0351, "lng": 77.5968},
    {"id": 15, "name": "Byatarayanapura", "lat": 13.0617, "lng": 77.5728},
    {"id": 16, "name": "Yeshwanthpura", "lat": 13.0220, "lng": 77.5399},
    {"id": 17, "name": "Chickpet", "lat": 12.9723, "lng": 77.5761},
    {"id": 18, "name": "Basavanagudi", "lat": 12.9406, "lng": 77.5740},
]


# ─── Supported Languages ────────────────────────────────────────
SUPPORTED_LANGUAGES = {
    "en": {"name": "English", "google_code": "en-IN", "tts_voice": "en-IN-Standard-A"},
    "hi": {"name": "Hindi", "google_code": "hi-IN", "tts_voice": "hi-IN-Standard-A"},
    "kn": {"name": "Kannada", "google_code": "kn-IN", "tts_voice": "kn-IN-Standard-A"},
}


# ─── Emergency Keyword Patterns ─────────────────────────────────
EMERGENCY_KEYWORDS = {
    "en": ["emergency", "sos", "help", "danger", "flood", "fire", "accident", "overflow", "blocked", "injured"],
    "hi": ["आपातकाल", "मदद", "खतरा", "बाढ़", "आग", "दुर्घटना", "अवरुद्ध"],
    "kn": ["ತುರ್ತು", "ಸಹಾಯ", "ಅಪಾಯ", "ಪ್ರವಾಹ", "ಬೆಂಕಿ", "ಅಪಘಾತ"],
}