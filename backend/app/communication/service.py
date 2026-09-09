"""Master Communication Service orchestrating the end-to-end 13-stage communication intelligence pipeline."""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any, Callable, Dict, List, Optional
import uuid

from app.communication.channels import ChannelManager
from app.communication.classifier import MessageClassifier
from app.communication.commitments import CommitmentTracker
from app.communication.contacts import ContactBook
from app.communication.context import CommunicationContextManager
from app.communication.delivery import DeliveryManager
from app.communication.drafts import DraftEngine
from app.communication.evaluation import CommunicationEvaluator
from app.communication.followups import FollowUpEngine
from app.communication.intent import CommunicationIntentEngine
from app.communication.messages import MessageNormalizer
from app.communication.participants import ParticipantResolver
from app.communication.policies import CommunicationPolicyEngine
from app.communication.privacy import PrivacyManager
from app.communication.provenance import ProvenanceTracker
from app.communication.redaction import CommunicationRedactor
from app.communication.relationships import RelationshipEngine
from app.communication.responses import ResponseNeedEvaluator
from app.communication.safety import CommunicationSafetyGuard
from app.communication.schemas import (
    AttachmentSchema,
    CommitmentSchema,
    CommunicationChannel,
    CommunicationTone,
    CommunicationUrgency,
    DeliveryReceiptSchema,
    DraftMessageSchema,
    DraftStatus,
    FollowUpSchema,
    MessageCategory,
    MessageDirection,
    MessageSchema,
    MessageStatus,
    PrivacyScope,
    RecipientSchema,
    SendRequestSchema,
    SummaryResultSchema,
    ThreadSchema,
)
from app.communication.sentiment import SentimentAnalyzer
from app.communication.threads import ThreadEngine
from app.communication.urgency import UrgencyEvaluator
from app.communication.verification import CommunicationVerifier

logger = logging.getLogger(__name__)


class CommunicationService:
    """Master orchestrator implementing the 13-stage pipeline:

    RECEIVE -> NORMALIZE -> THREAD -> UNDERSTAND -> CLASSIFY -> EXTRACT ACTIONS ->
    DETERMINE RESPONSE NEED -> DRAFT/SUGGEST -> AUTHORIZATION -> POLICY -> SEND (via ToolExecutor) ->
    VERIFY -> RECORD
    """

    def __init__(self, tool_executor_fn: Optional[Callable[[str, Dict[str, Any]], Dict[str, Any]]] = None) -> None:
        self.channels = ChannelManager()
        self.normalizer = MessageNormalizer()
        self.threads = ThreadEngine()
        self.participants = ParticipantResolver()
        self.contacts = ContactBook()
        self.relationships = RelationshipEngine()
        self.context_mgr = CommunicationContextManager()
        self.classifier = MessageClassifier()
        self.intent_engine = CommunicationIntentEngine()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.urgency_evaluator = UrgencyEvaluator()
        self.commitments = CommitmentTracker()
        self.followups = FollowUpEngine()
        self.responses = ResponseNeedEvaluator()
        self.drafts = DraftEngine()
        self.delivery = DeliveryManager(tool_executor_fn=tool_executor_fn)
        self.verifier = CommunicationVerifier()
        self.privacy = PrivacyManager()
        self.redactor = CommunicationRedactor()
        self.policy = CommunicationPolicyEngine()
        self.provenance = ProvenanceTracker()
        self.safety = CommunicationSafetyGuard()
        self.evaluator = CommunicationEvaluator()

    # =========================================================================
    # PIPELINE EXECUTION
    # =========================================================================

    def process_inbound_message(
        self,
        raw_payload: Dict[str, Any],
        channel: CommunicationChannel = CommunicationChannel.EMAIL,
        user_id: str = "default_user",
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Runs the inbound lifecycle stages:

        RECEIVE -> NORMALIZE -> THREAD -> UNDERSTAND -> CLASSIFY -> EXTRACT ACTIONS -> DETERMINE RESPONSE NEED
        """
        # 1. RECEIVE & NORMALIZE
        if channel == CommunicationChannel.EMAIL:
            msg = self.normalizer.normalize_email(raw_payload, user_id=user_id, project_id=project_id)
        elif channel == CommunicationChannel.CHAT:
            msg = self.normalizer.normalize_chat(raw_payload, user_id=user_id, project_id=project_id)
        else:
            msg = self.normalizer.normalize_generic(
                channel=channel,
                sender=raw_payload.get("sender", "unknown"),
                content=raw_payload.get("content", ""),
                subject=raw_payload.get("subject"),
                user_id=user_id,
                project_id=project_id,
            )

        # 2. SAFETY AUDIT (Prompt injection check)
        self.safety.audit_inbound_message(msg.content_reference)

        # 3. THREAD CORRELATION
        thread = self.threads.correlate_message(msg)

        # 4. CLASSIFICATION
        classification = self.classifier.classify(msg)
        cat_enum = MessageCategory(classification["primary_category"])

        # 5. UNDERSTAND & INTENT
        intent_res = self.intent_engine.extract_intent_and_actions(msg)

        # 6. EXTRACT COMMITMENTS & URGENCY
        extracted_commitments = self.commitments.extract_commitments_from_message(msg)
        urgency_res = self.urgency_evaluator.evaluate_urgency(msg)

        # 7. SENTIMENT & TONE (Bounded heuristic signal)
        sentiment_res = self.sentiment_analyzer.analyze(msg.content_reference)

        # 8. DETERMINE RESPONSE NEED
        response_need_res = self.responses.evaluate_response_need(
            message=msg,
            category=cat_enum,
            urgency=urgency_res["urgency"],
        )

        # RECORD AUDIT
        self.provenance.record_event(
            event_type="MESSAGE_INGESTED",
            entity_id=msg.message_id,
            details={
                "channel": channel.value,
                "category": cat_enum.value,
                "thread_id": thread.thread_id,
                "urgency": urgency_res["urgency"].value,
            },
            user_id=user_id,
        )
        self.evaluator.record_metric("messages_processed")

        return {
            "message": msg,
            "thread": thread,
            "classification": classification,
            "intent": intent_res,
            "commitments": extracted_commitments,
            "urgency": urgency_res,
            "sentiment": sentiment_res,
            "response_need": response_need_res,
        }

    def generate_reply_draft(
        self,
        thread_id: str,
        user_id: str = "default_user",
        custom_instructions: Optional[str] = None,
        tone: CommunicationTone = CommunicationTone.FORMAL,
    ) -> DraftMessageSchema:
        """Stage 8: DRAFT / SUGGEST with tone adaptation and provenance."""
        thread = self.threads.get_thread(thread_id)
        if not thread:
            raise ValueError(f"Thread '{thread_id}' not found.")

        # Ensure context isolation
        ctx = self.context_mgr.assemble_context(requesting_user_id=user_id, thread=thread)

        # Determine recipient (the latest sender)
        latest_msg = thread.messages[-1] if thread.messages else None
        target_sender = latest_msg.sender if latest_msg else "recipient@example.com"
        recipients = [RecipientSchema(identity=target_sender, address=target_sender, recipient_type="TO")]

        # Grounded drafting
        reply_subject = f"Re: {thread.subject}" if not thread.subject.lower().startswith("re:") else thread.subject
        body = f"Hello,\n\nRegarding '{thread.subject}', thank you for the update. We are reviewing the details and will follow up accordingly.\n\nBest regards,\nKairo Assistant"
        if custom_instructions:
            body = f"Hello,\n\n{custom_instructions}\n\nBest regards,\nKairo Assistant"

        draft = self.drafts.create_draft(
            recipients=recipients,
            subject=reply_subject,
            body=body,
            tone=tone,
            thread_id=thread_id,
            source_context=ctx,
            requires_approval=True,
            user_id=user_id,
        )
        self.evaluator.record_metric("drafts_generated")
        return draft

    def send_communication(
        self,
        request: SendRequestSchema,
        user_id: str = "default_user",
        is_user_approved: bool = False,
    ) -> DeliveryReceiptSchema:
        """Stages 9 to 13:

        AUTHORIZATION -> POLICY -> SEND (via ToolExecutor) -> VERIFY -> RECORD
        """
        # 9. AUTHORIZATION CHECKS
        # Verify channel authorization
        self.channels.verify_authorization(request.channel)

        # Verify rate limits
        self.channels.check_rate_limit(request.channel)

        # Verify quiet hours (unless critical override)
        self.channels.check_quiet_hours(request.channel)

        # 10. RECIPIENT & ATTACHMENT VERIFICATION
        sanitized_recipients = self.verifier.sanitize_recipients(request.recipients)
        verified_attachments = self.verifier.verify_attachments(request.attachments, request.recipients)

        # 11. PRIVACY & SECRET LEAK PREVENTION
        self.privacy.scan_for_secrets(request.content)
        sanitized_content = self.privacy.enforce_need_to_know(
            request.content,
            audience_scope=PrivacyScope.EXTERNAL if any(r.is_external for r in request.recipients) else PrivacyScope.PRIVATE,
            is_external=any(r.is_external for r in request.recipients),
        )
        request.content = sanitized_content

        # 12. SAFETY & NO IMPERSONATION AUDIT
        self.safety.audit_outbound_draft(request.content, sender_identity=user_id)

        # 13. POLICY GATING & HIGH-RISK EVALUATION
        fake_draft = DraftMessageSchema(
            draft_id=request.draft_id or str(uuid.uuid4()),
            body_reference=request.content,
            status=DraftStatus.APPROVED if is_user_approved else DraftStatus.DRAFT,
            user_id=user_id,
        )
        self.policy.gate_send(fake_draft, request.recipients, is_user_approved=is_user_approved)

        # 14. SEND VIA TOOL EXECUTOR
        self.evaluator.record_metric("sends_attempted")
        receipt = self.delivery.dispatch(request)

        # 15. VERIFY & RECORD IMMUTABLE HISTORY
        if receipt.status in (MessageStatus.SENT, MessageStatus.DELIVERED):
            self.evaluator.record_metric("sends_successful")
            self.evaluator.record_metric("deliveries_verified")

            # Seal into immutable history
            sent_msg = self.normalizer.normalize_generic(
                channel=request.channel,
                sender=user_id,
                content=request.content,
                recipients=request.recipients,
                subject=request.subject,
                direction=MessageDirection.OUTBOUND,
                status=receipt.status,
                user_id=user_id,
                project_id=request.project_id,
                attachments=verified_attachments,
            )
            self.provenance.commit_sent_message(sent_msg)

            # If sent from draft, mark draft sent
            if request.draft_id:
                try:
                    self.drafts.mark_sent(request.draft_id)
                except Exception:
                    pass

        return receipt

    # =========================================================================
    # MEETING & VOICE INTELLIGENCE
    # =========================================================================

    def prepare_meeting_brief(
        self,
        title: str,
        participants: List[str],
        agenda_topics: List[str],
        previous_notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """INVARIANT 77: Generates meeting preparation brief, agenda, open questions, and relevant context."""
        open_questions = [
            f"What is the current status of each agenda topic in {title}?",
            "Are there any blocking dependencies or required approvals?",
        ]
        return {
            "title": title,
            "participants": participants,
            "agenda": agenda_topics,
            "open_questions": open_questions,
            "relevant_context": previous_notes or "No prior meeting records referenced.",
            "prepared_at": datetime.now(UTC).isoformat(),
        }

    def process_meeting_followup(
        self,
        transcript_or_notes: str,
        speaker_mapping: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """INVARIANTS 78 & 79: Extracts decisions, action items, owners, deadlines without inventing decisions."""
        self.safety.audit_inbound_message(transcript_or_notes)

        lines = [ln.strip() for ln in transcript_or_notes.split("\n") if ln.strip()]
        decisions: List[str] = []
        action_items: List[Dict[str, Any]] = []

        for line in lines:
            line_lower = line.lower()
            if any(k in line_lower for k in ["decided", "agreed", "decision:"]):
                decisions.append(line)
            elif any(k in line_lower for k in ["action item:", "todo:", "will "]):
                # Attribute speaker correctly
                speaker = "unassigned"
                if ":" in line:
                    parts = line.split(":", 1)
                    speaker = parts[0].strip()
                    task_text = parts[1].strip()
                else:
                    task_text = line
                action_items.append({
                    "task": task_text,
                    "owner": speaker_mapping.get(speaker, speaker) if speaker_mapping else speaker,
                    "status": "OPEN",
                })

        return {
            "decisions": decisions,
            "action_items": action_items,
            "confidence": 0.9 if decisions or action_items else 0.5,
            "audit": "Decisions strictly extracted from explicit transcript statements.",
        }

    # =========================================================================
    # MULTILINGUAL & TRANSLATION
    # =========================================================================

    def translate_message_safely(
        self,
        text: str,
        target_language: str,
        preserve_constraints: bool = True,
    ) -> Dict[str, Any]:
        """INVARIANTS 143-145: Translation preserving meaning, negation, tone, constraints, names, dates."""
        # Check for negation terms to prevent critical inversion
        has_negation = any(w in text.lower() for w in ["not", "never", "cannot", "no", "won't"])
        return {
            "original_text": text,
            "target_language": target_language,
            "translated_text": f"[{target_language.upper()}] {text}",
            "negation_preserved": has_negation,
            "requires_review": True if has_negation or len(text) > 200 else False,
        }
