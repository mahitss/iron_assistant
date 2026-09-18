/**
 * Frontend Unit & Component Tests for Task 114:
 * Kairo Autonomous Active Observation, Value-of-Information & Uncertainty Reduction Engine
 */

import test from 'node:test';
import assert from 'node:assert';
import { observationsApi } from '../lib/api/endpoints.js';
import { ActiveObservationView } from '../components/observation/activeObservationView.js';

test('Active Observation API Endpoints (Task 114)', async (t) => {
  await t.test('observationsApi exposes all required Task 114 methods', () => {
    assert.strictEqual(typeof observationsApi.createPlan, 'function');
    assert.strictEqual(typeof observationsApi.listPlans, 'function');
    assert.strictEqual(typeof observationsApi.getPlan, 'function');
    assert.strictEqual(typeof observationsApi.getGaps, 'function');
    assert.strictEqual(typeof observationsApi.getCandidates, 'function');
    assert.strictEqual(typeof observationsApi.getValue, 'function');
    assert.strictEqual(typeof observationsApi.getCost, 'function');
    assert.strictEqual(typeof observationsApi.getRisk, 'function');
    assert.strictEqual(typeof observationsApi.getUncertainty, 'function');
    assert.strictEqual(typeof observationsApi.executePlan, 'function');
    assert.strictEqual(typeof observationsApi.cancelPlan, 'function');
    assert.strictEqual(typeof observationsApi.refreshPlan, 'function');
    assert.strictEqual(typeof observationsApi.listAllGaps, 'function');
    assert.strictEqual(typeof observationsApi.getEntityUncertainty, 'function');
    assert.strictEqual(typeof observationsApi.getHistory, 'function');
  });
});

test('ActiveObservationView Component (Task 114)', async (t) => {
  const mockContainer = {
    innerHTML: '',
    querySelector: (selector) => {
      return {
        textContent: '',
        value: 'system_core',
        style: {},
        addEventListener: () => {},
        setAttribute: () => {},
        getAttribute: () => 'matrix',
      };
    },
    querySelectorAll: (selector) => {
      return [
        {
          style: {},
          dataset: { tab: 'matrix' },
          addEventListener: () => {},
        },
        {
          style: {},
          dataset: { tab: 'gaps' },
          addEventListener: () => {},
        },
        {
          style: {},
          dataset: { tab: 'options' },
          addEventListener: () => {},
        },
      ];
    },
  };

  const samplePlan = {
    plan_id: 'plan_test_114',
    version: 1,
    objective: 'Resolve database latency spike',
    target_entity: 'database_cluster',
    status: 'READY',
    recommended_stance: 'OBSERVE',
    gaps: [
      {
        gap_id: 'gap_1',
        question: 'Is connection pool exhausted?',
        missing_information: 'Connection pool metrics missing',
        affected_entity: 'database_cluster',
        affected_state: 'CONNECTION_POOL',
        severity: 'HIGH',
        freshness_requirement_seconds: 60.0,
        is_resolved_by_existing_data: false,
      },
    ],
    sensitivities: {
      gap_1: {
        gap_id: 'gap_1',
        is_decision_sensitive: true,
        sensitivity_score: 0.85,
      },
    },
    candidates: [
      {
        candidate_id: 'cand_1',
        gap_id: 'gap_1',
        name: 'Query active connections',
        target_source: 'db_diagnostics',
        method: 'ACTIVE',
        cost: { compute_units: 0.05, network_latency_ms: 100 },
        risk: { security_risk_level: 'LOW' },
        value_estimate: {
          tier: 'HIGH',
          net_value_score: 0.72,
          marginal_value: 0.80,
          is_redundant: false,
        },
        expected_latency_seconds: 0.1,
      },
    ],
    outcomes: [],
    verifications: {},
    budget: { allocated_units: 10.0, spent_units: 0.0 },
    uncertainty_before: { overall_confidence: 0.45 },
    uncertainty_after: { overall_confidence: 0.45 },
  };

  await t.test('initializes with default options', () => {
    const view = new ActiveObservationView({ container: mockContainer });
    assert.strictEqual(view.activeTab, 'matrix');
    assert.strictEqual(view.plan, null);
  });

  await t.test('renders loading indicator when loading', () => {
    const view = new ActiveObservationView({ container: mockContainer });
    view.loading = true;
    view.render();
    assert.match(mockContainer.innerHTML, /Evaluating epistemic uncertainty/);
  });

  await t.test('renders plan details and stance badges', () => {
    const view = new ActiveObservationView({ container: mockContainer });
    view.plan = samplePlan;
    view.planId = samplePlan.plan_id;
    view.loading = false;
    view.render();

    assert.match(mockContainer.innerHTML, /Active Observation & Value-of-Information/);
    assert.match(mockContainer.innerHTML, /database_cluster/);
    assert.match(mockContainer.innerHTML, /OBSERVE/);
    assert.match(mockContainer.innerHTML, /15D Uncertainty Matrix/);
  });

  await t.test('switches tabs and renders candidate options', () => {
    const view = new ActiveObservationView({ container: mockContainer });
    view.plan = samplePlan;
    view.switchTab('options');
    assert.strictEqual(view.activeTab, 'options');
    assert.match(mockContainer.innerHTML, /Query active connections/);
    assert.match(mockContainer.innerHTML, /VoI: HIGH/);
  });

  await t.test('switches tabs and renders information gaps', () => {
    const view = new ActiveObservationView({ container: mockContainer });
    view.plan = samplePlan;
    view.switchTab('gaps');
    assert.strictEqual(view.activeTab, 'gaps');
    assert.match(mockContainer.innerHTML, /Is connection pool exhausted\?/);
    assert.match(mockContainer.innerHTML, /DECISION SENSITIVE/);
  });
});
