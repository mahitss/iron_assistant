/**
 * Unit tests for Kairo Universal Context & Adaptive Personalization Engine (Task 69).
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { endpoints, universalContextApi, contextCenterApi } from '../lib/api/endpoints.js';
import { ContextCenterView } from '../components/context/contextCenterView.js';

describe('Universal Context & Adaptive Personalization Endpoints (Task 69)', () => {
  test('Endpoints exposes all universal context methods', () => {
    assert.strictEqual(typeof endpoints.buildUniversalContext, 'function');
    assert.strictEqual(typeof endpoints.previewUniversalContext, 'function');
    assert.strictEqual(typeof endpoints.getContextQuality, 'function');
    assert.strictEqual(typeof endpoints.getMissingContext, 'function');
    assert.strictEqual(typeof endpoints.getContextConflicts, 'function');
    assert.strictEqual(typeof endpoints.getUniversalContextHealth, 'function');
    assert.strictEqual(typeof endpoints.listAdaptivePreferences, 'function');
    assert.strictEqual(typeof endpoints.registerAdaptivePreference, 'function');
    assert.strictEqual(typeof endpoints.updateAdaptivePreference, 'function');
    assert.strictEqual(typeof endpoints.deleteAdaptivePreference, 'function');
    assert.strictEqual(typeof endpoints.listContextSnapshots, 'function');
    assert.strictEqual(typeof endpoints.getContextSnapshot, 'function');
    assert.strictEqual(typeof endpoints.replayContextSnapshot, 'function');
    assert.strictEqual(typeof endpoints.getContextPackage, 'function');
    assert.strictEqual(typeof endpoints.getContextExplanation, 'function');
    assert.strictEqual(typeof endpoints.getContextSources, 'function');
    assert.strictEqual(typeof endpoints.refreshContextPackage, 'function');
  });

  test('universalContextApi and contextCenterApi wrappers expose mapped methods', () => {
    assert.strictEqual(typeof universalContextApi.buildContext, 'function');
    assert.strictEqual(typeof universalContextApi.previewContext, 'function');
    assert.strictEqual(typeof universalContextApi.getQuality, 'function');
    assert.strictEqual(typeof universalContextApi.getMissing, 'function');
    assert.strictEqual(typeof universalContextApi.getConflicts, 'function');
    assert.strictEqual(typeof universalContextApi.getHealth, 'function');
    assert.strictEqual(typeof universalContextApi.listPreferences, 'function');
    assert.strictEqual(typeof universalContextApi.registerPreference, 'function');
    assert.strictEqual(typeof universalContextApi.updatePreference, 'function');
    assert.strictEqual(typeof universalContextApi.deletePreference, 'function');
    assert.strictEqual(typeof universalContextApi.listSnapshots, 'function');
    assert.strictEqual(typeof universalContextApi.getSnapshot, 'function');
    assert.strictEqual(typeof universalContextApi.replaySnapshot, 'function');
    assert.strictEqual(typeof universalContextApi.getContext, 'function');
    assert.strictEqual(typeof universalContextApi.getExplanation, 'function');
    assert.strictEqual(typeof universalContextApi.getSources, 'function');
    assert.strictEqual(typeof universalContextApi.refreshContext, 'function');

    assert.strictEqual(contextCenterApi, universalContextApi);
  });
});

describe('ContextCenterView Component (Task 69)', () => {
  test('initializes with current_context tab and default collections', () => {
    const view = new ContextCenterView({ tenantId: 'test_tenant' });
    assert.strictEqual(view.activeTab, 'current_context');
    assert.strictEqual(view.tenantId, 'test_tenant');
    assert.deepStrictEqual(view.missingContext, []);
    assert.deepStrictEqual(view.conflicts, []);
    assert.deepStrictEqual(view.preferences, []);
    assert.deepStrictEqual(view.snapshots, []);
  });

  test('renders base HTML structure and tabs', () => {
    const view = new ContextCenterView({ tenantId: 'test_tenant' });
    const html = view.render();
    assert.ok(html.includes('Universal Context &amp; Adaptive Personalization') || html.includes('Universal Context'));
    assert.ok(html.includes('Active Context'));
    assert.ok(html.includes('Context Quality'));
    assert.ok(html.includes('Why This Context?'));
    assert.ok(html.includes('Missing Context'));
    assert.ok(html.includes('Context Conflicts'));
    assert.ok(html.includes('Adaptive Personalization'));
    assert.ok(html.includes('Context History &amp; Snapshots') || html.includes('Context History'));
  });

  test('setTab updates active tab appropriately', () => {
    const view = new ContextCenterView({ tenantId: 'test_tenant' });
    view.setTab('conflicts');
    assert.strictEqual(view.activeTab, 'conflicts');
    const html = view.render();
    assert.ok(html.includes('Context Conflict Center'));
  });
});
