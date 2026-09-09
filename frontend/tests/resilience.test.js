/**
 * Unit tests for Kairo Resilience, Fault-Tolerance & System Reliability (Task 37)
 */

import { test, describe, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { endpoints } from '../lib/api/endpoints.js';
import { SecurityView } from '../components/security/securityView.js';

describe('Resilience & Fault-Tolerance Endpoints (Task 37)', () => {
  test('Endpoints exposes all resilience methods', () => {
    assert.strictEqual(typeof endpoints.getResilienceHealth, 'function');
    assert.strictEqual(typeof endpoints.getResilienceDashboard, 'function');
    assert.strictEqual(typeof endpoints.listCircuitBreakers, 'function');
    assert.strictEqual(typeof endpoints.resetCircuitBreaker, 'function');
    assert.strictEqual(typeof endpoints.listQuarantinedTasks, 'function');
    assert.strictEqual(typeof endpoints.releaseQuarantinedTask, 'function');
    assert.strictEqual(typeof endpoints.recoverTask, 'function');
    assert.strictEqual(typeof endpoints.setReadOnlyDegradation, 'function');
  });

  test('SecurityView renders System Reliability Card with metrics and probes', () => {
    const mockStore = {
      getState: () => ({
        capabilities: { web_research: true, browser: false, developer_tools: true },
        emergencyStop: { is_stopped: false },
        pendingApprovals: [],
      }),
    };

    const view = new SecurityView({ store: mockStore });
    view.resilienceData = {
      retry_success_rate: 0.985,
      recovery_success_rate: 1.0,
      active_leases: 2,
      quarantined_tasks_count: 0,
    };

    const html = view.render();
    assert.ok(html.includes('id="resilience-reliability-card"'));
    assert.ok(html.includes('SYSTEM RELIABILITY &amp; FAULT-TOLERANT RUNTIME'));
    assert.ok(html.includes('id="resilience-retry-rate"'));
    assert.ok(html.includes('98.5%'));
    assert.ok(html.includes('id="resilience-recovery-rate"'));
    assert.ok(html.includes('100.0%'));
    assert.ok(html.includes('id="resilience-active-leases"'));
    assert.ok(html.includes('Core Dependency Probes'));
    assert.ok(html.includes('PostgreSQL DB'));
    assert.ok(html.includes('Redis Broker'));
  });
});
