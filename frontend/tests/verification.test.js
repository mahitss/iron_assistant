/**
 * Unit tests for Kairo Truth, Verification & Self-Correction (Task 42)
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { endpoints } from '../lib/api/endpoints.js';
import { VerificationView } from '../components/verification/verificationView.js';

describe('Truth, Verification & Self-Correction Engine Endpoints (Task 42)', () => {
  test('Endpoints exposes all verification methods', () => {
    assert.strictEqual(typeof endpoints.createVerificationClaim, 'function');
    assert.strictEqual(typeof endpoints.listVerificationClaims, 'function');
    assert.strictEqual(typeof endpoints.getVerificationClaim, 'function');
    assert.strictEqual(typeof endpoints.registerVerificationEvidence, 'function');
    assert.strictEqual(typeof endpoints.getVerificationEvidence, 'function');
    assert.strictEqual(typeof endpoints.verifyClaimContract, 'function');
    assert.strictEqual(typeof endpoints.triangulateClaim, 'function');
    assert.strictEqual(typeof endpoints.getClaimConfidence, 'function');
    assert.strictEqual(typeof endpoints.getClaimContradictions, 'function');
    assert.strictEqual(typeof endpoints.submitSelfCorrection, 'function');
    assert.strictEqual(typeof endpoints.validateCitation, 'function');
    assert.strictEqual(typeof endpoints.evaluateInvariants, 'function');
    assert.strictEqual(typeof endpoints.getVerificationStats, 'function');
  });

  test('VerificationView initializes with default tabs and KPI containers', () => {
    const mockContainer = {
      innerHTML: '',
      querySelector: () => null,
      querySelectorAll: () => [],
    };

    const view = new VerificationView(mockContainer);
    assert.strictEqual(view.activeTab, 'claims');
    assert.strictEqual(view.isLoading, false);
    assert.deepStrictEqual(view.claims, []);
    assert.deepStrictEqual(view.corrections, []);
  });

  test('VerificationView status badge helper maps truth statuses accurately', () => {
    const mockContainer = {
      innerHTML: '',
      querySelector: () => null,
      querySelectorAll: () => [],
    };

    const view = new VerificationView(mockContainer);
    assert.match(view.getStatusBadge('VERIFIED'), /badge-success/);
    assert.match(view.getStatusBadge('SUPPORTED'), /badge-info/);
    assert.match(view.getStatusBadge('CONTRADICTED'), /badge-danger/);
    assert.match(view.getStatusBadge('STALE'), /badge-warning/);
    assert.match(view.getStatusBadge('UNVERIFIED'), /badge-secondary/);
  });
});
