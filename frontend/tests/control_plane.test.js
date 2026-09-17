/**
 * Unit tests for Kairo Autonomous Cognitive Control Plane & Unified Operating Loop (Task 102).
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { controlPlaneApi } from '../lib/api/endpoints.js';
import { ControlPlaneView } from '../components/control_plane/controlPlaneView.js';

describe('Control Plane API Endpoints (Task 102)', () => {
  test('controlPlaneApi exposes all canonical orchestration methods', () => {
    assert.strictEqual(typeof controlPlaneApi.getStatus, 'function');
    assert.strictEqual(typeof controlPlaneApi.listCycles, 'function');
    assert.strictEqual(typeof controlPlaneApi.getCycle, 'function');
    assert.strictEqual(typeof controlPlaneApi.getTimeline, 'function');
    assert.strictEqual(typeof controlPlaneApi.getSnapshot, 'function');
    assert.strictEqual(typeof controlPlaneApi.getQueue, 'function');
    assert.strictEqual(typeof controlPlaneApi.getHealth, 'function');
    assert.strictEqual(typeof controlPlaneApi.getMode, 'function');
    assert.strictEqual(typeof controlPlaneApi.reassess, 'function');
    assert.strictEqual(typeof controlPlaneApi.replayCycle, 'function');
  });
});

describe('ControlPlaneView Component', () => {
  test('initializes with default state and default cycles tab', () => {
    const mockContainer = { innerHTML: '', addEventListener: () => {} };
    const view = new ControlPlaneView(mockContainer);
    assert.strictEqual(view.activeTab, 'cycles');
    assert.strictEqual(view.status, null);
    assert.deepStrictEqual(view.cycles, []);
    assert.strictEqual(view.selectedCycle, null);
    assert.deepStrictEqual(view.timeline, []);
    assert.strictEqual(view.replayData, null);
    assert.strictEqual(view.isLoading, false);
    assert.strictEqual(view.error, null);
  });

  test('switches tabs correctly across all control plane panels', () => {
    const mockContainer = { innerHTML: '', addEventListener: () => {} };
    const view = new ControlPlaneView(mockContainer);
    view.setTab('timeline');
    assert.strictEqual(view.activeTab, 'timeline');
    view.setTab('loop_guard');
    assert.strictEqual(view.activeTab, 'loop_guard');
    view.setTab('replay');
    assert.strictEqual(view.activeTab, 'replay');
    view.setTab('cycles');
    assert.strictEqual(view.activeTab, 'cycles');
  });

  test('renders status overview header and badges accurately', () => {
    const mockContainer = { innerHTML: '', addEventListener: () => {} };
    const view = new ControlPlaneView(mockContainer);
    view.status = {
      control_mode: 'BOUNDED_AUTONOMY',
      emergency_stop_active: false,
      queue_depth: 2,
      total_cycles_executed: 14,
      metrics: {
        completed_cycles: 10,
        blocked_cycles: 1,
        no_action_cycles: 3,
        circuit_breaker_tripped: false,
        coalesced_events: 5,
        circuit_trips: 0,
      },
    };

    view.render();
    assert.ok(mockContainer.innerHTML.includes('Cognitive Control Plane &amp; Unified Operating Loop') || mockContainer.innerHTML.includes('Cognitive Control Plane & Unified Operating Loop'));
    assert.ok(mockContainer.innerHTML.includes('BOUNDED_AUTONOMY'));
    assert.ok(mockContainer.innerHTML.includes('INACTIVE'));
    assert.ok(mockContainer.innerHTML.includes('10 / 14'));
  });

  test('renders emergency stop banner when emergency stop is active', () => {
    const mockContainer = { innerHTML: '', addEventListener: () => {} };
    const view = new ControlPlaneView(mockContainer);
    view.status = {
      control_mode: 'EMERGENCY_STOP',
      emergency_stop_active: true,
      queue_depth: 0,
      total_cycles_executed: 5,
      metrics: {
        completed_cycles: 2,
        blocked_cycles: 3,
        no_action_cycles: 0,
        circuit_breaker_tripped: false,
      },
    };

    view.render();
    assert.ok(mockContainer.innerHTML.includes('ACTIVE (Fail-Closed)'));
  });

  test('renders cycles list table with statuses, triggers, and durations', () => {
    const mockContainer = { innerHTML: '', addEventListener: () => {} };
    const view = new ControlPlaneView(mockContainer);
    view.cycles = [
      {
        cycle_id: 'cycle-deploy-001',
        trigger_type: 'USER_REQUEST',
        status: 'COMPLETED',
        priority: 'CRITICAL',
        result: 'Deployment verified healthy',
        reason: 'Execution confirmed by world observation',
        budget: { consumed_duration_s: 1.4 },
      },
      {
        cycle_id: 'cycle-stale-002',
        trigger_type: 'RECOVERY_EVENT',
        status: 'BLOCKED',
        priority: 'HIGH',
        result: 'Blocked by emergency stop',
        reason: 'EmergencyStop invariant holds',
        budget: { consumed_duration_s: 0.2 },
      },
    ];

    const html = view.renderCycles();
    assert.ok(html.includes('cycle-deploy-001'));
    assert.ok(html.includes('USER_REQUEST'));
    assert.ok(html.includes('COMPLETED'));
    assert.ok(html.includes('cycle-stale-002'));
    assert.ok(html.includes('BLOCKED'));
  });

  test('renders timeline stages for the selected cycle', () => {
    const mockContainer = { innerHTML: '', addEventListener: () => {} };
    const view = new ControlPlaneView(mockContainer);
    view.selectedCycle = {
      cycle_id: 'cycle-test-123',
      trigger_type: 'SITUATION_ESCALATION',
      control_mode: 'BOUNDED_AUTONOMY',
      result: 'REMEDIATED',
    };
    view.timeline = [
      {
        stage: 'OBSERVE',
        status: 'SUCCESS',
        details: 'World state snapshot captured',
      },
      {
        stage: 'RECONCILE_WORLD',
        status: 'SUCCESS',
        details: 'Reconciled external metrics with zero drift',
      },
      {
        stage: 'VERIFY',
        status: 'SUCCESS',
        details: 'World telemetry confirms post-action success',
      },
    ];

    const html = view.renderTimeline();
    assert.ok(html.includes('cycle-test-123'));
    assert.ok(html.includes('OBSERVE'));
    assert.ok(html.includes('RECONCILE_WORLD'));
    assert.ok(html.includes('VERIFY'));
    assert.ok(html.includes('World telemetry confirms post-action success'));
  });

  test('renders loop guard anti-thrashing circuit breaker state', () => {
    const mockContainer = { innerHTML: '', addEventListener: () => {} };
    const view = new ControlPlaneView(mockContainer);
    view.status = {
      metrics: {
        circuit_breaker_tripped: true,
      },
    };

    const html = view.renderLoopGuard();
    assert.ok(html.includes('CIRCUIT BREAKER TRIPPED'));
    assert.ok(html.includes('Failure Threshold'));
    assert.ok(html.includes('3 Consecutive'));
  });

  test('renders deterministic read-only replay panel', () => {
    const mockContainer = { innerHTML: '', addEventListener: () => {} };
    const view = new ControlPlaneView(mockContainer);
    view.replayData = {
      replayed_cycle_id: 'cycle-source-888',
      replay_mode: 'DETERMINISTIC_REPLAY',
      side_effects_executed: 'NONE (READ-ONLY)',
      reconstructed_status: 'COMPLETED',
      total_stages_replayed: 16,
    };

    const html = view.renderReplay();
    assert.ok(html.includes('Deterministic Replay: cycle-source-888'));
    assert.ok(html.includes('NONE (READ-ONLY)'));
  });
});
