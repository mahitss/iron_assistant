/**
 * Unit tests for Task 93: KAIRO System State Graph & Self-Modeling UI.
 * Verifies SystemStateView initialization, template generation, tab rendering, and safety boundaries.
 */

import { test, describe } from 'node:test';
import assert from 'node:assert';
import { SystemStateView } from '../components/system_state/systemStateView.js';

describe('SystemStateView Component (Task 93 Phase 27)', () => {
  function createMockContainer() {
    let containerHtml = '';
    let paneHtml = '';
    const pane = {
      get innerHTML() {
        return paneHtml;
      },
      set innerHTML(val) {
        paneHtml = val;
      },
    };
    return {
      get innerHTML() {
        return containerHtml + paneHtml;
      },
      set innerHTML(val) {
        containerHtml = val;
      },
      querySelectorAll: () => [],
      querySelector: (sel) => (sel === '#ss-content-pane' ? pane : null),
    };
  }

  function createMockApi() {
    return {
      getSummary: async () => ({
        overall_state: 'HEALTHY',
        health_score: 0.98,
        total_entities: 12,
        total_edges: 18,
        active_work_count: 2,
        active_objectives_count: 1,
        security_emergency_stop: false,
        epistemic_breakdown: { OBSERVED: 10, PREDICTED: 2 },
      }),
      getHealth: async () => ({ overall_state: 'HEALTHY', composite_health_score: 0.98, unhealthy_components: [] }),
      getGraph: async () => ({
        nodes: [
          { id: 'goal:1', type: 'GOAL', status: 'ACTIVE', epistemic: 'OBSERVED', health: 1.0 },
          { id: 'task:1', type: 'TASK', status: 'ACTIVE', epistemic: 'OBSERVED', health: 1.0 },
        ],
        links: [{ source: 'goal:1', target: 'task:1', type: 'SERVES' }],
      }),
      getDiagnostics: async () => ({
        current_state: 'HEALTHY',
        health_score: 0.98,
        active_objectives: [{ id: 'goal:1' }],
        active_work: [{ id: 'task:1' }],
      }),
      getSelfModel: async () => ({
        what_am_i_doing: [{ entity_id: 'task:1' }],
        why_am_i_doing_it: [{ work_id: 'task:1', serving_goals: [{ goal_id: 'goal:1' }] }],
        what_am_i_waiting_for: [],
        what_is_broken: [],
        what_goals_are_blocked: [],
        what_do_i_not_know: [],
        which_assumptions_are_inferred: [],
      }),
      getResources: async () => ({ pools: [{ id: 'res:cpu', status: 'HEALTHY', health: 0.9 }] }),
      getDependencies: async () => ({ internal_dependencies: [], external_dependencies: [] }),
      getIncidents: async () => ({ active_incidents: [] }),
      getChanges: async () => [],
      getSnapshots: async () => [],
    };
  }

  test('initializes with default state and overview tab', () => {
    const container = createMockContainer();
    const view = new SystemStateView({ container, api: createMockApi() });

    assert.strictEqual(view.state.activeTab, 'overview');
    assert.strictEqual(view.state.isLoading, false);
    assert.strictEqual(view.state.error, null);
  });

  test('renders header, title, and action buttons', async () => {
    const container = createMockContainer();
    const view = new SystemStateView({ container, api: createMockApi() });
    await view.render();

    assert.ok(container.innerHTML.includes('KAIRO Autonomous System State Graph'));
    assert.ok(container.innerHTML.includes('Operational Digital Twin &amp; Self-Modeling Substrate') || container.innerHTML.includes('Operational Digital Twin & Self-Modeling Substrate'));
    assert.ok(container.innerHTML.includes('Capture Snapshot'));
    assert.ok(container.innerHTML.includes('Reconcile State'));
  });

  test('fetches operational data and populates state', async () => {
    const container = createMockContainer();
    const view = new SystemStateView({ container, api: createMockApi() });
    await view.fetchData();

    assert.strictEqual(view.state.summary.overall_state, 'HEALTHY');
    assert.strictEqual(view.state.summary.total_entities, 12);
    assert.strictEqual(view.state.graphData.nodes.length, 2);
    assert.strictEqual(view.state.graphData.links.length, 1);
  });

  test('renders self-model introspection questions', async () => {
    const container = createMockContainer();
    const view = new SystemStateView({ container, api: createMockApi() });
    await view.fetchData();
    view.state.activeTab = 'self_model';
    view._renderActiveTab();

    assert.ok(container.innerHTML.includes('1. What am I doing?'));
    assert.ok(container.innerHTML.includes('2. Why am I doing it? (Serving Goals)'));
    assert.ok(container.innerHTML.includes('4. What is currently broken?'));
    assert.ok(container.innerHTML.includes('7. Which assumptions are inferred rather than observed?'));
  });

  test('renders security center boundary notice', async () => {
    const container = createMockContainer();
    const view = new SystemStateView({ container, api: createMockApi() });
    await view.fetchData();
    view.state.activeTab = 'security';
    view._renderActiveTab();

    assert.ok(container.innerHTML.includes('SecurityCenter &amp; EmergencyStop Boundary') || container.innerHTML.includes('SecurityCenter & EmergencyStop Boundary'));
    assert.ok(container.innerHTML.includes('The System State Graph is strictly an observational layer'));
  });
});
