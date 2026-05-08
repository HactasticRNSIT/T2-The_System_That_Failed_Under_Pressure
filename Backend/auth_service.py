"""
Urban Resilience Platform — Auth & Worker Services
Part 1–2: Authentication, Workforce Management
"""

import uuid
import json
import random
import string
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, func
from sqlalchemy.orm import selectinload
import httpx
from loguru import logger

from app.core.config import settings, BANGALORE_DISTRICTS
from app.core.database import cache_service
from app.core.security import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, generate_otp, verify_otp,
    check_brute_force, record_failed_attempt, clear_failed_attempts,
    revoke_token, generate_totp_secret, generate_totp_uri,
    verify_totp, generate_device_fingerprint, get_client_ip,
    validate_password_strength
)
from app.models.models import (
    Worker, WorkerSession, LoginHistory, Device, AuditLog
)
from app.schemas.schemas import (
    WorkerRegisterRequest, WorkerLoginRequest
)


def generate_worker_code() -> str:
    """Generate unique worker code like URB-BLR-00042"""
    suffix = "".join(random.choices(string.digits, k=5))
    return f"URB-BLR-{suffix}"


# ══════════════════════════════════════════════════════════════════
# AUTH SERVICE
# ══════════════════════════════════════════════════════════════════

class AuthService:
    """
    Handles all authentication flows:
    - Registration, Login/Logout
    - JWT + Refresh Token Rotation
    - OTP, MFA
    - Device Tracking
    - Brute-Force Protection
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_worker(
        self, data: WorkerRegisterRequest, created_by_id: Optional[str] = None
    ) -> Worker:
        """Register a new workforce member"""
        # Check uniqueness
        existing = await self.db.execute(
            select(Worker).where(or_(Worker.email == data.email, Worker.phone == data.phone))
        )
        if existing.scalars().first():
            raise ValueError("Worker with this email or phone already exists")

        # Validate password
        valid, msg = validate_password_strength(data.password)
        if not valid:
            raise ValueError(msg)

        # Create worker
        worker = Worker(
            worker_code=generate_worker_code(),
            full_name=data.full_name,
            email=data.email,
            phone=data.phone,
            password_hash=hash_password(data.password),
            role=data.role,
            department=data.department,
            district_id=data.district_id,
            ward_id=data.ward_id,
            preferred_language=data.preferred_language,
            shift_type=data.shift_type,
            skills=data.skills or [],
            experience_years=data.experience_years or 0,
            certifications=data.certifications or [],
            supervisor_id=data.supervisor_id,
        )

        self.db.add(worker)
        await self.db.flush()

        # Audit log
        await self._audit(
            worker_id=str(created_by_id) if created_by_id else str(worker.id),
            action="worker.registered",
            resource_type="worker",
            resource_id=str(worker.id),
            new_value={"email": data.email, "role": data.role},
        )

        logger.info(f"Worker registered: {worker.email} [{worker.role}]")
        return worker

    async def login(
        self,
        data: WorkerLoginRequest,
        ip_address: str,
        user_agent: str,
        device_fingerprint: str,
    ) -> Dict:
        """Authenticate a worker and return tokens"""
        # Brute-force check
        await check_brute_force(data.email)

        # Find worker
        result = await self.db.execute(
            select(Worker).where(Worker.email == data.email, Worker.is_active == True)
        )
        worker = result.scalars().first()

        if not worker or not verify_password(data.password, worker.password_hash):
            await record_failed_attempt(data.email)
            await self._log_login(
                worker_id=str(worker.id) if worker else None,
                email=data.email,
                ip=ip_address,
                user_agent=user_agent,
                device_fingerprint=device_fingerprint,
                success=False,
                reason="invalid_credentials",
            )
            raise ValueError("Invalid email or password")

        # Check account lock
        if worker.locked_until and worker.locked_until > datetime.utcnow():
            raise ValueError(f"Account locked until {worker.locked_until}")

        # MFA check
        if worker.mfa_enabled:
            if not data.mfa_token:
                raise ValueError("MFA token required")
            if not verify_totp(worker.mfa_secret, data.mfa_token):
                raise ValueError("Invalid MFA token")

        # Clear failed attempts
        await clear_failed_attempts(data.email)

        # Register/update device
        device = await self._register_device(worker.id, device_fingerprint, user_agent)

        # Create tokens
        access_token = create_access_token(
            worker_id=str(worker.id),
            role=worker.role.value if hasattr(worker.role, 'value') else worker.role,
            district_id=worker.district_id,
        )
        raw_refresh, hashed_refresh = create_refresh_token(str(worker.id))

        # Save session
        session = WorkerSession(
            worker_id=worker.id,
            refresh_token_hash=hashed_refresh,
            device_id=device.id if device else None,
            ip_address=ip_address,
            user_agent=user_agent,
            is_active=True,
            expires_at=datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        )
        self.db.add(session)

        # Update worker
        await self.db.execute(
            update(Worker)
            .where(Worker.id == worker.id)
            .values(
                last_login_at=datetime.utcnow(),
                last_login_ip=ip_address,
                failed_login_count=0,
            )
        )

        await self._log_login(
            worker_id=str(worker.id),
            email=data.email,
            ip=ip_address,
            user_agent=user_agent,
            device_fingerprint=device_fingerprint,
            success=True,
        )

        # Cache worker session
        await cache_service.set(
            "session",
            str(session.id),
            json.dumps({"worker_id": str(worker.id), "role": worker.role.value if hasattr(worker.role, 'value') else worker.role}),
            ttl=settings.REDIS_TTL_SESSION,
        )

        logger.info(f"Worker logged in: {worker.email} from {ip_address}")

        return {
            "access_token": access_token,
            "refresh_token": raw_refresh,
            "token_type": "bearer",
            "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "worker": worker,
        }

    async def refresh_token(self, raw_refresh_token: str) -> Dict:
        """Rotate refresh token and issue new access token"""
        import hashlib
        hashed = hashlib.sha256(raw_refresh_token.encode()).hexdigest()

        result = await self.db.execute(
            select(WorkerSession)
            .options(selectinload(WorkerSession.worker))
            .where(
                WorkerSession.refresh_token_hash == hashed,
                WorkerSession.is_active == True,
                WorkerSession.expires_at > datetime.utcnow(),
            )
        )
        session = result.scalars().first()
        if not session or not session.worker:
            raise ValueError("Invalid or expired refresh token")

        # Rotate: invalidate old, create new
        session.is_active = False

        new_access = create_access_token(
            worker_id=str(session.worker.id),
            role=session.worker.role.value if hasattr(session.worker.role, 'value') else session.worker.role,
            district_id=session.worker.district_id,
        )
        raw_new, hashed_new = create_refresh_token(str(session.worker.id))

        new_session = WorkerSession(
            worker_id=session.worker.id,
            refresh_token_hash=hashed_new,
            device_id=session.device_id,
            ip_address=session.ip_address,
            is_active=True,
            expires_at=datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        )
        self.db.add(new_session)

        return {
            "access_token": new_access,
            "refresh_token": raw_new,
            "token_type": "bearer",
            "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    async def logout(self, worker_id: str, jti: str, session_id: Optional[str] = None) -> None:
        """Revoke tokens and end session"""
        # Blacklist current access token JTI
        await revoke_token(jti, settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60)

        # Invalidate all sessions for worker
        await self.db.execute(
            update(WorkerSession)
            .where(WorkerSession.worker_id == uuid.UUID(worker_id), WorkerSession.is_active == True)
            .values(is_active=False)
        )

        await cache_service.delete("session", worker_id)
        logger.info(f"Worker logged out: {worker_id}")

    async def send_otp(self, email: str) -> str:
        """Generate and cache OTP for verification"""
        result = await self.db.execute(
            select(Worker).where(Worker.email == email)
        )
        worker = result.scalars().first()
        if not worker:
            raise ValueError("Worker not found")

        code, hashed = generate_otp()

        # Cache OTP
        await cache_service.set(
            "session",
            f"otp:{email}",
            hashed,
            ttl=settings.OTP_EXPIRE_MINUTES * 60,
        )

        logger.info(f"OTP generated for: {email} [NOT sending in dev mode]")
        # In production: send via SMS or email service
        return code  # Return only in dev; in prod don't return

    async def verify_otp(self, email: str, code: str) -> bool:
        """Verify OTP"""
        hashed = await cache_service.get("session", f"otp:{email}")
        if not hashed:
            raise ValueError("OTP expired or not found")

        if not verify_otp(code, hashed):
            raise ValueError("Invalid OTP")

        await cache_service.delete("session", f"otp:{email}")

        # Mark worker verified
        await self.db.execute(
            update(Worker).where(Worker.email == email).values(is_verified=True)
        )
        return True

    async def setup_mfa(self, worker_id: str) -> Dict:
        """Setup MFA for a worker"""
        result = await self.db.execute(select(Worker).where(Worker.id == uuid.UUID(worker_id)))
        worker = result.scalars().first()
        if not worker:
            raise ValueError("Worker not found")

        secret = generate_totp_secret()
        uri = generate_totp_uri(secret, worker.email)

        # Store secret (not enabled until verified)
        await cache_service.set("session", f"mfa_pending:{worker_id}", secret, ttl=600)

        return {"totp_secret": secret, "totp_uri": uri, "backup_codes": []}

    async def _register_device(
        self, worker_id: uuid.UUID, fingerprint: str, user_agent: str
    ) -> Optional[Device]:
        """Register or update worker device"""
        result = await self.db.execute(
            select(Device).where(Device.fingerprint == fingerprint)
        )
        device = result.scalars().first()

        if not device:
            device = Device(
                worker_id=worker_id,
                fingerprint=fingerprint,
                user_agent=user_agent,
                device_type="mobile" if "Mobile" in user_agent else "web",
                last_seen_at=datetime.utcnow(),
            )
            self.db.add(device)
            await self.db.flush()
        else:
            device.last_seen_at = datetime.utcnow()

        return device

    async def _log_login(
        self, worker_id, email, ip, user_agent,
        device_fingerprint, success, reason=None
    ) -> None:
        log = LoginHistory(
            worker_id=uuid.UUID(worker_id) if worker_id else None,
            email_attempted=email,
            ip_address=ip,
            device_fingerprint=device_fingerprint,
            user_agent=user_agent,
            success=success,
            failure_reason=reason,
        )
        self.db.add(log)

    async def _audit(self, worker_id, action, resource_type=None, resource_id=None, new_value=None) -> None:
        log = AuditLog(
            worker_id=uuid.UUID(worker_id) if worker_id else None,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            new_value=new_value,
        )
        self.db.add(log)


# ══════════════════════════════════════════════════════════════════
# WORKER SERVICE
# ══════════════════════════════════════════════════════════════════

class WorkerService:
    """Workforce management and analytics"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_worker(self, worker_id: str) -> Optional[Worker]:
        """Get worker with caching"""
        # Try cache first
        cached = await cache_service.get("worker", worker_id)
        if cached:
            return json.loads(cached)

        result = await self.db.execute(
            select(Worker).where(Worker.id == uuid.UUID(worker_id))
        )
        worker = result.scalars().first()
        if worker:
            # Cache for 5 min
            await cache_service.set("worker", worker_id, json.dumps({"id": str(worker.id), "role": worker.role.value if hasattr(worker.role, 'value') else worker.role}), ttl=300)
        return worker

    async def list_workers(
        self,
        district_id: Optional[int] = None,
        role: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Worker], int]:
        """List workers with filters"""
        query = select(Worker).where(Worker.is_active == True)

        if district_id:
            query = query.where(Worker.district_id == district_id)
        if role:
            query = query.where(Worker.role == role)
        if status:
            query = query.where(Worker.operational_status == status)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar()

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        return result.scalars().all(), total

    async def update_worker_status(
        self, worker_id: str, status: str, reason: Optional[str] = None
    ) -> Worker:
        """Update operational status and notify"""
        await self.db.execute(
            update(Worker)
            .where(Worker.id == uuid.UUID(worker_id))
            .values(operational_status=status)
        )

        # Publish to WebSocket channel
        await cache_service.publish(
            f"district:worker_status",
            json.dumps({"worker_id": worker_id, "status": status, "reason": reason, "timestamp": datetime.utcnow().isoformat()}),
        )

        # Invalidate cache
        await cache_service.delete("worker", worker_id)
        logger.info(f"Worker {worker_id} status → {status}")

        result = await self.db.execute(select(Worker).where(Worker.id == uuid.UUID(worker_id)))
        return result.scalars().first()

    async def get_nearby_workers(
        self, lat: float, lng: float, radius_m: float = 1000,
        role_filter: Optional[List[str]] = None
    ) -> List[Dict]:
        """Get workers within radius using PostGIS"""
        from sqlalchemy import text
        query = text("""
            SELECT w.id, w.full_name, w.role, w.operational_status,
                   w.fatigue_score, w.district_id,
                   ST_Distance(
                       w.current_location::geography,
                       ST_SetSRID(ST_Point(:lng, :lat), 4326)::geography
                   ) AS distance_m,
                   ST_X(w.current_location) AS longitude,
                   ST_Y(w.current_location) AS latitude
            FROM workers w
            WHERE w.is_active = TRUE
              AND w.current_location IS NOT NULL
              AND ST_DWithin(
                  w.current_location::geography,
                  ST_SetSRID(ST_Point(:lng, :lat), 4326)::geography,
                  :radius
              )
            ORDER BY distance_m ASC
            LIMIT 50
        """)

        result = await self.db.execute(query, {"lat": lat, "lng": lng, "radius": radius_m})
        rows = result.fetchall()

        return [
            {
                "worker_id": str(row.id),
                "full_name": row.full_name,
                "role": row.role,
                "status": row.operational_status,
                "fatigue_score": row.fatigue_score,
                "distance_m": round(row.distance_m, 1),
                "latitude": row.latitude,
                "longitude": row.longitude,
            }
            for row in rows
        ]

    async def update_gps_location(
        self, worker_id: str, lat: float, lng: float,
        accuracy_m: Optional[float] = None,
        speed_kmh: Optional[float] = None,
        battery_level: Optional[float] = None,
    ) -> None:
        """Update worker GPS location"""
        from app.models.models import GPSLocation
        from geoalchemy2.functions import ST_SetSRID, ST_Point

        # Update worker current location
        point_wkt = f"SRID=4326;POINT({lng} {lat})"
        await self.db.execute(
            update(Worker)
            .where(Worker.id == uuid.UUID(worker_id))
            .values(current_location=point_wkt)
        )

        # Record GPS history
        gps = GPSLocation(
            worker_id=uuid.UUID(worker_id),
            location=point_wkt,
            accuracy_m=accuracy_m,
            speed_kmh=speed_kmh,
            battery_level=battery_level,
        )
        self.db.add(gps)

        # Publish real-time location update
        await cache_service.publish(
            "worker:location",
            json.dumps({
                "worker_id": worker_id,
                "lat": lat,
                "lng": lng,
                "speed_kmh": speed_kmh,
                "timestamp": datetime.utcnow().isoformat(),
            }),
        )

        # Cache latest location
        await cache_service.set(
            "gps",
            worker_id,
            json.dumps({"lat": lat, "lng": lng, "ts": datetime.utcnow().isoformat()}),
            ttl=300,
        )

    async def get_district_workforce_heatmap(self, district_id: int) -> Dict:
        """Get workforce density heatmap data for a district"""
        from sqlalchemy import text
        result = await self.db.execute(text("""
            SELECT
                ST_X(current_location) AS lng,
                ST_Y(current_location) AS lat,
                COUNT(*) AS worker_count,
                AVG(fatigue_score) AS avg_fatigue
            FROM workers
            WHERE is_active = TRUE
              AND district_id = :district_id
              AND current_location IS NOT NULL
            GROUP BY ST_SnapToGrid(current_location, 0.005)
        """), {"district_id": district_id})

        return {
            "district_id": district_id,
            "heatmap_points": [
                {"lat": row.lat, "lng": row.lng, "weight": row.worker_count, "avg_fatigue": row.avg_fatigue}
                for row in result.fetchall()
            ],
        }