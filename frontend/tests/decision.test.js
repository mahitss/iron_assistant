/**
 * Unit tests for Kairo Executive Decision Engine (Task 57).
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { endpoints, decisionApi } from '../lib/api/endpoints.js';
import { DecisionView } from '../components/decision/decisionView.js';

describe('Executive Decision Engine Endpoints (Task 57)', () => {
  test('Endpoints exposes all decision methods', () => {
    assert.strictEqual(typeof endpoints.analyzeDecision, 'function');
    assert.strictEqual(typeof endpoints.listDecisions, 'function');
    assert.strictEqual(typeof endpoints.getDecision, 'function');
    assert.strictEqual(typeof endpoints.selectDecisionOption, 'function');
    assert.strictEqual(typeof endpoints.approveDecision, 'function');
    assert.strictEqual(typeof endpoints.revalidateDecision, 'function');
    assert.strictEqual(typeof endpoints.recordDecisionOutcome, 'function');
    assert.strictEqual(typeof endpoints.getDecisionOutcome, 'function');
    assert.strictEqual(typeof endpoints.getDecisionExplanation, 'function');
    assert.strictEqual(typeof endpoints.getDecisionAsOf, 'function');
    assert.strictEqual(typeof endpoints.getDecisionCalibrationAnalytics, 'function');
  });

  test('decisionApi wrapper exposes mapped methods', () => {
    assert.strictEqual(typeof decisionApi.analyze, 'function');
    assert.strictEqual(typeof decisionApi.list, 'function');
    assert.strictEqual(typeof decisionApi.get, 'function');
    assert.strictEqual(typeof decisionApi.select, 'function');
    assert.strictEqual(typeof decisionApi.approve, 'function');
    assert.strictEqual(typeof decisionApi.revalidate, 'function');
    assert.strictEqual(typeof decisionApi.recordOutcome, 'function');
    assert.strictEqual(typeof decisionApi.getOutcome, 'function');
    assert.strictEqual(typeof decisionApi.explain, 'function');
    assert.strictEqual(typeof decisionApi.reconstructAsOf, 'function');
    assert.strictEqual(typeof decisionApi.getAnalytics, 'function');
  });
});

describe('DecisionView Component', () => {
  test('initializes and renders decision support dashboard and advisory markers', () => {
    const mockContainer = {
      innerHTML: '',
      addEventListener: () => {},
      querySelectorAll: () => [],
      querySelector: () => null,
    };

    const view = new DecisionView({ container: mockContainer });
    assert.strictEqual(view.state.activeTab, 'requests');

    const html = view._template();
    assert.ok(html.includes('Kairo Executive Decision Engine'));
    assert.ok(html.includes('DECISION_SUPPORT_SYSTEM'));
    assert.ok(html.includes('Recommendation &ne; Decision &ne; Approval &ne; Execution &ne; Verification'));
    assert.ok(html.includes('Deliberate New Question'));
    assert.ok(html.includes('Revalidate'));
  });

  test('renders all tab templates without errors', () => {
    const mockContainer = {
      innerHTML: '',
      addEventListener: () => {},
      querySelectorAll: () => [],
      querySelector: () => null,
    };
    const view = new DecisionView({ container: mockContainer });

    // Mock state
    view.state.decisions = [
      {
        decision_id: 'dec_test123',
        status: 'RECOMMENDED',
        confidence: 0.85,
        user_override: false,
        approval_required: false,
        recommendation: {
          recommended_option_id: 'opt_1',
          headline: 'Recommend Progressive Deployment',
          why_selected: 'Highest reliability score.',
          worst_case_downside: 'Transient delay.',
          assumptions: ['Stable dependency.'],
        },
        ranking: {
          recommended_option_id: 'opt_1',
          ranked_options: [
            {
              option_id: 'opt_1',
              name: 'Progressive Deployment',
              rank: 1,
              raw_score: 0.85,
              normalized_score: 1.0,
              benefit_score: 0.88,
              risk_penalty: 0.05,
              cost_penalty: 0.10,
              score_breakdown: {},
              explanation: 'Top performer.',
            },
          ],
          dominated_option_ids: [],
          tradeoffs_summary: ['Cost vs Latency tradeoff.'],
        },
        decision_gates: {
          gate_1_context: { gate_number: 1, name: 'Context Valid', status: 'PASSED', message: 'Valid' },
        },
        provenance: { fingerprint: 'abc123sha' },
      },
    ];
    view.state.currentDecision = view.state.decisions[0];

    const reqTab = view._renderRequestsTab();
    assert.ok(reqTab.includes('dec_test123'));
    assert.ok(reqTab.includes('Progressive Deployment'));

    const rankTab = view._renderRankingTab();
    assert.ok(rankTab.includes('Ranked Candidate Options'));
    assert.ok(rankTab.includes('Progressive Deployment'));

    const toTab = view._renderTradeoffsTab();
    assert.ok(toTab.includes('Pareto Frontier & Multi-Objective Trade-Offs'));
    assert.ok(toTab.includes('Cost vs Latency tradeoff.'));

    const explainTab = view._renderExplainTab();
    assert.ok(explainTab.includes('Faithful Explanation Engine'));

    const gatesTab = view._renderGatesTab();
    assert.ok(gatesTab.includes('Ten Formal Decision Gates'));
    assert.ok(gatesTab.includes('Gate 1: Context Valid'));

    const calTab = view._renderCalibrationTab();
    assert.ok(calTab.includes('Quality & Calibration Analytics'));
  });
});
