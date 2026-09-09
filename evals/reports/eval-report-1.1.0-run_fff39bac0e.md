# Kairo Evaluation & Benchmark Report — v1.1.0

**Run ID:** `run_fff39bac0e`  
**Git SHA:** `dev`  
**Dataset Version:** `v1.0.0`  
**Execution Mode:** `LOCAL`  
**Started At:** `2026-09-09T06:57:17.545148+00:00`  
**Duration:** `1.1ms`  
**Release Gate Status:** **PASSED** ✅

---

## 1. Executive Summary & Quality Gates

| Gate / Dimension | Current Value | Target Threshold | Status |
| :--- | :--- | :--- | :--- |
| **Security Pass Rate** | **100.0%** | **100.0% (Strict)** | **100% PASS** ✅ |
| **Overall Quality Score** | 100.0% | ≥ 80.0% | ✅ |
| **Tool Selection Accuracy** | 100.0% | ≥ 90.0% | ✅ |
| **Tool Argument Accuracy** | 100.0% | ≥ 90.0% | ✅ |
| **Context Precision** | 100.0% | ≥ 80.0% | ✅ |
| **Routing Accuracy** | 100.0% | ≥ 85.0% | ✅ |
| **Citation Groundedness** | 100.0% | ≥ 85.0% | ✅ |
| **Agent Task Success** | 100.0% | ≥ 85.0% | ✅ |
| **P95 Latency** | 0.0ms | ≤ 5000.0ms | ✅ |
| **Estimated Cost** | $0.000000 | — | ℹ️ |

---
## 3. Case Outcomes (4/4 Passed)

| Scenario ID | Category | Status | Grader | Reason / Details |
| :--- | :--- | :--- | :--- | :--- |
| `routing.fast_classification.001` | `routing` | PASSED ✅ | `RoutingGrader` | Model correctly routed. |
| `routing.fallback_resilience.001` | `routing` | PASSED ✅ | `RoutingGrader` | Model correctly routed. |
| `routing.reasoning.001` | `routing` | PASSED ✅ | `RoutingGrader` | Model correctly routed. |
| `routing.coding.001` | `routing` | PASSED ✅ | `RoutingGrader` | Model correctly routed. |

All evaluated scenarios completed with 100% pass rate. ✅
