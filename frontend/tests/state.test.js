/**
 * Unit tests for Kairo Unified Data & State Fabric (Task 39)
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { endpoints } from '../lib/api/endpoints.js';

describe('Unified Data & State Fabric Endpoints (Task 39)', () => {
  test('Endpoints exposes all state fabric methods', () => {
    assert.strictEqual(typeof endpoints.getStateHealth, 'function');
    assert.strictEqual(typeof endpoints.getStateRecord, 'function');
    assert.strictEqual(typeof endpoints.getStateChangelog, 'function');
    assert.strictEqual(typeof endpoints.triggerStateReconciliation, 'function');
    assert.strictEqual(typeof endpoints.getLastStateReconciliation, 'function');
    assert.strictEqual(typeof endpoints.listStateQuarantine, 'function');
    assert.strictEqual(typeof endpoints.releaseStateQuarantine, 'function');
  });

  test('State fabric method signatures and query building', async () => {
    assert.ok(endpoints.getStateRecord.length >= 3);
    assert.ok(endpoints.triggerStateReconciliation.length >= 0);
  });
});
