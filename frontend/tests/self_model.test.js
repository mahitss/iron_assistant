/**
 * Unit tests for Kairo Autonomous Self-Model, Capability Awareness & Internal State Intelligence (Task 101).
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { selfModelApi } from '../lib/api/endpoints.js';
import { SelfModelView } from '../components/self_model/selfModelView.js';

describe('Self-Model API Endpoints (Task 101)', () => {
  test('selfModelApi exposes all required introspective methods', () => {
    assert.strictEqual(typeof selfModelApi.getSnapshot, 'function');
    assert.strictEqual(typeof selfModelApi.reconcile, 'function');
    assert.strictEqual(typeof selfModelApi.getAnswers, 'function');
    assert.strictEqual(typeof selfModelApi.getCapabilities, 'function');
    assert.strictEqual(typeof selfModelApi.getCapabilityDetail, 'function');
    assert.strictEqual(typeof selfModelApi.getLimitations, 'function');
    assert.strictEqual(typeof selfModelApi.getUncertainties, 'function');
    assert.strictEqual(typeof selfModelApi.getDeltas, 'function');
    assert.strictEqual(typeof selfModelApi.getHistory, 'function');
    assert.strictEqual(typeof selfModelApi.verifyGrounding, 'function');
    assert.strictEqual(typeof selfModelApi.getSummary, 'function');
  });
});

describe('SelfModelView Component', () => {
  test('initializes with default state and default answers tab', () => {
    const view = new SelfModelView('mock-container');
    assert.strictEqual(view.activeTab, 'answers');
    assert.strictEqual(view.snapshot, null);
    assert.strictEqual(view.answers, null);
    assert.deepStrictEqual(view.capabilities, {});
    assert.strictEqual(view.limitations.length, 0);
    assert.strictEqual(view.uncertainties.length, 0);
    assert.strictEqual(view.deltas.length, 0);
    assert.strictEqual(view.isLoading, false);
  });

  test('switches tabs correctly across all introspective views', () => {
    const view = new SelfModelView('mock-container');
    view.setTab('capabilities');
    assert.strictEqual(view.activeTab, 'capabilities');
    view.setTab('limitations');
    assert.strictEqual(view.activeTab, 'limitations');
    view.setTab('uncertainties');
    assert.strictEqual(view.activeTab, 'uncertainties');
    view.setTab('deltas');
    assert.strictEqual(view.activeTab, 'deltas');
    view.setTab('grounding');
    assert.strictEqual(view.activeTab, 'grounding');
    view.setTab('answers');
    assert.strictEqual(view.activeTab, 'answers');
  });

  test('renders 15 canonical introspective questions HTML correctly', () => {
    const view = new SelfModelView('mock-container');
    view.answers = {
      q1_capabilities: ['code_execution', 'web_research'],
      q2_versions: { code_execution: '1.0.0' },
      q3_ready_capabilities: ['code_execution'],
      q4_degraded_capabilities: [],
      q5_temporarily_unavailable: [],
      q6_current_resources: { saturation_pct: 0.25, degradation_tier: 'FULL_FIDELITY' },
      q7_usable_tools: ['calculator', 'system_info'],
      q8_authorized_access: ['STANDARD_SAFE_READ_WRITE'],
      q9_actions_requiring_approval: ['destructive_shell'],
      q10_failing_dependencies: [],
      q11_recently_failed_capabilities: [],
      q12_capability_reliability: { code_execution: 1.0 },
      q13_changes_since_last_check: [],
      q14_limitations: [{ subject: 'BOUNDARIES', description: 'Cannot delete database' }],
      q15_uncertainties: [{ subject: 'TELEMETRY', reason: 'Intermittent ping' }],
    };

    const html = view.renderAnswers();
    assert.ok(html.includes('What capabilities do I have?'));
    assert.ok(html.includes('code_execution, web_research'));
    assert.ok(html.includes('Which capabilities are actually ready?'));
    assert.ok(html.includes('What do I know about my own limitations?'));
    assert.ok(html.includes('What am I uncertain about?'));
  });

  test('renders capability matrix correctly', () => {
    const view = new SelfModelView('mock-container');
    view.capabilities = {
      code_execution: {
        capability_id: 'code_execution',
        name: 'Code Execution Engine',
        version: '1.0.0',
        lifecycle_state: 'ACTIVE',
        readiness_state: 'READY',
        health_state: 'HEALTHY',
        reliability_score: 0.98,
        consecutive_failures: 0,
        evidence: ['Lifecycle: ACTIVE', 'Health: HEALTHY'],
      },
    };

    const html = view.renderCapabilities();
    assert.ok(html.includes('Code Execution Engine'));
    assert.ok(html.includes('READY'));
    assert.ok(html.includes('98%'));
  });

  test('renders limitations and uncertainties correctly', () => {
    const view = new SelfModelView('mock-container');
    view.limitations = [
      {
        limitation_id: 'lim_1',
        subject: 'EMERGENCY_STOP',
        description: 'External execution blocked',
        reason: 'Kill switch active',
        evidence: 'EmergencyStop flag',
        is_hard_limit: true,
      },
    ];
    view.uncertainties = [
      {
        uncertainty_id: 'unc_1',
        subject: 'NETWORK',
        reason: 'Latency fluctuating',
        evidence: 'Packet telemetry',
        revalidation_policy: 'PING_EVERY_60S',
      },
    ];

    const limHtml = view.renderLimitations();
    assert.ok(limHtml.includes('EMERGENCY_STOP'));
    assert.ok(limHtml.includes('External execution blocked'));

    const uncHtml = view.renderUncertainties();
    assert.ok(uncHtml.includes('NETWORK'));
    assert.ok(uncHtml.includes('Latency fluctuating'));
  });
});
