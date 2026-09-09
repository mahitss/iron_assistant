import test from 'node:test';
import assert from 'node:assert/strict';
import { EvaluationView } from '../components/evaluation/evaluationView.js';

test('EvaluationView Frontend Component Tests', async (t) => {
  await t.test('initializes with default state and suites', () => {
    const view = new EvaluationView();
    assert.ok(view);
    assert.strictEqual(view.selectedSuite, 'all');
    assert.strictEqual(view.selectedCategory, 'all');
    assert.strictEqual(view.filterStatus, 'all');
    assert.strictEqual(view.activeTab, 'overview');
    assert.strictEqual(view.isRunning, false);
    assert.ok(Array.isArray(view.scenarios));
    assert.ok(Array.isArray(view.runs));
    assert.strictEqual(view.currentRun, null);
  });

  await t.test('filters scenarios by category and suite correctly', () => {
    const view = new EvaluationView();
    view.scenarios = [
      { id: 'security.prompt_injection.001', category: 'security', name: 'Prompt Injection Test' },
      { id: 'routing.code_generation.001', category: 'routing', name: 'Code Routing Test' },
      { id: 'tools.calculator.001', category: 'tools', name: 'Calculator Tool Test' },
    ];

    view.selectedCategory = 'security';
    const securityScenarios = view.getFilteredScenarios();
    assert.strictEqual(securityScenarios.length, 1);
    assert.strictEqual(securityScenarios[0].id, 'security.prompt_injection.001');

    view.selectedCategory = 'all';
    view.searchQuery = 'Calculator';
    const searched = view.getFilteredScenarios();
    assert.strictEqual(searched.length, 1);
    assert.strictEqual(searched[0].id, 'tools.calculator.001');
  });

  await t.test('renders empty state when not evaluated yet', () => {
    const view = new EvaluationView();
    view.currentRun = null;
    const html = view.render();
    assert.ok(html.includes('Not evaluated yet'));
    assert.ok(html.includes('Kairo Evaluation & Benchmarking'));
    assert.ok(html.includes('Run Evaluation'));
  });

  await t.test('renders run metrics and KPI cards when run data exists', () => {
    const view = new EvaluationView();
    view.currentRun = {
      run_id: 'run_test_123',
      dataset_version: 'golden-v1.0',
      status: 'completed',
      metrics: {
        total_scenarios: 10,
        passed_scenarios: 10,
        failed_scenarios: 0,
        flaky_scenarios: 0,
        pass_rate: 1.0,
        quality_score: 0.95,
        security_pass_rate: 1.0,
        tool_selection_accuracy: 0.94,
        context_precision: 0.88,
        p95_latency_ms: 2400,
        estimated_cost_usd: 0.0125,
      },
      results: [
        {
          scenario_id: 'security.prompt_injection.001',
          passed: true,
          status: 'passed',
          actual_behavior: 'Refused prompt injection and executed safely',
          metrics: { security_passed: true, latency_ms: 120 },
        },
      ],
    };

    const html = view.render();
    assert.ok(html.includes('95%'));
    assert.ok(html.includes('100%'));
    assert.ok(html.includes('2.4s'));
    assert.ok(html.includes('run_test_123'));
    assert.ok(html.includes('security.prompt_injection.001'));
  });

  await t.test('renders security dashboard with distinct controls', () => {
    const view = new EvaluationView();
    view.activeTab = 'security';
    view.securitySummary = {
      pass_rate: 1.0,
      total_tests: 12,
      passed_tests: 12,
      failed_tests: 0,
      controls: {
        prompt_injection: 'PASS',
        tool_injection: 'PASS',
        authorization_idor: 'PASS',
        approval_bypass: 'PASS',
        ssrf: 'PASS',
        secret_leakage: 'PASS',
        path_traversal: 'PASS',
        agent_loop_protection: 'PASS',
      },
    };

    const html = view.render();
    assert.ok(html.includes('Prompt Injection Resistance'));
    assert.ok(html.includes('Secret Leak Prevention'));
    assert.ok(html.includes('SSRF Defense'));
    assert.ok(html.includes('PASS'));
    assert.ok(!html.includes('FAIL'));
  });

  await t.test('renders baseline regression comparison with approved or blocked status', () => {
    const view = new EvaluationView();
    view.activeTab = 'baseline';
    view.comparisonResult = {
      baseline_version: 'v1.0.0',
      current_run_id: 'run_test_123',
      status: 'RELEASE APPROVED',
      block_release: false,
      block_reasons: [],
      warnings: [],
      metric_deltas: {
        quality_score: 0.03,
        tool_selection_accuracy: 0.02,
        security_pass_rate: 0.0,
      },
    };

    const html = view.render();
    assert.ok(html.includes('RELEASE APPROVED'));
    assert.ok(html.includes('v1.0.0'));
    assert.ok(html.includes('+3.0%'));
  });
});
