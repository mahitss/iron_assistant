/**
 * Unit tests for Kairo Unified Observability & System Intelligence (Task 38)
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { endpoints, observabilityApi } from '../lib/api/endpoints.js';
import { ObservabilityView } from '../components/observability/observabilityView.js';
import { ResourceCenterView } from '../components/orchestration/resourceCenterView.js';

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

describe('Native Event, Telemetry & Observability Fabric (Task 86)', () => {
  test('observabilityApi and endpoints expose all Task 86 methods', () => {
    assert.strictEqual(typeof observabilityApi.getComponentHealth, 'function');
    assert.strictEqual(typeof observabilityApi.getSubsystems, 'function');
    assert.strictEqual(typeof observabilityApi.getEvents, 'function');
    assert.strictEqual(typeof observabilityApi.getTraces, 'function');
    assert.strictEqual(typeof observabilityApi.getExecutionDetails, 'function');
    assert.strictEqual(typeof observabilityApi.getTimeline, 'function');
    assert.strictEqual(typeof observabilityApi.replayExecution, 'function');

    assert.strictEqual(typeof endpoints.getComponentHealth, 'function');
    assert.strictEqual(typeof endpoints.getObservabilitySubsystems, 'function');
    assert.strictEqual(typeof endpoints.getObservabilityEvents, 'function');
    assert.strictEqual(typeof endpoints.getObservabilityTraces, 'function');
    assert.strictEqual(typeof endpoints.getExecutionDetails, 'function');
    assert.strictEqual(typeof endpoints.getExecutionTimeline, 'function');
    assert.strictEqual(typeof endpoints.replayExecution, 'function');
  });

  test('ResourceCenterView switches to subtab 11 (Observability Fabric) and renders', () => {
    const mockContainer = {
      innerHTML: '',
      querySelector: () => null,
      querySelectorAll: () => [],
    };

    const view = new ResourceCenterView(mockContainer);
    view.setSubTab('observability');
    assert.strictEqual(view.activeSubTab, 'observability');
    assert.ok(mockContainer.innerHTML.includes('11. Observability Fabric (Task 86)'));
    assert.ok(mockContainer.innerHTML.includes('Forensic Execution Timeline Reconstructor'));
    assert.ok(mockContainer.innerHTML.includes('Recent Telemetry Events (Ring Buffer)'));
    assert.ok(mockContainer.innerHTML.includes('Zero CoT Leakage'));
  });
});

