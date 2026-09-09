"""Communication channels management, authorization, rate limiting, and quiet hours."""

from __future__ import annotations

from datetime import datetime, time
import logging
from typing import Any, Dict, Optional

from app.communication.schemas import CommunicationChannel, CommunicationUrgency

logger = logging.getLogger(__name__)


class ChannelAuthorizationError(Exception):
    """Raised when an operation is attempted on an unauthorized communication channel."""
    pass


class RateLimitExceededError(Exception):
    """Raised when channel rate limit is exceeded."""
    pass


class QuietHoursViolationError(Exception):
    """Raised when non-critical communication is attempted during quiet hours."""
    pass


class ChannelManager:
    """Manages communication channels, explicit authorizations, rate limits, and quiet hours."""

    def __init__(self) -> None:
        # channel_name/type -> dict config
        self._channels: Dict[str, Dict[str, Any]] = {}
        # rate limit tracking: channel -> list of timestamps
        self._call_history: Dict[str, list[datetime]] = {}
        # Pre-register default channels with required authorization flags
        for ch in CommunicationChannel:
            self._channels[ch.value] = {
                "channel_type": ch.value,
                "name": ch.value.title(),
                "is_authorized": True if ch in (CommunicationChannel.EMAIL, CommunicationChannel.CHAT, CommunicationChannel.NOTIFICATION) else False,
                "rate_limit_per_minute": 30,
                "quiet_hours_start": None,
                "quiet_hours_end": None,
                "configuration": {}
            }
            self._call_history[ch.value] = []

    def register_channel(
        self,
        channel: CommunicationChannel | str,
        name: str,
        is_authorized: bool = False,
        rate_limit_per_minute: int = 30,
        quiet_hours_start: Optional[str] = None,
        quiet_hours_end: Optional[str] = None,
        configuration: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        ch_key = channel.value if isinstance(channel, CommunicationChannel) else str(channel).upper()
        self._channels[ch_key] = {
            "channel_type": ch_key,
            "name": name,
            "is_authorized": is_authorized,
            "rate_limit_per_minute": rate_limit_per_minute,
            "quiet_hours_start": quiet_hours_start,
            "quiet_hours_end": quiet_hours_end,
            "configuration": configuration or {},
        }
        if ch_key not in self._call_history:
            self._call_history[ch_key] = []
        return self._channels[ch_key]

    def authorize_channel(self, channel: CommunicationChannel | str, authorized: bool = True) -> None:
        ch_key = channel.value if isinstance(channel, CommunicationChannel) else str(channel).upper()
        if ch_key in self._channels:
            self._channels[ch_key]["is_authorized"] = authorized
        else:
            self.register_channel(ch_key, ch_key.title(), is_authorized=authorized)

    def is_authorized(self, channel: CommunicationChannel | str) -> bool:
        ch_key = channel.value if isinstance(channel, CommunicationChannel) else str(channel).upper()
        ch_info = self._channels.get(ch_key)
        if not ch_info:
            return False
        return bool(ch_info.get("is_authorized", False))

    def verify_authorization(self, channel: CommunicationChannel | str) -> None:
        if not self.is_authorized(channel):
            ch_key = channel.value if isinstance(channel, CommunicationChannel) else str(channel)
            raise ChannelAuthorizationError(
                f"Channel '{ch_key}' is not authorized. Consequential communication requires explicit channel authorization."
            )

    def check_rate_limit(self, channel: CommunicationChannel | str, now: Optional[datetime] = None) -> None:
        ch_key = channel.value if isinstance(channel, CommunicationChannel) else str(channel).upper()
        self.verify_authorization(ch_key)
        ch_info = self._channels.get(ch_key, {})
        limit = ch_info.get("rate_limit_per_minute", 30)

        current_time = now or datetime.now()
        history = self._call_history.setdefault(ch_key, [])
        # Prune timestamps older than 60 seconds
        cutoff = current_time.timestamp() - 60.0
        self._call_history[ch_key] = [t for t in history if t.timestamp() > cutoff]

        if len(self._call_history[ch_key]) >= limit:
            raise RateLimitExceededError(
                f"Rate limit exceeded for channel '{ch_key}'. Maximum {limit} messages per minute."
            )
        self._call_history[ch_key].append(current_time)

    def check_quiet_hours(
        self,
        channel: CommunicationChannel | str,
        current_time: Optional[time] = None,
        urgency: CommunicationUrgency = CommunicationUrgency.NORMAL,
        allow_critical_override: bool = False,
    ) -> bool:
        """Returns True if send is allowed. Raises QuietHoursViolationError if blocked."""
        # Critical notifications may override quiet hours only when allowed
        if urgency == CommunicationUrgency.CRITICAL and allow_critical_override:
            return True

        ch_key = channel.value if isinstance(channel, CommunicationChannel) else str(channel).upper()
        ch_info = self._channels.get(ch_key, {})
        q_start = ch_info.get("quiet_hours_start")
        q_end = ch_info.get("quiet_hours_end")

        if not q_start or not q_end:
            return True

        check_time = current_time or datetime.now().time()
        start_t = datetime.strptime(q_start, "%H:%M").time()
        end_t = datetime.strptime(q_end, "%H:%M").time()

        is_in_quiet_period = False
        if start_t > end_t:  # Overnight range, e.g. 22:00 to 07:00
            is_in_quiet_period = (check_time >= start_t or check_time <= end_t)
        else:
            is_in_quiet_period = (start_t <= check_time <= end_t)

        if is_in_quiet_period:
            raise QuietHoursViolationError(
                f"Cannot send non-critical communication on channel '{ch_key}' during quiet hours ({q_start} - {q_end})."
            )
        return True

    def get_channel(self, channel: CommunicationChannel | str) -> Optional[Dict[str, Any]]:
        ch_key = channel.value if isinstance(channel, CommunicationChannel) else str(channel).upper()
        return self._channels.get(ch_key)
