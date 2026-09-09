"""Idempotency key generation, verification, and duplicate side-effect prevention."""

from datetime import UTC, datetime, timedelta
import hashlib
import logging
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.resilience.models import IdempotencyModel
from app.resilience.schemas import IdempotencyRecord, utc_now

logger = logging.getLogger(__name__)


class ConcurrentExecutionError(Exception):
    """Raised when an operation with the same idempotency key is currently running."""
    pass


class IdempotencyManager:
    """Manages idempotency records in DB with in-memory fallback for resilience."""

    def __init__(self) -> None:
        self._memory_cache: dict[str, IdempotencyRecord] = {}

    @staticmethod
    def generate_key(
        operation: str,
        user_id: str | None = None,
        task_id: str | None = None,
        step_id: str | None = None,
        target: str | None = None,
        payload_hash: str | None = None,
    ) -> str:
        """Generates a deterministic, non-sensitive idempotency key."""
        raw_components = [
            f"op:{operation}",
            f"usr:{user_id or 'anon'}",
            f"tsk:{task_id or 'none'}",
            f"stp:{step_id or 'none'}",
            f"tgt:{target or 'none'}",
        ]
        if payload_hash:
            raw_components.append(f"hash:{payload_hash}")

        base_string = "|".join(raw_components)
        digest = hashlib.sha256(base_string.encode("utf-8")).hexdigest()[:32]
        return f"idem_{operation}_{digest}"

    @staticmethod
    def hash_payload(payload: Any) -> str:
        """Computes a SHA256 hash of a payload dictionary or string."""
        serialized = str(payload)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]

    async def get_record(
        self,
        key: str,
        session: AsyncSession | None = None,
    ) -> IdempotencyRecord | None:
        """Fetches an existing idempotency record from DB or memory cache."""
        # Check memory cache first
        cached = self._memory_cache.get(key)
        now = utc_now()
        if cached:
            if cached.expires_at > now:
                return cached
            else:
                self._memory_cache.pop(key, None)

        if session:
            try:
                stmt = select(IdempotencyModel).where(IdempotencyModel.idempotency_key == key)
                res = await session.execute(stmt)
                db_model = res.scalar_one_or_none()
                if db_model:
                    if db_model.expires_at.replace(tzinfo=UTC) if db_model.expires_at.tzinfo is None else db_model.expires_at > now:
                        rec = IdempotencyRecord.model_validate(db_model)
                        self._memory_cache[key] = rec
                        return rec
                    else:
                        await session.delete(db_model)
                        await session.commit()
            except Exception as e:
                logger.warning("Resilience: DB error fetching idempotency key %s: %s", key, e)

        return None

    async def begin_operation(
        self,
        key: str,
        operation: str,
        user_id: str | None = None,
        task_id: str | None = None,
        ttl_seconds: int = 86400,
        session: AsyncSession | None = None,
    ) -> tuple[bool, IdempotencyRecord | None]:
        """Starts an operation under an idempotency key.

        Returns (is_new, existing_record).
        If not new and COMPLETED: existing_record has the prior result.
        If not new and STARTED: concurrent execution detected!
        """
        existing = await self.get_record(key, session)
        if existing:
            if existing.status == "STARTED":
                raise ConcurrentExecutionError(
                    f"Operation with idempotency key '{key}' is already in progress."
                )
            # Already completed or failed
            return False, existing

        expires_at = utc_now() + timedelta(seconds=ttl_seconds)
        new_record = IdempotencyRecord(
            idempotency_key=key,
            operation=operation,
            user_id=user_id,
            task_id=task_id,
            status="STARTED",
            result_reference=None,
            created_at=utc_now(),
            expires_at=expires_at,
        )

        # Write to memory cache immediately
        self._memory_cache[key] = new_record

        if session:
            try:
                db_item = IdempotencyModel(
                    idempotency_key=key,
                    operation=operation,
                    user_id=user_id,
                    task_id=task_id,
                    status="STARTED",
                    result_reference=None,
                    created_at=new_record.created_at,
                    expires_at=expires_at,
                )
                session.add(db_item)
                await session.commit()
            except Exception as e:
                logger.warning("Resilience: DB error saving idempotency record %s: %s", key, e)

        return True, new_record

    async def complete_operation(
        self,
        key: str,
        result_reference: dict[str, Any] | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        """Marks the operation as COMPLETED and records the result reference."""
        now = utc_now()
        if key in self._memory_cache:
            rec = self._memory_cache[key]
            rec.status = "COMPLETED"
            rec.result_reference = result_reference

        if session:
            try:
                stmt = select(IdempotencyModel).where(IdempotencyModel.idempotency_key == key)
                res = await session.execute(stmt)
                db_model = res.scalar_one_or_none()
                if db_model:
                    db_model.status = "COMPLETED"
                    db_model.result_reference = result_reference
                    await session.commit()
            except Exception as e:
                logger.warning("Resilience: DB error completing idempotency key %s: %s", key, e)

    async def fail_operation(
        self,
        key: str,
        session: AsyncSession | None = None,
    ) -> None:
        """Marks the operation as FAILED so future attempts may retry if safe."""
        if key in self._memory_cache:
            self._memory_cache[key].status = "FAILED"

        if session:
            try:
                stmt = select(IdempotencyModel).where(IdempotencyModel.idempotency_key == key)
                res = await session.execute(stmt)
                db_model = res.scalar_one_or_none()
                if db_model:
                    db_model.status = "FAILED"
                    await session.commit()
            except Exception as e:
                logger.warning("Resilience: DB error failing idempotency key %s: %s", key, e)
