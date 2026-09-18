/**
 * Unit tests for Kairo Autonomous Attention, Cognitive Resource Allocation, Focus Management & Interruption Governance (Task 109).
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { attentionV2Api } from '../lib/api/endpoints.js';
import { AttentionV2View } from '../components/attention/attentionV2View.js';

describe('Autonomous Attention Engine V2 Endpoints (Task 109)', () => {
  test('attentionV2Api exposes all required Task 109 endpoints', () => {
    assert.strictEqual(typeof attentionV2Api.ingestCandidate, 'function');
    assert.strictEqual(typeof attentionV2Api.listCandidates, 'function');
    assert.strictEqual(typeof attentionV2Api.getCandidate, 'function');
    assert.strictEqual(typeof attentionV2Api.requestFocus, 'function');
    assert.strictEqual(typeof attentionV2Api.completeFocus, 'function');
    assert.strictEqual(typeof attentionV2Api.abortFocus, 'function');
    assert.strictEqual(typeof attentionV2Api.evaluateInterruption, 'function');
    assert.strictEqual(typeof attentionV2Api.createWatch, 'function');
    assert.strictEqual(typeof attentionV2Api.evaluateSignal, 'function');
    assert.strictEqual(typeof attentionV2Api.runFairnessSweep, 'function');
    assert.strictEqual(typeof attentionV2Api.getHealth, 'function');
    assert.strictEqual(typeof attentionV2Api.getSnapshot, 'function');
    assert.strictEqual(typeof attentionV2Api.submitFeedback, 'function');
  });
});

describe('AttentionV2View Component (Task 109)', () => {
  test('initializes with default candidates tab and empty collections', () => {
    const view = new AttentionV2View({ tenantId: 'test_tenant' });
    assert.strictEqual(view.activeTab, 'candidates');
    assert.strictEqual(view.tenantId, 'test_tenant');
    assert.deepStrictEqual(view.candidates, []);
    assert.strictEqual(view.activeFocus, null);
    assert.deepStrictEqual(view.stack, []);
  });

  test('generates complete HTML including header, health banner, and tabs', () => {
    const view = new AttentionV2View({ tenantId: 'test_tenant' });
    view.health = {
      health_status: 'HEALTHY',
      cognitive_fragmentation_score: 0.15,
      queued_candidates: 3,
      watching_candidates: 1,
      deferred_candidates: 0,
      churn_details: 'Churn: 0.1 switches/min',
    };
    view.candidates = [
      {
        candidate_id: 'cand_test_1',
        title: 'High Salience Alert',
        type: 'SECURITY',
        lifecycle: 'QUEUED',
        aging_boost: 0.05,
        is_adversarial_dampened: false,
        score: {
          composite_salience: 0.92,
          risk: 0.85,
        },
      },
    ];

    const html = view.render();
    assert.ok(html.includes('Attention & Focus Management Engine'));
    assert.ok(html.includes('Task 109'));
    assert.ok(html.includes('STATUS: HEALTHY'));
    assert.ok(html.includes('High Salience Alert'));
    assert.ok(html.includes('0.92'));
  });

  test('switches tabs properly and reflects active state', () => {
    const view = new AttentionV2View();
    view.setTab('watches');
    assert.strictEqual(view.activeTab, 'watches');

    const html = view.render();
    assert.ok(html.includes('Condition Watches'));
    assert.ok(html.includes('Zero-cost condition watches'));

    view.setTab('snapshot');
    assert.strictEqual(view.activeTab, 'snapshot');
    const snapHtml = view.render();
    assert.ok(snapHtml.includes('Point-in-Time Snapshot'));
  });

  test('renders active focus session card and interrupted stack correctly', () => {
    const view = new AttentionV2View();
    view.activeFocus = {
      session_id: 'sess_focus_99',
      candidate_id: 'cand_active_1',
      depth: 1,
      allow_interruption: true,
      primary_target: {
        target_id: 't_primary',
        name: 'Critical Vulnerability Triage',
      },
      resource_budget: {
        tokens_allocated: 4000,
        time_seconds_allocated: 120,
      },
      allocated_context_window_tokens: 8000,
    };
    view.stack = [
      {
        candidate_id: 'cand_bg_work',
        depth: 0,
        primary_target: { name: 'Background indexing' },
      },
    ];

    const html = view.render();
    assert.ok(html.includes('Critical Vulnerability Triage'));
    assert.ok(html.includes('sess_focus_99'));
    assert.ok(html.includes('4000 tok'));
    assert.ok(html.includes('Background indexing'));
    assert.ok(html.includes('Lvl 0'));
  });

  test('renders lifecycle badge classes correctly', () => {
    const view = new AttentionV2View();
    assert.ok(view._getLifecycleBadgeClass('FOCUSED').includes('emerald'));
    assert.ok(view._getLifecycleBadgeClass('QUEUED').includes('sky'));
    assert.ok(view._getLifecycleBadgeClass('INTERRUPTED').includes('amber'));
    assert.ok(view._getLifecycleBadgeClass('DEFERRED').includes('purple'));
  });
});
