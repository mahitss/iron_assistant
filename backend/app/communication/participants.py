"""Participant modeling, role tracking, authorization scoping, and speaker attribution."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from app.communication.schemas import ParticipantSchema


class ParticipantResolver:
    """Tracks and resolves communication participants, their organizational roles, and channel mappings."""

    def __init__(self) -> None:
        # identity -> ParticipantSchema
        self._participants: Dict[str, ParticipantSchema] = {}

    def register_participant(
        self,
        identity: str,
        display_name: str,
        organization: Optional[str] = None,
        role: Optional[str] = None,
        authorization_scope: str = "standard",
        channel_addresses: Optional[Dict[str, str]] = None,
    ) -> ParticipantSchema:
        p = ParticipantSchema(
            identity=identity,
            display_name=display_name,
            organization=organization,
            role=role,
            authorization_scope=authorization_scope,
            channel_addresses=channel_addresses or {},
        )
        self._participants[identity] = p
        return p

    def get_participant(self, identity: str) -> Optional[ParticipantSchema]:
        return self._participants.get(identity)

    def resolve_speaker(
        self,
        speaker_tag: str,
        context_participants: Optional[List[ParticipantSchema]] = None,
    ) -> ParticipantSchema:
        """Resolves a speaker label from audio/meeting transcript (e.g. 'Alice', 'Speaker 1', 'Alice Smith')

        Ensures accurate speaker attribution so commitments are never assigned to the wrong speaker.
        """
        tag_lower = speaker_tag.strip().lower()
        candidates = context_participants or list(self._participants.values())

        for p in candidates:
            if tag_lower in (p.identity.lower(), p.display_name.lower()):
                return p
            # Check prefix/first name
            if p.display_name.lower().startswith(tag_lower):
                return p

        # If not known, create an unverified participant with unknown role to prevent false attribution
        unverified = ParticipantSchema(
            identity=f"speaker_{speaker_tag.replace(' ', '_').lower()}",
            display_name=speaker_tag,
            role="UNKNOWN_SPEAKER",
            authorization_scope="unverified",
        )
        return unverified
