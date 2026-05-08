"""
Urban Resilience Platform — Complete Database Models
Parts 1–14: All SQLAlchemy Models with PostGIS Support
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text,
    ForeignKey, Enum, JSON, BigInteger, Index, UniqueConstraint,
    CheckConstraint, Numeric, SmallInteger
)
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB, TSVECTOR
from geoalchemy2 import Geometry
from datetime import datetime
import uuid
import enum


class Base(DeclarativeBase):
    pass


def uuid_pk():
    return Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def now():
    return Column(DateTime, default=datetime.utcnow, nullable=False)


def updated():
    return Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ══════════════════════════════════════════════════════════════════
# PART 1 — CORE: ENUMS
# ══════════════════════════════════════════════════════════════════

class RoleEnum(str, enum.Enum):
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


class WorkerStatusEnum(str, enum.Enum):
    ACTIVE = "active"
    ON_BREAK = "on_break"
    OFF_DUTY = "off_duty"
    ON_LEAVE = "on_leave"
    EMERGENCY = "emergency"
    FATIGUED = "fatigued"
    SUSPENDED = "suspended"


class TaskStatusEnum(str, enum.Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ESCALATED = "escalated"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"


class TaskPriorityEnum(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class EventTypeEnum(str, enum.Enum):
    FESTIVAL = "festival"
    RAINSTORM = "rainstorm"
    CONCERT = "concert"
    POLITICAL_RALLY = "political_rally"
    TRANSPORT_STRIKE = "transport_strike"
    FLASH_FLOOD = "flash_flood"
    TRAFFIC_ACCIDENT = "traffic_accident"
    WASTE_OVERFLOW = "waste_overflow"
    WORKFORCE_SHORTAGE = "workforce_shortage"
    POWER_OUTAGE = "power_outage"
    PUBLIC_GATHERING = "public_gathering"
    ROAD_CLOSURE = "road_closure"
    SANITATION_INCIDENT = "sanitation_incident"
    UTILITY_FAILURE = "utility_failure"
    EMERGENCY_RESPONSE = "emergency_response"


class AlertSeverityEnum(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class LanguageEnum(str, enum.Enum):
    ENGLISH = "en"
    HINDI = "hi"
    KANNADA = "kn"


class ShiftTypeEnum(str, enum.Enum):
    MORNING = "morning"    # 06:00–14:00
    AFTERNOON = "afternoon"  # 14:00–22:00
    NIGHT = "night"        # 22:00–06:00
    FLEXIBLE = "flexible"


class SimulationStatusEnum(str, enum.Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


# ══════════════════════════════════════════════════════════════════
# PART 1 — CORE: FOUNDATION MODELS
# ══════════════════════════════════════════════════════════════════

class AuditLog(Base):
    """Audit trail for all system actions"""
    __tablename__ = "audit_logs"

    id = uuid_pk()
    worker_id = Column(UUID(as_uuid=True), ForeignKey("workers.id"), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100))
    resource_id = Column(String(255))
    old_value = Column(JSONB)
    new_value = Column(JSONB)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    device_fingerprint = Column(String(255))
    geo_location = Column(JSONB)
    status = Column(String(20), default="success")
    error_message = Column(Text)
    duration_ms = Column(Integer)
    created_at = now()

    __table_args__ = (
        Index("ix_audit_logs_worker_id", "worker_id"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
    )


class ActivityLog(Base):
    """Real-time activity tracking"""
    __tablename__ = "activity_logs"

    id = uuid_pk()
    worker_id = Column(UUID(as_uuid=True), ForeignKey("workers.id"))
    activity_type = Column(String(100), nullable=False)
    description = Column(Text)
    metadata = Column(JSONB)
    district_id = Column(Integer)
    ward_id = Column(Integer)
    location = Column(Geometry("POINT", srid=4326))
    created_at = now()

    __table_args__ = (
        Index("ix_activity_logs_worker_id", "worker_id"),
        Index("ix_activity_logs_type", "activity_type"),
        Index("ix_activity_logs_created_at", "created_at"),
    )


class SystemHealth(Base):
    """System health metrics"""
    __tablename__ = "system_health"

    id = uuid_pk()
    service_name = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False)
    response_time_ms = Column(Integer)
    cpu_usage = Column(Float)
    memory_usage = Column(Float)
    active_connections = Column(Integer)
    error_rate = Column(Float)
    metadata = Column(JSONB)
    checked_at = now()

    __table_args__ = (
        Index("ix_system_health_service", "service_name"),
        Index("ix_system_health_checked_at", "checked_at"),
    )


# ══════════════════════════════════════════════════════════════════
# PART 2 — WORKFORCE IDENTITY & INTELLIGENCE
# ══════════════════════════════════════════════════════════════════

class Worker(Base):
    """Core workforce identity model"""
    __tablename__ = "workers"

    id = uuid_pk()
    worker_code = Column(String(20), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(20), unique=True)
    password_hash = Column(String(255), nullable=False)
    profile_photo_url = Column(Text)

    # Role & Department
    role = Column(Enum(RoleEnum), nullable=False)
    department = Column(String(100))

    # Location Assignment
    district_id = Column(Integer, ForeignKey("districts.id"))
    ward_id = Column(Integer)
    zone_id = Column(String(50))

    # Professional Profile
    skills = Column(ARRAY(String))
    experience_years = Column(Float, default=0)
    certifications = Column(ARRAY(String))
    emergency_certifications = Column(ARRAY(String))

    # Preferences
    preferred_language = Column(Enum(LanguageEnum), default=LanguageEnum.ENGLISH)
    shift_type = Column(Enum(ShiftTypeEnum), default=ShiftTypeEnum.MORNING)

    # Status
    operational_status = Column(Enum(WorkerStatusEnum), default=WorkerStatusEnum.OFF_DUTY)
    attendance_status = Column(String(20), default="absent")
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    # Supervisor
    supervisor_id = Column(UUID(as_uuid=True), ForeignKey("workers.id"), nullable=True)

    # Device & GPS
    gps_device_id = Column(String(100))
    current_location = Column(Geometry("POINT", srid=4326))

    # AI Metadata
    ai_behavior_model = Column(JSONB, default={})
    voice_profile_id = Column(String(255))
    biometric_hash = Column(String(255))

    # Scores (cached)
    health_score = Column(Float, default=100.0)
    resilience_score = Column(Float, default=100.0)
    fatigue_score = Column(Float, default=0.0)
    productivity_score = Column(Float, default=100.0)

    # Security
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(100))
    last_login_at = Column(DateTime)
    last_login_ip = Column(String(45))
    failed_login_count = Column(Integer, default=0)
    locked_until = Column(DateTime)
    password_changed_at = Column(DateTime)

    created_at = now()
    updated_at = updated()

    # Relationships
    district = relationship("District", back_populates="workers")
    supervisor = relationship("Worker", remote_side=[id])
    sessions = relationship("WorkerSession", back_populates="worker")
    devices = relationship("Device", back_populates="worker")
    gps_locations = relationship("GPSLocation", back_populates="worker")
    tasks = relationship("WorkerTask", back_populates="worker")
    fatigue_metrics = relationship("WorkerFatigueMetric", back_populates="worker")
    shifts = relationship("ShiftAssignment", back_populates="worker")
    voice_commands = relationship("VoiceCommand", back_populates="worker")
    alerts = relationship("WorkforceAlert", back_populates="worker")
    health_scores = relationship("HealthScore", back_populates="worker")
    safety_incidents = relationship("SafetyIncident", back_populates="worker")
    notifications = relationship("Notification", back_populates="worker")

    __table_args__ = (
        Index("ix_workers_email", "email"),
        Index("ix_workers_role", "role"),
        Index("ix_workers_district", "district_id"),
        Index("ix_workers_status", "operational_status"),
        Index("ix_workers_location", "current_location", postgresql_using="gist"),
    )


class WorkerSession(Base):
    """JWT session management"""
    __tablename__ = "worker_sessions"

    id = uuid_pk()
    worker_id = Column(UUID(as_uuid=True), ForeignKey("workers.id"), nullable=False)
    refresh_token_hash = Column(String(255), nullable=False)
    access_token_jti = Column(String(255))
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"))
    ip_address = Column(String(45))
    user_agent = Column(Text)
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=False)
    last_used_at = Column(DateTime)
    created_at = now()

    worker = relationship("Worker", back_populates="sessions")
    device = relationship("Device")

    __table_args__ = (
        Index("ix_sessions_worker_id", "worker_id"),
        Index("ix_sessions_token_hash", "refresh_token_hash"),
    )


class LoginHistory(Base):
    """Login attempt tracking"""
    __tablename__ = "login_history"

    id = uuid_pk()
    worker_id = Column(UUID(as_uuid=True), ForeignKey("workers.id"))
    email_attempted = Column(String(255))
    ip_address = Column(String(45))
    device_fingerprint = Column(String(255))
    user_agent = Column(Text)
    geo_data = Column(JSONB)  # Country, city, ISP
    success = Column(Boolean, nullable=False)
    failure_reason = Column(String(100))
    mfa_used = Column(Boolean, default=False)
    emergency_override = Column(Boolean, default=False)
    created_at = now()

    __table_args__ = (
        Index("ix_login_history_worker", "worker_id"),
        Index("ix_login_history_ip", "ip_address"),
        Index("ix_login_history_created", "created_at"),
    )


class Device(Base):
    """Worker device registry"""
    __tablename__ = "devices"

    id = uuid_pk()
    worker_id = Column(UUID(as_uuid=True), ForeignKey("workers.id"))
    device_name = Column(String(255))
    device_type = Column(String(50))
    os_type = Column(String(50))
    os_version = Column(String(50))
    app_version = Column(String(50))
    fingerprint = Column(String(255), unique=True)
    firebase_token = Column(Text)
    is_trusted = Column(Boolean, default=False)
    last_seen_at = Column(DateTime)
    registered_at = now()

    worker = relationship("Worker", back_populates="devices")

    __table_args__ = (
        Index("ix_devices_worker", "worker_id"),
        Index("ix_devices_fingerprint", "fingerprint"),
    )


class APIKey(Base):
    """API key management"""
    __tablename__ = "api_keys"

    id = uuid_pk()
    worker_id = Column(UUID(as_uuid=True), ForeignKey("workers.id"))
    key_hash = Column(String(255), unique=True, nullable=False)
    key_prefix = Column(String(20))
    name = Column(String(100))
    scopes = Column(ARRAY(String))
    rate_limit = Column(Integer, default=1000)
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime)
    last_used_at = Column(DateTime)
    usage_count = Column(BigInteger, default=0)
    created_at = now()

    __table_args__ = (Index("ix_api_keys_hash", "key_hash"),)


# ══════════════════════════════════════════════════════════════════
# PART 3 — URBAN DIGITAL TWIN ENGINE
# ══════════════════════════════════════════════════════════════════

class District(Base):
    """Bangalore district master data"""
    __tablename__ = "districts"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    code = Column(String(20), unique=True)
    boundary = Column(Geometry("MULTIPOLYGON", srid=4326))
    centroid = Column(Geometry("POINT", srid=4326))
    area_sq_km = Column(Float)
    population = Column(Integer)
    ward_count = Column(Integer)
    metadata = Column(JSONB)

    # Live state (cached from Redis, persisted hourly)
    stress_level = Column(Float, default=0.0)
    congestion_level = Column(Float, default=0.0)
    crowd_density = Column(Float, default=0.0)
    waste_pressure = Column(Float, default=0.0)
    resilience_score = Column(Float, default=100.0)

    created_at = now()
    updated_at = updated()

    workers = relationship("Worker", back_populates="district")
    events = relationship("DistrictEvent", back_populates="district")
    resilience_scores = relationship("ResilienceScore", back_populates="district")

    __table_args__ = (
        Index("ix_districts_boundary", "boundary", postgresql_using="gist"),
        Index("ix_districts_centroid", "centroid", postgresql_using="gist"),
    )


class Ward(Base):
    """Ward-level city division"""
    __tablename__ = "wards"

    id = Column(Integer, primary_key=True)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=False)
    name = Column(String(100))
    code = Column(String(20))
    boundary = Column(Geometry("POLYGON", srid=4326))
    centroid = Column(Geometry("POINT", srid=4326))
    population = Column(Integer)
    area_sq_km = Column(Float)
    waste_bins_count = Column(Integer, default=0)
    stress_level = Column(Float, default=0.0)
    created_at = now()

    __table_args__ = (
        Index("ix_wards_district", "district_id"),
        Index("ix_wards_boundary", "boundary", postgresql_using="gist"),
    )


class RoadSegment(Base):
    """Road network for routing and congestion"""
    __tablename__ = "road_segments"

    id = uuid_pk()
    name = Column(String(255))
    district_id = Column(Integer, ForeignKey("districts.id"))
    ward_id = Column(Integer)
    geometry = Column(Geometry("LINESTRING", srid=4326))
    length_km = Column(Float)
    road_type = Column(String(50))
    speed_limit_kmh = Column(Integer)
    lanes = Column(Integer, default=2)

    # Live state
    current_speed_kmh = Column(Float)
    congestion_level = Column(Float, default=0.0)  # 0–1
    traffic_density = Column(Integer, default=0)
    incident_count = Column(Integer, default=0)
    is_blocked = Column(Boolean, default=False)

    updated_at = updated()

    __table_args__ = (
        Index("ix_road_segments_geometry", "geometry", postgresql_using="gist"),
        Index("ix_road_segments_district", "district_id"),
        Index("ix_road_segments_congestion", "congestion_level"),
    )


class WasteZone(Base):
    """Waste management zones"""
    __tablename__ = "waste_zones"

    id = uuid_pk()
    district_id = Column(Integer, ForeignKey("districts.id"))
    ward_id = Column(Integer)
    zone_code = Column(String(20))
    boundary = Column(Geometry("POLYGON", srid=4326))
    centroid = Column(Geometry("POINT", srid=4326))
    capacity_kg = Column(Float)
    current_fill_pct = Column(Float, default=0.0)
    overflow_risk = Column(Float, default=0.0)
    collection_frequency_hours = Column(Integer, default=24)
    last_collected_at = Column(DateTime)
    next_collection_at = Column(DateTime)
    is_overflowing = Column(Boolean, default=False)
    updated_at = updated()

    __table_args__ = (
        Index("ix_waste_zones_district", "district_id"),
        Index("ix_waste_zones_overflow", "overflow_risk"),
        Index("ix_waste_zones_geometry", "boundary", postgresql_using="gist"),
    )


class CrowdDensity(Base):
    """Time-series crowd density measurements"""
    __tablename__ = "crowd_density"

    id = uuid_pk()
    district_id = Column(Integer, ForeignKey("districts.id"))
    ward_id = Column(Integer)
    location = Column(Geometry("POINT", srid=4326))
    density_level = Column(Float)  # 0–1
    estimated_count = Column(Integer)
    source = Column(String(50))  # sensor, satellite, estimate
    recorded_at = now()

    __table_args__ = (
        Index("ix_crowd_density_district", "district_id"),
        Index("ix_crowd_density_time", "recorded_at"),
        Index("ix_crowd_density_location", "location", postgresql_using="gist"),
    )


class PressureZone(Base):
    """Urban pressure point tracking"""
    __tablename__ = "pressure_zones"

    id = uuid_pk()
    district_id = Column(Integer, ForeignKey("districts.id"))
    name = Column(String(255))
    zone_type = Column(String(50))
    location = Column(Geometry("POINT", srid=4326))
    radius_m = Column(Float)
    pressure_level = Column(Float, default=0.0)
    contributing_factors = Column(JSONB)
    is_critical = Column(Boolean, default=False)
    updated_at = updated()

    __table_args__ = (
        Index("ix_pressure_zones_district", "district_id"),
        Index("ix_pressure_zones_level", "pressure_level"),
        Index("ix_pressure_zones_location", "location", postgresql_using="gist"),
    )


class SensorData(Base):
    """IoT sensor ingestion"""
    __tablename__ = "sensor_data"

    id = uuid_pk()
    sensor_id = Column(String(100), nullable=False)
    sensor_type = Column(String(50))  # weather, traffic, waste, air_quality
    district_id = Column(Integer, ForeignKey("districts.id"))
    location = Column(Geometry("POINT", srid=4326))
    readings = Column(JSONB, nullable=False)
    raw_payload = Column(JSONB)
    quality_score = Column(Float)  # Data reliability
    recorded_at = now()

    __table_args__ = (
        Index("ix_sensor_data_sensor_id", "sensor_id"),
        Index("ix_sensor_data_type", "sensor_type"),
        Index("ix_sensor_data_time", "recorded_at"),
        Index("ix_sensor_data_location", "location", postgresql_using="gist"),
    )


class TrafficFlow(Base):
    """Traffic flow time-series"""
    __tablename__ = "traffic_flow"

    id = uuid_pk()
    road_segment_id = Column(UUID(as_uuid=True), ForeignKey("road_segments.id"))
    district_id = Column(Integer, ForeignKey("districts.id"))
    vehicles_per_hour = Column(Integer)
    avg_speed_kmh = Column(Float)
    congestion_index = Column(Float)
    incident_active = Column(Boolean, default=False)
    recorded_at = now()

    __table_args__ = (
        Index("ix_traffic_flow_segment", "road_segment_id"),
        Index("ix_traffic_flow_time", "recorded_at"),
    )


class OverflowEvent(Base):
    """Waste/flood overflow events"""
    __tablename__ = "overflow_events"

    id = uuid_pk()
    district_id = Column(Integer, ForeignKey("districts.id"))
    waste_zone_id = Column(UUID(as_uuid=True), ForeignKey("waste_zones.id"), nullable=True)
    event_type = Column(String(50))  # waste_overflow, flood, drain_block
    severity = Column(Enum(AlertSeverityEnum))
    location = Column(Geometry("POINT", srid=4326))
    description = Column(Text)
    pressure_value = Column(Float)
    propagation_radius_m = Column(Float)
    affected_wards = Column(ARRAY(Integer))
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime)
    created_at = now()

    __table_args__ = (
        Index("ix_overflow_events_district", "district_id"),
        Index("ix_overflow_events_location", "location", postgresql_using="gist"),
        Index("ix_overflow_events_time", "created_at"),
    )


class GeoLayer(Base):
    """Map rendering layers"""
    __tablename__ = "geo_layers"

    id = uuid_pk()
    name = Column(String(100), nullable=False)
    layer_type = Column(String(50))  # heatmap, polygon, points, lines
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=True)
    data = Column(JSONB)  # GeoJSON feature collection
    style = Column(JSONB)
    is_active = Column(Boolean, default=True)
    updated_at = updated()


class GPSLocation(Base):
    """Real-time GPS tracking for workers"""
    __tablename__ = "gps_locations"

    id = uuid_pk()
    worker_id = Column(UUID(as_uuid=True), ForeignKey("workers.id"), nullable=False)
    location = Column(Geometry("POINT", srid=4326), nullable=False)
    accuracy_m = Column(Float)
    altitude_m = Column(Float)
    speed_kmh = Column(Float)
    bearing_degrees = Column(Float)
    district_id = Column(Integer, ForeignKey("districts.id"))
    ward_id = Column(Integer)
    is_in_geofence = Column(Boolean, default=True)
    battery_level = Column(Float)
    recorded_at = now()

    worker = relationship("Worker", back_populates="gps_locations")

    __table_args__ = (
        Index("ix_gps_locations_worker", "worker_id"),
        Index("ix_gps_locations_time", "recorded_at"),
        Index("ix_gps_locations_point", "location", postgresql_using="gist"),
    )


class GeoZone(Base):
    """Geo-fencing zones"""
    __tablename__ = "geo_zones"

    id = uuid_pk()
    name = Column(String(255), nullable=False)
    zone_type = Column(String(50))  # safe, restricted, emergency, work
    district_id = Column(Integer, ForeignKey("districts.id"))
    boundary = Column(Geometry("POLYGON", srid=4326))
    radius_m = Column(Float)  # For circular zones
    is_active = Column(Boolean, default=True)
    alert_on_enter = Column(Boolean, default=False)
    alert_on_exit = Column(Boolean, default=True)
    metadata = Column(JSONB)
    created_at = now()

    __table_args__ = (
        Index("ix_geo_zones_boundary", "boundary", postgresql_using="gist"),
        Index("ix_geo_zones_district", "district_id"),
    )


# ══════════════════════════════════════════════════════════════════
# PART 4 — STRESS STORM SIMULATOR
# ══════════════════════════════════════════════════════════════════

class SimulationScenario(Base):
    """Saved simulation scenarios"""
    __tablename__ = "simulation_scenarios"

    id = uuid_pk()
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_by = Column(UUID(as_uuid=True), ForeignKey("workers.id"))
    event_type = Column(Enum(EventTypeEnum))
    config = Column(JSONB, nullable=False)
    district_ids = Column(ARRAY(Integer))
    time_acceleration = Column(Float, default=1.0)
    duration_minutes = Column(Integer)
    is_template = Column(Boolean, default=False)
    tags = Column(ARRAY(String))
    created_at = now()


class SimulationRun(Base):
    """Simulation execution logs"""
    __tablename__ = "simulation_runs"

    id = uuid_pk()
    scenario_id = Column(UUID(as_uuid=True), ForeignKey("simulation_scenarios.id"))
    triggered_by = Column(UUID(as_uuid=True), ForeignKey("workers.id"))
    status = Column(Enum(SimulationStatusEnum), default=SimulationStatusEnum.IDLE)
    config_snapshot = Column(JSONB)
    results = Column(JSONB)
    peak_stress_level = Column(Float)
    affected_districts = Column(ARRAY(Integer))
    recovery_time_minutes = Column(Float)
    ai_recommendations = Column(JSONB)
    replay_data = Column(JSONB)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = now()

    __table_args__ = (
        Index("ix_simulation_runs_status", "status"),
        Index("ix_simulation_runs_created", "created_at"),
    )


class StressEvent(Base):
    """Active stress events (simulation + real)"""
    __tablename__ = "stress_events"

    id = uuid_pk()
    simulation_run_id = Column(UUID(as_uuid=True), ForeignKey("simulation_runs.id"), nullable=True)
    event_type = Column(Enum(EventTypeEnum), nullable=False)
    district_id = Column(Integer, ForeignKey("districts.id"))
    location = Column(Geometry("POINT", srid=4326))
    radius_m = Column(Float)
    intensity = Column(Float)  # 0–1
    propagation_rate = Column(Float)
    affected_systems = Column(ARRAY(String))
    cascading_events = Column(JSONB)
    is_simulated = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    created_at = now()

    __table_args__ = (
        Index("ix_stress_events_district", "district_id"),
        Index("ix_stress_events_active", "is_active"),
        Index("ix_stress_events_location", "location", postgresql_using="gist"),
    )


# ══════════════════════════════════════════════════════════════════
# PART 5 — RESILIENCE DNA SCORE ENGINE
# ══════════════════════════════════════════════════════════════════

class ResilienceScore(Base):
    """District resilience DNA scores"""
    __tablename__ = "resilience_scores"

    id = uuid_pk()
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=False)
    scoring_period = Column(String(20))  # e.g., "2024-W22", "2024-05"
    period_type = Column(String(10))  # daily, weekly, monthly

    # DNA Score Components
    adaptability_score = Column(Float, default=0.0)
    recovery_score = Column(Float, default=0.0)
    pressure_tolerance_score = Column(Float, default=0.0)
    sustainability_score = Column(Float, default=0.0)
    emergency_readiness_score = Column(Float, default=0.0)
    infrastructure_stability_score = Column(Float, default=0.0)
    workforce_stability_score = Column(Float, default=0.0)
    waste_management_score = Column(Float, default=0.0)
    public_safety_score = Column(Float, default=0.0)
    overall_health_score = Column(Float, default=0.0)

    # AI Metadata
    ai_confidence = Column(Float)
    weight_matrix = Column(JSONB)
    score_explanation = Column(JSONB)
    anomalies_detected = Column(JSONB)
    risk_forecast = Column(JSONB)

    # Ranking
    district_rank = Column(Integer)
    city_percentile = Column(Float)
    score_delta = Column(Float)  # Change from previous period

    calculated_at = now()

    district = relationship("District", back_populates="resilience_scores")

    __table_args__ = (
        Index("ix_resilience_scores_district", "district_id"),
        Index("ix_resilience_scores_period", "scoring_period"),
        Index("ix_resilience_scores_health", "overall_health_score"),
        UniqueConstraint("district_id", "scoring_period", "period_type", name="uq_resilience_period"),
    )


class ResilienceBadge(Base):
    """Achievement badges for districts/workers"""
    __tablename__ = "resilience_badges"

    id = uuid_pk()
    entity_type = Column(String(20))  # district, worker
    entity_id = Column(String(255))
    badge_type = Column(String(50))
    badge_name = Column(String(100))
    description = Column(Text)
    criteria = Column(JSONB)
    icon_url = Column(Text)
    awarded_at = now()

    __table_args__ = (
        Index("ix_badges_entity", "entity_type", "entity_id"),
    )


# ══════════════════════════════════════════════════════════════════
# PART 6 — HUMAN FATIGUE INTELLIGENCE SYSTEM
# ══════════════════════════════════════════════════════════════════

class ShiftAssignment(Base):
    """Worker shift assignments"""
    __tablename__ = "shift_assignments"

    id = uuid_pk()
    worker_id = Column(UUID(as_uuid=True), ForeignKey("workers.id"), nullable=False)
    district_id = Column(Integer, ForeignKey("districts.id"))
    shift_type = Column(Enum(ShiftTypeEnum))
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    actual_start = Column(DateTime)
    actual_end = Column(DateTime)
    overtime_minutes = Column(Integer, default=0)
    break_minutes_taken = Column(Integer, default=0)
    tasks_completed = Column(Integer, default=0)
    distance_covered_km = Column(Float, default=0.0)
    status = Column(String(20), default="scheduled")
    notes = Column(Text)
    created_at = now()

    worker = relationship("Worker", back_populates="shifts")

    __table_args__ = (
        Index("ix_shifts_worker", "worker_id"),
        Index("ix_shifts_start", "start_time"),
        Index("ix_shifts_district", "district_id"),
    )


class WorkerFatigueMetric(Base):
    """Real-time fatigue measurements"""
    __tablename__ = "worker_fatigue_metrics"

    id = uuid_pk()
    worker_id = Column(UUID(as_uuid=True), ForeignKey("workers.id"), nullable=False)
    shift_id = Column(UUID(as_uuid=True), ForeignKey("shift_assignments.id"))

    # Fatigue Components
    physical_exhaustion = Column(Float, default=0.0)   # 0–100
    cognitive_overload = Column(Float, default=0.0)    # 0–100
    burnout_probability = Column(Float, default=0.0)   # 0–1
    shift_overload_risk = Column(Float, default=0.0)   # 0–1
    hydration_risk = Column(Float, default=0.0)        # 0–1
    heat_stress_score = Column(Float, default=0.0)     # 0–100
    route_difficulty_score = Column(Float, default=0.0) # 0–100
    emergency_fatigue = Column(Float, default=0.0)     # 0–100
    overtime_penalty = Column(Float, default=0.0)      # Additional fatigue
    overall_fatigue_score = Column(Float, default=0.0)  # 0–100

    # Context
    ambient_temp_celsius = Column(Float)
    humidity_pct = Column(Float)
    weather_condition = Column(String(50))
    tasks_in_window = Column(Integer)
    distance_this_hour_km = Column(Float)

    # AI Predictions
    predicted_fatigue_1h = Column(Float)
    predicted_fatigue_4h = Column(Float)
    injury_probability = Column(Float)
    productivity_decline_pct = Column(Float)
    recommended_break_minutes = Column(Integer)
    ai_confidence = Column(Float)

    # Recovery
    recovery_efficiency = Column(Float)
    estimated_recovery_hours = Column(Float)

    recorded_at = now()

    worker = relationship("Worker", back_populates="fatigue_metrics")

    __table_args__ = (
        Index("ix_fatigue_worker", "worker_id"),
        Index("ix_fatigue_time", "recorded_at"),
        Index("ix_fatigue_score", "overall_fatigue_score"),
    )


class RecoveryLog(Base):
    """Worker recovery tracking"""
    __tablename__ = "recovery_logs"

    id = uuid_pk()
    worker_id = Column(UUID(as_uuid=True), ForeignKey("workers.id"))
    shift_id = Column(UUID(as_uuid=True), ForeignKey("shift_assignments.id"))
    break_type = Column(String(50))  # short, meal, rest, medical
    duration_minutes = Column(Integer)
    pre_break_fatigue = Column(Float)
    post_break_fatigue = Column(Float)
    recovery_delta = Column(Float)
    location = Column(Geometry("POINT", srid=4326))
    ai_recommended = Column(Boolean, default=False)
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    created_at = now()

    __table_args__ = (Index("ix_recovery_worker", "worker_id"),)


class RouteDifficulty(Base):
    """Route difficulty scoring for fatigue modeling"""
    __tablename__ = "route_difficulty"

    id = uuid_pk()
    route_id = Column(String(100))
    district_id = Column(Integer, ForeignKey("districts.id"))
    geometry = Column(Geometry("LINESTRING", srid=4326))
    distance_km = Column(Float)
    elevation_change_m = Column(Float)
    surface_type = Column(String(50))
    traffic_exposure = Column(Float)
    waste_density = Column(Float)
    heat_exposure_factor = Column(Float)
    difficulty_score = Column(Float)  # 0–100
    estimated_energy_kcal = Column(Float)
    calculated_at = now()

    __table_args__ = (
        Index("ix_route_difficulty_district", "district_id"),
        Index("ix_route_difficulty_geometry", "geometry", postgresql_using="gist"),
    )


class WorkloadHistory(Base):
    """Worker workload history"""
    __tablename__ = "workload_history"

    id = uuid_pk()
    worker_id = Column(UUID(as_uuid=True), ForeignKey("workers.id"))
    date = Column(DateTime, nullable=False)
    tasks_assigned = Column(Integer, default=0)
    tasks_completed = Column(Integer, default=0)
    hours_worked = Column(Float, default=0)
    overtime_hours = Column(Float, default=0)
    distance_km = Column(Float, default=0)
    emergency_assignments = Column(Integer, default=0)
    avg_fatigue_score = Column(Float)
    workload_fairness_score = Column(Float)
    created_at = now()

    __table_args__ = (
        Index("ix_workload_worker", "worker_id"),
        Index("ix_workload_date", "date"),
    )


class FatiguePrediction(Base):
    """ML fatigue predictions"""
    __tablename__ = "fatigue_predictions"

    id = uuid_pk()
    worker_id = Column(UUID(as_uuid=True), ForeignKey("workers.id"))
    prediction_horizon_hours = Column(Integer)
    predicted_fatigue = Column(Float)
    predicted_burnout_risk = Column(Float)
    predicted_injury_risk = Column(Float)
    recommended_actions = Column(JSONB)
    model_version = Column(String(50))
    confidence_score = Column(Float)
    features_used = Column(JSONB)
    predicted_at = now()

    __table_args__ = (
        Index("ix_fatigue_pred_worker", "worker_id"),
        Index("ix_fatigue_pred_time", "predicted_at"),
    )


# ══════════════════════════════════════════════════════════════════
# PART 7 — VOICE RECOGNITION + MULTILINGUAL AI
# ══════════════════════════════════════════════════════════════════

class VoiceCommand(Base):
    """Voice command processing log"""
    __tablename__ = "voice_commands"

    id = uuid_pk()
    worker_id = Column(UUID(as_uuid=True), ForeignKey("workers.id"))
    session_id = Column(String(255))
    audio_url = Column(Text)
    duration_seconds = Column(Float)
    language = Column(Enum(LanguageEnum))
    raw_transcript = Column(Text)
    processed_transcript = Column(Text)
    intent = Column(String(100))
    entities = Column(JSONB)
    confidence_score = Column(Float)
    is_emergency = Column(Boolean, default=False)
    emergency_keywords = Column(ARRAY(String))
    action_taken = Column(String(100))
    action_result = Column(JSONB)
    processing_time_ms = Column(Integer)
    model_used = Column(String(50))
    district_id = Column(Integer, ForeignKey("districts.id"))
    location = Column(Geometry("POINT", srid=4326))
    created_at = now()

    worker = relationship("Worker", back_populates="voice_commands")

    __table_args__ = (
        Index("ix_voice_commands_worker", "worker_id"),
        Index("ix_voice_commands_emergency", "is_emergency"),
        Index("ix_voice_commands_time", "created_at"),
    )


class AudioLog(Base):
    """Audio file storage metadata"""
    __tablename__ = "audio_logs"

    id = uuid_pk()
    worker_id = Column(UUID(as_uuid=True), ForeignKey("workers.id"))
    voice_command_id = Column(UUID(as_uuid=True), ForeignKey("voice_commands.id"))
    file_path = Column(Text)
    file_size_bytes = Column(Integer)
    duration_seconds = Column(Float)
    format = Column(String(10))
    sample_rate = Column(Integer)
    noise_level_db = Column(Float)
    quality_score = Column(Float)
    created_at = now()


# ══════════════════════════════════════════════════════════════════
# PART 9 — DISTRICT EVENT TRACKING
# ══════════════════════════════════════════════════════════════════

class DistrictEvent(Base):
    """Real-world district events"""
    __tablename__ = "district_events"

    id = uuid_pk()
    district_id = Column(Integer, ForeignKey("districts.id"))
    ward_id = Column(Integer)
    event_type = Column(Enum(EventTypeEnum), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    location = Column(Geometry("POINT", srid=4326))
    radius_impact_m = Column(Float)
    severity = Column(Enum(AlertSeverityEnum))
    ai_severity_score = Column(Float)
    impact_prediction = Column(JSONB)
    crowd_surge_forecast = Column(JSONB)
    affected_systems = Column(ARRAY(String))
    reported_by = Column(UUID(as_uuid=True), ForeignKey("workers.id"))
    source = Column(String(50))  # manual, voice, sensor, ai
    is_verified = Column(Boolean, default=False)
    is_resolved = Column(Boolean, default=False)
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    created_at = now()
    updated_at = updated()

    district = relationship("District", back_populates="events")

    __table_args__ = (
        Index("ix_district_events_district", "district_id"),
        Index("ix_district_events_type", "event_type"),
        Index("ix_district_events_severity", "severity"),
        Index("ix_district_events_time", "created_at"),
        Index("ix_district_events_location", "location", postgresql_using="gist"),
        Index("ix_district_events_active", "is_resolved"),
    )


# ══════════════════════════════════════════════════════════════════
# PART 10 — TASK MANAGEMENT + OPERATIONS
# ══════════════════════════════════════════════════════════════════

class WorkerTask(Base):
    """Operational tasks"""
    __tablename__ = "worker_tasks"

    id = uuid_pk()
    task_code = Column(String(30), unique=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)

    # Classification
    task_type = Column(String(50))  # sanitation, emergency, inspection, route
    priority = Column(Enum(TaskPriorityEnum), default=TaskPriorityEnum.MEDIUM)
    status = Column(Enum(TaskStatusEnum), default=TaskStatusEnum.PENDING)

    # Assignment
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("workers.id"))
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("workers.id"))
    team_ids = Column(ARRAY(UUID))

    # Location
    district_id = Column(Integer, ForeignKey("districts.id"))
    ward_id = Column(Integer)
    location = Column(Geometry("POINT", srid=4326))
    route_id = Column(String(100))

    # Timing
    due_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    sla_deadline = Column(DateTime)
    estimated_duration_minutes = Column(Integer)
    actual_duration_minutes = Column(Integer)

    # Links
    shift_id = Column(UUID(as_uuid=True), ForeignKey("shift_assignments.id"))
    event_id = Column(UUID(as_uuid=True), ForeignKey("district_events.id"))
    parent_task_id = Column(UUID(as_uuid=True), ForeignKey("worker_tasks.id"))

    # Creation source
    is_emergency = Column(Boolean, default=False)
    is_voice_created = Column(Boolean, default=False)
    is_ai_generated = Column(Boolean, default=False)
    voice_command_id = Column(UUID(as_uuid=True), ForeignKey("voice_commands.id"))

    # Analytics
    productivity_score = Column(Float)
    quality_score = Column(Float)
    fatigue_impact = Column(Float)
    ai_recommendation = Column(JSONB)

    # Escalation
    escalation_count = Column(Integer, default=0)
    last_escalated_at = Column(DateTime)
    escalated_to = Column(UUID(as_uuid=True), ForeignKey("workers.id"))

    created_at = now()
    updated_at = updated()

    worker = relationship("Worker", back_populates="tasks", foreign_keys=[assigned_to])

    __table_args__ = (
        Index("ix_tasks_assigned_to", "assigned_to"),
        Index("ix_tasks_status", "status"),
        Index("ix_tasks_priority", "priority"),
        Index("ix_tasks_district", "district_id"),
        Index("ix_tasks_due", "due_at"),
        Index("ix_tasks_location", "location", postgresql_using="gist"),
        Index("ix_tasks_emergency", "is_emergency"),
    )


class TaskAssignment(Base):
    """Task assignment history"""
    __tablename__ = "task_assignments"

    id = uuid_pk()
    task_id = Column(UUID(as_uuid=True), ForeignKey("worker_tasks.id"))
    worker_id = Column(UUID(as_uuid=True), ForeignKey("workers.id"))
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("workers.id"))
    assignment_reason = Column(String(100))
    fatigue_score_at_assignment = Column(Float)
    is_active = Column(Boolean, default=True)
    assigned_at = now()


class EmergencyAssignment(Base):
    """Emergency response assignments"""
    __tablename__ = "emergency_assignments"

    id = uuid_pk()
    event_id = Column(UUID(as_uuid=True), ForeignKey("district_events.id"))
    worker_id = Column(UUID(as_uuid=True), ForeignKey("workers.id"))
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("workers.id"))
    role_in_emergency = Column(String(100))
    response_time_minutes = Column(Float)
    status = Column(String(30))
    outcome = Column(Text)
    fatigue_before = Column(Float)
    fatigue_after = Column(Float)
    assigned_at = now()
    completed_at = Column(DateTime)

    __table_args__ = (
        Index("ix_emergency_worker", "worker_id"),
        Index("ix_emergency_event", "event_id"),
    )


# ══════════════════════════════════════════════════════════════════
# PART 11 — HEALTH METER LEADERBOARD
# ══════════════════════════════════════════════════════════════════

class HealthScore(Base):
    """Worker health meter scores"""
    __tablename__ = "health_scores"

    id = uuid_pk()
    worker_id = Column(UUID(as_uuid=True), ForeignKey("workers.id"))
    period = Column(String(20))
    period_type = Column(String(10))

    productivity_score = Column(Float, default=0.0)
    resilience_score = Column(Float, default=0.0)
    recovery_score = Column(Float, default=0.0)
    emergency_response_score = Column(Float, default=0.0)
    attendance_score = Column(Float, default=0.0)
    reliability_index = Column(Float, default=0.0)
    route_efficiency_score = Column(Float, default=0.0)
    team_coordination_score = Column(Float, default=0.0)
    sustainability_score = Column(Float, default=0.0)
    overall_health_meter = Column(Float, default=0.0)

    district_rank = Column(Integer)
    city_rank = Column(Integer)
    percentile = Column(Float)
    score_delta = Column(Float)

    calculated_at = now()

    worker = relationship("Worker", back_populates="health_scores")

    __table_args__ = (
        Index("ix_health_scores_worker", "worker_id"),
        Index("ix_health_scores_period", "period"),
        Index("ix_health_scores_rank", "city_rank"),
        UniqueConstraint("worker_id", "period", "period_type", name="uq_health_period"),
    )


class WorkforceLeaderboard(Base):
    """Workforce leaderboard rankings"""
    __tablename__ = "workforce_leaderboards"

    id = uuid_pk()
    leaderboard_type = Column(String(50))  # district, ward, city
    entity_type = Column(String(20))       # district, worker
    entity_id = Column(String(255))
    entity_name = Column(String(255))
    rank = Column(Integer)
    score = Column(Float)
    category = Column(String(50))
    period = Column(String(20))
    period_type = Column(String(10))
    score_breakdown = Column(JSONB)
    trend = Column(String(10))  # up, down, stable
    badges = Column(ARRAY(String))
    calculated_at = now()

    __table_args__ = (
        Index("ix_leaderboard_type_period", "leaderboard_type", "period"),
        Index("ix_leaderboard_rank", "rank"),
    )


# ══════════════════════════════════════════════════════════════════
# PART 12 — AI ALERTS & PREDICTION
# ══════════════════════════════════════════════════════════════════

class WorkforceAlert(Base):
    """System-wide alerts"""
    __tablename__ = "workforce_alerts"

    id = uuid_pk()
    worker_id = Column(UUID(as_uuid=True), ForeignKey("workers.id"), nullable=True)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=True)
    alert_type = Column(String(100), nullable=False)
    severity = Column(Enum(AlertSeverityEnum))
    title = Column(String(255))
    message = Column(Text)
    metadata = Column(JSONB)
    location = Column(Geometry("POINT", srid=4326))
    is_ai_generated = Column(Boolean, default=False)
    ai_confidence = Column(Float)
    is_acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(UUID(as_uuid=True), ForeignKey("workers.id"))
    acknowledged_at = Column(DateTime)
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime)
    escalation_chain = Column(JSONB)
    auto_response_taken = Column(JSONB)
    created_at = now()

    worker = relationship("Worker", back_populates="alerts", foreign_keys=[worker_id])

    __table_args__ = (
        Index("ix_alerts_severity", "severity"),
        Index("ix_alerts_district", "district_id"),
        Index("ix_alerts_type", "alert_type"),
        Index("ix_alerts_created", "created_at"),
        Index("ix_alerts_unresolved", "is_resolved"),
    )


class AIPrediction(Base):
    """AI prediction records"""
    __tablename__ = "ai_predictions"

    id = uuid_pk()
    prediction_type = Column(String(100), nullable=False)
    district_id = Column(Integer, ForeignKey("districts.id"))
    entity_id = Column(String(255))
    horizon_hours = Column(Float)
    prediction_value = Column(Float)
    confidence_score = Column(Float)
    risk_level = Column(String(20))
    contributing_factors = Column(JSONB)
    recommended_interventions = Column(JSONB)
    model_version = Column(String(50))
    features_snapshot = Column(JSONB)
    is_triggered = Column(Boolean, default=False)
    actual_value = Column(Float)
    accuracy_pct = Column(Float)
    predicted_at = now()
    evaluated_at = Column(DateTime)

    __table_args__ = (
        Index("ix_predictions_type", "prediction_type"),
        Index("ix_predictions_district", "district_id"),
        Index("ix_predictions_time", "predicted_at"),
        Index("ix_predictions_confidence", "confidence_score"),
    )


# ══════════════════════════════════════════════════════════════════
# PART 13 — NOTIFICATIONS
# ══════════════════════════════════════════════════════════════════

class Notification(Base):
    """Push notifications"""
    __tablename__ = "notifications"

    id = uuid_pk()
    worker_id = Column(UUID(as_uuid=True), ForeignKey("workers.id"))
    title = Column(String(255))
    body = Column(Text)
    notification_type = Column(String(50))
    data = Column(JSONB)
    channel = Column(String(20))  # push, sms, ws, email
    priority = Column(String(10), default="normal")
    is_read = Column(Boolean, default=False)
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime)
    read_at = Column(DateTime)
    firebase_message_id = Column(String(255))
    created_at = now()

    worker = relationship("Worker", back_populates="notifications")

    __table_args__ = (
        Index("ix_notifications_worker", "worker_id"),
        Index("ix_notifications_unread", "is_read"),
        Index("ix_notifications_created", "created_at"),
    )


class SafetyIncident(Base):
    """Worker safety incidents"""
    __tablename__ = "safety_incidents"

    id = uuid_pk()
    worker_id = Column(UUID(as_uuid=True), ForeignKey("workers.id"))
    incident_type = Column(String(100))
    severity = Column(Enum(AlertSeverityEnum))
    description = Column(Text)
    location = Column(Geometry("POINT", srid=4326))
    district_id = Column(Integer, ForeignKey("districts.id"))
    fatigue_at_incident = Column(Float)
    weather_conditions = Column(JSONB)
    was_sos_triggered = Column(Boolean, default=False)
    response_time_minutes = Column(Float)
    medical_attention_required = Column(Boolean, default=False)
    outcome = Column(Text)
    investigation_notes = Column(Text)
    is_resolved = Column(Boolean, default=False)
    occurred_at = Column(DateTime)
    created_at = now()

    worker = relationship("Worker", back_populates="safety_incidents")

    __table_args__ = (
        Index("ix_safety_incidents_worker", "worker_id"),
        Index("ix_safety_incidents_type", "incident_type"),
        Index("ix_safety_incidents_location", "location", postgresql_using="gist"),
    )


class WorkerAnalytics(Base):
    """Aggregated worker analytics"""
    __tablename__ = "worker_analytics"

    id = uuid_pk()
    worker_id = Column(UUID(as_uuid=True), ForeignKey("workers.id"))
    period = Column(String(20))
    period_type = Column(String(10))

    # Performance
    tasks_assigned = Column(Integer, default=0)
    tasks_completed = Column(Integer, default=0)
    tasks_escalated = Column(Integer, default=0)
    completion_rate = Column(Float)
    on_time_rate = Column(Float)
    quality_avg = Column(Float)

    # Attendance
    shifts_scheduled = Column(Integer, default=0)
    shifts_attended = Column(Integer, default=0)
    hours_worked = Column(Float, default=0)
    overtime_hours = Column(Float, default=0)
    leaves_taken = Column(Integer, default=0)

    # Health
    avg_fatigue_score = Column(Float)
    peak_fatigue_score = Column(Float)
    burnout_risk_days = Column(Integer, default=0)
    recovery_events = Column(Integer, default=0)
    safety_incidents = Column(Integer, default=0)

    # Voice & Communication
    voice_commands_issued = Column(Integer, default=0)
    sos_triggered = Column(Integer, default=0)
    emergencies_responded = Column(Integer, default=0)

    # Geo
    total_distance_km = Column(Float, default=0)
    districts_covered = Column(ARRAY(Integer))

    calculated_at = now()

    __table_args__ = (
        Index("ix_worker_analytics_worker", "worker_id"),
        Index("ix_worker_analytics_period", "period"),
    )


class DistrictAssignment(Base):
    """Worker district assignments history"""
    __tablename__ = "district_assignments"

    id = uuid_pk()
    worker_id = Column(UUID(as_uuid=True), ForeignKey("workers.id"))
    district_id = Column(Integer, ForeignKey("districts.id"))
    ward_id = Column(Integer)
    role_in_district = Column(String(100))
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("workers.id"))
    is_primary = Column(Boolean, default=True)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime)
    created_at = now()

    __table_args__ = (
        Index("ix_district_assignments_worker", "worker_id"),
        Index("ix_district_assignments_district", "district_id"),
    )