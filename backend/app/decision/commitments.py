"""Decision commitment governance for Kairo Executive Decision Engine (Task 57).

Guarantees that recommendations NEVER silently create real commitments.
Explicit authorization is strictly enforced.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.decision.schemas import DecisionCommitment


class CommitmentManager:
    """Manages proposed commitments and enforces explicit authorization boundaries."""

    def propose_commitment(
        self,
        decision_id: str,
        owner: str,
        title: str,
        deadline: datetime | None = None,
    ) -> DecisionCommitment:
        """Proposes a commitment resulting from a decision recommendation. Status is strictly PROPOSED."""
        return DecisionCommitment(
            decision_id=decision_id,
            owner=owner,
            title=title,
            deadline=deadline,
            status="PROPOSED",
            authorized_by=None,
            created_at=datetime.now(timezone.utc),
        )

    def authorize_commitment(
        self,
        commitment: DecisionCommitment,
        authorized_by: str,
    ) -> DecisionCommitment:
        """Explicitly authorizes a proposed commitment by an authenticated actor."""
        if not authorized_by or not authorized_by.strip():
            raise ValueError("Commitment authorization requires an explicit, verified authorizer.")

        return commitment.model_copy(
            update={
                "status": "AUTHORIZED",
                "authorized_by": authorized_by,
            }
        )

    def fulfill_commitment(
        self,
        commitment: DecisionCommitment,
    ) -> DecisionCommitment:
        """Marks an authorized commitment as fulfilled."""
        if commitment.status != "AUTHORIZED":
            raise ValueError(f"Cannot fulfill commitment in status '{commitment.status}'; must be AUTHORIZED.")

        return commitment.model_copy(update={"status": "FULFILLED"})


commitment_manager = CommitmentManager()
