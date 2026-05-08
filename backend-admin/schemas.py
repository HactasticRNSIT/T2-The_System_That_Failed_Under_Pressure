"""
Urban Resilience Platform — Pydantic Schemas
All request/response models for Parts 1–14
"""

from pydantic import BaseModel, Field, EmailStr, validator, field_validator
from typing import Optional, List, Any, Dict
from datetime import datetime
from uuid import UUID
import enum


# ══════════════════════════════════════════════════════════════════
# BASE SCHEMAS
# ══════════════════════════════════════════════════════════════════

class BaseResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None
    request_id: Optional[str] = None

    class Config:
        from_attributes = True


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: Optional[str] = None
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class PaginatedResponse(BaseResponse):
    total: int
    page: int
    page_size: int
    total_pages: int
    data: List[Any]


class GeoPoint(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy_m: Optional[float] = None


class DateRangeFilter(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


# ══════════════════════════════════════════════════════════════════
# PART 2 — WORKER SCHEMAS
# ══════════════════════════════════════════════════════════════════

class WorkerRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone: str = Field(..., pattern=r"^\+?[1-9]\d{9,14}$")
    password: str = Field(..., min_length=8, max_length=100)
    role: str
    department: Optional[str] = None
    district_id: Optional[int] = None
    ward_id: Optional[int] = None
    preferred_language: str = Field(default="en", pattern="^(en|hi|kn)$")
    shift_type: str = Field(default="morning")
    skills: Optional[List[str]] = []
    experience_years: Optional[float] = 0
    certifications: Optional[List[str]] = []
    supervisor_id: Optional[UUID] = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        import re
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must have an uppercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must have a digit")
        return v


class WorkerLoginRequest(BaseModel):
    email: EmailStr
    password: str
    device_fingerprint: Optional[str] = None
    mfa_token: Optional[str] = None


class WorkerLoginResponse(BaseResponse):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    worker: "WorkerProfileResponse"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class WorkerProfileResponse(BaseModel):
    id: UUID
    worker_code: str
    full_name: str
    email: str
    phone: Optional[str]
    role: str
    department: Optional[str]
    district_id: Optional[int]
    ward_id: Optional[int]
    operational_status: str
    health_score: float
    resilience_score: float
    fatigue_score: float
    productivity_score: float
    preferred_language: str
    shift_type: str
    is_active: bool
    is_verified: bool
    last_login_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class WorkerUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    phone: Optional[str] = None
    department: Optional[str] = None
    district_id: Optional[int] = None
    ward_id: Optional[int] = None
    preferred_language: Optional[str] = Field(None, pattern="^(en|hi|kn)$")
    shift_type: Optional[str] = None
    skills: Optional[List[str]] = None
    certifications: Optional[List[str]] = None
    gps_device_id: Optional[str] = None


class WorkerStatusUpdate(BaseModel):
    operational_status: str
    reason: Optional[str] = None
    location: Optional[GeoPoint] = None


class OTPVerifyRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)


class MFASetupResponse(BaseResponse):
    totp_secret: str
    totp_uri: str
    backup_codes: List[str]


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


# ══════════════════════════════════════════════════════════════════
# PART 3 — GPS & TRACKING SCHEMAS
# ══════════════════════════════════════════════════════════════════

class GPSUpdateRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy_m: Optional[float] = None
    altitude_m: Optional[float] = None
    speed_kmh: Optional[float] = None
    bearing_degrees: Optional[float] = None
    battery_level: Optional[float] = Field(None, ge=0, le=100)
    device_id: Optional[str] = None
    timestamp: Optional[datetime] = None


class GPSBatchRequest(BaseModel):
    locations: List[GPSUpdateRequest] = Field(..., max_length=100)


class WorkerLocationResponse(BaseModel):
    worker_id: UUID
    full_name: str
    role: str
    latitude: float
    longitude: float
    operational_status: str
    fatigue_score: float
    district_id: Optional[int]
    updated_at: datetime


class NearbyWorkersRequest(BaseModel):
    latitude: float
    longitude: float
    radius_m: float = Field(default=1000, ge=100, le=10000)
    status_filter: Optional[List[str]] = None
    role_filter: Optional[List[str]] = None


# ══════════════════════════════════════════════════════════════════
# PART 4 — SIMULATION SCHEMAS
# ══════════════════════════════════════════════════════════════════

class SimulationTriggerRequest(BaseModel):
    event_type: str
    district_ids: List[int] = Field(..., min_length=1)
    intensity: float = Field(..., ge=0.0, le=1.0)
    duration_minutes: int = Field(default=60, ge=5, le=1440)
    time_acceleration: float = Field(default=1.0, ge=0.1, le=100.0)
    custom_parameters: Optional[Dict[str, Any]] = None
    scenario_name: Optional[str] = None
    save_as_template: bool = False


class SimulationStatusResponse(BaseResponse):
    run_id: UUID
    status: str
    event_type: str
    current_stress_level: float
    affected_districts: List[int]
    active_since: datetime
    elapsed_minutes: float
    ai_recommendations: Optional[List[str]] = None


class SimulationReplayRequest(BaseModel):
    run_id: UUID
    start_step: int = 0
    speed_multiplier: float = Field(default=1.0, ge=0.1, le=10.0)


# ══════════════════════════════════════════════════════════════════
# PART 5 — RESILIENCE DNA SCHEMAS
# ══════════════════════════════════════════════════════════════════

class ResilienceScoreResponse(BaseModel):
    district_id: int
    district_name: str
    scoring_period: str
    adaptability_score: float
    recovery_score: float
    pressure_tolerance_score: float
    sustainability_score: float
    emergency_readiness_score: float
    infrastructure_stability_score: float
    workforce_stability_score: float
    waste_management_score: float
    public_safety_score: float
    overall_health_score: float
    district_rank: Optional[int]
    city_percentile: Optional[float]
    score_delta: Optional[float]
    ai_confidence: Optional[float]
    score_explanation: Optional[Dict] = None
    calculated_at: datetime

    class Config:
        from_attributes = True


class ResilienceLeaderboardEntry(BaseModel):
    rank: int
    district_id: int
    district_name: str
    overall_health_score: float
    score_delta: float
    trend: str
    badges: List[str]


# ══════════════════════════════════════════════════════════════════
# PART 6 — FATIGUE SCHEMAS
# ══════════════════════════════════════════════════════════════════

class FatigueMetricResponse(BaseModel):
    worker_id: UUID
    physical_exhaustion: float
    cognitive_overload: float
    burnout_probability: float
    shift_overload_risk: float
    hydration_risk: float
    heat_stress_score: float
    route_difficulty_score: float
    emergency_fatigue: float
    overall_fatigue_score: float
    predicted_fatigue_1h: Optional[float]
    predicted_fatigue_4h: Optional[float]
    injury_probability: Optional[float]
    recommended_break_minutes: Optional[int]
    recovery_efficiency: Optional[float]
    recorded_at: datetime

    class Config:
        from_attributes = True


class FatigueAlertThresholds(BaseModel):
    physical_exhaustion_threshold: float = 70.0
    burnout_threshold: float = 0.75
    injury_risk_threshold: float = 0.6
    mandatory_break_fatigue: float = 80.0


class BreakRecommendation(BaseModel):
    worker_id: UUID
    recommended_break_minutes: int
    urgency: str  # low, medium, high, immediate
    reason: str
    estimated_recovery_pct: float
    nearest_rest_location: Optional[GeoPoint] = None


class ShiftAssignmentRequest(BaseModel):
    worker_id: UUID
    shift_type: str
    start_time: datetime
    end_time: datetime
    district_id: Optional[int] = None
    notes: Optional[str] = None


class CrewBalancingRequest(BaseModel):
    district_id: int
    date: datetime
    optimize_for: str = Field(default="workload", pattern="^(workload|fatigue|distance)$")


# ══════════════════════════════════════════════════════════════════
# PART 7 — VOICE SCHEMAS
# ══════════════════════════════════════════════════════════════════

class VoiceCommandRequest(BaseModel):
    language: str = Field(default="en", pattern="^(en|hi|kn)$")
    audio_url: Optional[str] = None
    raw_text: Optional[str] = None  # For text-based command testing
    district_id: Optional[int] = None
    location: Optional[GeoPoint] = None


class VoiceCommandResponse(BaseResponse):
    command_id: UUID
    transcript: str
    intent: str
    entities: Dict[str, Any]
    confidence_score: float
    is_emergency: bool
    emergency_keywords: List[str]
    action_taken: Optional[str]
    action_result: Optional[Dict]
    tts_response_url: Optional[str]


class TTSRequest(BaseModel):
    text: str = Field(..., max_length=5000)
    language: str = Field(default="en", pattern="^(en|hi|kn)$")
    voice_type: str = Field(default="standard", pattern="^(standard|premium|wavenet)$")
    speaking_rate: float = Field(default=1.0, ge=0.5, le=2.0)
    pitch: float = Field(default=0.0, ge=-20.0, le=20.0)


class TTSResponse(BaseResponse):
    audio_url: str
    duration_seconds: float
    language: str


# ══════════════════════════════════════════════════════════════════
# PART 8 — MAPS & GIS SCHEMAS
# ══════════════════════════════════════════════════════════════════

class RouteOptimizationRequest(BaseModel):
    origin: GeoPoint
    destinations: List[GeoPoint] = Field(..., min_length=1, max_length=25)
    optimize_for: str = Field(default="time", pattern="^(time|distance|fatigue)$")
    avoid_congestion: bool = True
    worker_id: Optional[UUID] = None
    consider_fatigue: bool = False


class RouteOptimizationResponse(BaseResponse):
    optimized_route: List[GeoPoint]
    total_distance_km: float
    estimated_duration_minutes: float
    fatigue_impact_score: Optional[float]
    congestion_avoided: bool
    waypoints_reordered: bool


class GeoFenceCheckRequest(BaseModel):
    worker_id: UUID
    location: GeoPoint


class HeatmapRequest(BaseModel):
    district_ids: Optional[List[int]] = None
    heatmap_type: str = Field(..., pattern="^(fatigue|stress|crowd|waste|congestion)$")
    period_hours: int = Field(default=24, ge=1, le=168)


class DistrictMappingResponse(BaseModel):
    district_id: int
    name: str
    centroid_lat: float
    centroid_lng: float
    stress_level: float
    congestion_level: float
    crowd_density: float
    waste_pressure: float
    resilience_score: float
    active_workers: int
    active_events: int


# ══════════════════════════════════════════════════════════════════
# PART 9 — EVENT TRACKING SCHEMAS
# ══════════════════════════════════════════════════════════════════

class EventCreateRequest(BaseModel):
    event_type: str
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    district_id: int
    ward_id: Optional[int] = None
    location: Optional[GeoPoint] = None
    radius_impact_m: Optional[float] = None
    severity: Optional[str] = None
    started_at: Optional[datetime] = None
    is_voice_created: bool = False


class EventResponse(BaseModel):
    id: UUID
    event_type: str
    title: str
    description: Optional[str]
    district_id: int
    severity: Optional[str]
    ai_severity_score: Optional[float]
    is_verified: bool
    is_resolved: bool
    started_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class EventClusterResponse(BaseModel):
    cluster_id: str
    event_count: int
    dominant_type: str
    severity: str
    centroid: GeoPoint
    radius_m: float
    events: List[EventResponse]


# ══════════════════════════════════════════════════════════════════
# PART 10 — TASK SCHEMAS
# ══════════════════════════════════════════════════════════════════

class TaskCreateRequest(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    task_type: str
    priority: str = Field(default="medium", pattern="^(low|medium|high|critical|emergency)$")
    assigned_to: Optional[UUID] = None
    district_id: Optional[int] = None
    ward_id: Optional[int] = None
    location: Optional[GeoPoint] = None
    due_at: Optional[datetime] = None
    sla_deadline: Optional[datetime] = None
    estimated_duration_minutes: Optional[int] = None
    shift_id: Optional[UUID] = None
    event_id: Optional[UUID] = None
    is_emergency: bool = False
    is_voice_created: bool = False
    voice_command_id: Optional[UUID] = None


class TaskUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[UUID] = None
    due_at: Optional[datetime] = None
    notes: Optional[str] = None


class TaskResponse(BaseModel):
    id: UUID
    task_code: str
    title: str
    task_type: str
    priority: str
    status: str
    assigned_to: Optional[UUID]
    district_id: Optional[int]
    due_at: Optional[datetime]
    sla_deadline: Optional[datetime]
    is_emergency: bool
    is_voice_created: bool
    escalation_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class TaskEscalationRequest(BaseModel):
    task_id: UUID
    reason: str
    escalate_to: Optional[UUID] = None
    priority_override: Optional[str] = None


# ══════════════════════════════════════════════════════════════════
# PART 11 — LEADERBOARD SCHEMAS
# ══════════════════════════════════════════════════════════════════

class LeaderboardEntry(BaseModel):
    rank: int
    entity_id: str
    entity_name: str
    score: float
    score_delta: float
    trend: str
    badges: List[str]
    category: str


class LeaderboardResponse(BaseResponse):
    leaderboard_type: str
    period: str
    entries: List[LeaderboardEntry]
    generated_at: datetime


class HealthScoreResponse(BaseModel):
    worker_id: UUID
    period: str
    productivity_score: float
    resilience_score: float
    recovery_score: float
    emergency_response_score: float
    attendance_score: float
    overall_health_meter: float
    city_rank: Optional[int]
    percentile: Optional[float]
    score_delta: Optional[float]
    calculated_at: datetime

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════════════
# PART 12 — ALERTS & PREDICTIONS SCHEMAS
# ══════════════════════════════════════════════════════════════════

class AlertResponse(BaseModel):
    id: UUID
    alert_type: str
    severity: str
    title: str
    message: str
    is_ai_generated: bool
    ai_confidence: Optional[float]
    district_id: Optional[int]
    worker_id: Optional[UUID]
    is_acknowledged: bool
    is_resolved: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AlertAcknowledgeRequest(BaseModel):
    alert_id: UUID
    notes: Optional[str] = None


class PredictionResponse(BaseModel):
    prediction_type: str
    district_id: Optional[int]
    entity_id: Optional[str]
    prediction_value: float
    confidence_score: float
    risk_level: str
    contributing_factors: Dict[str, float]
    recommended_interventions: List[str]
    horizon_hours: float
    predicted_at: datetime

    class Config:
        from_attributes = True


class AnomalyResponse(BaseModel):
    entity_type: str
    entity_id: str
    anomaly_type: str
    severity: float
    description: str
    detected_value: float
    expected_value: float
    z_score: float
    detected_at: datetime


# ══════════════════════════════════════════════════════════════════
# PART 13 — DASHBOARD SCHEMAS
# ══════════════════════════════════════════════════════════════════

class CityDashboardResponse(BaseResponse):
    total_workers_active: int
    total_districts: int
    city_stress_level: float
    city_resilience_score: float
    active_events: int
    active_alerts: int
    critical_alerts: int
    workers_fatigued: int
    waste_overflow_zones: int
    congested_roads: int
    ongoing_simulations: int
    last_updated: datetime


class DistrictDashboardResponse(BaseResponse):
    district_id: int
    district_name: str
    active_workers: int
    stress_level: float
    resilience_score: float
    congestion_level: float
    waste_pressure: float
    active_events: int
    active_alerts: int
    top_worker: Optional[WorkerProfileResponse]
    recent_events: List[EventResponse]
    last_updated: datetime


class KPIResponse(BaseModel):
    kpi_name: str
    value: float
    unit: str
    change_pct: float
    trend: str
    period: str
    benchmark: Optional[float] = None


class DashboardKPIsResponse(BaseResponse):
    kpis: List[KPIResponse]
    generated_at: datetime


class ExportRequest(BaseModel):
    report_type: str
    district_ids: Optional[List[int]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    format: str = Field(default="csv", pattern="^(csv|xlsx|json|pdf)$")
    include_sections: Optional[List[str]] = None


# ══════════════════════════════════════════════════════════════════
# HEALTH CHECK SCHEMAS
# ══════════════════════════════════════════════════════════════════

class ServiceHealthResponse(BaseModel):
    service: str
    status: str
    response_time_ms: Optional[float] = None
    details: Optional[Dict] = None


class HealthCheckResponse(BaseModel):
    status: str
    version: str
    environment: str
    services: List[ServiceHealthResponse]
    uptime_seconds: float
    timestamp: datetime