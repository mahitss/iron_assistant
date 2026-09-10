/**
 * Unit tests for Kairo Continuous Self-Optimization & Adaptive Control Engine (Task 62).
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { endpoints, optimizationApi } from '../lib/api/endpoints.js';
import { OptimizationView } from '../components/optimization/optimizationView.js';

describe('Continuous Self-Optimization Endpoints (Task 62)', () => {
  test('Endpoints exposes all optimization methods', () => {
    assert.strictEqual(typeof endpoints.evaluateOptimization, 'function');
    assert.strictEqual(typeof endpoints.listOptimizationRecommendations, 'function');
    assert.strictEqual(typeof endpoints.getOptimizationRecommendation, 'function');
    assert.strictEqual(typeof endpoints.approveOptimizationRecommendation, 'function');
    assert.strictEqual(typeof endpoints.listOptimizationExperiments, 'function');
    assert.strictEqual(typeof endpoints.createOptimizationExperiment, 'function');
    assert.strictEqual(typeof endpoints.getOptimizationExperiment, 'function');
    assert.strictEqual(typeof endpoints.approveOptimizationExperiment, 'function');
    assert.strictEqual(typeof endpoints.startOptimizationExperiment, 'function');
    assert.strictEqual(typeof endpoints.deployOptimizationCanary, 'function');
    assert.strictEqual(typeof endpoints.verifyOptimizationCanary, 'function');
    assert.strictEqual(typeof endpoints.rollbackOptimizationCanary, 'function');
    assert.strictEqual(typeof endpoints.listOptimizationChangeSets, 'function');
    assert.strictEqual(typeof endpoints.ingestOptimizationMeasurement, 'function');
    assert.strictEqual(typeof endpoints.getOptimizationMetrics, 'function');
    assert.strictEqual(typeof endpoints.listOptimizationBaselines, 'function');
    assert.strictEqual(typeof endpoints.listOptimizationDrift, 'function');
    assert.strictEqual(typeof endpoints.listOptimizationCalibration, 'function');
    assert.strictEqual(typeof endpoints.getOptimizationAudit, 'function');
    assert.strictEqual(typeof endpoints.toggleOptimizationKillSwitch, 'function');
  });

  test('optimizationApi wrapper exposes mapped methods', () => {
    assert.strictEqual(typeof optimizationApi.evaluate, 'function');
    assert.strictEqual(typeof optimizationApi.listRecommendations, 'function');
    assert.strictEqual(typeof optimizationApi.getRecommendation, 'function');
    assert.strictEqual(typeof optimizationApi.approveRecommendation, 'function');
    assert.strictEqual(typeof optimizationApi.listExperiments, 'function');
    assert.strictEqual(typeof optimizationApi.createExperiment, 'function');
    assert.strictEqual(typeof optimizationApi.getExperiment, 'function');
    assert.strictEqual(typeof optimizationApi.approveExperiment, 'function');
    assert.strictEqual(typeof optimizationApi.startExperiment, 'function');
    assert.strictEqual(typeof optimizationApi.deployCanary, 'function');
    assert.strictEqual(typeof optimizationApi.verifyCanary, 'function');
    assert.strictEqual(typeof optimizationApi.rollbackCanary, 'function');
    assert.strictEqual(typeof optimizationApi.listChangeSets, 'function');
    assert.strictEqual(typeof optimizationApi.ingestMeasurement, 'function');
    assert.strictEqual(typeof optimizationApi.getMetrics, 'function');
    assert.strictEqual(typeof optimizationApi.listBaselines, 'function');
    assert.strictEqual(typeof optimizationApi.listDrift, 'function');
    assert.strictEqual(typeof optimizationApi.listCalibration, 'function');
    assert.strictEqual(typeof optimizationApi.getAudit, 'function');
    assert.strictEqual(typeof optimizationApi.toggleKillSwitch, 'function');
  });
});

describe('OptimizationView Component', () => {
  test('initializes with default performance tab and empty states', () => {
    const view = new OptimizationView('mock-container');
    assert.strictEqual(view.activeTab, 'performance');
    assert.strictEqual(view.metrics.length, 0);
    assert.strictEqual(view.recommendations.length, 0);
    assert.strictEqual(view.experiments.length, 0);
    assert.strictEqual(view.changeSets.length, 0);
    assert.strictEqual(view.driftRecords.length, 0);
    assert.strictEqual(view.calibrationRecords.length, 0);
    assert.strictEqual(view.auditTrail.length, 0);
    assert.strictEqual(view.killSwitchActive, false);
    assert.strictEqual(view.isLoading, false);
  });

  test('switches tabs correctly across all optimization views', () => {
    const view = new OptimizationView('mock-container');
    view.setTab('recommendations');
    assert.strictEqual(view.activeTab, 'recommendations');
    view.setTab('experiments');
    assert.strictEqual(view.activeTab, 'experiments');
    view.setTab('changesets');
    assert.strictEqual(view.activeTab, 'changesets');
    view.setTab('drift');
    assert.strictEqual(view.activeTab, 'drift');
    view.setTab('calibration');
    assert.strictEqual(view.activeTab, 'calibration');
    view.setTab('audit');
    assert.strictEqual(view.activeTab, 'audit');
    view.setTab('performance');
    assert.strictEqual(view.activeTab, 'performance');
  });

  test('selects recommendation and experiment models correctly', () => {
    const view = new OptimizationView('mock-container');
    const mockRec = {
      recommendation_id: 'rec_opt_001',
      action_type: 'ADJUST_BATCHING',
      target_parameter: 'inference.batch_size',
      current_value: 32,
      proposed_value: 48,
      expected_benefit: 0.15,
      expected_cost: 0.005,
      risk_level: 'LOW',
      confidence: 0.92,
      status: 'RECOMMENDED',
      requires_approval: false,
    };
    view.selectRecommendation(mockRec);
    assert.strictEqual(view.selectedRecommendation.recommendation_id, 'rec_opt_001');
    assert.strictEqual(view.selectedRecommendation.target_parameter, 'inference.batch_size');

    const mockExp = {
      experiment_id: 'exp_ab_001',
      name: 'Batch size scaling test',
      hypothesis: 'Increasing batch size from 32 to 48 reduces queue latency without breaching p99',
      status: 'RUNNING',
      variants: [],
      sample_size: 450,
    };
    view.selectExperiment(mockExp);
    assert.strictEqual(view.selectedExperiment.experiment_id, 'exp_ab_001');
    assert.strictEqual(view.selectedExperiment.sample_size, 450);
  });
});
