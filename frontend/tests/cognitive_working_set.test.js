/**
 * Unit tests for Kairo Task 110:
 * Autonomous Cognitive Working Set, Context Assembly, Relevance Packing & Context Lifecycle Engine.
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { workingSetApi } from '../lib/api/endpoints.js';
import { CognitiveWorkingSetView } from '../components/context/cognitiveWorkingSetView.js';

describe('Cognitive Working Set API Endpoints (Task 110)', () => {
  test('workingSetApi exposes all required endpoints', () => {
    assert.strictEqual(typeof workingSetApi.assembleContext, 'function');
    assert.strictEqual(typeof workingSetApi.listWorkingSets, 'function');
    assert.strictEqual(typeof workingSetApi.getWorkingSet, 'function');
    assert.strictEqual(typeof workingSetApi.getWorkingSetItems, 'function');
    assert.strictEqual(typeof workingSetApi.getWorkingSetProvenance, 'function');
    assert.strictEqual(typeof workingSetApi.getWorkingSetConflicts, 'function');
    assert.strictEqual(typeof workingSetApi.getWorkingSetGaps, 'function');
    assert.strictEqual(typeof workingSetApi.getWorkingSetSnapshot, 'function');
    assert.strictEqual(typeof workingSetApi.refreshWorkingSet, 'function');
    assert.strictEqual(typeof workingSetApi.invalidateWorkingSet, 'function');
    assert.strictEqual(typeof workingSetApi.pinItem, 'function');
    assert.strictEqual(typeof workingSetApi.unpinItem, 'function');
    assert.strictEqual(typeof workingSetApi.submitFeedback, 'function');
    assert.strictEqual(typeof workingSetApi.getQuality, 'function');
    assert.strictEqual(typeof workingSetApi.getTimeline, 'function');
  });
});

describe('CognitiveWorkingSetView Component (Task 110)', () => {
  test('initializes with default items tab and null selection', () => {
    const view = new CognitiveWorkingSetView();
    assert.strictEqual(view.activeTab, 'items');
    assert.strictEqual(view.selectedSection, 'ALL');
    assert.deepStrictEqual(view.workingSets, []);
    assert.strictEqual(view.activeWorkingSet, null);
    assert.strictEqual(view.selectedItem, null);
  });

  test('generates complete HTML with header, badges, and tabs when populated', () => {
    const view = new CognitiveWorkingSetView();
    view.activeWorkingSet = {
      working_set_id: 'ws_test_01',
      version: 1,
      tenant_id: 'default',
      user_scope: 'default_user',
      operation_type: 'DELIBERATION',
      objective: 'Optimize database indexes and cache invalidation policies',
      lifecycle: 'READY',
      lease_state: 'VALID',
      quality_score: 0.94,
      total_tokens: 3500,
      item_count: 5,
      has_untrusted_content: false,
      conflicts_count: 1,
      gaps_count: 0,
      sections: {
        SYSTEM_STATE: {
          section_type: 'SYSTEM_STATE',
          title: 'System State',
          item_count: 2,
          total_tokens: 1200,
          is_empty: false,
          items: [
            {
              item_id: 'item_1',
              version: 1,
              section: 'SYSTEM_STATE',
              title: 'PostgreSQL Buffer Cache',
              content: 'Cache hit ratio 98.4%',
              inclusion: 'REQUIRED',
              relevance_score: 0.92,
              relevance_components: { task_alignment: 0.9 },
              freshness_classification: 'FRESH',
              provenance_source: 'system_state',
              trust_label: 'OBSERVED',
              compression_level: 'NONE',
              token_estimate: 240,
              is_pinned: true,
              is_untrusted: false,
            },
          ],
        },
      },
      request_id: 'req_1',
      trace_id: 'trace_1',
      created_at: new Date().toISOString(),
    };
    view.workingSets = [view.activeWorkingSet];

    const html = view._renderHtml();
    assert.match(html, /Cognitive Working Set & Context Assembly/);
    assert.match(html, /ws_test_01/);
    assert.match(html, /READY/);
    assert.match(html, /PostgreSQL Buffer Cache/);
    assert.match(html, /📌 PINNED/);
  });

  test('correctly maps lifecycle and freshness badge CSS classes', () => {
    const view = new CognitiveWorkingSetView();
    assert.strictEqual(view._getLifecycleBadgeClass('READY'), 'success');
    assert.strictEqual(view._getLifecycleBadgeClass('INVALIDATED'), 'danger');
    assert.strictEqual(view._getFreshnessBadgeClass('FRESH'), 'success');
    assert.strictEqual(view._getFreshnessBadgeClass('STALE'), 'danger');
  });
});
