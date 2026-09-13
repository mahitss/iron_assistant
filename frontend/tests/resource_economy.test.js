/**
 * Unit tests for Kairo Autonomous Resource Economy, Capability Allocation & Cognitive Budget Engine (Task 77).
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { resourceEconomyApi, nativeRuntimeApi } from '../lib/api/endpoints.js';
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
    assert.match(htmlOutput, /7\. Native Enforcement/);
    assert.match(htmlOutput, /8\. Native Tool Fabric/);
    assert.match(htmlOutput, /9\. Computer Substrate/);
  });

  test('switches to native enforcement subtab and renders matrix and explanation', () => {
    let htmlOutput = '';
    const mockContainer = {
      set innerHTML(val) { htmlOutput = val; },
      get innerHTML() { return htmlOutput; },
      querySelector: () => null,
      querySelectorAll: () => [],
    };
    const view = new ResourceCenterView(mockContainer);
    view.setSubTab('native');

    assert.strictEqual(view.activeSubTab, 'native');
    assert.match(htmlOutput, /Cross-Platform Native Enforcement Matrix/);
    assert.match(htmlOutput, /Execution Resource Lifecycle & Explanation/);
    assert.match(htmlOutput, /RUST NATIVE/);
  });

  test('switches to native tool fabric subtab and renders tool catalog and invariants', () => {
    let htmlOutput = '';
    const mockContainer = {
      set innerHTML(val) { htmlOutput = val; },
      get innerHTML() { return htmlOutput; },
      querySelector: () => null,
      querySelectorAll: () => [],
    };
    const view = new ResourceCenterView(mockContainer);
    view.nativeToolsData = [
      {
        name: 'native_hash',
        version: '1.0.0',
        execution_class: 'NATIVE_RUST',
        preference: 'NATIVE_PREFERRED',
        capability_id: 'sandbox.hash',
        sandbox_profile: 'STANDARD',
        permission_level: 'READ',
        availability: 'AVAILABLE',
        metrics: { invocations: 12, success_rate: 1.0, avg_latency_ms: 4.2, fallbacks: 0 },
      },
    ];
    view.setSubTab('tools');

    assert.strictEqual(view.activeSubTab, 'tools');
    assert.match(htmlOutput, /Native Tool Execution Fabric Catalog/);
    assert.match(htmlOutput, /Runtime Substrate State/);
    assert.match(htmlOutput, /Registered Native Tools/);
    assert.match(htmlOutput, /Zero Shell Strings/);
    assert.match(htmlOutput, /native_hash/);
    assert.match(htmlOutput, /sandbox\.hash/);
  });

  test('switches to computer substrate subtab and renders window/process/display tables and safety alerts', () => {
    let htmlOutput = '';
    const mockContainer = {
      set innerHTML(val) { htmlOutput = val; },
      get innerHTML() { return htmlOutput; },
      querySelector: () => null,
      querySelectorAll: () => [],
    };
    const view = new ResourceCenterView(mockContainer);
    view.nativeWindowsData = [
      {
        window_id: 65538,
        title: 'Visual Studio Code',
        process_name: 'Code.exe',
        pid: 12345,
        rect: { x: 0, y: 0, width: 1920, height: 1080 },
        is_visible: true,
        is_focused: true,
      },
    ];
    view.nativeDisplaysData = [
      {
        display_id: 0,
        name: 'Primary Display',
        width: 1920,
        height: 1080,
        scale_factor: 1.0,
        is_primary: true,
      },
    ];
    view.setSubTab('computer');

    assert.strictEqual(view.activeSubTab, 'computer');
    assert.match(htmlOutput, /Observed Windows/);
    assert.match(htmlOutput, /Target Context Verification & Safety Invariants/);
    assert.match(htmlOutput, /ABORT_TARGET_CHANGED/);
    assert.match(htmlOutput, /Visual Studio Code/);
    assert.match(htmlOutput, /Code\.exe/);
    assert.match(htmlOutput, /FOCUSED/);
    assert.match(htmlOutput, /Connected Displays/);
  });
});

describe('Native Tool Execution Fabric API (Task 83)', () => {
  test('nativeRuntimeApi exposes all Task 83 tool fabric methods', () => {
    assert.strictEqual(typeof nativeRuntimeApi.listTools, 'function');
    assert.strictEqual(typeof nativeRuntimeApi.getToolHealth, 'function');
    assert.strictEqual(typeof nativeRuntimeApi.getToolDetail, 'function');
    assert.strictEqual(typeof nativeRuntimeApi.executeTool, 'function');
  });
});

describe('Native Computer Interaction Substrate API (Task 84)', () => {
  test('nativeRuntimeApi exposes all Task 84 computer interaction methods', () => {
    assert.strictEqual(typeof nativeRuntimeApi.listWindows, 'function');
    assert.strictEqual(typeof nativeRuntimeApi.listProcesses, 'function');
    assert.strictEqual(typeof nativeRuntimeApi.listDisplays, 'function');
    assert.strictEqual(typeof nativeRuntimeApi.captureScreen, 'function');
    assert.strictEqual(typeof nativeRuntimeApi.readClipboard, 'function');
    assert.strictEqual(typeof nativeRuntimeApi.writeClipboard, 'function');
    assert.strictEqual(typeof nativeRuntimeApi.executeMouse, 'function');
    assert.strictEqual(typeof nativeRuntimeApi.executeKeyboard, 'function');
  });
});



