import test from 'node:test';
import assert from 'node:assert/strict';
import { AdaptationView } from '../components/adaptation/adaptationView.js';

test('AdaptationView Frontend Component Tests (Task 105)', async (t) => {
  await t.test('initializes with default state and properties', () => {
    const view = new AdaptationView({ container: null });
    assert.ok(view);
    assert.strictEqual(view.activeTab, 'dashboard');
    assert.strictEqual(view.dashboardData, null);
    assert.ok(Array.isArray(view.programs));
    assert.ok(Array.isArray(view.experiments));
    assert.ok(Array.isArray(view.hypotheses));
    assert.ok(Array.isArray(view.comparisons));
    assert.ok(Array.isArray(view.proposals));
    assert.ok(Array.isArray(view.changesets));
    assert.ok(Array.isArray(view.gates));
    assert.strictEqual(view.loading, false);
    assert.strictEqual(view.error, null);
  });

  await t.test('renders dashboard tab with all 9 KPI categories', () => {
    const view = new AdaptationView({ container: null });
    view.dashboardData = {
      active_experiments: 2,
      blocked_count: 1,
      failed_count: 0,
      inconclusive_count: 1,
      improving_count: 3,
      regressing_count: 0,
      awaiting_review_count: 2,
      awaiting_approval_count: 1,
      validating_count: 1,
      emergency_stop_active: false,
    };
    view.programs = [
      {
        id: 'prog_1',
        title: 'Optimize Code Search Latency',
        affected_capability: 'code_search',
        baseline_id: 'golden_base_1',
        status: 'EXPERIMENTING',
        created_at: new Date().toISOString(),
      },
    ];
    view.experiments = [
      {
        id: 'run_1',
        program_id: 'prog_1',
        stage_number: 2,
        environment: 'SIMULATION',
        status: 'RUNNING',
        current_sample_count: 12,
        target_sample_count: 20,
      },
    ];

    const html = view.renderDashboardTab();
    assert.ok(html.includes('ACTIVE EXPERIMENTS'));
    assert.ok(html.includes('BLOCKED'));
    assert.ok(html.includes('FAILED'));
    assert.ok(html.includes('INCONCLUSIVE'));
    assert.ok(html.includes('IMPROVING'));
    assert.ok(html.includes('REGRESSING'));
    assert.ok(html.includes('AWAITING REVIEW'));
    assert.ok(html.includes('AWAITING APPROVAL'));
    assert.ok(html.includes('VALIDATING'));
    assert.ok(html.includes('Optimize Code Search Latency'));
    assert.ok(html.includes('code_search'));
    assert.ok(html.includes('run_1'));
    assert.ok(html.includes('SIMULATION'));
  });

  await t.test('renders hypothesis explorer with explicit IF-THEN-BECAUSE cards', () => {
    const view = new AdaptationView({ container: null });
    view.hypotheses = [
      {
        id: 'hyp_001',
        condition_change: 'If cache size is expanded to 4096 entries',
        expected_outcome: 'then latency will drop by 50ms',
        evidence_reasoning: 'Evaluation detected high cache miss rates',
        confidence: 0.85,
        falsification_criteria: ['Latency does not improve', 'Error rate rises'],
        measurable_outcomes: { latency_delta_ms: -50.0 },
      },
    ];

    const html = view.renderHypothesesTab();
    assert.ok(html.includes('hyp_001'));
    assert.ok(html.includes('Confidence: 85%'));
    assert.ok(html.includes('If cache size is expanded to 4096 entries'));
    assert.ok(html.includes('then latency will drop by 50ms'));
    assert.ok(html.includes('Evaluation detected high cache miss rates'));
    assert.ok(html.includes('Falsification Criteria'));
    assert.ok(html.includes('latency_delta_ms: -50'));
  });

  await t.test('renders variant comparison matrix across dimensions', () => {
    const view = new AdaptationView({ container: null });
    view.comparisons = [
      {
        id: 'cmp_001',
        run_id: 'run_123',
        verdict: 'IMPROVED',
        rationale: 'Candidate achieved statistically significant quality improvement.',
        sample_size: 25,
        causal_attribution_verified: true,
        world_state_verified: true,
        dimension_scores: {
          quality: { baseline: 0.8, candidate: 0.92, delta: 0.12 },
          safety: { baseline: 1.0, candidate: 1.0, delta: 0.0 },
          latency: { baseline: 500, candidate: 450, delta: -50 },
        },
      },
    ];

    const html = view.renderComparisonsTab();
    assert.ok(html.includes('cmp_001'));
    assert.ok(html.includes('IMPROVED'));
    assert.ok(html.includes('Candidate achieved statistically significant quality improvement.'));
    assert.ok(html.includes('QUALITY'));
    assert.ok(html.includes('SAFETY'));
    assert.ok(html.includes('+0.120'));
    assert.ok(html.includes('Sample Size: 25'));
    assert.ok(html.includes('Causal Attribution: ✓ Verified'));
  });

  await t.test('renders gates tab with pass and fail statuses', () => {
    const view = new AdaptationView({ container: null });
    view.gates = [
      {
        gate_name: 'SAFETY_INVARIANTS_GATE',
        run_id: 'run_1',
        passed: true,
        measured_value: 1.0,
        threshold: 1.0,
        reason: '100% security invariance satisfied.',
      },
      {
        gate_name: 'RESOURCE_BUDGET_GATE',
        run_id: 'run_2',
        passed: false,
        measured_value: 12.5,
        threshold: 10.0,
        reason: 'Cost exceeded $10 threshold.',
      },
    ];

    const html = view.renderGatesTab();
    assert.ok(html.includes('SAFETY_INVARIANTS_GATE'));
    assert.ok(html.includes('PASS'));
    assert.ok(html.includes('RESOURCE_BUDGET_GATE'));
    assert.ok(html.includes('FAIL'));
    assert.ok(html.includes('Cost exceeded $10 threshold.'));
  });

  await t.test('renders evolution proposals with governance review buttons', () => {
    const view = new AdaptationView({ container: null });
    view.proposals = [
      {
        id: 'prop_789',
        title: 'Evolution: Code Search Cache Expansion',
        affected_capability: 'code_search',
        current_version: '1.0.0',
        target_version: '1.1.0',
        status: 'SUBMITTED',
        evidence_summary: 'Candidate verified with sealed evidence package.',
        rollback_plan: 'Revert to 1.0.0 parameters immediately.',
        deployment_scope: 'CANARY_10_PERCENT',
        confidence: 0.9,
      },
    ];

    const html = view.renderEvolutionTab();
    assert.ok(html.includes('Evolution: Code Search Cache Expansion'));
    assert.ok(html.includes('code_search'));
    assert.ok(html.includes('1.0.0 → 1.1.0'));
    assert.ok(html.includes('SUBMITTED'));
    assert.ok(html.includes('Approve Proposal'));
    assert.ok(html.includes('Reject Proposal'));
    assert.ok(html.includes('Run Pre-Rollout Validation'));
  });
});
