/**
 * Unit tests for Kairo Autonomous Attention & Cognitive Resource Allocation Engine (Task 70).
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { endpoints, attentionApi, cognitiveResourceApi, attentionCenterApi } from '../lib/api/endpoints.js';
import { AttentionCenterView } from '../components/attention/attentionCenterView.js';

describe('Autonomous Attention Engine Endpoints (Task 70)', () => {
  test('Endpoints exposes all attention and cognitive resource methods', () => {
    assert.strictEqual(typeof endpoints.evaluateAttentionCandidate, 'function');
    assert.strictEqual(typeof endpoints.getCurrentAttentionFocus, 'function');
    assert.strictEqual(typeof endpoints.getAttentionQueue, 'function');
    assert.strictEqual(typeof endpoints.getAttentionSnapshot, 'function');
    assert.strictEqual(typeof endpoints.getAttentionHealth, 'function');
    assert.strictEqual(typeof endpoints.getAttentionMetrics, 'function');
    assert.strictEqual(typeof endpoints.getAttentionCandidate, 'function');
    assert.strictEqual(typeof endpoints.focusAttentionCandidate, 'function');
    assert.strictEqual(typeof endpoints.pauseAttentionCandidate, 'function');
    assert.strictEqual(typeof endpoints.resumeAttentionCandidate, 'function');
    assert.strictEqual(typeof endpoints.deferAttentionCandidate, 'function');
    assert.strictEqual(typeof endpoints.delegateAttentionCandidate, 'function');
    assert.strictEqual(typeof endpoints.dismissAttentionCandidate, 'function');
    assert.strictEqual(typeof endpoints.escalateAttentionCandidate, 'function');
    assert.strictEqual(typeof endpoints.deescalateAttentionCandidate, 'function');
    assert.strictEqual(typeof endpoints.getAttentionExplanation, 'function');
    assert.strictEqual(typeof endpoints.getAttentionHistory, 'function');
  });

  test('attentionApi and cognitiveResourceApi wrappers expose mapped methods', () => {
    assert.strictEqual(typeof attentionApi.evaluate, 'function');
    assert.strictEqual(typeof attentionApi.getCurrent, 'function');
    assert.strictEqual(typeof attentionApi.getQueue, 'function');
    assert.strictEqual(typeof attentionApi.getSnapshot, 'function');
    assert.strictEqual(typeof attentionApi.getHealth, 'function');
    assert.strictEqual(typeof attentionApi.getMetrics, 'function');
    assert.strictEqual(typeof attentionApi.getCandidate, 'function');
    assert.strictEqual(typeof attentionApi.focus, 'function');
    assert.strictEqual(typeof attentionApi.pause, 'function');
    assert.strictEqual(typeof attentionApi.resume, 'function');
    assert.strictEqual(typeof attentionApi.defer, 'function');
    assert.strictEqual(typeof attentionApi.delegate, 'function');
    assert.strictEqual(typeof attentionApi.dismiss, 'function');
    assert.strictEqual(typeof attentionApi.escalate, 'function');
    assert.strictEqual(typeof attentionApi.deescalate, 'function');
    assert.strictEqual(typeof attentionApi.getExplanation, 'function');
    assert.strictEqual(typeof attentionApi.getHistory, 'function');

    assert.strictEqual(typeof cognitiveResourceApi.getBudget, 'function');
    assert.strictEqual(typeof cognitiveResourceApi.getHealth, 'function');

    assert.strictEqual(attentionCenterApi, attentionApi);
  });
});

describe('AttentionCenterView Component (Task 70)', () => {
  test('initializes with current_focus tab and empty collections', () => {
    const view = new AttentionCenterView({ tenantId: 'tenant_alpha' });
    assert.strictEqual(view.activeTab, 'current_focus');
    assert.strictEqual(view.tenantId, 'tenant_alpha');
    assert.strictEqual(view.currentFocus, null);
    assert.deepStrictEqual(view.queue, []);
  });

  test('renders empty focus state gracefully', () => {
    const view = new AttentionCenterView({ tenantId: 'test_tenant' });
    const html = view._renderHtml();
    assert.ok(html.includes('Kairo Attention Center'));
    assert.ok(html.includes('No Active Focus'));
    assert.ok(html.includes('Mode: NORMAL_MODE'));
  });

  test('renders active focus card with factor badges and explanation', () => {
    const view = new AttentionCenterView({ tenantId: 'test_tenant' });
    view.currentFocus = {
      attention_id: 'attn-12345',
      title: 'Production Database Latency Spike',
      description: 'Query response times exceeding SLA in us-east-1.',
      importance: 0.95,
      urgency: 0.90,
      risk: 0.85,
      novelty: 0.75,
      attention_score: 0.892,
      threshold: 'CRITICAL',
      current_state: 'ATTENDING',
      estimated_effort: 2.5,
      estimated_duration_sec: 600,
      required_capabilities: ['database', 'incident_triage'],
      reason: 'Critical SLA breach requiring immediate mitigation.',
    };
    view.selectedExplanation = {
      focus_justification: 'Critical urgency and high risk in production environment.',
    };

    const html = view._renderHtml();
    assert.ok(html.includes('Production Database Latency Spike'));
    assert.ok(html.includes('ATTENDING'));
    assert.ok(html.includes('Score: 0.892 (CRITICAL)'));
    assert.ok(html.includes('Why is Kairo focusing on this?'));
    assert.ok(html.includes('Critical urgency and high risk in production environment.'));
    assert.ok(html.includes('Estimated Effort: 2.5'));
  });

  test('renders priority queue items and threshold tiers', () => {
    const view = new AttentionCenterView({ tenantId: 'test_tenant' });
    view.queue = [
      {
        attention_id: 'attn-q1',
        title: 'Security Vulnerability Scan',
        attention_score: 0.78,
        threshold: 'HIGH',
        importance: 0.8,
        urgency: 0.6,
        reason: 'Daily scheduled dependency scan.',
      },
      {
        attention_id: 'attn-q2',
        title: 'Minor UI Alignment Fix',
        attention_score: 0.45,
        threshold: 'NORMAL',
        importance: 0.4,
        urgency: 0.3,
        reason: 'Cosmetic tweak.',
      },
    ];
    view.setTab('queue');

    const html = view._renderHtml();
    assert.ok(html.includes('Security Vulnerability Scan'));
    assert.ok(html.includes('HIGH'));
    assert.ok(html.includes('Minor UI Alignment Fix'));
    assert.ok(html.includes('NORMAL'));
  });

  test('renders cognitive resource utilization dashboard', () => {
    const view = new AttentionCenterView({ tenantId: 'test_tenant' });
    view.metrics = {
      mode: 'NORMAL_MODE',
      resource_budget: {
        reasoning_capacity_pct: 75.0,
        active_tool_calls: 3,
        max_tool_calls: 10,
        active_agent_slots: 2,
        max_agent_slots: 5,
        execution_slots_used: 1,
        max_execution_slots: 4,
        context_tokens_used: 32000,
        context_token_budget: 128000,
      },
    };
    view.setTab('resources');

    const html = view._renderHtml();
    assert.ok(html.includes('Reasoning Capacity'));
    assert.ok(html.includes('75.0%'));
    assert.ok(html.includes('Active Tool Quota'));
    assert.ok(html.includes('3 / 10'));
    assert.ok(html.includes('Agent Slots'));
    assert.ok(html.includes('2 / 5'));
    assert.ok(html.includes('Context Tokens'));
    assert.ok(html.includes('32,000'));
  });
});
