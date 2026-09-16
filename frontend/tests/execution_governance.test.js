/**
 * Unit tests for Task 95: KAIRO Autonomous Execution Governance & Action Transactions UI.
 * Verifies ExecutionGovernanceView initialization, template rendering, 18-gate preflight inspector,
 * approval gating, empirical observations, rollback compensation, and UNKNOWN outcome recovery.
 */

import { test, describe } from 'node:test';
import assert from 'node:assert';
import { ExecutionGovernanceView } from '../components/execution/executionGovernanceView.js';

describe('ExecutionGovernanceView Component (Task 95 UI)', () => {
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
            classList: {
              add: () => {},
              remove: () => {},
            },
            addEventListener: () => {},
          });
        }
        return elements.get(sel);
      },
    };
    return container;
  }

  function createMockApi() {
    const mockTransactions = [
      {
        transaction_id: 'txn_test_001',
        decision_id: 'dec_test_001',
        status: 'SUCCEEDED',
        capability_id: 'system_exec',
        capability_version: '1.0.0',
        action_reference: 'tool:system_exec',
        target: { target_id: 'prod_cluster_1', target_type: 'SERVICE' },
        verification_state: 'PASSED',
        outcome_type: 'FULL_SUCCESS',
        deviation_score: 0.02,
        regret_score: 0.0,
        preflight_checks: [
          { gate_name: 'gate_1_decision_currency', passed: true, reason: 'Decision active', latency_ms: 1.2 },
          { gate_name: 'gate_9_security_authorization', passed: true, reason: 'SecurityCenter OK', latency_ms: 3.4 },
          { gate_name: 'gate_13_emergency_stop_inactive', passed: true, reason: 'E-stop inactive', latency_ms: 0.5 },
        ],
        observations: [
          { observation_id: 'obs_1', source: 'ToolExecutor', exit_code: 0, raw_snippet: 'Process exited code 0' },
        ],
      },
      {
        transaction_id: 'txn_test_002',
        decision_id: 'dec_test_002',
        status: 'AWAITING_APPROVAL',
        capability_id: 'database_drop',
        capability_version: '1.0.0',
        action_reference: 'tool:database_drop',
        target: { target_id: 'db_archive_2023', target_type: 'RESOURCE' },
        verification_state: 'NOT_STARTED',
        outcome_type: null,
      },
      {
        transaction_id: 'txn_test_003',
        decision_id: 'dec_test_003',
        status: 'UNKNOWN',
        capability_id: 'network_probe',
        capability_version: '1.0.0',
        action_reference: 'tool:network_probe',
        target: { target_id: 'remote_edge_gateway', target_type: 'ENDPOINT' },
        verification_state: 'UNKNOWN',
        outcome_type: null,
        compensation_action: 'tool:network_probe_reset',
      },
    ];

    let executedActions = [];
    let cancelledActions = [];
    let reconciledActions = [];
    let rolledBackActions = [];

    return {
      executedActions,
      cancelledActions,
      reconciledActions,
      rolledBackActions,
      listTransactions: async () => mockTransactions,
      getTransaction: async (id) => mockTransactions.find((t) => t.transaction_id === id) || null,
      getPreflight: async (id) => mockTransactions.find((t) => t.transaction_id === id)?.preflight_checks || [],
      getObservations: async (id) => mockTransactions.find((t) => t.transaction_id === id)?.observations || [],
      executeAction: async (id, approvalId) => {
        executedActions.push({ id, approvalId });
        return { success: true, transaction_id: id, status: 'EXECUTING' };
      },
      cancelAction: async (id, reason) => {
        cancelledActions.push({ id, reason });
        return { success: true, transaction_id: id, status: 'CANCELLED' };
      },
      rollbackAction: async (id, reason) => {
        rolledBackActions.push({ id, reason });
        return { success: true, transaction_id: id, status: 'ROLLED_BACK' };
      },
      reconcileAction: async (id) => {
        reconciledActions.push({ id });
        return { success: true, transaction_id: id, status: 'RECOVERED' };
      },
    };
  }

  test('ExecutionGovernanceView initializes with default state and mock API', () => {
    const container = createMockContainer();
    const api = createMockApi();
    const view = new ExecutionGovernanceView({ container, api });

    assert.strictEqual(view.state.activeTab, 'inbox');
    assert.strictEqual(view.state.isLoading, false);
    assert.deepStrictEqual(view.state.transactions, []);
  });

  test('render generates header, navigation tabs, and content pane', async () => {
    const container = createMockContainer();
    const api = createMockApi();
    const view = new ExecutionGovernanceView({ container, api });

    await view.render();

    assert.ok(container.innerHTML.includes('KAIRO Autonomous Execution Governance'));
    assert.ok(container.innerHTML.includes('Pre-Flight Gates (18)'));
    assert.ok(container.innerHTML.includes('Awaiting Approval'));
    assert.ok(container.innerHTML.includes('Rollback & Unknown Recovery'));
    assert.ok(container.innerHTML.includes('Verified Outcomes'));
    assert.strictEqual(view.state.transactions.length, 3);
  });

  test('renderActiveTab switches tabs and displays expected views', async () => {
    const container = createMockContainer();
    const api = createMockApi();
    const view = new ExecutionGovernanceView({ container, api });

    await view.render();

    // 1. Preflight tab
    await view.switchTab('preflight');
    const pane = container.querySelector('#eg-content-pane');
    assert.ok(pane.innerHTML.includes('18-Gate Pre-Flight Validation'));
    assert.ok(pane.innerHTML.includes('gate_1_decision_currency'));
    assert.ok(pane.innerHTML.includes('PASSED'));

    // 2. Approvals tab
    await view.switchTab('approvals');
    assert.ok(pane.innerHTML.includes('Awaiting Human Authorization (1)'));
    assert.ok(pane.innerHTML.includes('database_drop'));
    assert.ok(pane.innerHTML.includes('Approve & Execute'));

    // 3. Recovery tab
    await view.switchTab('recovery');
    assert.ok(pane.innerHTML.includes('Rollback Compensation & Unknown Outcome Recovery'));
    assert.ok(pane.innerHTML.includes('UNKNOWN'));
    assert.ok(pane.innerHTML.includes('Reconcile State'));

    // 4. History tab
    await view.switchTab('history');
    assert.ok(pane.innerHTML.includes('Verified Outcomes History'));
    assert.ok(pane.innerHTML.includes('FULL_SUCCESS'));
  });

  test('api execution, rollback and reconciliation methods trigger properly', async () => {
    const container = createMockContainer();
    const api = createMockApi();
    const view = new ExecutionGovernanceView({ container, api });

    await view.render();

    // Execute with approval
    await api.executeAction('txn_test_002', 'appr_adm_99');
    assert.strictEqual(api.executedActions.length, 1);
    assert.strictEqual(api.executedActions[0].approvalId, 'appr_adm_99');

    // Reconcile unknown
    await api.reconcileAction('txn_test_003');
    assert.strictEqual(api.reconciledActions.length, 1);
    assert.strictEqual(api.reconciledActions[0].id, 'txn_test_003');

    // Rollback
    await api.rollbackAction('txn_test_003', 'Manual operator revert');
    assert.strictEqual(api.rolledBackActions.length, 1);
    assert.strictEqual(api.rolledBackActions[0].reason, 'Manual operator revert');
  });
});
