"""Communication policies, high-risk detection, and approval validation."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from app.communication.schemas import (
    CommunicationRiskSchema,
    DraftMessageSchema,
    PrivacyScope,
    RecipientSchema,
    RiskCategory,
    RiskSeverity,
)


class PolicyGatingError(Exception):
    """Raised when a high-risk communication fails policy gating or lacks required approval."""
    pass


class CommunicationPolicyEngine:
    """Evaluates high-risk communication triggers (financial, legal, security, employment, medical, access control)."""

    HIGH_RISK_TRIGGERS = {
        "financial": [r"\bwire transfer\b", r"\bbank account\b", r"\binvoice payment\b", r"\bpayroll\b", r"\$\d+,\d+"],
        "legal": [r"\blawsuit\b", r"\bnda\b", r"\bsettlement\b", r"\bliability\b", r"\bsubpoena\b", r"\bbreach of contract\b"],
        "security": [r"\bvulnerability\b", r"\bzero-day\b", r"\bexploit\b", r"\bincident response\b", r"\bcredentials\b"],
        "employment": [r"\btermination\b", r"\bseverance\b", r"\bdisciplinary\b", r"\boffer letter\b", r"\bsalary\b"],
        "medical": [r"\bdiagnosis\b", r"\bhipaa\b", r"\bpatient record\b", r"\bprescription\b"],
        "access_control": [r"\bgrant admin\b", r"\bsudo access\b", r"\broot permission\b", r"\bssh key\b"],
    }

    def evaluate_risk(
        self,
        content: str,
        recipients: List[RecipientSchema],
        audience: PrivacyScope = PrivacyScope.PRIVATE,
    ) -> List[CommunicationRiskSchema]:
        """INVARIANT 104 & 154: Evaluates communication risk across categories."""
        risks: List[CommunicationRiskSchema] = []
        lower_content = content.lower()

        # Check high-risk categories
        for category_name, patterns in self.HIGH_RISK_TRIGGERS.items():
            for pat in patterns:
                if re.search(pat, lower_content):
                    cat_enum = RiskCategory.LEGAL if category_name == "legal" else (
                        RiskCategory.FINANCIAL if category_name == "financial" else (
                            RiskCategory.SECURITY if category_name in ("security", "access_control") else RiskCategory.CONTENT
                        )
                    )
                    risks.append(
                        CommunicationRiskSchema(
                            audience=audience,
                            category=cat_enum,
                            severity=RiskSeverity.HIGH,
                            evidence=f"Matched high-risk keyword pattern '{pat}' in category '{category_name}'.",
                            mitigation="Require explicit user sign-off and multi-factor approval before transmission.",
                        )
                    )
                    break

        # External audience risk
        if any(r.is_external for r in recipients):
            risks.append(
                CommunicationRiskSchema(
                    audience=PrivacyScope.EXTERNAL,
                    category=RiskCategory.RECIPIENT,
                    severity=RiskSeverity.MEDIUM,
                    evidence="Outbound message includes external non-organization recipient.",
                    mitigation="Confirm recipient identity and external dispatch approval.",
                )
            )

        return risks

    def gate_send(
        self,
        draft: DraftMessageSchema,
        recipients: List[RecipientSchema],
        is_user_approved: bool = False,
    ) -> None:
        """INVARIANT 105: High-risk communication must pass Policy Engine."""
        risks = self.evaluate_risk(draft.body_reference, recipients)
        high_severity_risks = [r for r in risks if r.severity in (RiskSeverity.HIGH, RiskSeverity.CRITICAL)]

        if high_severity_risks and not is_user_approved and draft.status.value != "APPROVED":
            evidences = "; ".join([r.evidence for r in high_severity_risks])
            raise PolicyGatingError(
                f"Policy gating blocked transmission: High-risk communication detected ({evidences}). Explicit approval is required."
            )
