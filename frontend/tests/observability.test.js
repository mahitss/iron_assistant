/**
 * Unit tests for Kairo Unified Observability & System Intelligence (Task 38)
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { endpoints } from '../lib/api/endpoints.js';
import { ObservabilityView } from '../components/observability/observabilityView.js';

describe('Observability & System Intelligence Endpoints (Task 38)', () => {
  test('Endpoints exposes all observability methods', () => {
    assert.strictEqual(typeof endpoints.getObservabilityHealth, 'function');
    assert.strictEqual(typeof endpoints.getObservabilityDashboard, 'function');
    assert.strictEqual(typeof endpoints.getTrace, 'function');
    assert.strictEqual(typeof endpoints.getTaskTrace, 'function');
    assert.strictEqual(typeof endpoints.listIncidents, 'function');
    assert.strictEqual(typeof endpoints.getIncident, 'function');
    assert.strictEqual(typeof endpoints.acknowledgeIncident, 'function');
    assert.strictEqual(typeof endpoints.resolveIncident, 'function');
    assert.strictEqual(typeof endpoints.getDependencies, 'function');
    assert.strictEqual(typeof endpoints.runDiagnostics, 'function');
    assert.strictEqual(typeof endpoints.runRootCauseAnalysis, 'function');
  });

  test('ObservabilityView initializes with tabs and KPI containers', () => {
    const mockContainer = {
      innerHTML: '',
      querySelector: () => null,
      querySelectorAll: () => [],
    };

    const view = new ObservabilityView(mockContainer);
    assert.strictEqual(view.activeTab, 'traces');
    assert.strictEqual(view.isLoading, false);
  });
});
