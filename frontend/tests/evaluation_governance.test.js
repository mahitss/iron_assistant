import test from 'node:test';
import assert from 'node:assert/strict';
import { EvaluationView } from '../components/evaluation/evaluationView.js';

test('Task 104: Continuous Evaluation & Improvement Governance Console Tests', async (t) => {
  await t.test('renders regression center with zero-regression state', () => {
    const view = new EvaluationView({ activeTab: 'regressions' });
    view.comparison = {
      baseline_version: 'v1.0.0',
      status: 'RELEASE APPROVED',
      block_release: false,
      regressions_count: 0,
      deltas: [
        { metric_name: 'quality_score', status: 'improved', delta_percentage: '+3.0' },
        { metric_name: 'security_pass_rate', status: 'unchanged', delta_percentage: '0.0' },
      ],
    };
    const html = view.render();
    assert.ok(html.includes('Regression Center (13 Governance Categories)'));
    assert.ok(html.includes('ZERO REGRESSIONS'));
    assert.ok(html.includes('No Regressions Detected'));
  });

  await t.test('renders regression center with detected regressions and blocking alert', () => {
    const view = new EvaluationView({ activeTab: 'regressions' });
    view.comparison = {
      baseline_version: 'v1.0.0',
      status: 'RELEASE BLOCKED',
      block_release: true,
      regressions_count: 1,
      deltas: [
        {
          metric_name: 'security_pass_rate',
          status: 'regressed',
          baseline_value: 1.0,
          current_value: 0.9,
          delta_percentage: '-10.0',
          is_blocking: true,
        },
      ],
    };
    const html = view.render();
    assert.ok(html.includes('1 REGRESSION(S) DETECTED'));
    assert.ok(html.includes('BLOCKING 🛑'));
    assert.ok(html.includes('security_pass_rate'));
  });

  await t.test('renders probabilistic calibration center with ECE and Brier scores', () => {
    const view = new EvaluationView({ activeTab: 'calibration' });
    const html = view.render();
    assert.ok(html.includes('Calibration &amp; Uncertainty Center') || html.includes('Calibration & Uncertainty Center'));
    assert.ok(html.includes('EXPECTED CALIBRATION ERROR (ECE)'));
    assert.ok(html.includes('BRIER PROBABILISTIC SCORE'));
    assert.ok(html.includes('0.038'));
    assert.ok(html.includes('0.042'));
  });

  await t.test('renders improvement proposals inbox with review action buttons', () => {
    const view = new EvaluationView({ activeTab: 'proposals' });
    const html = view.render();
    assert.ok(html.includes('Governed Improvement Proposals'));
    assert.ok(html.includes('Approve Proposal'));
    assert.ok(html.includes('Request Changes'));
    assert.ok(html.includes('Adaptive Retry Backoff Tuning for Tool Dispatch'));
  });

  await t.test('renders controlled canary and shadow experiments view', () => {
    const view = new EvaluationView({ activeTab: 'experiments' });
    const html = view.render();
    assert.ok(html.includes('Controlled Canary &amp; Shadow Experiments') || html.includes('Controlled Canary & Shadow Experiments'));
    assert.ok(html.includes('SHADOW MODE'));
    assert.ok(html.includes('exp_shadow_retry_01'));
  });

  await t.test('renders immutable evidence lineage with cryptographic hash', () => {
    const view = new EvaluationView({ activeTab: 'evidence' });
    const html = view.render();
    assert.ok(html.includes('Immutable Evaluation Evidence Lineage'));
    assert.ok(html.includes('evid_release_v1.0.0_verified'));
    assert.ok(html.includes('sha256:'));
  });
});
