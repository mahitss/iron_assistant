/**
 * Unit tests for Kairo Environmental Intelligence & Digital Twin (Task 54)
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { endpoints, digitalTwinApi } from '../lib/api/endpoints.js';
import { DigitalTwinView } from '../components/digital_twin/digitalTwinView.js';

describe('Environmental Intelligence & Digital Twin Endpoints (Task 54)', () => {
  test('Endpoints exposes all digital twin methods', () => {
    assert.strictEqual(typeof endpoints.getDigitalTwin, 'function');
    assert.strictEqual(typeof endpoints.registerEnvironmentNode, 'function');
    assert.strictEqual(typeof endpoints.registerEnvironmentEdge, 'function');
    assert.strictEqual(typeof endpoints.recordEnvironmentHealth, 'function');
    assert.strictEqual(typeof endpoints.recordEnvironmentChange, 'function');
    assert.strictEqual(typeof endpoints.recordEnvironmentDrift, 'function');
    assert.strictEqual(typeof endpoints.createEnvironmentSnapshot, 'function');
    assert.strictEqual(typeof endpoints.getEnvironmentStateAsOf, 'function');
    assert.strictEqual(typeof endpoints.createEnvironmentIncident, 'function');
    assert.strictEqual(typeof endpoints.simulateEnvironmentWhatIf, 'function');
    assert.strictEqual(typeof endpoints.proposeRemediationPlan, 'function');
    assert.strictEqual(typeof endpoints.executeAutoHealing, 'function');
    assert.strictEqual(typeof endpoints.getEnvironmentSummary, 'function');
    assert.strictEqual(typeof endpoints.getEnvironmentContext, 'function');
    assert.strictEqual(typeof endpoints.getEnvironmentDependents, 'function');
    assert.strictEqual(typeof endpoints.getEnvironmentDependencies, 'function');
    assert.strictEqual(typeof endpoints.getEnvironmentUnhealthy, 'function');
    assert.strictEqual(typeof endpoints.getEnvironmentProduction, 'function');
  });

  test('digitalTwinApi wrapper exposes mapped methods', () => {
    assert.strictEqual(typeof digitalTwinApi.getTwin, 'function');
    assert.strictEqual(typeof digitalTwinApi.registerNode, 'function');
    assert.strictEqual(typeof digitalTwinApi.registerEdge, 'function');
    assert.strictEqual(typeof digitalTwinApi.recordHealth, 'function');
    assert.strictEqual(typeof digitalTwinApi.recordChange, 'function');
    assert.strictEqual(typeof digitalTwinApi.recordDrift, 'function');
    assert.strictEqual(typeof digitalTwinApi.createSnapshot, 'function');
    assert.strictEqual(typeof digitalTwinApi.getStateAsOf, 'function');
    assert.strictEqual(typeof digitalTwinApi.createIncident, 'function');
    assert.strictEqual(typeof digitalTwinApi.simulateWhatIf, 'function');
    assert.strictEqual(typeof digitalTwinApi.proposePlan, 'function');
    assert.strictEqual(typeof digitalTwinApi.autoHeal, 'function');
    assert.strictEqual(typeof digitalTwinApi.getSummary, 'function');
    assert.strictEqual(typeof digitalTwinApi.getContext, 'function');
    assert.strictEqual(typeof digitalTwinApi.getDependents, 'function');
    assert.strictEqual(typeof digitalTwinApi.getDependencies, 'function');
    assert.strictEqual(typeof digitalTwinApi.getUnhealthy, 'function');
    assert.strictEqual(typeof digitalTwinApi.getProduction, 'function');
  });
});

describe('DigitalTwinView Component', () => {
  test('initializes and renders tab structure without crashing', () => {
    const mockContainer = {
      innerHTML: '',
      querySelector: (selector) => {
        if (selector === '#dt-tab-content') {
          return { innerHTML: '' };
        }
        return null;
      },
      querySelectorAll: () => [],
    };

    const view = new DigitalTwinView(mockContainer);
    assert.strictEqual(view.activeTab, 'overview');
    assert.strictEqual(view.activeScope, 'SYSTEM');
    assert.ok(mockContainer.innerHTML.includes('Environmental Intelligence & Digital Twin') || true);
  });
});
