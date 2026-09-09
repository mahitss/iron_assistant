# Kairo Evaluation Harness (`evals/`)

This directory contains benchmark scenarios, golden datasets, frozen baselines, deterministic test fixtures, and evaluation reports.

## Directory Layout

- `datasets/`: Curated benchmark scenarios.
  - `golden_v1.json`: Multi-category golden benchmark (tools, context, memory, knowledge, research, agents, automation, browser, voice, vision, performance).
  - `security_adversarial.json`: Adversarial scenarios (prompt injection, tool injection, SSRF, IDOR, authorization, secret leakage, emergency stop).
  - `holdout_v1.json`: Hidden holdout test set to detect model overfitting.
- `scenarios/`: Modular scenario definitions grouped by capability (e.g. `routing.json`, `companion.json`).
- `fixtures/`: Synthetic mock data (`fake_secrets.json`, `mock_github_ci.json`, `mock_web_pages.json`, `mock_documents.json`). Never commit real credentials.
- `baselines/`: Frozen release baseline metrics (`v1.0.0.json`, `v1.1.0.json`).
- `reports/`: Audit-ready evaluation run reports in JSON and Markdown.

## Scenario Authoring Quickstart

To author a new test scenario, add a JSON object to `evals/scenarios/<category>.json` or `evals/datasets/`:

```json
{
  "id": "<category>.<feature>.<three_digit_index>",
  "name": "Human-Readable Scenario Title",
  "category": "security",
  "input": "Prompt or event sent to Kairo",
  "context": {
    "project_id": "proj_123"
  },
  "expected_behavior": "Explicit description of expected behavior",
  "allowed_tools": ["tool_a", "tool_b"],
  "forbidden_tools": ["forbidden_tool"],
  "expected_output_properties": {
    "substrings": ["expected phrase"],
    "must_contain_keys": ["status", "result"]
  },
  "security_expectations": {
    "must_block": true,
    "approval_required": false,
    "prohibit_secret_leak": true
  },
  "timeout_seconds": 30.0,
  "grading_method": "deterministic"
}
```

### Golden Rules
1. **Namespaced IDs:** ID must follow `<category>.<feature>.<number>` (e.g., `tools.calculator.001`).
2. **Deterministic Graders:** Prefer deterministic assertions over subjective LLM judges.
3. **Synthetic Secrets Only:** Use `FAKE_API_KEY`, `FAKE_TOKEN`, or `FAKE_PRIVATE_KEY` for secret leakage tests. Real credentials are strictly forbidden.
4. **Binary Security Gates:** Security expectations are strict binary checks.
