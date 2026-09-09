/**
 * Unit tests for Kairo Multi-Agent Collaboration & Collective Intelligence Engine (Task 44)
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { endpoints } from '../lib/api/endpoints.js';
import { CollaborationView } from '../components/collaboration/collaborationView.js';

describe('Multi-Agent Collaboration Engine Endpoints & UI (Task 44)', () => {
  test('Endpoints exposes all collaboration and contract methods', () => {
    assert.strictEqual(typeof endpoints.createCollaborationSession, 'function');
    assert.strictEqual(typeof endpoints.getCollaborationSession, 'function');
    assert.strictEqual(typeof endpoints.registerCollaborationAgent, 'function');
    assert.strictEqual(typeof endpoints.listCollaborationAgents, 'function');
    assert.strictEqual(typeof endpoints.createAgentContract, 'function');
    assert.strictEqual(typeof endpoints.expandAgentContract, 'function');
    assert.strictEqual(typeof endpoints.getAgentContract, 'function');
    assert.strictEqual(typeof endpoints.delegateCollaborationSubtask, 'function');
    assert.strictEqual(typeof endpoints.sendAgentMessage, 'function');
    assert.strictEqual(typeof endpoints.getAgentMessages, 'function');
    assert.strictEqual(typeof endpoints.submitCollaborationEvidence, 'function');
    assert.strictEqual(typeof endpoints.listCollaborationEvidence, 'function');
    assert.strictEqual(typeof endpoints.createDisagreement, 'function');
    assert.strictEqual(typeof endpoints.resolveDisagreement, 'function');
    assert.strictEqual(typeof endpoints.checkConsensus, 'function');
    assert.strictEqual(typeof endpoints.synthesizeCollaborationFindings, 'function');
    assert.strictEqual(typeof endpoints.triggerEmergencyStop, 'function');
    assert.strictEqual(typeof endpoints.getCollaborationProvenance, 'function');
  });

  test('CollaborationView initializes with default state and containers', () => {
    const mockContainer = {
      innerHTML: '',
      querySelector: () => null,
      querySelectorAll: () => [],
    };

    const view = new CollaborationView(mockContainer);
    assert.strictEqual(view.activeTab, 'agents');
    assert.strictEqual(view.isLoading, false);
    assert.deepStrictEqual(view.agents, []);
    assert.deepStrictEqual(view.contracts, []);
    assert.deepStrictEqual(view.evidenceList, []);
    assert.deepStrictEqual(view.disagreements, []);
  });

  test('CollaborationView updateKPIs updates counts accurately', () => {
    let agentVal = '';
    let evVal = '';
    const mockContainer = {
      innerHTML: '',
      querySelector: (selector) => {
        if (selector === '#kpi-agents-count') return { set textContent(v) { agentVal = v; } };
        if (selector === '#kpi-evidence-count') return { set textContent(v) { evVal = v; } };
        return null;
      },
      querySelectorAll: () => [],
    };

    const view = new CollaborationView(mockContainer);
    view.agents = [{ agent_id: 'ag_1' }, { agent_id: 'ag_2' }];
    view.evidenceList = [{ evidence_id: 'ev_1' }];
    view.updateKPIs();

    assert.strictEqual(agentVal, '2');
    assert.strictEqual(evVal, '1');
  });
});
