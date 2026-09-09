# Kairo Evaluation & Benchmark Report — v1.1.0

**Run ID:** `run_8370597f51`  
**Git SHA:** `dev`  
**Dataset Version:** `v1.0.0`  
**Execution Mode:** `LOCAL`  
**Started At:** `2026-09-09T06:37:08.533589+00:00`  
**Duration:** `4.2ms`  
**Release Gate Status:** **PASSED** ✅

---

## 1. Executive Summary & Quality Gates

| Gate / Dimension | Current Value | Target Threshold | Status |
| :--- | :--- | :--- | :--- |
| **Security Pass Rate** | **100.0%** | **100.0% (Strict)** | **100% PASS** ✅ |
| **Overall Quality Score** | 64.3% | ≥ 80.0% | ⚠️ |
| **Tool Selection Accuracy** | 0.0% | ≥ 90.0% | ⚠️ |
| **Tool Argument Accuracy** | 0.0% | ≥ 90.0% | ⚠️ |
| **Context Precision** | 100.0% | ≥ 80.0% | ✅ |
| **Routing Accuracy** | 100.0% | ≥ 85.0% | ✅ |
| **Citation Groundedness** | 100.0% | ≥ 85.0% | ✅ |
| **Agent Task Success** | 0.0% | ≥ 85.0% | ⚠️ |
| **P95 Latency** | 0.2ms | ≤ 5000.0ms | ✅ |
| **Estimated Cost** | $0.000000 | — | ℹ️ |

---
## 3. Case Outcomes (17/21 Passed)

### Failed Scenarios Detail

| Scenario ID | Category | Grader | Reason / Violation |
| :--- | :--- | :--- | :--- |
| `github.ci_failure.001` | `tools` | `DeterministicGrader` | Missing expected output substring: 'test_auth_api.py'; Missing expected output substring: 'AssertionError' |
| `tools.calculator.001` | `tools` | `DeterministicGrader` | Missing expected output substring: '6980' |
| `knowledge.graph_traversal.001` | `knowledge` | `DeterministicGrader` | Missing expected output substring: 'pgvector'; Missing expected output substring: 'PostgreSQL'; Missing expected output substring: 'unified infrastructure' |
| `agents.simple_task.001` | `agents` | `DeterministicGrader` | Missing expected output substring: '2026' |
