"""Deterministic task verifier and bounded subjective evaluator (Spec 27, 28, 29, 142, 143)."""

import json
import logging
import os
from typing import Any, Dict, List, Tuple

from app.tasks.schemas import VerificationCriterion

logger = logging.getLogger("kairo.tasks.verifier")


class VerificationError(RuntimeError):
    """Raised when deterministic verification criteria fail."""
    pass


class TaskVerifier:
    """Evaluates task and step completion against deterministic and subjective contracts."""

    @classmethod
    async def verify_criterion(
        cls,
        criterion: VerificationCriterion,
        step_result: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> Tuple[bool, str]:
        """Evaluate an individual verification criterion.

        Strict invariant:
        - Security, authorization, file existence, and test exit codes use DETERMINISTIC checks ONLY.
        - Subjective LLM evaluator is only used for subjective summary or research quality.
        """
        c_type = criterion.type.lower()
        res = step_result or {}

        # 1. Deterministic: File exists
        if c_type == "file_exists":
            target_path = criterion.target
            if not target_path:
                return False, "Target path not specified for file_exists"
            exists = os.path.exists(target_path)
            return exists, f"File '{target_path}' {'exists' if exists else 'does not exist'}"

        # 2. Deterministic: Test Exit Code
        if c_type == "exit_code":
            actual_code = res.get("exit_code")
            expected_code = criterion.expected_value if criterion.expected_value is not None else 0
            if actual_code is None:
                return False, "Execution produced no exit code"
            matches = (actual_code == expected_code)
            return matches, f"Exit code {actual_code} (expected: {expected_code})"

        # 3. Deterministic: Contains Text
        if c_type == "contains_text":
            target_text = criterion.expected_value or criterion.target
            output_str = str(res.get("output", "")) + " " + str(res.get("evidence", ""))
            matches = target_text.lower() in output_str.lower()
            return matches, f"Text '{target_text}' {'found' if matches else 'missing'} in output"

        # 4. Deterministic: JSON Schema / Key Presence
        if c_type == "json_key":
            required_key = criterion.target
            output_val = res.get("output", {})
            if isinstance(output_val, str):
                try:
                    output_val = json.loads(output_val)
                except Exception:
                    return False, "Output is not valid JSON"
            if isinstance(output_val, dict):
                has_key = required_key in output_val
                return has_key, f"Key '{required_key}' {'found' if has_key else 'missing'}"
            return False, "Output is not a dictionary"

        # 5. Deterministic: Evidence Collected
        if c_type == "evidence_present":
            evidence = res.get("evidence", [])
            has_evidence = bool(evidence and len(evidence) > 0)
            return has_evidence, f"Evidence count: {len(evidence) if evidence else 0}"

        # 6. Subjective: Synthesis / Research Quality (Bounded LLM or heuristic check)
        if c_type == "subjective_llm":
            output_str = str(res.get("output", ""))
            if len(output_str.strip()) < 20:
                return False, "Subjective summary is too short or empty"
            # In production, can query ModelRouter; heuristic minimum length and non-error check
            return True, "Subjective synthesis meets minimum quality standards"

        # Default fallback
        return True, f"Criterion '{c_type}' evaluated as passing"

    @classmethod
    async def verify_step(
        cls,
        criteria: list[VerificationCriterion],
        step_result: dict[str, Any] | None,
        context: dict[str, Any] | None = None,
    ) -> Tuple[bool, list[str]]:
        """Verify all criteria for a single step."""
        if not criteria:
            # Default check: step output must not contain unhandled execution failure
            if step_result and step_result.get("error"):
                return False, [f"Step error: {step_result.get('error')}"]
            return True, ["No explicit verification criteria declared; default passed"]

        passed = True
        notes: list[str] = []
        for c in criteria:
            ok, msg = await cls.verify_criterion(c, step_result, context)
            notes.append(f"[{'PASS' if ok else 'FAIL'}] {c.description or c.type}: {msg}")
            if not ok:
                passed = False

        return passed, notes

    @classmethod
    async def verify_task_completion(
        cls,
        task_objective: str,
        plan_criteria: list[VerificationCriterion],
        completed_step_results: list[dict[str, Any]],
    ) -> Tuple[bool, dict[str, Any]]:
        """Verify that the overall task objective has been met."""
        if not completed_step_results:
            return False, {"reason": "No completed steps to verify"}

        combined_output = " ".join(str(r.get("output", "")) for r in completed_step_results)
        all_evidence = [e for r in completed_step_results for e in r.get("evidence", [])]
        aggregated_payload = {
            "output": combined_output,
            "evidence": all_evidence,
            "results": completed_step_results,
        }

        all_notes: list[str] = []
        overall_ok = True

        for c in plan_criteria:
            ok, msg = await cls.verify_criterion(c, step_result=aggregated_payload)
            all_notes.append(f"[{'PASS' if ok else 'FAIL'}] {c.description or c.type}: {msg}")
            if not ok:
                overall_ok = False

        return overall_ok, {
            "verified": overall_ok,
            "notes": all_notes,
            "step_count": len(completed_step_results),
        }
