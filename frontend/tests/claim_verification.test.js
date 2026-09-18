/**
 * Frontend Unit & Component Tests for Task 116:
 * Kairo Autonomous Claim Verification, Source Integrity & Evidence Provenance Engine
 */

import test from 'node:test';
import assert from 'node:assert';
import { verificationsApi } from '../lib/api/endpoints.js';
import { VerificationCenterView } from '../components/verification/verificationCenterView.js';

test('Claim Verification API Endpoints (Task 116)', async (t) => {
  await t.test('verificationsApi exposes all required Task 116 methods', () => {
    assert.strictEqual(typeof verificationsApi.create, 'function');
    assert.strictEqual(typeof verificationsApi.list, 'function');
    assert.strictEqual(typeof verificationsApi.get, 'function');
    assert.strictEqual(typeof verificationsApi.cancel, 'function');
    assert.strictEqual(typeof verificationsApi.revalidate, 'function');
    assert.strictEqual(typeof verificationsApi.getClaims, 'function');
    assert.strictEqual(typeof verificationsApi.getEvidence, 'function');
    assert.strictEqual(typeof verificationsApi.getProvenance, 'function');
    assert.strictEqual(typeof verificationsApi.getContradictions, 'function');
    assert.strictEqual(typeof verificationsApi.getGaps, 'function');
    assert.strictEqual(typeof verificationsApi.getTimeline, 'function');
    assert.strictEqual(typeof verificationsApi.getExplanation, 'function');
    assert.strictEqual(typeof verificationsApi.getClaimStatus, 'function');
    assert.strictEqual(typeof verificationsApi.getSource, 'function');
    assert.strictEqual(typeof verificationsApi.getSourceHistory, 'function');
    assert.strictEqual(typeof verificationsApi.getSourceRelationships, 'function');
    assert.strictEqual(typeof verificationsApi.getEvidenceLineage, 'function');
  });
});

test('VerificationCenterView Component (Task 116)', async (t) => {
  await t.test('instantiates with container ID and default tab', () => {
    const view = new VerificationCenterView('test-viewport');
    assert.strictEqual(view.containerId, 'test-viewport');
    assert.strictEqual(view.activeTab, 'inbox');
    assert.deepStrictEqual(view.cases, []);
    assert.strictEqual(view.selectedCaseId, null);
  });

  await t.test('renders appropriate status colors', () => {
    const view = new VerificationCenterView();
    const verifiedColor = view._getStatusColor('VERIFIED_UNDER_SCOPE');
    assert.strictEqual(verifiedColor.text, '#4ade80');

    const contradictedColor = view._getStatusColor('CONTRADICTED');
    assert.strictEqual(contradictedColor.text, '#f87171');

    const staleColor = view._getStatusColor('STALE');
    assert.strictEqual(staleColor.text, '#fb923c');

    const defaultColor = view._getStatusColor('UNKNOWN');
    assert.strictEqual(defaultColor.text, '#94a3b8');
  });

  await t.test('renders tab buttons with active styling', () => {
    const view = new VerificationCenterView();
    const inboxBtn = view._renderTabBtn('inbox', 'Inbox');
    assert.match(inboxBtn, /#7c3aed/); // Active color

    const detailBtn = view._renderTabBtn('detail', 'Detail');
    assert.match(detailBtn, /transparent/); // Inactive color
  });
});
