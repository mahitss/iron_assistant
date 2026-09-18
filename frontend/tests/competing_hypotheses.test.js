/**
 * Frontend Unit & Component Tests for Task 115:
 * Kairo Autonomous Hypothesis Management, Competing Explanations, Falsification & Uncertainty Resolution Engine
 */

import test from 'node:test';
import assert from 'node:assert';
import { hypothesesApi } from '../lib/api/endpoints.js';
import { CompetingHypothesesView } from '../components/hypothesis/competingHypothesesView.js';

test('Competing Hypotheses API Endpoints (Task 115)', async (t) => {
  await t.test('hypothesesApi exposes all required Task 115 methods', () => {
    assert.strictEqual(typeof hypothesesApi.createSet, 'function');
    assert.strictEqual(typeof hypothesesApi.listSets, 'function');
    assert.strictEqual(typeof hypothesesApi.getSet, 'function');
    assert.strictEqual(typeof hypothesesApi.compareSet, 'function');
    assert.strictEqual(typeof hypothesesApi.getDiscriminators, 'function');
    assert.strictEqual(typeof hypothesesApi.getUncertainty, 'function');
    assert.strictEqual(typeof hypothesesApi.attachEvidence, 'function');
    assert.strictEqual(typeof hypothesesApi.splitHypothesis, 'function');
    assert.strictEqual(typeof hypothesesApi.mergeHypotheses, 'function');
    assert.strictEqual(typeof hypothesesApi.createHypothesis, 'function');
    assert.strictEqual(typeof hypothesesApi.listHypotheses, 'function');
    assert.strictEqual(typeof hypothesesApi.getHypothesis, 'function');
    assert.strictEqual(typeof hypothesesApi.getEvidence, 'function');
    assert.strictEqual(typeof hypothesesApi.getPredictions, 'function');
    assert.strictEqual(typeof hypothesesApi.getFalsification, 'function');
    assert.strictEqual(typeof hypothesesApi.getAlternatives, 'function');
    assert.strictEqual(typeof hypothesesApi.getConflicts, 'function');
    assert.strictEqual(typeof hypothesesApi.getHistory, 'function');
    assert.strictEqual(typeof hypothesesApi.getSnapshot, 'function');
    assert.strictEqual(typeof hypothesesApi.evaluate, 'function');
    assert.strictEqual(typeof hypothesesApi.verify, 'function');
    assert.strictEqual(typeof hypothesesApi.feedback, 'function');
  });
});

test('CompetingHypothesesView Component (Task 115)', async (t) => {
  await t.test('instantiates with default container ID', () => {
    const view = new CompetingHypothesesView('test-container');
    assert.strictEqual(view.containerId, 'test-container');
    assert.strictEqual(view.activeSetId, null);
    assert.deepStrictEqual(view.sets, []);
  });

  await t.test('returns appropriate status badges', () => {
    const view = new CompetingHypothesesView();
    const badgeSupported = view._getStatusBadge('SUPPORTED');
    assert.match(badgeSupported, /SUPPORTED/);
    assert.match(badgeSupported, /#34d399/);

    const badgeFalsified = view._getStatusBadge('FALSIFIED');
    assert.match(badgeFalsified, /FALSIFIED/);
    assert.match(badgeFalsified, /#fca5a5/);

    const badgeUnknown = view._getStatusBadge('UNKNOWN');
    assert.match(badgeUnknown, /UNKNOWN/);
    assert.match(badgeUnknown, /#94a3b8/);
  });
});
