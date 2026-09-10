/**
 * Unit tests for Kairo Real-Time Situational Awareness & Event Correlation Engine (Task 60).
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { endpoints, situationsApi } from '../lib/api/endpoints.js';
import { SituationsView } from '../components/situations/situationsView.js';

describe('Situational Awareness & Event Correlation Endpoints (Task 60)', () => {
  test('Endpoints exposes all situational awareness methods', () => {
    assert.strictEqual(typeof endpoints.ingestSituationEvent, 'function');
    assert.strictEqual(typeof endpoints.listSituations, 'function');
    assert.strictEqual(typeof endpoints.getSituation, 'function');
    assert.strictEqual(typeof endpoints.getSituationTimeline, 'function');
    assert.strictEqual(typeof endpoints.getSituationImpact, 'function');
    assert.strictEqual(typeof endpoints.getSituationHypotheses, 'function');
    assert.strictEqual(typeof endpoints.resolveSituation, 'function');
    assert.strictEqual(typeof endpoints.escalateSituation, 'function');
    assert.strictEqual(typeof endpoints.getAttentionFeed, 'function');
    assert.strictEqual(typeof endpoints.listSignalBaselines, 'function');
    assert.strictEqual(typeof endpoints.getSituationAudit, 'function');
  });

  test('situationsApi wrapper exposes mapped methods', () => {
    assert.strictEqual(typeof situationsApi.ingest, 'function');
    assert.strictEqual(typeof situationsApi.list, 'function');
    assert.strictEqual(typeof situationsApi.get, 'function');
    assert.strictEqual(typeof situationsApi.getTimeline, 'function');
    assert.strictEqual(typeof situationsApi.getImpact, 'function');
    assert.strictEqual(typeof situationsApi.getHypotheses, 'function');
    assert.strictEqual(typeof situationsApi.resolve, 'function');
    assert.strictEqual(typeof situationsApi.escalate, 'function');
    assert.strictEqual(typeof situationsApi.getAttentionFeed, 'function');
    assert.strictEqual(typeof situationsApi.getBaselines, 'function');
    assert.strictEqual(typeof situationsApi.getAudit, 'function');
  });
});

describe('SituationsView Component', () => {
  test('initializes with default tab and empty states', () => {
    const view = new SituationsView('mock-container');
    assert.strictEqual(view.activeTab, 'situations');
    assert.strictEqual(view.situations.length, 0);
    assert.strictEqual(view.attentionItems.length, 0);
    assert.strictEqual(view.baselines.length, 0);
    assert.strictEqual(view.selectedSituation, null);
    assert.strictEqual(view.isLoading, false);
  });

  test('switches tabs correctly', () => {
    const view = new SituationsView('mock-container');
    view.setTab('timeline');
    assert.strictEqual(view.activeTab, 'timeline');
    view.setTab('impact');
    assert.strictEqual(view.activeTab, 'impact');
    view.setTab('hypotheses');
    assert.strictEqual(view.activeTab, 'hypotheses');
    view.setTab('baselines');
    assert.strictEqual(view.activeTab, 'baselines');
    view.setTab('attention');
    assert.strictEqual(view.activeTab, 'attention');
    view.setTab('audit');
    assert.strictEqual(view.activeTab, 'audit');
  });

  test('selects situation correctly', () => {
    const view = new SituationsView('mock-container');
    const mockSituation = {
      situation_id: 'sit_test_456',
      title: 'Database connection pool exhaustion',
      status: 'CONFIRMED',
      severity: 'HIGH',
      confidence: 0.92,
      affected_resources: ['db-primary', 'auth-service'],
      timeline: [],
      hypotheses: [],
    };
    view.selectSituation(mockSituation);
    assert.strictEqual(view.selectedSituation.situation_id, 'sit_test_456');
    assert.strictEqual(view.selectedSituation.status, 'CONFIRMED');
    assert.strictEqual(view.selectedSituation.severity, 'HIGH');
  });
});
