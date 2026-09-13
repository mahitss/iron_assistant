"""
Kairo Native Runtime Protocol Models (Pydantic v2).
Mirrors native/crates/kairo-protocol definitions for strong typing and serialization.
"""

from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field

CURRENT_PROTOCOL_VERSION = "1.0"


class ErrorCategory(str, Enum):
    INVALID_REQUEST = "INVALID_REQUEST"
    UNSUPPORTED_OPERATION = "UNSUPPORTED_OPERATION"
    PROTOCOL_ERROR = "PROTOCOL_ERROR"
    AUTHENTICATION_FAILURE = "AUTHENTICATION_FAILURE"
    AUTHORIZATION_REQUIRED = "AUTHORIZATION_REQUIRED"
    RESOURCE_LIMIT = "RESOURCE_LIMIT"
    DEADLINE_EXCEEDED = "DEADLINE_EXCEEDED"
    CANCELLED = "CANCELLED"
    RUNTIME_UNAVAILABLE = "RUNTIME_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SHUTTING_DOWN = "SHUTTING_DOWN"


class RuntimeErrorModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    category: ErrorCategory
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    retryable: bool = False


class ExecutionClass(str, Enum):
    PURE_COMPUTE = "PURE_COMPUTE"
    IO_BOUNDED = "IO_BOUNDED"
    SYSTEM_INSPECTION = "SYSTEM_INSPECTION"
    PRIVILEGED_NATIVE = "PRIVILEGED_NATIVE"


class SideEffectClass(str, Enum):
    NONE = "NONE"
    READ_ONLY = "READ_ONLY"
    STATEFUL_LOCAL = "STATEFUL_LOCAL"
    EXTERNAL_MUTATION = "EXTERNAL_MUTATION"


class ResourceBudget(BaseModel):
    model_config = ConfigDict(extra="ignore")

    max_cpu_percent: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    max_memory_bytes: Optional[int] = Field(default=None, gt=0)
    max_execution_time_ms: Optional[int] = Field(default=None, gt=0, le=300000)
    max_concurrency: Optional[int] = Field(default=None, gt=0, le=64)
    max_output_bytes: Optional[int] = Field(default=None, gt=0)


class CapabilityDescriptor(BaseModel):
    model_config = ConfigDict(extra="ignore")

    capability_id: str
    name: str
    version: str
    description: str
    available: bool = True
    execution_class: ExecutionClass
    side_effect_class: SideEffectClass
    supported_operations: List[str]
    default_budget: Optional[ResourceBudget] = None


class HealthState(str, Enum):
    STARTING = "STARTING"
    READY = "READY"
    DEGRADED = "DEGRADED"
    DRAINING = "DRAINING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


class RuntimeMetadata(BaseModel):
    model_config = ConfigDict(extra="ignore")

    runtime_version: str
    protocol_version: str = CURRENT_PROTOCOL_VERSION
    build_id: str
    platform: str
    arch: str
    uptime_seconds: int
    active_requests: int
    capabilities: List[str] = Field(default_factory=list)


class RuntimeHealth(BaseModel):
    model_config = ConfigDict(extra="ignore")

    state: HealthState
    healthy: bool
    message: str
    metadata: RuntimeMetadata
    last_heartbeat: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))


class RequestContext(BaseModel):
    model_config = ConfigDict(extra="ignore")

    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    security_level: Optional[str] = None
    auth_token_hash: Optional[str] = None
    client_version: Optional[str] = "1.0.0"


class ResponseStatus(str, Enum):
    OK = "OK"
    ERROR = "ERROR"
    CANCELLED = "CANCELLED"
    SHUTTING_DOWN = "SHUTTING_DOWN"


class TimingMetadata(BaseModel):
    model_config = ConfigDict(extra="ignore")

    queue_time_ms: int = 0
    execution_time_ms: int = 0
    total_time_ms: int = 0


class RuntimeRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    protocol_version: str = CURRENT_PROTOCOL_VERSION
    operation: str
    timestamp: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    deadline_ms: Optional[int] = 30000
    cancellation_id: Optional[str] = None
    correlation_id: Optional[str] = None
    caller_context: Optional[RequestContext] = None
    capability: Optional[str] = None
    resource_budget: Optional[ResourceBudget] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class RuntimeResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    request_id: str
    protocol_version: str
    status: ResponseStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[RuntimeErrorModel] = None
    runtime_metadata: Optional[RuntimeMetadata] = None
    timing: Optional[TimingMetadata] = None
    correlation_id: Optional[str] = None


class HandshakeRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    protocol_version: str = CURRENT_PROTOCOL_VERSION
    secret: Optional[str] = None
    client_id: str = "kairo-python-backend"
    client_version: str = "1.0.0"


class HandshakeResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    protocol_version: str
    runtime_version: str
    authenticated: bool
    error: Optional[str] = None
    capabilities: List[CapabilityDescriptor] = Field(default_factory=list)
