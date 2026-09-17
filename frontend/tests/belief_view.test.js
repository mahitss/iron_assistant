import test from 'node:test';
import assert from 'node:assert/strict';
import { BeliefView } from '../components/belief/beliefView.js';

test('BeliefView Frontend Component Tests (Task 107)', async (t) => {
  await t.test('initializes with default state and properties', () => {
    const view = new BeliefView({ container: null });
    assert.ok(view);
    assert.strictEqual(view.activeTab, 'dashboard');
    assert.strictEqual(view.dashboardData, null);
    assert.ok(Array.isArray(view.beliefs));
    assert.ok(Array.isArray(view.evidenceList));
    assert.ok(Array.isArray(view.conflicts));
    assert.strictEqual(view.loading, false);
    assert.strictEqual(view.error, null);
  });

  await t.test('renders dashboard tab with all 9 KPI categories and invariants notice', () => {
    const view = new BeliefView({ container: null });
    view.dashboardData = {
      total_beliefs: 15,
      confident_beliefs: 9,
      contested_beliefs: 2,
      stale_beliefs: 1,
      unknown_beliefs: 3,
      total_evidence_items: 42,
      active_conflicts: 2,
      total_revisions: 8,
      total_snapshots: 4,
    };

    const html = view.renderDashboardHtml();
    assert.ok(html.includes('Active Beliefs'));
    assert.ok(html.includes('Confident State'));
    assert.ok(html.includes('Contested Beliefs'));
    assert.ok(html.includes('Stale Beliefs'));
    assert.ok(html.includes('Unknown / Insufficient'));
    assert.ok(html.includes('Ingested Evidence'));
    assert.ok(html.includes('Active Conflicts'));
    assert.ok(html.includes('Versioned Revisions'));
    assert.ok(html.includes('Decision Snapshots'));
    assert.ok(html.includes('BELIEF != TRUTH'));
    assert.ok(html.includes('BELIEF != AUTHORIZATION'));
    assert.ok(html.includes('EMERGENCY_STOP ABSOLUTE PRIMACY'));
  });

  await t.test('renders beliefs table with rows and confidence gauge', () => {
    const view = new BeliefView({ container: null });
    view.beliefs = [
      {
        belief_id: 'blf_test_001',
        subject: 'auth_service',
        predicate: 'is_available',
        status: 'CONFIDENT',
        confidence: 0.94,
        scope: 'ENVIRONMENT:production',
        current_version: 3,
        is_stale: false,
      },
      {
        belief_id: 'blf_test_002',
        subject: 'worker_pool',
        predicate: 'memory_pressure',
        status: 'STALE',
        confidence: 0.42,
        scope: 'SYSTEM',
        current_version: 1,
        is_stale: true,
      },
    ];

    const html = view.renderBeliefsHtml();
    assert.ok(html.includes('blf_test_001'));
    assert.ok(html.includes('auth_service'));
    assert.ok(html.includes('CONFIDENT'));
    assert.ok(html.includes('94%'));
    assert.ok(html.includes('blf_test_002'));
    assert.ok(html.includes('STALE'));
  });

  await t.test('renders detail tab with explanation and evidence breakdown', () => {
    const view = new BeliefView({ container: null });
    view.selectedBelief = {
      belief_id: 'blf_123',
      subject: 'payment_gateway',
      predicate: 'is_healthy',
      status: 'SUPPORTED',
      confidence: 0.85,
      scope: 'SYSTEM',
      current_version: 2,
      valid_from: '2026-09-18T00:00:00Z',
      evidence_ids: ['evi_1', 'evi_2'],
      contradiction_evidence_ids: [],
    };
    view.explanation = {
      what: "Kairo believes that payment_gateway is_healthy is 'true' with 85.0% confidence.",
      when: 'Valid from 2026-09-18T00:00:00Z (last verified 3.2 mins ago).',
      why_evidence: ['[TELEMETRY] 200 OK baseline verified'],
      when_not_contradictions: ['Zero active contradictions observed.'],
      limitations: ['Standard bounded empirical confidence.'],
    };

    const html = view.renderDetailHtml();
    assert.ok(html.includes('payment_gateway'));
    assert.ok(html.includes('is_healthy'));
    assert.ok(html.includes('85.0% confidence'));
    assert.ok(html.includes('200 OK baseline verified'));
    assert.ok(html.includes('Zero active contradictions observed.'));
  });

  await t.test('renders conflict matrix with contextual validity and direct conflict cards', () => {
    const view = new BeliefView({ container: null });
    view.conflicts = [
      {
        conflict_id: 'bcnf_1',
        conflict_type: 'DIRECT',
        resolution: 'CONTESTED',
        rationale: 'Direct contradiction between observed timeout and reported readiness.',
      },
      {
        conflict_id: 'bcnf_2',
        conflict_type: 'SCOPE',
        resolution: 'BOTH_CONTEXTUALLY_VALID',
        rationale: 'Healthy in staging, degraded in production. Both are contextually valid.',
      },
    ];

    const html = view.renderConflictsHtml();
    assert.ok(html.includes('bcnf_1'));
    assert.ok(html.includes('DIRECT'));
    assert.ok(html.includes('CONTESTED'));
    assert.ok(html.includes('bcnf_2'));
    assert.ok(html.includes('SCOPE'));
    assert.ok(html.includes('BOTH_CONTEXTUALLY_VALID'));
  });

  await t.test('renders evidence chronology timeline', () => {
    const view = new BeliefView({ container: null });
    view.evidenceList = [
      {
        evidence_id: 'evi_999',
        source_id: 'k8s_telemetry',
        source_type: 'TELEMETRY',
        timestamp: '2026-09-18T01:30:00Z',
        summary: 'CPU usage at 45%, memory nominal.',
        reliability_weight: 0.9,
        content_hash: '9a8b7c6d5e4f1a2b3c',
      },
    ];

    const html = view.renderEvidenceHtml();
    assert.ok(html.includes('evi_999'));
    assert.ok(html.includes('TELEMETRY'));
    assert.ok(html.includes('CPU usage at 45%'));
  });
});
