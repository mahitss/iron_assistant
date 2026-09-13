"""
Kairo Native Runtime Foundation Package.
"""

try:
    from app.native.client import NativeRuntimeClient, NativeRuntimeUnavailableError
    from app.native.models import (
        CURRENT_PROTOCOL_VERSION,
        CapabilityDescriptor,
        ErrorCategory,
        ExecutionClass,
        HealthState,
        RequestContext,
        ResourceBudget,
        ResponseStatus,
        RuntimeErrorModel,
        RuntimeHealth,
        RuntimeMetadata,
        RuntimeRequest,
        RuntimeResponse,
        SideEffectClass,
    )
    from app.native.router import router as native_router
    from app.native.service import NativeRuntimeService
except ImportError:
    from backend.app.native.client import NativeRuntimeClient, NativeRuntimeUnavailableError
    from backend.app.native.models import (
        CURRENT_PROTOCOL_VERSION,
        CapabilityDescriptor,
        ErrorCategory,
        ExecutionClass,
        HealthState,
        RequestContext,
        ResourceBudget,
        ResponseStatus,
        RuntimeErrorModel,
        RuntimeHealth,
        RuntimeMetadata,
        RuntimeRequest,
        RuntimeResponse,
        SideEffectClass,
    )
    from backend.app.native.router import router as native_router
    from backend.app.native.service import NativeRuntimeService

__all__ = [
    "NativeRuntimeClient",
    "NativeRuntimeService",
    "NativeRuntimeUnavailableError",
    "native_router",
    "CURRENT_PROTOCOL_VERSION",
    "CapabilityDescriptor",
    "ErrorCategory",
    "ExecutionClass",
    "HealthState",
    "RequestContext",
    "ResourceBudget",
    "ResponseStatus",
    "RuntimeErrorModel",
    "RuntimeHealth",
    "RuntimeMetadata",
    "RuntimeRequest",
    "RuntimeResponse",
    "SideEffectClass",
]
