/**
 * Frontend Unit & Component Tests for Task 113:
 * Kairo Autonomous Counterfactual, Intervention Analysis, What-If Simulation & Causal Experiment Planning Engine
 */

import test from 'node:test';
import assert from 'node:assert';
import { counterfactualsApi } from '../lib/api/endpoints.js';
import { CounterfactualAnalysisView } from '../components/counterfactual/counterfactualAnalysisView.js';

test('Counterfactuals API Endpoints (Task 113)', async (t) => {
  await t.test('counterfactualsApi exposes all required Task 113 methods', () => {
    assert.strictEqual(typeof counterfactualsApi.create, 'function');
    assert.strictEqual(typeof counterfactualsApi.list, 'function');
    assert.strictEqual(typeof counterfactualsApi.get, 'function');
    assert.strictEqual(typeof counterfactualsApi.getBaseline, 'function');
    assert.strictEqual(typeof counterfactualsApi.getScenarios, 'function');
    assert.strictEqual(typeof counterfactualsApi.getInterventions, 'function');
    assert.strictEqual(typeof counterfactualsApi.getPredictions, 'function');
    assert.strictEqual(typeof counterfactualsApi.getComparisons, 'function');
    assert.strictEqual(typeof counterfactualsApi.getAssumptions, 'function');
    assert.strictEqual(typeof counterfactualsApi.getEvidence, 'function');
    assert.strictEqual(typeof counterfactualsApi.getRisks, 'function');
    assert.strictEqual(typeof counterfactualsApi.getSensitivity, 'function');
    assert.strictEqual(typeof counterfactualsApi.getRobustness, 'function');
    assert.strictEqual(typeof counterfactualsApi.getSnapshot, 'function');
    assert.strictEqual(typeof counterfactualsApi.simulate, 'function');
    assert.strictEqual(typeof counterfactualsApi.verify, 'function');
    assert.strictEqual(typeof counterfactualsApi.feedback, 'function');
  });
});

test('CounterfactualAnalysisView Component (Task 113)', async (t) => {
  const mockContainer = {
    innerHTML: '',
    querySelector: (selector) => {
      return {
        textContent: '',
        value: 'payment_gateway',
        style: {},
        addEventListener: () => {},
        setAttribute: () => {},
        getAttribute: () => 'comparison',
      };
    },
    querySelectorAll: (selector) => {
      return [
        {
          style: {},
          dataset: { tab: 'comparison' },
          addEventListener: () => {},
        },
        {
          style: {},
          dataset: { tab: 'pathways' },
          addEventListener: () => {},
        },
      ];
    },
  };

  const view = new CounterfactualAnalysisView({
    container: mockContainer,
  });

  await t.test('initializes with default comparison tab and null analysis', () => {
    assert.strictEqual(view.activeTab, 'comparison');
    assert.strictEqual(view.analysis, null);
  });

  await t.test('renders HTML skeleton for initial inquiry prompt', () => {
    view.render();
    assert.ok(mockContainer.innerHTML.includes('What-If & Counterfactual Simulation Engine'));
    assert.ok(mockContainer.innerHTML.includes('Run What-If Analysis'));
  });

  await t.test('renders side-by-side comparison when analysis data is present', () => {
    view.analysis = {
      analysis_id: 'cfa_test123',
      target_entity: 'payment_gateway',
      question: 'What if we increase thread pool by 20%?',
      lifecycle_stage: 'READY_FOR_DECISION',
      counterfactual_type: 'RESOURCE',
      causal_model_version: 'v1.0',
      is_stale: false,
      comparison: {
        items: [
          {
            scenario_id: 'scen_no_act',
            scenario_name: 'NO_ACTION (Baseline Reference)',
            is_no_action: true,
            predicted_summary: 'Predicted status: DEGRADED, latency: 250ms',
            risk_level: 'LOW',
            reversibility: 'N/A',
            resource_cost_summary: 'Cost: 0 units',
            confidence: 0.85,
            uncertainty_level: 'LOW',
          },
          {
            scenario_id: 'scen_scale',
            scenario_name: 'Scale Thread Pool +20%',
            is_no_action: false,
            predicted_summary: 'Predicted status: RECOVERED, latency: 45ms',
            risk_level: 'LOW',
            reversibility: 'REVERSIBLE',
            resource_cost_summary: 'Cost: 10 units',
            confidence: 0.82,
            uncertainty_level: 'LOW',
          },
        ],
        tradeoff_summary: 'Baseline degrades under load. Thread pool scale achieves recovery.',
        recommended_option_for_decision: 'Scale Thread Pool +20%',
        no_action_viable: false,
      },
    };

    view.render();
    assert.ok(mockContainer.innerHTML.includes('SIMULATION_ONLY [HYPOTHETICAL]'));
    assert.ok(mockContainer.innerHTML.includes('NO_ACTION (BASELINE)'));
    assert.ok(mockContainer.innerHTML.includes('Scale Thread Pool +20%'));
    assert.ok(mockContainer.innerHTML.includes('Predicted status: RECOVERED'));
  });
});
