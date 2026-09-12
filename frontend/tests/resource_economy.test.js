/**
 * Unit tests for Kairo Autonomous Resource Economy, Capability Allocation & Cognitive Budget Engine (Task 77).
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { resourceEconomyApi } from '../lib/api/endpoints.js';
import { ResourceCenterView } from '../components/orchestration/resourceCenterView.js';

describe('Autonomous Resource Economy & Cognitive Budget API (Task 77)', () => {
  test('resourceEconomyApi exposes all authoritative endpoints', () => {
    assert.strictEqual(typeof resourceEconomyApi.getOverview, 'function');
    assert.strictEqual(typeof resourceEconomyApi.estimateDemand, 'function');
    assert.strictEqual(typeof resourceEconomyApi.createBudget, 'function');
    assert.strictEqual(typeof resourceEconomyApi.listBudgets, 'function');
    assert.strictEqual(typeof resourceEconomyApi.getBudget, 'function');
    assert.strictEqual(typeof resourceEconomyApi.checkBudget, 'function');
    assert.strictEqual(typeof resourceEconomyApi.allocateBudget, 'function');
    assert.strictEqual(typeof resourceEconomyApi.resetBudget, 'function');
    assert.strictEqual(typeof resourceEconomyApi.requestPreemption, 'function');
    assert.strictEqual(typeof resourceEconomyApi.checkpointTask, 'function');
    assert.strictEqual(typeof resourceEconomyApi.resumeTask, 'function');
    assert.strictEqual(typeof resourceEconomyApi.listPreemptions, 'function');
    assert.strictEqual(typeof resourceEconomyApi.detectDeadlocks, 'function');
    assert.strictEqual(typeof resourceEconomyApi.resolveDeadlocks, 'function');
    assert.strictEqual(typeof resourceEconomyApi.getFairnessMetrics, 'function');
    assert.strictEqual(typeof resourceEconomyApi.evaluateTradeOff, 'function');
    assert.strictEqual(typeof resourceEconomyApi.routeModel, 'function');
  });
});

describe('ResourceCenterView Component (Task 77)', () => {
  test('initializes with overview subtab and default collections', () => {
    const mockContainer = { innerHTML: '', querySelector: () => null, querySelectorAll: () => [] };
    const view = new ResourceCenterView(mockContainer);
    assert.strictEqual(view.activeSubTab, 'overview');
    assert.strictEqual(view.budgetsData.length, 0);
    assert.strictEqual(view.preemptionsData.length, 0);
    assert.strictEqual(view.deadlocksData.length, 0);
  });

  test('switches subtabs correctly across all 6 views', () => {
    const mockContainer = { innerHTML: '', querySelector: () => null, querySelectorAll: () => [] };
    const view = new ResourceCenterView(mockContainer);

    view.setSubTab('budgets');
    assert.strictEqual(view.activeSubTab, 'budgets');

    view.setSubTab('preemption');
    assert.strictEqual(view.activeSubTab, 'preemption');

    view.setSubTab('deadlock');
    assert.strictEqual(view.activeSubTab, 'deadlock');

    view.setSubTab('tradeoffs');
    assert.strictEqual(view.activeSubTab, 'tradeoffs');

    view.setSubTab('fairness');
    assert.strictEqual(view.activeSubTab, 'fairness');

    view.setSubTab('overview');
    assert.strictEqual(view.activeSubTab, 'overview');
  });

  test('enforces explicit safety badge formatting', () => {
    const mockContainer = { innerHTML: '', querySelector: () => null, querySelectorAll: () => [] };
    const view = new ResourceCenterView(mockContainer);

    const availableBadge = view.formatSafetyBadge('AVAILABLE');
    assert.match(availableBadge, /AVAILABLE/);
    assert.match(availableBadge, /#10b981/);

    const reservedBadge = view.formatSafetyBadge('RESERVED');
    assert.match(reservedBadge, /RESERVED/);
    assert.match(reservedBadge, /#f59e0b/);

    const allocatedBadge = view.formatSafetyBadge('ALLOCATED');
    assert.match(allocatedBadge, /ALLOCATED/);
    assert.match(allocatedBadge, /#3b82f6/);

    const degradedBadge = view.formatSafetyBadge('DEGRADED');
    assert.match(degradedBadge, /DEGRADED/);
    assert.match(degradedBadge, /#ea580c/);

    const exhaustedBadge = view.formatSafetyBadge('EXHAUSTED');
    assert.match(exhaustedBadge, /EXHAUSTED/);
    assert.match(exhaustedBadge, /#ef4444/);
  });

  test('renders base HTML structure and sub-navigation cleanly', () => {
    let htmlOutput = '';
    const mockContainer = {
      set innerHTML(val) { htmlOutput = val; },
      get innerHTML() { return htmlOutput; },
      querySelector: () => null,
      querySelectorAll: () => [],
    };
    const view = new ResourceCenterView(mockContainer);
    view.render();

    assert.match(htmlOutput, /Autonomous Resource Economy & Cognitive Budget Center/);
    assert.match(htmlOutput, /1\. Economy Overview/);
    assert.match(htmlOutput, /2\. Cognitive Budgets/);
    assert.match(htmlOutput, /3\. Preemption & Queue/);
    assert.match(htmlOutput, /4\. Deadlock & Contention/);
    assert.match(htmlOutput, /5\. Trade-Offs & Degradation/);
    assert.match(htmlOutput, /6\. Starvation & Fair Share/);
  });
});
