/**
 * Unit tests for Kairo Strategic Planning & Long-Horizon Execution Engine (Task 58).
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { endpoints, planningApi } from '../lib/api/endpoints.js';
import { PlanningView } from '../components/planning/planningView.js';

describe('Strategic Planning Endpoints (Task 58)', () => {
  test('Endpoints exposes all planning methods', () => {
    assert.strictEqual(typeof endpoints.createPlan, 'function');
    assert.strictEqual(typeof endpoints.listPlans, 'function');
    assert.strictEqual(typeof endpoints.getPlan, 'function');
    assert.strictEqual(typeof endpoints.validatePlan, 'function');
    assert.strictEqual(typeof endpoints.analyzePlan, 'function');
    assert.strictEqual(typeof endpoints.startPlan, 'function');
    assert.strictEqual(typeof endpoints.pausePlan, 'function');
    assert.strictEqual(typeof endpoints.resumePlan, 'function');
    assert.strictEqual(typeof endpoints.cancelPlan, 'function');
    assert.strictEqual(typeof endpoints.replan, 'function');
    assert.strictEqual(typeof endpoints.getPlanProgress, 'function');
    assert.strictEqual(typeof endpoints.getPlanTimeline, 'function');
    assert.strictEqual(typeof endpoints.getPlanDependencies, 'function');
    assert.strictEqual(typeof endpoints.getPlanRisks, 'function');
    assert.strictEqual(typeof endpoints.getPlanOutcomes, 'function');
    assert.strictEqual(typeof endpoints.recordPlanOutcome, 'function');
    assert.strictEqual(typeof endpoints.getExecutionProposal, 'function');
    assert.strictEqual(typeof endpoints.getPlanAudit, 'function');
  });

  test('planningApi wrapper exposes mapped methods', () => {
    assert.strictEqual(typeof planningApi.create, 'function');
    assert.strictEqual(typeof planningApi.list, 'function');
    assert.strictEqual(typeof planningApi.get, 'function');
    assert.strictEqual(typeof planningApi.validate, 'function');
    assert.strictEqual(typeof planningApi.analyze, 'function');
    assert.strictEqual(typeof planningApi.start, 'function');
    assert.strictEqual(typeof planningApi.pause, 'function');
    assert.strictEqual(typeof planningApi.resume, 'function');
    assert.strictEqual(typeof planningApi.cancel, 'function');
    assert.strictEqual(typeof planningApi.replan, 'function');
    assert.strictEqual(typeof planningApi.getProgress, 'function');
    assert.strictEqual(typeof planningApi.getTimeline, 'function');
    assert.strictEqual(typeof planningApi.getDependencies, 'function');
    assert.strictEqual(typeof planningApi.getRisks, 'function');
    assert.strictEqual(typeof planningApi.getOutcomes, 'function');
    assert.strictEqual(typeof planningApi.recordOutcome, 'function');
    assert.strictEqual(typeof planningApi.getProposal, 'function');
    assert.strictEqual(typeof planningApi.getAudit, 'function');
  });
});

describe('PlanningView Component', () => {
  test('initializes and renders planning dashboard and invariant banners', () => {
    const mockContainer = {
      innerHTML: '',
      addEventListener: () => {},
      querySelectorAll: () => [],
      querySelector: () => null,
    };

    const view = new PlanningView({ container: mockContainer });
    assert.strictEqual(view.state.activeTab, 'overview');

    const html = view._template();
    assert.ok(html.includes('Kairo Strategic Planning Engine'));
    assert.ok(html.includes('LONG_HORIZON_EXECUTION'));
    assert.ok(html.includes('Plan &ne; Execution &ne; Verification'));
    assert.ok(html.includes('DIRECT TOOL EXECUTION BLOCKED'));
    assert.ok(html.includes('Validate Plan'));
    assert.ok(html.includes('Execution Proposal'));
    assert.ok(html.includes('Synthesize New Plan'));
  });

  test('renders all tab templates without errors', () => {
    const mockPlan = {
      plan_id: 'plan_test_482',
      name: 'Test Infrastructure Modernization',
      purpose: 'Migrate to resilient microservices',
      status: 'RUNNING',
      health: 'ON_TRACK',
      current_state: {
        summary: 'Legacy state',
        certainty: 'VERIFIED',
      },
      desired_state: {
        summary: 'Target state',
        completion_invariants: ['Zero downtime failover'],
      },
      gap_analysis: {
        missing_capabilities: ['Multi-region HA'],
        technical_gaps: ['Latency deficit: 120ms vs 50ms'],
      },
      strategy: {
        name: 'Incremental Phased Rollout',
        strategy_type: 'INCREMENTAL',
        estimated_complexity: 'MEDIUM',
        expected_risk: 'LOW',
        reversibility: 'REVERSIBLE',
      },
      phases: [
        {
          phase_id: 'pph_1',
          name: 'Phase 1: Preparation',
          status: 'IN_PROGRESS',
          entry_criteria: ['Baseline verified'],
          exit_criteria: ['Sandbox ready'],
        },
      ],
      milestones: [
        {
          milestone_id: 'pml_1',
          phase_id: 'pph_1',
          name: 'M1: Preconditions Ready',
          weight: 1.0,
          is_verified: true,
          status: 'REACHED',
          verification_criteria: ['Telemetry active'],
        },
      ],
      execution_waves: [
        {
          wave_number: 1,
          task_ids: ['ptk_1'],
          estimated_duration: 2.0,
        },
      ],
      tasks: [
        {
          task_id: 'ptk_1',
          title: 'Sync Environment',
          owner: 'OWNER_UNASSIGNED',
          duration_min: 1.0,
          duration_expected: 2.0,
          duration_max: 4.0,
          is_irreversible: false,
          resources: [
            { name: 'db_slot', amount: 1.0, unit: 'node', is_exclusive: true },
          ],
        },
      ],
      checkpoints: [
        {
          name: 'CP-1: Initial Health',
          expected_state: { error_count: 0 },
          variance_score: 0.05,
          decision_action: 'CONTINUE',
        },
      ],
      risks: [
        {
          description: 'Network partition risk',
          severity: 'HIGH',
          mitigation: 'Implement retries',
          contingency_plan: 'Fallback to secondary DC',
        },
      ],
    };

    const view = new PlanningView();
    view.state.currentPlan = mockPlan;
    view.state.progress = {
      composite_progress_pct: 45.0,
      task_count_completed: 1,
      task_count_total: 1,
      milestone_weighted_progress_pct: 50.0,
    };
    view.state.timeline = {
      critical_path: { total_duration: 2.0, critical_task_ids: ['ptk_1'] },
    };
    view.state.dependencies = {
      has_cycle: false,
      tasks: [{ id: 'ptk_1', title: 'Sync Environment', status: 'RUNNING' }],
      predecessors: { ptk_1: [] },
      successors: { ptk_1: [] },
    };
    view.state.risks = {
      rollback_strategy: {
        rollback_trigger: 'Wave failure',
        steps: ['Revert routing', 'Verify health'],
      },
    };
    view.state.auditEvents = [
      {
        event_type: 'PLAN_CREATED',
        actor: 'operator',
        timestamp: '2026-09-10T12:00:00Z',
        details: { version: 1 },
      },
    ];

    // Verify all 8 view templates produce non-empty strings
    const overviewHtml = view._renderOverview(mockPlan);
    assert.ok(overviewHtml.includes('Test Infrastructure Modernization'));
    assert.ok(overviewHtml.includes('Zero downtime failover'));
    assert.ok(overviewHtml.includes('Incremental Phased Rollout'));

    const phasesHtml = view._renderPhases(mockPlan);
    assert.ok(phasesHtml.includes('Phase 1: Preparation'));
    assert.ok(phasesHtml.includes('M1: Preconditions Ready'));

    const wavesHtml = view._renderWaves(mockPlan);
    assert.ok(wavesHtml.includes('Wave 1'));
    assert.ok(wavesHtml.includes('Sync Environment'));

    const graphHtml = view._renderGraph(mockPlan);
    assert.ok(graphHtml.includes('ACYCLIC (DAG VALIDATED)'));

    const resHtml = view._renderResources(mockPlan);
    assert.ok(resHtml.includes('db_slot'));
    assert.ok(resHtml.includes('MUTEX EXCLUSIVE'));

    const risksHtml = view._renderRisks(mockPlan);
    assert.ok(risksHtml.includes('Network partition risk'));
    assert.ok(risksHtml.includes('Rollback & Disaster Recovery Strategy'));

    const adaptHtml = view._renderAdaptation(mockPlan);
    assert.ok(adaptHtml.includes('CP-1: Initial Health'));
    assert.ok(adaptHtml.includes('Sunk Cost Defense Engine'));

    const auditHtml = view._renderAudit(mockPlan);
    assert.ok(auditHtml.includes('PLAN_CREATED'));
  });
});
