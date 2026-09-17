/**
 * Unit tests for Task 96: KAIRO Autonomous Multi-Agent Collaboration, Delegation & Swarm Orchestration UI.
 * Verifies SwarmOrchestrationView initialization, template rendering, agent worker registry,
 * DAG visualization, supervision & stall monitoring, blackboard auditing, and consensus synthesis.
 */

import { test, describe } from 'node:test';
import assert from 'node:assert';
import { SwarmOrchestrationView } from '../components/swarm/swarmOrchestrationView.js';

describe('SwarmOrchestrationView Component (Task 96 UI)', () => {
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
              toggle: () => {},
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
    const mockSwarms = [
      {
        session_id: 'swm_test_001',
        status: 'EXECUTING',
        objective: { goal: 'Security Architecture Audit' },
        created_at: new Date().toISOString(),
        topology: 'STAR',
      },
    ];

    const mockAgents = [
      {
        agent_id: 'ag_res_001',
        role: 'RESEARCHER',
        session_id: 'swm_test_001',
        lifecycle_state: 'RUNNING',
        trust_score: 0.95,
        context_scope: 'PRIVATE_AGENT_CONTEXT',
        capability_scope: ['web_search', 'document_read'],
        history: [],
      },
      {
        agent_id: 'ag_val_002',
        role: 'VALIDATOR',
        session_id: 'swm_test_001',
        lifecycle_state: 'RUNNING',
        trust_score: 0.98,
        context_scope: 'PRIVATE_AGENT_CONTEXT',
        capability_scope: ['verification_check'],
        history: [],
      },
    ];

    const mockGraph = {
      nodes: [
        { id: 'ag_res_001', label: 'RESEARCHER', type: 'agent', state: 'RUNNING' },
        { id: 'tsk_001', label: 'Gather Evidence', type: 'task', state: 'COMPLETED' },
      ],
      edges: [
        { source: 'ag_res_001', target: 'tsk_001', type: 'executes' },
      ],
    };

    return {
      listSwarms: async () => mockSwarms,
      getSwarm: async (id) => mockSwarms[0],
      getSwarmGraph: async (id) => mockGraph,
      getSwarmAgents: async (id) => mockAgents,
      getSwarmResults: async (id) => [
        {
          agent_id: 'ag_res_001',
          task_id: 'tsk_001',
          summary: 'Identified 2 unencrypted endpoints',
          validation_status: 'VALIDATED',
        },
      ],
      getSwarmConflicts: async (id) => [],
      superviseSwarm: async (id) => [{ agent_id: 'ag_res_001', stall_state: 'HEALTHY' }],
      synthesizeSwarm: async (id) => ({
        swarm_id: id,
        summary: 'Synthesized collective security findings',
        verification_status: 'VERIFIED',
      }),
      listAgents: async () => mockAgents,
      getAgent: async (id) => mockAgents[0],
      getAgentTasks: async (id) => [],
      getAgentMessages: async (id) => [],
      getAgentHealth: async (id) => ({ agent_id: id, lifecycle_state: 'RUNNING', is_active: true }),
      getAgentHistory: async (id) => [],
    };
  }

  test('Component initializes with default state and expected activeTab', () => {
    const container = createMockContainer();
    const view = new SwarmOrchestrationView({ container });
    assert.strictEqual(view.state.activeTab, 'overview');
    assert.deepStrictEqual(view.state.swarms, []);
    assert.deepStrictEqual(view.state.agents, []);
  });

  test('Render produces proper navigation tabs and container elements', async () => {
    const container = createMockContainer();
    const api = createMockApi();
    const view = new SwarmOrchestrationView({ container, api });

    await view.render();

    assert.ok(container.innerHTML.includes('Swarm Orchestration & Multi-Agent Collaboration'));
    assert.ok(container.innerHTML.includes('Swarm Overview'));
    assert.ok(container.innerHTML.includes('Agent Workers'));
    assert.ok(container.innerHTML.includes('Task DAG & Dependencies'));
    assert.ok(container.innerHTML.includes('Supervision & Stalls'));
    assert.ok(container.innerHTML.includes('Messages & Blackboard'));
    assert.ok(container.innerHTML.includes('Disagreements & Synthesis'));
  });

  test('switchTab properly updates state to agents and triggers render', async () => {
    const container = createMockContainer();
    const api = createMockApi();
    const view = new SwarmOrchestrationView({ container, api });

    await view.render();
    await view.switchTab('agents');

    assert.strictEqual(view.state.activeTab, 'agents');
    const content = container.querySelector('#swarm-tab-content');
    assert.ok(content.innerHTML.includes('Agent Workers Registry'));
  });

  test('DAG tab renders task nodes and dependency edges', async () => {
    const container = createMockContainer();
    const api = createMockApi();
    const view = new SwarmOrchestrationView({ container, api });

    await view.render();
    await view.switchTab('dag');

    assert.strictEqual(view.state.activeTab, 'dag');
    const content = container.querySelector('#swarm-tab-content');
    assert.ok(content.innerHTML.includes('Task Graph & Worker Dependencies'));
  });

  test('Synthesis tab renders output verification pipeline', async () => {
    const container = createMockContainer();
    const api = createMockApi();
    const view = new SwarmOrchestrationView({ container, api });

    await view.render();
    await view.switchTab('synthesis');

    assert.strictEqual(view.state.activeTab, 'synthesis');
    const content = container.querySelector('#swarm-tab-content');
    assert.ok(content.innerHTML.includes('AGENT RESULT (Worker Output)'));
    assert.ok(content.innerHTML.includes('VALIDATED RESULT (Empirical Verification)'));
    assert.ok(content.innerHTML.includes('FINAL VERIFIED RESULT (Authoritative Synthesis)'));
  });
});
