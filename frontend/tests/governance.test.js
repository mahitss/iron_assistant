/**
 * Unit tests for Kairo Autonomous Governance, Constitutional Reasoning,
 * Policy Intelligence & Authority Management Engine (Task 78).
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { governanceApi } from '../lib/api/endpoints.js';
import { GovernanceCenterView } from '../components/governance/governanceCenterView.js';

describe('Autonomous Governance & Constitutional Reasoning API (Task 78)', () => {
  test('governanceApi exposes all authoritative endpoints', () => {
    assert.strictEqual(typeof governanceApi.submitReview, 'function');
    assert.strictEqual(typeof governanceApi.getConstitution, 'function');
    assert.strictEqual(typeof governanceApi.updatePrinciple, 'function');
    assert.strictEqual(typeof governanceApi.issueAuthorityGrant, 'function');
    assert.strictEqual(typeof governanceApi.getAuthority, 'function');
    assert.strictEqual(typeof governanceApi.revokeAuthority, 'function');
    assert.strictEqual(typeof governanceApi.listPendingHumanReviews, 'function');
    assert.strictEqual(typeof governanceApi.getReview, 'function');
    assert.strictEqual(typeof governanceApi.resolveHumanReview, 'function');
    assert.strictEqual(typeof governanceApi.getDashboard, 'function');
    assert.strictEqual(typeof governanceApi.getEscalations, 'function');
  });
});

describe('GovernanceCenterView Component (Task 78)', () => {
  test('initializes with overview subtab and empty collections', () => {
    const mockContainer = { innerHTML: '', querySelector: () => null, querySelectorAll: () => [] };
    const view = new GovernanceCenterView(mockContainer);
    assert.strictEqual(view.activeSubTab, 'overview');
    assert.strictEqual(view.humanQueueData.length, 0);
    assert.strictEqual(view.escalationsData.length, 0);
    assert.strictEqual(view.dashboardData, null);
    assert.strictEqual(view.constitutionData, null);
  });

  test('switches subtabs correctly across all 7 views', () => {
    const mockContainer = { innerHTML: '', querySelector: () => null, querySelectorAll: () => [] };
    const view = new GovernanceCenterView(mockContainer);

    const tabs = ['overview', 'constitution', 'authority', 'human_queue', 'decisions', 'conflicts', 'escalations'];
    tabs.forEach(tab => {
      view.setSubTab(tab);
      assert.strictEqual(view.activeSubTab, tab);
    });
  });

  test('formatStateBadge generates distinct badges for all 8 lifecycle states', () => {
    const mockContainer = { innerHTML: '', querySelector: () => null, querySelectorAll: () => [] };
    const view = new GovernanceCenterView(mockContainer);

    const states = ['PENDING_REVIEW', 'APPROVED', 'DENIED', 'REQUIRES_APPROVAL', 'REQUIRES_HUMAN', 'EXECUTABLE', 'EXPIRED', 'ABORTED'];
    states.forEach(s => {
      const badge = view.formatStateBadge(s);
      assert.ok(badge.includes(s));
    });
  });

  test('formatStrictnessBadge accurately maps MANDATORY, STRICT, and ADVISORY', () => {
    const mockContainer = { innerHTML: '', querySelector: () => null, querySelectorAll: () => [] };
    const view = new GovernanceCenterView(mockContainer);

    const strictnesses = ['MANDATORY', 'STRICT', 'ADVISORY'];
    strictnesses.forEach(st => {
      const badge = view.formatStrictnessBadge(st);
      assert.ok(badge.includes(st));
    });
  });

  test('formatTierBadge styles all 6 hierarchy tiers', () => {
    const mockContainer = { innerHTML: '', querySelector: () => null, querySelectorAll: () => [] };
    const view = new GovernanceCenterView(mockContainer);

    const tiers = ['SYSTEM', 'SECURITY', 'TENANT', 'PROJECT', 'WORKFLOW', 'TASK'];
    tiers.forEach(t => {
      const badge = view.formatTierBadge(t);
      assert.ok(badge.includes(t));
    });
  });

  test('render creates full dashboard structure with safety invariant banner', () => {
    let capturedHtml = '';
    const mockContainer = {
      set innerHTML(val) { capturedHtml = val; },
      get innerHTML() { return capturedHtml; },
      querySelector: () => null,
      querySelectorAll: () => [],
    };

    const view = new GovernanceCenterView(mockContainer);
    view.render();

    assert.ok(capturedHtml.includes('Autonomous Governance & Constitutional Intelligence Engine'));
    assert.ok(capturedHtml.includes('TASK 78'));
    assert.ok(capturedHtml.includes('Core Invariant:'));
    assert.ok(capturedHtml.includes('Autonomous Self-Approval Strictly Prohibited'));
    assert.ok(capturedHtml.includes('Policy Overview'));
    assert.ok(capturedHtml.includes('Constitution Matrix'));
    assert.ok(capturedHtml.includes('Human Review Queue'));
  });
});
