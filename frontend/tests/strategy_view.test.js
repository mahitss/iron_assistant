import test from 'node:test';
import assert from 'node:assert/strict';
import { StrategyView } from '../components/strategy/strategyView.js';

test('StrategyView Frontend Component Tests (Task 106)', async (t) => {
  await t.test('initializes with default state and properties', () => {
    const view = new StrategyView({ container: null });
    assert.ok(view);
    assert.strictEqual(view.activeTab, 'dashboard');
    assert.strictEqual(view.dashboardData, null);
    assert.ok(Array.isArray(view.strategies));
    assert.ok(Array.isArray(view.conflicts));
    assert.ok(Array.isArray(view.proposals));
    assert.strictEqual(view.loading, false);
    assert.strictEqual(view.error, null);
  });

  await t.test('renders dashboard tab with all 9 KPI categories and invariants notice', () => {
    const view = new StrategyView({ container: null });
    view.dashboardData = {
      total_strategies: 12,
      available_count: 8,
      candidate_count: 2,
      validating_count: 1,
      stale_count: 1,
      suspended_count: 0,
      conflicted_count: 1,
      revalidation_queue_count: 1,
      proposals_pending_count: 1,
      emergency_stop_active: false,
    };
    view.strategies = [
      {
        id: 'strat_1',
        name: 'Conservative Query Retry with Exponential Backoff',
        category: 'RECOVERY',
        lifecycle_status: 'AVAILABLE',
        confidence: 0.88,
        success_rate: 0.92,
        is_stale: false,
        usage_count: 24,
      },
    ];

    const html = view.renderDashboardTab();
    assert.ok(html.includes('TOTAL STRATEGIES'));
    assert.ok(html.includes('AVAILABLE (VALIDATED)'));
    assert.ok(html.includes('CANDIDATES'));
    assert.ok(html.includes('STALE / EXPIRED'));
    assert.ok(html.includes('LEARNED STRATEGY != POLICY AUTHORITY'));
    assert.ok(html.includes('Conservative Query Retry'));
  });

  await t.test('renders explorer tab with category filter and strategy cards', () => {
    const view = new StrategyView({ container: null });
    view.strategies = [
      {
        id: 'strat_test_1',
        name: 'Multi-Agent Blind Consensus Strategy',
        category: 'AGENT_COORDINATION',
        objective: 'Mitigate cognitive bias in complex reasoning tasks',
        lifecycle_status: 'CANDIDATE',
        confidence: 0.76,
        usage_count: 15,
        success_rate: 0.85,
      },
    ];

    const html = view.renderExplorerTab();
    assert.ok(html.includes('id="filter-category"'));
    assert.ok(html.includes('Multi-Agent Blind Consensus Strategy'));
    assert.ok(html.includes('Mitigate cognitive bias'));
  });

  await t.test('renders detail tab with conditions, contraindications, and counterexamples', () => {
    const view = new StrategyView({ container: null });
    view.selectedStrategy = {
      id: 'strat_detail_1',
      stable_id: 'strat_stable_999',
      name: 'Resource Constrained Batch Processing',
      category: 'RESOURCE',
      lifecycle_status: 'AVAILABLE',
      objective: 'Process queue without exceeding 80% RAM',
      recommended_approach: 'Throttle worker concurrency to 2 when load > 0.7',
      domain_scope: 'SYSTEM',
      confidence: 0.89,
      uncertainty: 0.11,
      success_rate: 0.94,
      usage_count: 42,
      is_stale: false,
      conditions: [
        { field_path: 'resource_pressure', operator: 'EQUALS', target_value: 'HIGH' },
      ],
      preconditions: [
        { requirement_description: 'Worker queue healthy', verification_key: 'queue.status', is_hard_requirement: true },
      ],
      contraindications: [
        { severity: 'PROHIBITIVE', contraindication_type: 'EMERGENCY_STOP_ACTIVE', rationale: 'Halt on emergency stop' },
      ],
      counterexamples: [
        { claim: 'Worker stalled during burst memory consumption', environmental_context: { memory_mb: 4096 } },
      ],
      failure_modes: [
        { failure_class: 'DEADLOCK', symptom: 'Worker thread hangs', known_cause: 'Lock contention' },
      ],
    };

    const html = view.renderDetailTab();
    assert.ok(html.includes('Resource Constrained Batch Processing'));
    assert.ok(html.includes('Throttle worker concurrency'));
    assert.ok(html.includes('Contraindications (DO NOT USE WHEN...)'));
    assert.ok(html.includes('Known Counterexamples & Exceptions'));
    assert.ok(html.includes('Worker stalled during burst memory consumption'));
  });

  await t.test('renders interactive applicability evaluator', () => {
    const view = new StrategyView({ container: null });
    view.strategies = [
      { id: 'strat_app_1', name: 'Safe Network Fallback' },
    ];

    const html = view.renderApplicabilityTab();
    assert.ok(html.includes('Interactive Applicability Evaluator'));
    assert.ok(html.includes('id="app-test-strategy-select"'));
    assert.ok(html.includes('id="btn-run-app-test"'));
  });

  await t.test('renders conflict explorer with pairwise conflict cards', () => {
    const view = new StrategyView({ container: null });
    view.conflicts = [
      {
        id: 'sconf_1',
        strategy_a_id: 'strat_fast_act',
        strategy_b_id: 'strat_wait_ev',
        conflict_type: 'TEMPORAL',
        description: 'Act immediately vs wait for evidence divergence',
        resolution_hint: 'Evaluate latency budget in Decision Engine',
      },
    ];

    const html = view.renderConflictsTab();
    assert.ok(html.includes('TEMPORAL CONFLICT'));
    assert.ok(html.includes('Act immediately vs wait for evidence'));
  });

  await t.test('renders coverage and drift monitoring grid', () => {
    const view = new StrategyView({ container: null });
    view.dashboardData = {
      coverage_by_category: {
        PLANNING: 3,
        DECISION: 5,
        RECOVERY: 2,
        SECURITY_DEFENSE: 1,
      },
    };

    const html = view.renderCoverageTab();
    assert.ok(html.includes('Strategy Coverage & Drift Monitoring'));
    assert.ok(html.includes('PLANNING'));
    assert.ok(html.includes('SECURITY_DEFENSE'));
  });

  await t.test('renders proposals tab with governance review buttons', () => {
    const view = new StrategyView({ container: null });
    view.proposals = [
      {
        id: 'sprop_1',
        proposal_title: 'Promote Recovery Strategy for Web Search API Timeout',
        rationale: 'Verified across 25 successful runs with 0 regressions',
        status: 'SUBMITTED',
      },
    ];

    const html = view.renderProposalsTab();
    assert.ok(html.includes('Strategy Promotion Proposals'));
    assert.ok(html.includes('Promote Recovery Strategy'));
    assert.ok(html.includes('btn-approve-proposal'));
    assert.ok(html.includes('btn-reject-proposal'));
  });
});
