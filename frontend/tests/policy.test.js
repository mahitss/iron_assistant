import test from 'node:test';
import assert from 'node:assert/strict';
import { endpoints } from '../lib/api/endpoints.js';
import { SecurityView } from '../components/security/securityView.js';

test('Frontend Governance & Policy Engine Tests (Task 36)', async (t) => {
  await t.test('verifies policy endpoint methods exist on endpoints object', () => {
    assert.strictEqual(typeof endpoints.evaluatePolicy, 'function');
    assert.strictEqual(typeof endpoints.simulatePolicy, 'function');
    assert.strictEqual(typeof endpoints.getPolicyDecision, 'function');
    assert.strictEqual(typeof endpoints.getPolicyStatus, 'function');
    assert.strictEqual(typeof endpoints.listPolicies, 'function');
    assert.strictEqual(typeof endpoints.createPolicy, 'function');
    assert.strictEqual(typeof endpoints.updatePolicy, 'function');
    assert.strictEqual(typeof endpoints.activatePolicy, 'function');
    assert.strictEqual(typeof endpoints.disablePolicy, 'function');
    assert.strictEqual(typeof endpoints.rollbackPolicy, 'function');
    assert.strictEqual(typeof endpoints.setChangeFreeze, 'function');
    assert.strictEqual(typeof endpoints.toggleSafeMode, 'function');
  });

  await t.test('renders SecurityView with Governance & Policy Engine card', () => {
    const view = new SecurityView({
      policyStatus: {
        total_policies: 10,
        active_policies: 8,
        shadow_policies: 2,
        system_policies: 5,
        emergency_stop_active: false,
        safe_mode_active: false,
        change_freeze_environments: ['staging'],
      }
    });

    const html = view.render();
    assert.match(html, /GOVERNANCE &amp; POLICY DECISION ENGINE/);
    assert.match(html, /Active Policies/);
    assert.match(html, /Policy Simulation Sandbox/);
    assert.match(html, /id="policy-active-count"/);
  });
});
