"""FastAPI endpoints for Kairo Social & Communication Intelligence Engine."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.communication.schemas import (
    CommunicationChannel,
    CommunicationTone,
    DraftMessageSchema,
    RecipientSchema,
    SendRequestSchema,
    ThreadSchema,
    ThreadState,
)
from app.communication.service import CommunicationService

router = APIRouter(prefix="/communication", tags=["communication"])

# Global service instance
_comm_service: Optional[CommunicationService] = None


def get_comm_service() -> CommunicationService:
    global _comm_service
    if _comm_service is None:
        _comm_service = CommunicationService()
    return _comm_service


class InboundMessageRequest(BaseModel):
    raw_payload: Dict[str, Any]
    channel: CommunicationChannel = CommunicationChannel.EMAIL
    user_id: str = "default_user"
    project_id: Optional[str] = None


class DraftReplyRequest(BaseModel):
    custom_instructions: Optional[str] = None
    tone: CommunicationTone = CommunicationTone.FORMAL
    user_id: str = "default_user"


class ApproveDraftRequest(BaseModel):
    approver_identity: str = "user@kairo.internal"


class AddContactRequest(BaseModel):
    identity: str
    address: str
    display_name: Optional[str] = None
    is_external: bool = False
    organization: Optional[str] = None


@router.get("/health")
def communication_health() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service": "kairo_social_communication_intelligence",
        "supported_channels": [ch.value for ch in CommunicationChannel],
    }


@router.post("/messages/inbound")
def ingest_inbound_message(
    req: InboundMessageRequest,
    service: CommunicationService = Depends(get_comm_service),
) -> Dict[str, Any]:
    try:
        res = service.process_inbound_message(
            raw_payload=req.raw_payload,
            channel=req.channel,
            user_id=req.user_id,
            project_id=req.project_id,
        )
        return {
            "status": "processed",
            "message_id": res["message"].message_id,
            "thread_id": res["thread"].thread_id,
            "category": res["classification"]["primary_category"],
            "urgency": res["urgency"]["urgency"].value,
            "response_need": res["response_need"]["response_need"].value,
            "commitments_count": len(res["commitments"]),
        }
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex))


@router.get("/threads")
def list_threads(
    user_id: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
    state: Optional[ThreadState] = Query(None),
    service: CommunicationService = Depends(get_comm_service),
) -> List[Dict[str, Any]]:
    threads = service.threads.list_threads(user_id=user_id, project_id=project_id, state=state)
    return [t.model_dump() for t in threads]


@router.get("/threads/{thread_id}")
def get_thread_details(
    thread_id: str,
    service: CommunicationService = Depends(get_comm_service),
) -> Dict[str, Any]:
    thread = service.threads.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Thread '{thread_id}' not found.")
    summary = service.threads.generate_rolling_summary(thread_id)
    return {
        "thread": thread.model_dump(),
        "summary": summary,
    }


@router.post("/threads/{thread_id}/draft")
def generate_draft_reply(
    thread_id: str,
    req: DraftReplyRequest,
    service: CommunicationService = Depends(get_comm_service),
) -> Dict[str, Any]:
    try:
        draft = service.generate_reply_draft(
            thread_id=thread_id,
            user_id=req.user_id,
            custom_instructions=req.custom_instructions,
            tone=req.tone,
        )
        return draft.model_dump()
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex))


@router.get("/drafts")
def list_drafts(
    user_id: Optional[str] = Query(None),
    service: CommunicationService = Depends(get_comm_service),
) -> List[Dict[str, Any]]:
    drafts = service.drafts.list_drafts(user_id=user_id)
    return [d.model_dump() for d in drafts]


@router.post("/drafts/{draft_id}/approve")
def approve_draft(
    draft_id: str,
    req: ApproveDraftRequest,
    service: CommunicationService = Depends(get_comm_service),
) -> Dict[str, Any]:
    try:
        approved = service.drafts.approve_draft(draft_id, req.approver_identity)
        service.evaluator.record_user_feedback(
            draft_id=draft_id,
            feedback_type="approve",
            original_content=approved.body_reference,
        )
        return approved.model_dump()
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex))


@router.post("/send")
def send_message(
    req: SendRequestSchema,
    is_user_approved: bool = Query(False),
    service: CommunicationService = Depends(get_comm_service),
) -> Dict[str, Any]:
    try:
        receipt = service.send_communication(
            request=req,
            user_id=req.user_id,
            is_user_approved=is_user_approved,
        )
        return receipt.model_dump()
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex))


@router.get("/contacts")
def list_contacts(
    service: CommunicationService = Depends(get_comm_service),
) -> List[Dict[str, Any]]:
    return [c.model_dump() for c in service.contacts.list_contacts()]


@router.post("/contacts")
def add_contact(
    req: AddContactRequest,
    service: CommunicationService = Depends(get_comm_service),
) -> Dict[str, Any]:
    contact = service.contacts.add_contact(
        identity=req.identity,
        address=req.address,
        display_name=req.display_name,
        is_external=req.is_external,
        organization=req.organization,
    )
    return contact.model_dump()


@router.get("/commitments")
def list_commitments(
    user_id: Optional[str] = Query(None),
    owner: Optional[str] = Query(None),
    service: CommunicationService = Depends(get_comm_service),
) -> List[Dict[str, Any]]:
    return [c.model_dump() for c in service.commitments.list_commitments(user_id=user_id, owner=owner)]


@router.get("/followups")
def list_followups(
    user_id: Optional[str] = Query(None),
    service: CommunicationService = Depends(get_comm_service),
) -> List[Dict[str, Any]]:
    return [f.model_dump() for f in service.followups.list_pending_followups(user_id=user_id)]


@router.get("/metrics")
def get_metrics(
    service: CommunicationService = Depends(get_comm_service),
) -> Dict[str, Any]:
    return service.evaluator.get_summary_metrics()
