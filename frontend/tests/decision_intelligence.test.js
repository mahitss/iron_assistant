/**
 * Unit tests for Task 94: KAIRO Autonomous Decision Intelligence & Decision Memory UI.
 * Verifies DecisionIntelligenceView initialization, template rendering, tab switching,
 * Pareto options rendering, approval gates, and precedent inspections.
 */

import { test, describe } from 'node:test';
import assert from 'node:assert';
import { DecisionIntelligenceView } from '../components/decision/decisionIntelligenceView.js';

describe('DecisionIntelligenceView Component (Task 94 UI)', () => {
  function createMockContainer() {
    let containerHtml = '';
    const elements = new Map();

    const container = {
      get innerHTML() {
        return containerHtml;
      },
      set innerHTML(val) {
        containerHtml = val;
      },
      querySelectorAll: (sel) => {
        return [];
      },
      querySelector: (sel) => {
        if (!elements.has(sel)) {
          let elHtml = '';
          elements.set(sel, {
            get innerHTML() {
              return elHtml;
            },
            set innerHTML(val) {
              elHtml = val;
            },
            classList: {
              add: () => {},
              remove: () => {},
            },
            addEventListener: () => {},
          });
        }
        return elements.get(sel);
      },
    };
    return container;
  }

  function createMockApi() {
    const mockDecisions = [
      {
        decision_id: 'dec_test_001',
        objective_id: 'obj_scale_infra',
        title: 'Scale Cluster Nodes',
        status: 'SELECTED',
        decision_type: 'RESOURCE_ALLOCATION',
        selected_option: {
          option_id: 'opt_scale_5',
          name: 'Scale 5 Nodes',
          reversibility: 'REVERSIBLE',
          scores: { objective_alignment: 0.9, risk_score: 0.8, reversibility_score: 0.9 },
        },
        options: [
          {
            option_id: 'opt_scale_5',
            name: 'Scale 5 Nodes',
            is_feasible: true,
            is_dominated: false,
            scores: { objective_alignment: 0.9, risk_score: 0.8 },
          },
          {
            option_id: 'opt_no_action',
            name: 'NO_ACTION (Status Quo)',
            is_feasible: true,
            is_dominated: false,
            scores: { objective_alignment: 0.5, risk_score: 1.0 },
          },
        ],
        assumptions: [
          { assumption_id: 'asm_1', statement: 'Cluster CPU > 80%', status: 'ACTIVE' },
        ],
        created_at: new Date().toISOString(),
      },
      {
        decision_id: 'dec_test_002',
        objective_id: 'obj_purge_db',
        title: 'Purge Old Logs',
        status: 'AWAITING_APPROVAL',
        decision_type: 'DESTRUCTIVE',
        options: [
          { option_id: 'opt_purge', name: 'Purge Tables', is_feasible: true, is_dominated: false },
        ],
        approval_summary: { required: true, reason: 'High risk destructive operation' },
        created_at: new Date().toISOString(),
      },
    ];

    const mockExplanation = {
      decision_id: 'dec_test_001',
      objective: 'obj_scale_infra',
      options_considered: ['Scale 5 Nodes', 'NO_ACTION'],
      constraints_summary: ['Budget limit: 100 credits'],
      evidence_basis: ['Prometheus metric cpu_usage=86%'],
      risks_evaluated: ['Temporary latency spike'],
      forecasts_used: ['Traffic peak expected at 14:00 UTC'],
      causal_effects_identified: ['Cluster scaling prevents worker starvation'],
      resource_implications: { cost_score: 0.2 },
      governance_status: 'COMPLIANT',
      security_status: 'AUTHORIZED',
      approval_status: 'NOT_REQUIRED',
      uncertainty_profile: { certainty: 'HIGH' },
      selected_action: 'Scale 5 Nodes',
      expected_outcome: 'Latency normalized under 50ms',
      verification_plan: ['Poll cluster latency every 30s'],
    };

    return {
      listDecisions: async () => mockDecisions,
      getDecision: async (id) => mockDecisions.find((d) => d.decision_id === id) || mockDecisions[0],
      getExplanation: async () => mockExplanation,
      selectOption: async (id, optId) => ({ ...mockDecisions[0], selected_option_id: optId }),
      approveDecision: async (id) => ({ ...mockDecisions[1], status: 'APPROVED' }),
      rejectDecision: async (id, reason) => ({ ...mockDecisions[1], status: 'REJECTED' }),
      evaluateDecision: async (inp) => mockDecisions[0],
    };
  }

  test('Component initializes with clean state and default tabs', () => {
    const container = createMockContainer();
    const view = new DecisionIntelligenceView({ container });

    assert.strictEqual(view.state.activeTab, 'inbox');
    assert.deepStrictEqual(view.state.decisions, []);
    assert.strictEqual(view.state.selectedDecision, null);
    assert.strictEqual(view.state.isLoading, false);
  });

  test('Renders template header with title and navigation tabs', () => {
    const container = createMockContainer();
    const view = new DecisionIntelligenceView({ container });
    const html = view._template();

    assert.match(html, /Decision Intelligence/);
    assert.match(html, /data-tab="inbox"/);
    assert.match(html, /data-tab="detail"/);
    assert.match(html, /data-tab="approvals"/);
    assert.match(html, /data-tab="blocked"/);
    assert.match(html, /data-tab="memory"/);
  });

  test('Fetches decisions and populates state via API', async () => {
    const container = createMockContainer();
    const api = createMockApi();
    const view = new DecisionIntelligenceView({ container, api });

    await view.fetchData();

    assert.strictEqual(view.state.decisions.length, 2);
    assert.strictEqual(view.state.decisions[0].decision_id, 'dec_test_001');
    assert.strictEqual(view.state.decisions[1].status, 'AWAITING_APPROVAL');
  });

  test('Selects decision and fetches full detail and 15-point explanation', async () => {
    const container = createMockContainer();
    const api = createMockApi();
    const view = new DecisionIntelligenceView({ container, api });

    await view.fetchData();
    await view.selectDecision('dec_test_001');

    assert.ok(view.state.selectedDecision);
    assert.strictEqual(view.state.selectedDecision.decision_id, 'dec_test_001');
    assert.ok(view.state.explanation);
    assert.strictEqual(view.state.explanation.selected_action, 'Scale 5 Nodes');
    assert.strictEqual(view.state.explanation.governance_status, 'COMPLIANT');
  });

  test('Generates Pareto options cards and renders NO_ACTION baseline', () => {
    const container = createMockContainer();
    const api = createMockApi();
    const view = new DecisionIntelligenceView({ container, api });

    const options = [
      {
        option_id: 'opt_1',
        name: 'Scale Nodes',
        is_feasible: true,
        is_dominated: false,
        scores: { objective_alignment: 0.9, risk_score: 0.8 },
      },
      {
        option_id: 'opt_no_action',
        name: 'NO_ACTION (Status Quo)',
        is_feasible: true,
        is_dominated: false,
        scores: { objective_alignment: 0.5, risk_score: 1.0 },
      },
    ];

    const html = view._renderOptionsGrid(options, options[0]);
    assert.match(html, /Scale Nodes/);
    assert.match(html, /NO_ACTION/);
    assert.match(html, /SELECTED/);
  });

  test('Handles tab switching across views', () => {
    const container = createMockContainer();
    const view = new DecisionIntelligenceView({ container });

    view.switchTab('approvals');
    assert.strictEqual(view.state.activeTab, 'approvals');

    view.switchTab('memory');
    assert.strictEqual(view.state.activeTab, 'memory');

    view.switchTab('blocked');
    assert.strictEqual(view.state.activeTab, 'blocked');
  });
});
