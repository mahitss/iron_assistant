/**
 * Unit tests for Kairo Autonomous Causal Discovery & World-Model Learning Engine (Task 73)
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { endpoints, causalApi, causalIntelligenceCenterApi } from '../lib/api/endpoints.js';
import { CausalIntelligenceCenterView } from '../components/causal/causalIntelligenceCenterView.js';

describe('Autonomous Causal Discovery & World-Model Learning Endpoints (Task 73)', () => {
  test('Endpoints object defines all required Task 73 causal discovery methods', () => {
    assert.strictEqual(typeof endpoints.getCausalGraph, 'function');
    assert.strictEqual(typeof endpoints.getCausalRelationships, 'function');
    assert.strictEqual(typeof endpoints.getCausalRelationship, 'function');
    assert.strictEqual(typeof endpoints.proposeCausalCandidate, 'function');
    assert.strictEqual(typeof endpoints.registerCausalHypothesis, 'function');
    assert.strictEqual(typeof endpoints.getCausalHypotheses, 'function');
    assert.strictEqual(typeof endpoints.getCausalEvidence, 'function');
    assert.strictEqual(typeof endpoints.getCausalExplanation, 'function');
    assert.strictEqual(typeof endpoints.getCausalTrace, 'function');
    assert.strictEqual(typeof endpoints.getCausalProvenance, 'function');
    assert.strictEqual(typeof endpoints.invalidateCausalRelationship, 'function');
    assert.strictEqual(typeof endpoints.verifyCausalRelationship, 'function');
    assert.strictEqual(typeof endpoints.getCausalConflicts, 'function');
    assert.strictEqual(typeof endpoints.getCausalDrift, 'function');
    assert.strictEqual(typeof endpoints.getCausalHealth, 'function');
    assert.strictEqual(typeof endpoints.queryCausalEngine, 'function');
    assert.strictEqual(typeof endpoints.recordCausalIntervention, 'function');
    assert.strictEqual(typeof endpoints.listCausalInterventions, 'function');
    assert.strictEqual(typeof endpoints.evaluateCausalExperiment, 'function');
    assert.strictEqual(typeof endpoints.getDiscriminativeExperiments, 'function');
  });

  test('causalApi and causalIntelligenceCenterApi wrappers expose all discovery methods', () => {
    assert.strictEqual(typeof causalIntelligenceCenterApi.getRelationships, 'function');
    assert.strictEqual(typeof causalIntelligenceCenterApi.getRelationship, 'function');
    assert.strictEqual(typeof causalIntelligenceCenterApi.proposeCandidate, 'function');
    assert.strictEqual(typeof causalIntelligenceCenterApi.registerHypothesis, 'function');
    assert.strictEqual(typeof causalIntelligenceCenterApi.getHypotheses, 'function');
    assert.strictEqual(typeof causalIntelligenceCenterApi.getEvidence, 'function');
    assert.strictEqual(typeof causalIntelligenceCenterApi.getTrace, 'function');
    assert.strictEqual(typeof causalIntelligenceCenterApi.getProvenance, 'function');
    assert.strictEqual(typeof causalIntelligenceCenterApi.invalidate, 'function');
    assert.strictEqual(typeof causalIntelligenceCenterApi.verify, 'function');
    assert.strictEqual(typeof causalIntelligenceCenterApi.getConflicts, 'function');
    assert.strictEqual(typeof causalIntelligenceCenterApi.getDrift, 'function');
    assert.strictEqual(typeof causalIntelligenceCenterApi.getHealth, 'function');
    assert.strictEqual(typeof causalIntelligenceCenterApi.query, 'function');
    assert.strictEqual(typeof causalIntelligenceCenterApi.recordIntervention, 'function');
    assert.strictEqual(typeof causalIntelligenceCenterApi.listInterventions, 'function');
    assert.strictEqual(typeof causalIntelligenceCenterApi.evaluateExperiment, 'function');
    assert.strictEqual(typeof causalIntelligenceCenterApi.getDiscriminativeExperiments, 'function');
  });
});

describe('CausalIntelligenceCenterView Component (Task 73)', () => {
  test('initializes with default tab and empty collections', () => {
    const mockContainer = {
      innerHTML: '',
      querySelector: () => null,
      querySelectorAll: () => [],
    };

    const view = new CausalIntelligenceCenterView({ container: mockContainer });
    assert.strictEqual(view.state.activeTab, 'graph');
    assert.strictEqual(view.state.queryQuestion, 'WHAT_CAUSED_X');
    assert.strictEqual(view.state.queryEntity, 'APIGateway');
    assert.deepStrictEqual(view.state.relationships, []);
    assert.deepStrictEqual(view.state.conflicts, []);
    assert.deepStrictEqual(view.state.driftReports, []);
  });

  test('setTab updates activeTab state properly', () => {
    const mockContainer = {
      innerHTML: '',
      querySelector: () => ({ innerHTML: '' }),
      querySelectorAll: () => [],
    };

    const view = new CausalIntelligenceCenterView({ container: mockContainer });
    view.setTab('hypotheses');
    assert.strictEqual(view.state.activeTab, 'hypotheses');

    view.setTab('conflicts');
    assert.strictEqual(view.state.activeTab, 'conflicts');

    view.setTab('drift');
    assert.strictEqual(view.state.activeTab, 'drift');

    view.setTab('world_model');
    assert.strictEqual(view.state.activeTab, 'world_model');

    view.setTab('explorer');
    assert.strictEqual(view.state.activeTab, 'explorer');
  });

  test('renders template structure and tab contents without errors', () => {
    const mockContainer = {
      innerHTML: '',
      querySelector: () => null,
      querySelectorAll: () => [],
    };

    const view = new CausalIntelligenceCenterView({ container: mockContainer });
    view.state.relationships = [
      {
        causal_relation_id: 'rel_test_1',
        cause_entity: 'ThreadPool',
        cause_variable: 'saturation',
        effect_entity: 'Gateway',
        effect_variable: 'latency',
        relationship_type: 'CAUSAL',
        direction: 'POSITIVE',
        mechanism: 'Queuing blockage',
        status: 'VERIFIED',
        confidence: 0.95,
        strength: 'STRONG',
        environment: 'STAGING',
        evidence_refs: ['ev1'],
        experiment_refs: ['exp1'],
        falsification_criteria: ['Latency decreases when thread pool is saturated'],
      },
    ];

    const html = view._template();
    assert.ok(html.includes('Causal Intelligence Center'));
    assert.ok(html.includes('Causal Graph'));
    assert.ok(html.includes('Hypotheses'));
    assert.ok(html.includes('Conflicts & Dissent'));
    assert.ok(html.includes('Drift & Quality'));
    assert.ok(html.includes('World Model Active'));
    assert.ok(html.includes('Experiment Explorer'));

    // Test tab views
    view.state.activeTab = 'graph';
    const graphHtml = view._renderTabContent();
    assert.ok(graphHtml.includes('ThreadPool.saturation'));
    assert.ok(graphHtml.includes('Gateway.latency'));

    view.state.activeTab = 'conflicts';
    view.state.conflicts = [
      {
        conflict_id: 'conf_1',
        effect_entity: 'Gateway',
        effect_variable: 'latency',
        dissenting_agents: ['AgentA', 'AgentB'],
        competing_relationship_ids: ['rel_a', 'rel_b'],
      },
    ];
    const confHtml = view._renderTabContent();
    assert.ok(confHtml.includes('ACTIVE DISSENT'));
    assert.ok(confHtml.includes('AgentA, AgentB'));

    view.state.activeTab = 'drift';
    view.state.driftReports = [
      {
        report_id: 'drift_1',
        drift_type: 'CAUSAL_DRIFT',
        relation_id: 'rel_test_1',
        environment: 'PRODUCTION',
        prediction_error: 0.35,
        recommended_action: 'Recalibrate model',
        timestamp: new Date().toISOString(),
      },
    ];
    const driftHtml = view._renderTabContent();
    assert.ok(driftHtml.includes('CAUSAL_DRIFT'));
    assert.ok(driftHtml.includes('35.0%'));

    view.state.activeTab = 'explorer';
    view.state.discriminativeExperiments = [
      {
        objective: 'Discriminate H1 vs H2',
        independent_variable: 'Config.timeout',
        control_variables: ['Traffic.qps'],
        dependent_variable: 'Gateway.latency',
        risk_level: 'LOW_RISK',
        estimated_cost: 2.0,
        information_value: 0.9,
        falsification_criteria: {
          falsifies_hyp_a: 'No change on modulation',
          falsifies_hyp_b: 'Change persists despite controls',
        },
      },
    ];
    const expHtml = view._renderTabContent();
    assert.ok(expHtml.includes('Discriminate H1 vs H2'));
    assert.ok(expHtml.includes('Config.timeout'));
  });
});
