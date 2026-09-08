"""Timezone-aware date and time inspection tool."""

import zoneinfo
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.tools.base import BaseTool
from app.tools.permissions import PermissionLevel


class DateTimeArgs(BaseModel):
    """Input arguments for the datetime tool."""

    timezone: str | None = Field(
        default="UTC",
        description="Optional IANA timezone name (e.g. 'UTC', 'Asia/Kolkata', 'America/New_York'). Defaults to 'UTC'.",
    )


class DateTimeTool(BaseTool):
    """Tool providing timezone-aware date and time information."""

    name = "datetime"
    description = (
        "Retrieve current date and time. Supports optional IANA timezones "
        "(e.g. 'Asia/Kolkata', 'UTC', 'America/New_York'). Defaults to UTC."
    )
    permission_level = PermissionLevel.READ
    args_model = DateTimeArgs

    async def execute(self, timezone: str | None = "UTC", **kwargs: Any) -> dict[str, str]:
        """Return structured current date and time in the requested timezone."""
        target_tz_str = (timezone or "UTC").strip()

        try:
            tz = zoneinfo.ZoneInfo(target_tz_str)
        except zoneinfo.ZoneInfoNotFoundError:
            raise ValueError(
                f"Invalid or unrecognized IANA timezone: '{target_tz_str}'. "
                f"Examples of valid timezones include 'UTC', 'Asia/Kolkata', 'America/New_York', 'Europe/London'."
            )

        now = datetime.now(tz)

        return {
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "timezone": target_tz_str,
            "iso": now.isoformat(),
            "day_of_week": now.strftime("%A"),
        }

    def verify(self, result: Any) -> bool:
        """Verify that the result contains required date and time fields."""
        if not isinstance(result, dict):
            return False
        required_keys = {"date", "time", "timezone", "iso", "day_of_week"}
        return required_keys.issubset(result.keys())
