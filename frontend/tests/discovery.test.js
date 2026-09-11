/**
 * Unit tests for Kairo Autonomous Hypothesis, Experimentation & Scientific Discovery Engine (Task 72).
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { endpoints, discoveryApi, discoveryCenterApi } from '../lib/api/endpoints.js';
import { DiscoveryCenterView } from '../components/discovery/discoveryCenterView.js';

describe('Autonomous Hypothesis & Discovery Endpoints (Task 72)', () => {
  test('Endpoints exposes all discovery and experiment methods', () => {
    assert.strictEqual(typeof endpoints.startDiscovery, 'function');
    assert.strictEqual(typeof endpoints.getDiscovery, 'function');
    assert.strictEqual(typeof endpoints.listDiscoveries, 'function');
    assert.strictEqual(typeof endpoints.addDiscoveryHypotheses, 'function');
    assert.strictEqual(typeof endpoints.getDiscoveryHypotheses, 'function');
    assert.strictEqual(typeof endpoints.concludeDiscovery, 'function');
    assert.strictEqual(typeof endpoints.getDiscoveryAudit, 'function');
    assert.strictEqual(typeof endpoints.designExperiment, 'function');
    assert.strictEqual(typeof endpoints.getExperiment, 'function');
    assert.strictEqual(typeof endpoints.recordExperimentPrediction, 'function');
    assert.strictEqual(typeof endpoints.approveExperiment, 'function');
    assert.strictEqual(typeof endpoints.startExperiment, 'function');
    assert.strictEqual(typeof endpoints.recordExperimentObservation, 'function');
    assert.strictEqual(typeof endpoints.analyzeExperiment, 'function');
    assert.strictEqual(typeof endpoints.rollbackExperiment, 'function');
    assert.strictEqual(typeof endpoints.cleanupExperiment, 'function');
    assert.strictEqual(typeof endpoints.replicateExperiment, 'function');
    assert.strictEqual(typeof endpoints.getExperimentExplanation, 'function');
    assert.strictEqual(typeof endpoints.getExperimentQueue, 'function');
    assert.strictEqual(typeof endpoints.getDiscoveryHealth, 'function');
  });

  test('discoveryApi and discoveryCenterApi wrappers expose mapped methods', () => {
    assert.strictEqual(typeof discoveryApi.start, 'function');
    assert.strictEqual(typeof discoveryApi.get, 'function');
    assert.strictEqual(typeof discoveryApi.list, 'function');
    assert.strictEqual(typeof discoveryApi.addHypotheses, 'function');
    assert.strictEqual(typeof discoveryApi.getHypotheses, 'function');
    assert.strictEqual(typeof discoveryApi.conclude, 'function');
    assert.strictEqual(typeof discoveryApi.getAudit, 'function');
    assert.strictEqual(typeof discoveryApi.designExperiment, 'function');
    assert.strictEqual(typeof discoveryApi.getExperiment, 'function');
    assert.strictEqual(typeof discoveryApi.recordPrediction, 'function');
    assert.strictEqual(typeof discoveryApi.approveExperiment, 'function');
    assert.strictEqual(typeof discoveryApi.startExperiment, 'function');
    assert.strictEqual(typeof discoveryApi.recordObservation, 'function');
    assert.strictEqual(typeof discoveryApi.analyzeExperiment, 'function');
    assert.strictEqual(typeof discoveryApi.rollbackExperiment, 'function');
    assert.strictEqual(typeof discoveryApi.cleanupExperiment, 'function');
    assert.strictEqual(typeof discoveryApi.replicate, 'function');
    assert.strictEqual(typeof discoveryApi.getExplanation, 'function');
    assert.strictEqual(typeof discoveryApi.getQueue, 'function');
    assert.strictEqual(typeof discoveryApi.getHealth, 'function');

    assert.strictEqual(discoveryCenterApi, discoveryApi);
  });
});

describe('DiscoveryCenterView Component (Task 72)', () => {
  test('initializes with default questions tab and empty collections', () => {
    const view = new DiscoveryCenterView({ tenantId: 'tenant_sci', workspaceId: 'ws_sci' });
    assert.strictEqual(view.activeTab, 'questions');
    assert.strictEqual(view.tenantId, 'tenant_sci');
    assert.strictEqual(view.workspaceId, 'ws_sci');
    assert.strictEqual(Array.isArray(view.discoveries), true);
    assert.strictEqual(view.currentDiscovery, null);
    assert.strictEqual(view.currentExperiment, null);
  });

  test('tab switching updates activeTab state', () => {
    const view = new DiscoveryCenterView();
    view.setTab('hypotheses');
    assert.strictEqual(view.activeTab, 'hypotheses');
    view.setTab('queue');
    assert.strictEqual(view.activeTab, 'queue');
    view.setTab('results');
    assert.strictEqual(view.activeTab, 'results');
    view.setTab('detail');
    assert.strictEqual(view.activeTab, 'detail');
  });

  test('risk color mapping properly distinguishes safety tiers', () => {
    const view = new DiscoveryCenterView();
    assert.strictEqual(view.getRiskColor('SAFE'), '#34d399');
    assert.strictEqual(view.getRiskColor('LOW_RISK'), '#38bdf8');
    assert.strictEqual(view.getRiskColor('MEDIUM_RISK'), '#eab308');
    assert.strictEqual(view.getRiskColor('HIGH_RISK'), '#f97316');
    assert.strictEqual(view.getRiskColor('CRITICAL_RISK'), '#ef4444');
  });
});
