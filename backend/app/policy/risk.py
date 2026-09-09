"""Deterministic 5-Tier Risk Engine for Kairo Governance (Task 36).

Never allows an LLM to freely decide the final risk level.
Strictly uses deterministic risk factor evaluation and escalation.
"""

from typing import Any

from app.policy.schemas import PolicyContext, RiskLevel
from app.security.risk import TOOL_RISK_MAP, RiskLevel as SecurityRiskLevel


class DeterministicRiskEngine:
    """Evaluates multi-dimensional risk factors and deterministically calculates the risk level."""

    READ_VERBS = {
        "read", "get", "list", "search", "inspect", "status", "view",
        "fetch", "describe", "check", "diff", "branches", "logs", "metrics"
    }
    LOW_VERBS = {
        "navigate", "scroll", "move", "wait", "calculate", "analyze", "format", "ping"
    }
    MODERATE_VERBS = {
        "click", "mouse_click", "save_draft", "create_branch", "checkout",
        "stage_file", "generate", "summarize", "convert"
    }
    HIGH_VERBS = {
        "push", "commit", "create_pr", "type_text", "form_submission", "execute",
        "run_command", "send", "notify", "update", "patch", "deploy_staging",
        "reboot", "restart_service"
    }
    CRITICAL_VERBS = {
        "delete", "drop", "purge", "wipe", "terminate", "destroy", "revoke",
        "deploy_production", "publish", "modify_security", "change_password",
        "grant_permission", "financial_transfer", "pay", "execute_raw_sql",
        "rotate_keys", "export_all_data"
    }

    @classmethod
    def evaluate_risk(cls, context: PolicyContext) -> tuple[RiskLevel, list[str]]:
        """Compute the deterministic risk level and list contributing risk factors."""
        factors: list[str] = []
        base_level = RiskLevel.R1_LOW

        # 1. Action verb analysis
        action = (context.action or "").strip().lower()
        if action in cls.READ_VERBS or (action.startswith("get_") or action.startswith("list_") or action.startswith("read_")):
            base_level = RiskLevel.R0_READ_ONLY
            factors.append(f"read_only_action:{action}")
        elif action in cls.LOW_VERBS:
            base_level = RiskLevel.R1_LOW
            factors.append(f"low_impact_action:{action}")
        elif action in cls.MODERATE_VERBS:
            base_level = RiskLevel.R2_MODERATE
            factors.append(f"interactive_action:{action}")
        elif action in cls.HIGH_VERBS:
            base_level = RiskLevel.R3_HIGH
            factors.append(f"high_impact_action:{action}")
        elif action in cls.CRITICAL_VERBS or "delete" in action or "destroy" in action or "purge" in action:
            base_level = RiskLevel.R4_CRITICAL
            factors.append(f"destructive_action:{action}")

        # 2. Tool-based mapping integration
        tool_name = ""
        if isinstance(context.tool, dict):
            tool_name = context.tool.get("name", "")
        elif isinstance(context.tool, str):
            tool_name = context.tool

        # 2. Computer Control Granular Classification (Section 32)
        if tool_name.startswith("computer_"):
            if any(k in action for k in ("system_settings", "account_change", "sudo")):
                factors.append("computer_control:system_critical")
                base_level = RiskLevel.R4_CRITICAL
            elif tool_name in ("computer_screenshot", "computer_wait", "computer_mouse_move", "computer_mouse_scroll"):
                factors.append("computer_control:observe")
                base_level = RiskLevel.R1_LOW
            elif tool_name in ("computer_click", "computer_mouse_click", "computer_mouse_double_click"):
                factors.append("computer_control:click")
                base_level = RiskLevel.R2_MODERATE
            elif tool_name in ("computer_type", "computer_type_text", "computer_press_key"):
                factors.append("computer_control:input")
                base_level = RiskLevel.R3_HIGH
        elif tool_name and tool_name in TOOL_RISK_MAP:
            sec_risk = TOOL_RISK_MAP[tool_name]
            factors.append(f"tool_risk:{tool_name}:{sec_risk.value}")
            if sec_risk == SecurityRiskLevel.CRITICAL:
                base_level = cls._escalate(base_level, RiskLevel.R4_CRITICAL)
            elif sec_risk == SecurityRiskLevel.HIGH:
                base_level = cls._escalate(base_level, RiskLevel.R3_HIGH)
            elif sec_risk == SecurityRiskLevel.MEDIUM:
                base_level = cls._escalate(base_level, RiskLevel.R2_MODERATE)

        # 4. Environment factor (Production escalates risk)
        env = (context.environment or "development").strip().lower()
        if env == "production":
            factors.append("target_environment:production")
            # If action is not strictly read-only, escalate to HIGH or CRITICAL
            if base_level != RiskLevel.R0_READ_ONLY:
                base_level = cls._escalate(base_level, RiskLevel.R3_HIGH)
                if any(x in action for x in ("deploy", "delete", "modify", "patch", "config", "execute")):
                    base_level = RiskLevel.R4_CRITICAL
                    factors.append("production_mutation")

        # 5. Financial factor
        target_str = str(context.target or "").lower()
        if any(w in action for w in ("pay", "billing", "transfer", "purchase", "credit_card", "invoice")) or \
           any(w in target_str for w in ("payment", "stripe", "billing", "bank", "card")):
            factors.append("financial_operation")
            base_level = RiskLevel.R4_CRITICAL

        # 6. Security factor (IAM, firewalls, credentials)
        if any(w in action for w in ("security", "permission", "firewall", "credential", "auth_rule", "iam")) or \
           any(w in target_str for w in ("secrets", ".env", "id_rsa", "password", "token", "api_key", "iam")):
            factors.append("security_sensitive_operation")
            base_level = RiskLevel.R4_CRITICAL

        # 7. Data Classification factor
        data_scope = context.data_scope or {}
        classification = str(data_scope.get("classification", "")).upper()
        if classification == "RESTRICTED" or data_scope.get("contains_secrets"):
            factors.append("data_classification:RESTRICTED_OR_SECRETS")
            base_level = RiskLevel.R4_CRITICAL
        elif classification == "SENSITIVE":
            factors.append("data_classification:SENSITIVE")
            base_level = cls._escalate(base_level, RiskLevel.R3_HIGH)

        # 8. Blast radius factor
        target_dict = context.target if isinstance(context.target, dict) else {}
        blast_radius = target_dict.get("blast_radius") or (context.task or {}).get("blast_radius")
        if blast_radius in ("multi_project", "entire_cluster", "all_users", "organization"):
            factors.append(f"large_blast_radius:{blast_radius}")
            base_level = cls._escalate(base_level, RiskLevel.R4_CRITICAL)
        elif blast_radius in ("project", "environment"):
            factors.append(f"moderate_blast_radius:{blast_radius}")
            base_level = cls._escalate(base_level, RiskLevel.R3_HIGH)

        # 9. Irreversibility factor
        if target_dict.get("reversible") is False or (context.task or {}).get("reversible") is False or \
           any(k in action for k in ("hard_delete", "drop_table", "truncate", "revoke_permanently")):
            factors.append("irreversible_operation")
            base_level = cls._escalate(base_level, RiskLevel.R3_HIGH)

        # 10. Data bulk export
        if data_scope.get("bulk_export") is True:
            factors.append("bulk_data_export")
            base_level = cls._escalate(base_level, RiskLevel.R3_HIGH)

        return base_level, factors

    @staticmethod
    def _escalate(current: RiskLevel, candidate: RiskLevel) -> RiskLevel:
        """Escalate to the highest applicable risk level. Never average risk."""
        if candidate.severity > current.severity:
            return candidate
        return current
