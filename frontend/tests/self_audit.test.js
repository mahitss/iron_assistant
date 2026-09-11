/**
 * Unit tests for Kairo Metacognitive Control & Autonomous Self-Audit Engine (Task 67).
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { endpoints, selfAuditApi, metacognitiveControlApi } from '../lib/api/endpoints.js';
import { SelfAuditView } from '../components/self_audit/selfAuditView.js';

describe('Metacognitive Control & Autonomous Self-Audit Endpoints (Task 67)', () => {
  test('Endpoints exposes all self-audit methods', () => {
    assert.strictEqual(typeof endpoints.createSelfAudit, 'function');
    assert.strictEqual(typeof endpoints.runSelfAuditCycle, 'function');
    assert.strictEqual(typeof endpoints.listSelfAudits, 'function');
    assert.strictEqual(typeof endpoints.getSelfAuditOverview, 'function');
    assert.strictEqual(typeof endpoints.getSelfAudit, 'function');
    assert.strictEqual(typeof endpoints.getSelfAuditFindings, 'function');
    assert.strictEqual(typeof endpoints.getSelfAuditEvidence, 'function');
    assert.strictEqual(typeof endpoints.getSelfAuditHistory, 'function');
    assert.strictEqual(typeof endpoints.getSelfAuditDrift, 'function');
    assert.strictEqual(typeof endpoints.getSelfAuditCalibration, 'function');
    assert.strictEqual(typeof endpoints.getSelfAuditErrors, 'function');
    assert.strictEqual(typeof endpoints.reassessSelfAudit, 'function');
    assert.strictEqual(typeof endpoints.listSelfAuditBeliefs, 'function');
    assert.strictEqual(typeof endpoints.registerSelfAuditBelief, 'function');
    assert.strictEqual(typeof endpoints.reviseSelfAuditBelief, 'function');
    assert.strictEqual(typeof endpoints.resolveSelfAuditFinding, 'function');
    assert.strictEqual(typeof endpoints.getSelfAuditHealth, 'function');
  });

  test('selfAuditApi and metacognitiveControlApi wrappers expose mapped methods', () => {
    assert.strictEqual(typeof selfAuditApi.createAudit, 'function');
    assert.strictEqual(typeof selfAuditApi.runCycle, 'function');
    assert.strictEqual(typeof selfAuditApi.listAudits, 'function');
    assert.strictEqual(typeof selfAuditApi.getOverview, 'function');
    assert.strictEqual(typeof selfAuditApi.getAudit, 'function');
    assert.strictEqual(typeof selfAuditApi.getFindings, 'function');
    assert.strictEqual(typeof selfAuditApi.getEvidence, 'function');
    assert.strictEqual(typeof selfAuditApi.getHistory, 'function');
    assert.strictEqual(typeof selfAuditApi.getDrift, 'function');
    assert.strictEqual(typeof selfAuditApi.getCalibration, 'function');
    assert.strictEqual(typeof selfAuditApi.getErrors, 'function');
    assert.strictEqual(typeof selfAuditApi.reassess, 'function');
    assert.strictEqual(typeof selfAuditApi.listBeliefs, 'function');
    assert.strictEqual(typeof selfAuditApi.registerBelief, 'function');
    assert.strictEqual(typeof selfAuditApi.reviseBelief, 'function');
    assert.strictEqual(typeof selfAuditApi.resolveFinding, 'function');
    assert.strictEqual(typeof selfAuditApi.getHealth, 'function');

    // Alias equality
    assert.strictEqual(metacognitiveControlApi, selfAuditApi);
  });
});

describe('SelfAuditView Component (Task 67)', () => {
  test('initializes with active_audits tab and default state', () => {
    const view = new SelfAuditView(null);
    assert.strictEqual(view.activeTab, 'active_audits');
    assert.deepStrictEqual(view.audits, []);
    assert.strictEqual(view.selectedAudit, null);
    assert.strictEqual(view.overview, null);
    assert.deepStrictEqual(view.beliefs, []);
    assert.deepStrictEqual(view.driftData, []);
    assert.strictEqual(view.isLoading, false);
    assert.strictEqual(view.error, null);
  });

  test('setTab updates active tab appropriately', () => {
    const view = new SelfAuditView(null);
    view.setTab('calibration_accuracy');
    assert.strictEqual(view.activeTab, 'calibration_accuracy');
    view.setTab('behavior_drift');
    assert.strictEqual(view.activeTab, 'behavior_drift');
    view.setTab('beliefs_revisions');
    assert.strictEqual(view.activeTab, 'beliefs_revisions');
  });

  test('selectAudit assigns object directly when provided', () => {
    const view = new SelfAuditView(null);
    const mockAudit = {
      audit_id: 'aud_test_123',
      subject: 'Verification audit',
      severity: 'INFO',
      depth: 'STANDARD',
      findings: [],
    };
    view.selectAudit(mockAudit);
    assert.strictEqual(view.selectedAudit, mockAudit);
  });
});
