/**
 * Unit tests for Task 98: KAIRO Autonomous World-State Reconstruction, State Estimation,
 * Reality Synchronization & Drift Reconciliation UI.
 * Verifies WorldStateReconciliationView initialization, DOM structure, tab navigation,
 * entity inspection, drift analytics, dialectic conflict views, and historical reconstruction.
 */

import { test, describe } from 'node:test';
import assert from 'node:assert';
import { WorldStateReconciliationView } from '../components/world_state/worldStateReconciliationView.js';

describe('WorldStateReconciliationView Component (Task 98 UI)', () => {
  function createMockContainer() {
    let containerHtml = '';
    const elements = new Map();

    const container = {
      get innerHTML() {
        return containerHtml;
      },
      set innerHTML(val) {
        containerHtml = val;
      },
      querySelectorAll: (sel) => {
        return [];
      },
      querySelector: (sel) => {
        if (!elements.has(sel)) {
          let elHtml = '';
          elements.set(sel, {
            get innerHTML() {
              return elHtml;
            },
            set innerHTML(val) {
              elHtml = val;
            },
            value: '',
            style: {},
            classList: {
              add: () => {},
              remove: () => {},
              toggle: () => {},
            },
            addEventListener: () => {},
          });
        }
        return elements.get(sel);
      },
      addEventListener: () => {},
    };
    return container;
  }

  function createMockApi() {
    const mockEntities = [
      {
        canonical_id: 'cluster:k8s:prod-eu',
        scope: 'INFRASTRUCTURE',
        entity_type: 'KUBERNETES_CLUSTER',
        status: 'ACTIVE',
        certainty: 'CERTAIN',
        confidence: 0.98,
        freshness: 'FRESH',
        attributes: {
          node_count: {
            value: 12,
            confidence: 0.98,
            observed_at: '2026-09-17T12:00:00Z',
            epistemic_status: 'OBSERVED',
            source_count: 2,
          }
        },
        drift_count: 1,
        conflict_count: 0,
        invariant_violation_count: 0,
        last_observed_at: '2026-09-17T12:00:00Z',
        last_reconciled_at: '2026-09-17T12:05:00Z',
        active_drifts: ['drift_node_mismatch']
      },
      {
        canonical_id: 'service:api:gateway',
        scope: 'SYSTEM',
        entity_type: 'MICROSERVICE',
        status: 'DEGRADED',
        certainty: 'PROBABLE',
        confidence: 0.82,
        freshness: 'STALE',
        attributes: {
          latency_ms: {
            value: 450,
            confidence: 0.82,
            observed_at: '2026-09-17T11:30:00Z',
            epistemic_status: 'OBSERVED',
            source_count: 1,
          }
        },
        drift_count: 0,
        conflict_count: 1,
        invariant_violation_count: 1,
        last_observed_at: '2026-09-17T11:30:00Z',
        last_reconciled_at: '2026-09-17T11:35:00Z',
        active_drifts: []
      }
    ];

    const mockDrifts = [
      {
        drift_id: 'drift_node_mismatch',
        scope: 'INFRASTRUCTURE',
        canonical_id: 'cluster:k8s:prod-eu',
        attribute_name: 'node_count',
        drift_type: 'VALUE_DIVERGENCE',
        severity: 'MEDIUM',
        classification: 'EXTERNAL_MODIFICATION',
        status: 'ACTIVE',
        expected_value: 16,
        observed_value: 12,
        detected_at: '2026-09-17T12:05:00Z',
        cause_hypothesis: 'Preemptible worker pool scale-down without agent notification',
        attribution: 'UNATTRIBUTED_CHANGE'
      }
    ];

    const mockObservations = [
      {
        observation_id: 'obs_node_telemetry_001',
        scope: 'INFRASTRUCTURE',
        canonical_id: 'cluster:k8s:prod-eu',
        source_id: 'telemetry_daemon_node_exporter',
        observed_at: '2026-09-17T12:00:00Z',
        certainty: 'CERTAIN',
        confidence: 0.99,
        attributes: { node_count: 12 }
      }
    ];

    const mockConflicts = [
      {
        conflict_id: 'conf_gateway_latency_001',
        canonical_id: 'service:api:gateway',
        attribute_name: 'latency_ms',
        status: 'OPEN',
        sources: ['prometheus_metrics', 'synthetic_probe'],
        divergence_ratio: 0.65,
        resolved: false,
        created_at: '2026-09-17T11:35:00Z'
      }
    ];

    const mockInvariants = [
      {
        violation_id: 'inv_freshness_001',
        canonical_id: 'service:api:gateway',
        rule_name: 'STALE_CANNOT_BE_CURRENT',
        severity: 'HIGH',
        detected_at: '2026-09-17T11:45:00Z',
        description: 'Entity marked as DEGRADED has not received observation within maximum staleness SLA'
      }
    ];

    return {
      getCurrentState: async () => ({
        success: true,
        scope: 'INFRASTRUCTURE',
        entity_count: mockEntities.length,
        entities: mockEntities,
        active_drift_count: 1,
        active_conflict_count: 0
      }),
      getScopeEntities: async () => ({
        success: true,
        entities: mockEntities
      }),
      getObservations: async () => ({
        success: true,
        observations: mockObservations
      }),
      getDriftRecords: async () => ({
        success: true,
        drifts: mockDrifts
      }),
      getConflicts: async () => ({
        success: true,
        conflicts: mockConflicts
      }),
      auditFreshnessAndInvariants: async () => ({
        success: true,
        violations: mockInvariants,
        stale_count: 1
      }),
      getSnapshots: async () => ({
        success: true,
        snapshots: [
          {
            snapshot_id: 'snap_1726574400',
            created_at: '2026-09-17T12:00:00Z',
            scope: 'ALL',
            entity_count: 2
          }
        ]
      }),
      getRevalidations: async () => ({
        success: true,
        revalidations: [
          {
            revalidation_id: 'reval_001',
            canonical_id: 'cluster:k8s:prod-eu',
            reason: 'VALUE_DIVERGENCE_RECHECK',
            status: 'PENDING'
          }
        ]
      }),
      reconcile: async () => ({
        success: true,
        reconciled_count: 2,
        detected_drifts: 1
      }),
      reconcileState: async () => ({
        success: true,
        reconciled_count: 2,
        detected_drifts: 1
      }),
      reconstructHistoricalState: async (timestamp, scope) => ({
        success: true,
        reconstructed_at: timestamp,
        entity_count: 2,
        entities: mockEntities
      }),
      reconstructHistorical: async (timestamp, scope) => ({
        success: true,
        reconstructed_at: timestamp,
        entity_count: 2,
        entities: mockEntities
      }),
      getDiff: async (fromId, toId) => ({
        success: true,
        from_snapshot: fromId,
        to_snapshot: toId,
        added: [],
        removed: [],
        modified: [
          {
            canonical_id: 'cluster:k8s:prod-eu',
            changes: { node_count: { old: 16, new: 12 } }
          }
        ]
      })
    };
  }

  test('should instantiate WorldStateReconciliationView properly with default state', () => {
    const container = createMockContainer();
    const api = createMockApi();
    const view = new WorldStateReconciliationView({ container, api });

    assert.ok(view);
    assert.strictEqual(view.state.activeTab, 'current');
    assert.strictEqual(view.state.selectedScope, 'SYSTEM');
    assert.strictEqual(view.state.entities.length, 0);
  });

  test('should render shell structure containing header, tabs, and metrics', async () => {
    const container = createMockContainer();
    const api = createMockApi();
    const view = new WorldStateReconciliationView({ container, api });

    await view.render();

    assert.ok(container.innerHTML.includes('World-State Reconstruction & Drift Engine'));
    assert.ok(container.innerHTML.includes('Total Reconstructed Entities'));
    assert.ok(container.innerHTML.includes('Active Reality Drifts'));
    assert.ok(container.innerHTML.includes('Dialectic Conflicts'));
    assert.ok(container.innerHTML.includes('data-tab="current"'));
    assert.ok(container.innerHTML.includes('data-tab="drift"'));
    assert.ok(container.innerHTML.includes('data-tab="observations"'));
    assert.ok(container.innerHTML.includes('data-tab="conflicts"'));
    assert.ok(container.innerHTML.includes('data-tab="invariants"'));
    assert.ok(container.innerHTML.includes('data-tab="historical"'));
  });

  test('should load entities and refresh current state cards', async () => {
    const container = createMockContainer();
    const api = createMockApi();
    const view = new WorldStateReconciliationView({ container, api });

    await view.render();
    await view.refresh();

    assert.strictEqual(view.state.entities.length, 2);
    assert.strictEqual(view.state.metrics.totalEntities, 2);
    assert.strictEqual(view.state.metrics.activeDriftCount, 1);
    assert.strictEqual(view.state.drifts.length, 1);
    assert.strictEqual(view.state.observations.length, 1);
    assert.strictEqual(view.state.conflicts.length, 1);
  });

  test('should switch active tabs correctly and update view content', async () => {
    const container = createMockContainer();
    const api = createMockApi();
    const view = new WorldStateReconciliationView({ container, api });

    await view.render();
    await view.refresh();

    // Switch to drift tab
    view.setTab('drift');
    assert.strictEqual(view.state.activeTab, 'drift');
    assert.ok(container.innerHTML.includes('drift_node_mismatch') || container.innerHTML.includes('VALUE_DIVERGENCE'));

    // Switch to observations tab
    view.setTab('observations');
    assert.strictEqual(view.state.activeTab, 'observations');
    assert.ok(container.innerHTML.includes('obs_node_telemetry_001') || container.innerHTML.includes('Observations'));

    // Switch to conflicts tab
    view.setTab('conflicts');
    assert.strictEqual(view.state.activeTab, 'conflicts');
    assert.ok(container.innerHTML.includes('conf_gateway_latency_001') || container.innerHTML.includes('Conflicts'));

    // Switch to invariants tab
    view.setTab('invariants');
    assert.strictEqual(view.state.activeTab, 'invariants');
    assert.ok(container.innerHTML.includes('inv_freshness_001') || container.innerHTML.includes('Invariants'));
  });

  test('should handle historical reconstruction query', async () => {
    const container = createMockContainer();
    const api = createMockApi();
    const view = new WorldStateReconciliationView({ container, api });

    await view.render();
    view.setTab('historical');

    await view.triggerHistoricalReconstruct('2026-09-17T10:00:00Z');
    assert.ok(view.state.reconstructionResult);
    assert.strictEqual(view.state.reconstructionResult.success, true);
    assert.strictEqual(view.state.reconstructionResult.entity_count, 2);
  });

  test('should trigger reconciliation cycle successfully', async () => {
    const container = createMockContainer();
    const api = createMockApi();
    const view = new WorldStateReconciliationView({ container, api });

    await view.render();
    await view.triggerReconcile();

    assert.strictEqual(view.state.error, null);
    assert.strictEqual(view.state.entities.length, 2);
  });
});
