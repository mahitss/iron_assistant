"""Health check response models."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Schema for service health status."""

    status: str = Field(default="healthy", description="Current service health status")
    app: str = Field(default="Kairo", description="Application name")
    version: str = Field(default="0.1.0", description="Application version")
    environment: str = Field(default="development", description="Current running environment")
