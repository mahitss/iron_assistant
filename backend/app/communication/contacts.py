"""Contact resolution against authorized address books and ambiguity gating."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict
from app.communication.schemas import RecipientSchema, RecipientType


class ContactAmbiguityError(Exception):
    """Raised when multiple contacts match a target name and confirmation is required before sending."""

    def __init__(self, query: str, candidates: List[RecipientSchema]) -> None:
        self.query = query
        self.candidates = candidates
        msg = (
            f"Ambiguous contact query '{query}' matched {len(candidates)} candidates: "
            f"{[c.display_name or c.address for c in candidates]}. "
            f"Confirmation is required before sending."
        )
        super().__init__(msg)


class ContactNotFoundError(Exception):
    """Raised when a contact cannot be found in authorized address books."""
    pass


class ContactBook:
    """Manages authorized contacts and safe lookup without guessing."""

    def __init__(self) -> None:
        # identity/email -> RecipientSchema
        self._contacts: Dict[str, RecipientSchema] = {}

    def add_contact(
        self,
        identity: str,
        address: str,
        display_name: Optional[str] = None,
        recipient_type: RecipientType = RecipientType.TO,
        is_external: bool = False,
        organization: Optional[str] = None,
    ) -> RecipientSchema:
        contact = RecipientSchema(
            identity=identity,
            address=address,
            display_name=display_name or identity,
            recipient_type=recipient_type,
            is_external=is_external,
            organization=organization,
        )
        self._contacts[address.lower()] = contact
        self._contacts[identity.lower()] = contact
        return contact

    def resolve_contact(self, query: str, require_unambiguous: bool = True) -> RecipientSchema:
        """Resolves a contact string (email address, full name, or alias).

        INVARIANT 11 & 196: If multiple contacts match, NEVER guess an ambiguous recipient.
        Raise ContactAmbiguityError to gate consequential actions.
        """
        query_clean = query.strip().lower()
        if not query_clean:
            raise ContactNotFoundError("Empty contact query.")

        # Exact address or identity match
        if query_clean in self._contacts:
            return self._contacts[query_clean]

        # Search by display name or address prefix
        matches: List[RecipientSchema] = []
        seen_addresses = set()

        for c in self._contacts.values():
            if c.address in seen_addresses:
                continue
            name = (c.display_name or "").lower()
            addr = c.address.lower()
            if query_clean == name or query_clean in name.split() or query_clean in addr:
                matches.append(c)
                seen_addresses.add(c.address)

        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            if require_unambiguous:
                raise ContactAmbiguityError(query=query, candidates=matches)
            return matches[0]

        # If it looks like a valid explicit email address and not found, create new external recipient
        if "@" in query_clean and "." in query_clean:
            new_contact = RecipientSchema(
                identity=query.strip(),
                address=query.strip(),
                display_name=query.strip().split("@")[0],
                is_external=True,
            )
            return new_contact

        raise ContactNotFoundError(f"No contact found matching '{query}'.")

    def list_contacts(self) -> List[RecipientSchema]:
        seen = set()
        out = []
        for c in self._contacts.values():
            if c.address not in seen:
                out.append(c)
                seen.add(c.address)
        return out
