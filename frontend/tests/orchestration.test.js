/**
 * Unit tests for Kairo Resource & Capability Orchestration Engine (Task 59).
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { endpoints, orchestrationApi } from '../lib/api/endpoints.js';
import { OrchestrationView } from '../components/orchestration/orchestrationView.js';

describe('Resource & Capability Orchestration Endpoints (Task 59)', () => {
  test('Endpoints exposes all orchestration methods', () => {
    assert.strictEqual(typeof endpoints.analyzeOrchestration, 'function');
    assert.strictEqual(typeof endpoints.createOrchestration, 'function');
    assert.strictEqual(typeof endpoints.listCapabilities, 'function');
    assert.strictEqual(typeof endpoints.listResources, 'function');
    assert.strictEqual(typeof endpoints.reserveResource, 'function');
    assert.strictEqual(typeof endpoints.releaseReservation, 'function');
    assert.strictEqual(typeof endpoints.listOrchestrations, 'function');
    assert.strictEqual(typeof endpoints.getOrchestration, 'function');
    assert.strictEqual(typeof endpoints.getOrchestrationAssignments, 'function');
    assert.strictEqual(typeof endpoints.getOrchestrationTopology, 'function');
    assert.strictEqual(typeof endpoints.revalidateOrchestration, 'function');
    assert.strictEqual(typeof endpoints.failoverOrchestration, 'function');
    assert.strictEqual(typeof endpoints.getOrchestrationHealth, 'function');
    assert.strictEqual(typeof endpoints.explainOrchestrationTask, 'function');
    assert.strictEqual(typeof endpoints.getOrchestrationAudit, 'function');
  });

  test('orchestrationApi wrapper exposes mapped methods', () => {
    assert.strictEqual(typeof orchestrationApi.analyze, 'function');
    assert.strictEqual(typeof orchestrationApi.create, 'function');
    assert.strictEqual(typeof orchestrationApi.listCapabilities, 'function');
    assert.strictEqual(typeof orchestrationApi.listResources, 'function');
    assert.strictEqual(typeof orchestrationApi.reserveResource, 'function');
    assert.strictEqual(typeof orchestrationApi.releaseReservation, 'function');
    assert.strictEqual(typeof orchestrationApi.list, 'function');
    assert.strictEqual(typeof orchestrationApi.get, 'function');
    assert.strictEqual(typeof orchestrationApi.getAssignments, 'function');
    assert.strictEqual(typeof orchestrationApi.getTopology, 'function');
    assert.strictEqual(typeof orchestrationApi.revalidate, 'function');
    assert.strictEqual(typeof orchestrationApi.failover, 'function');
    assert.strictEqual(typeof orchestrationApi.getHealth, 'function');
    assert.strictEqual(typeof orchestrationApi.explain, 'function');
    assert.strictEqual(typeof orchestrationApi.getAudit, 'function');
  });
});

describe('OrchestrationView Component', () => {
  test('initializes with default tab and empty states', () => {
    const view = new OrchestrationView('mock-container');
    assert.strictEqual(view.activeTab, 'plans');
    assert.strictEqual(view.plans.length, 0);
    assert.strictEqual(view.capabilities.length, 0);
    assert.strictEqual(view.resources.length, 0);
  });

  test('switches tabs correctly', () => {
    const view = new OrchestrationView('mock-container');
    view.setTab('capabilities');
    assert.strictEqual(view.activeTab, 'capabilities');
    view.setTab('resources');
    assert.strictEqual(view.activeTab, 'resources');
    view.setTab('failover');
    assert.strictEqual(view.activeTab, 'failover');
  });

  test('selects orchestration plan correctly', () => {
    const view = new OrchestrationView('mock-container');
    const mockPlan = {
      orchestration_id: 'orch_test123',
      name: 'Test Plan',
      status: 'READY',
      version: 1,
      assignments: [],
      execution_waves: [],
    };
    view.selectPlan(mockPlan);
    assert.strictEqual(view.selectedPlan.orchestration_id, 'orch_test123');
  });
});
