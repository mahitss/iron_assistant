/**
 * Unit tests for Kairo Autonomous Reasoning & Deliberation Engine (Task 71).
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { endpoints, reasoningApi, reasoningCenterApi } from '../lib/api/endpoints.js';
import { ReasoningCenterView } from '../components/reasoning/reasoningCenterView.js';

describe('Autonomous Reasoning & Deliberation Endpoints (Task 71)', () => {
  test('Endpoints exposes all reasoning and deliberation methods', () => {
    assert.strictEqual(typeof endpoints.startReasoning, 'function');
    assert.strictEqual(typeof endpoints.listReasoningSessions, 'function');
    assert.strictEqual(typeof endpoints.getReasoningSession, 'function');
    assert.strictEqual(typeof endpoints.getReasoningHypotheses, 'function');
    assert.strictEqual(typeof endpoints.getReasoningEvidence, 'function');
    assert.strictEqual(typeof endpoints.addReasoningEvidence, 'function');
    assert.strictEqual(typeof endpoints.getReasoningAssumptions, 'function');
    assert.strictEqual(typeof endpoints.invalidateReasoningAssumption, 'function');
    assert.strictEqual(typeof endpoints.getReasoningConclusion, 'function');
    assert.strictEqual(typeof endpoints.getReasoningExplanation, 'function');
    assert.strictEqual(typeof endpoints.getReasoningTrace, 'function');
    assert.strictEqual(typeof endpoints.getReasoningGraph, 'function');
    assert.strictEqual(typeof endpoints.getReasoningQuality, 'function');
    assert.strictEqual(typeof endpoints.replayReasoning, 'function');
    assert.strictEqual(typeof endpoints.verifyReasoningConclusion, 'function');
    assert.strictEqual(typeof endpoints.getReasoningHealth, 'function');
  });

  test('reasoningApi and reasoningCenterApi wrappers expose mapped methods', () => {
    assert.strictEqual(typeof reasoningApi.start, 'function');
    assert.strictEqual(typeof reasoningApi.listSessions, 'function');
    assert.strictEqual(typeof reasoningApi.getSession, 'function');
    assert.strictEqual(typeof reasoningApi.getHypotheses, 'function');
    assert.strictEqual(typeof reasoningApi.getEvidence, 'function');
    assert.strictEqual(typeof reasoningApi.addEvidence, 'function');
    assert.strictEqual(typeof reasoningApi.getAssumptions, 'function');
    assert.strictEqual(typeof reasoningApi.invalidateAssumption, 'function');
    assert.strictEqual(typeof reasoningApi.getConclusion, 'function');
    assert.strictEqual(typeof reasoningApi.getExplanation, 'function');
    assert.strictEqual(typeof reasoningApi.getTrace, 'function');
    assert.strictEqual(typeof reasoningApi.getGraph, 'function');
    assert.strictEqual(typeof reasoningApi.getQuality, 'function');
    assert.strictEqual(typeof reasoningApi.replay, 'function');
    assert.strictEqual(typeof reasoningApi.verify, 'function');
    assert.strictEqual(typeof reasoningApi.getHealth, 'function');

    assert.strictEqual(reasoningCenterApi, reasoningApi);
  });
});

describe('ReasoningCenterView Component (Task 71)', () => {
  test('initializes with active tab and empty initial collections', () => {
    const view = new ReasoningCenterView({ tenantId: 'tenant_alpha', workspaceId: 'ws_alpha' });
    assert.strictEqual(view.activeTab, 'active');
    assert.strictEqual(view.tenantId, 'tenant_alpha');
    assert.strictEqual(view.workspaceId, 'ws_alpha');
    assert.strictEqual(Array.isArray(view.sessions), true);
    assert.strictEqual(view.currentSession, null);
  });

  test('setTab updates activeTab correctly', () => {
    const view = new ReasoningCenterView();
    view.setTab('hypotheses');
    assert.strictEqual(view.activeTab, 'hypotheses');
    view.setTab('assumptions');
    assert.strictEqual(view.activeTab, 'assumptions');
    view.setTab('why');
    assert.strictEqual(view.activeTab, 'why');
  });

  test('renders container with tab buttons and empty state safely', () => {
    // Mock minimal DOM container
    const mockContainer = {
      innerHTML: '',
      querySelectorAll: () => [],
      querySelector: () => null,
    };
    const view = new ReasoningCenterView({ container: mockContainer });
    view.render();
    assert.ok(mockContainer.innerHTML.includes('reasoning-center-view'));
    assert.ok(mockContainer.innerHTML.includes('Active Reasoning'));
    assert.ok(mockContainer.innerHTML.includes('Hypotheses'));
    assert.ok(mockContainer.innerHTML.includes('Evidence'));
    assert.ok(mockContainer.innerHTML.includes('Assumptions'));
    assert.ok(mockContainer.innerHTML.includes('Why? (Safe Explanation)'));
  });
});
