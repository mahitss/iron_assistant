import test, { describe } from 'node:test';
import assert from 'node:assert';
import { resilienceApi, recoveryApi, resilienceCenterApi } from '../lib/api/endpoints.js';
import { ResilienceCenterView } from '../components/resilience/resilienceCenterView.js';

describe('Autonomous Resilience, Recovery, Containment & Adaptive Defense (Task 76)', () => {
  test('resilienceApi and recoveryApi expose all authoritative endpoints', () => {
    assert.strictEqual(typeof resilienceApi.assess, 'function');
    assert.strictEqual(typeof resilienceApi.getOverview, 'function');
    assert.strictEqual(typeof resilienceApi.getBottlenecks, 'function');
    assert.strictEqual(typeof resilienceApi.getRecoveryHistory, 'function');
    assert.strictEqual(typeof resilienceApi.get, 'function');
    assert.strictEqual(typeof resilienceApi.getGaps, 'function');
    assert.strictEqual(typeof resilienceApi.getRecoveryPaths, 'function');
    assert.strictEqual(typeof resilienceApi.getScenarios, 'function');
    assert.strictEqual(typeof resilienceApi.getExplanation, 'function');
    assert.strictEqual(typeof resilienceApi.getProvenance, 'function');

    assert.strictEqual(typeof recoveryApi.plan, 'function');
    assert.strictEqual(typeof recoveryApi.listActive, 'function');
    assert.strictEqual(typeof recoveryApi.get, 'function');
    assert.strictEqual(typeof recoveryApi.approve, 'function');
    assert.strictEqual(typeof recoveryApi.executeContainment, 'function');
    assert.strictEqual(typeof recoveryApi.execute, 'function');
    assert.strictEqual(typeof recoveryApi.verify, 'function');
    assert.strictEqual(typeof recoveryApi.rollback, 'function');
    assert.strictEqual(typeof recoveryApi.abort, 'function');
    assert.strictEqual(typeof recoveryApi.handoff, 'function');
  });

  test('ResilienceCenterView initializes with overview subtab and renders cleanly', () => {
    const fakeContainer = {
      innerHTML: '',
      querySelector: () => null,
      querySelectorAll: () => [],
    };
    const view = new ResilienceCenterView(fakeContainer);
    assert.strictEqual(view.activeSubTab, 'overview');

    view.render();
    assert.ok(fakeContainer.innerHTML.includes('Resilience & Adaptive Defense Center'));
    assert.ok(fakeContainer.innerHTML.includes('Composite Resilience Index'));
    assert.ok(fakeContainer.innerHTML.includes('12 Dimensions of Resilience'));
  });

  test('ResilienceCenterView enforces explicit safety badges', () => {
    const fakeContainer = { innerHTML: '', querySelector: () => null, querySelectorAll: () => [] };
    const view = new ResilienceCenterView(fakeContainer);

    assert.ok(view.formatSafetyBadge('SIMULATION').includes('SIMULATION'));
    assert.ok(view.formatSafetyBadge('PENDING_APPROVAL').includes('PENDING_APPROVAL'));
    assert.ok(view.formatSafetyBadge('EXECUTING').includes('EXECUTING'));
    assert.ok(view.formatSafetyBadge('VERIFIED').includes('VERIFIED'));
    assert.ok(view.formatSafetyBadge('OBSERVED').includes('OBSERVED'));
    assert.ok(view.formatSafetyBadge('RECOMMENDATION').includes('RECOMMENDATION'));
  });

  test('ResilienceCenterView switches subtabs and renders respective views', () => {
    const fakeContainer = { innerHTML: '', querySelector: () => null, querySelectorAll: () => [] };
    const view = new ResilienceCenterView(fakeContainer);

    // Weaknesses tab
    view.setSubTab('weaknesses');
    assert.strictEqual(view.activeSubTab, 'weaknesses');
    assert.ok(fakeContainer.innerHTML.includes('Single Points of Failure'));

    // Recovery tab
    view.activePlans = [{
      plan_id: 'plan_123',
      state: 'CONTAINMENT_PLANNED',
      selected_strategy: 'FAILOVER',
      execution_order: ['db', 'api'],
      containment_points: [{ entity_id: 'api', isolation_method: 'CIRCUIT_BREAKER' }],
    }];
    view.setSubTab('recovery');
    assert.strictEqual(view.activeSubTab, 'recovery');
    assert.ok(fakeContainer.innerHTML.includes('plan_123'));
    assert.ok(fakeContainer.innerHTML.includes('FAILOVER'));

    // Simulator tab
    view.setSubTab('simulator');
    assert.strictEqual(view.activeSubTab, 'simulator');
    assert.ok(fakeContainer.innerHTML.includes('Counterfactual Resilience'));

    // History tab
    view.historyData = {
      trends: { mttd_seconds: 12.5, mttc_seconds: 4.2, mttr_seconds: 28.0, trend_direction: 'IMPROVING' },
      lessons: [{ incident_id: 'inc_test', status: 'OBSERVED', what_happened: 'Network partition', what_should_change: 'Add second route' }],
    };
    view.setSubTab('history');
    assert.strictEqual(view.activeSubTab, 'history');
    assert.ok(fakeContainer.innerHTML.includes('12.5s'));
    assert.ok(fakeContainer.innerHTML.includes('IMPROVING'));

    // Adaptive Defense tab
    view.setSubTab('adaptive');
    assert.strictEqual(view.activeSubTab, 'adaptive');
    assert.ok(fakeContainer.innerHTML.includes('Adaptive Defense Recommendations'));
  });
});
