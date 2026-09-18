/**
 * Frontend Unit & Component Tests for Task 112:
 * Kairo Autonomous Causal Explanation & "Why Did This Happen?" Engine
 */

import test from 'node:test';
import assert from 'node:assert';
import { explanationsApi } from '../lib/api/endpoints.js';
import { WhyDidThisHappenView } from '../components/causal/whyDidThisHappenView.js';

test('Causal Explanations API Endpoints (Task 112)', async (t) => {
  await t.test('explanationsApi exposes all required Task 112 methods', () => {
    assert.strictEqual(typeof explanationsApi.create, 'function');
    assert.strictEqual(typeof explanationsApi.list, 'function');
    assert.strictEqual(typeof explanationsApi.get, 'function');
    assert.strictEqual(typeof explanationsApi.getTimeline, 'function');
    assert.strictEqual(typeof explanationsApi.getChain, 'function');
    assert.strictEqual(typeof explanationsApi.getHypotheses, 'function');
    assert.strictEqual(typeof explanationsApi.getEvidence, 'function');
    assert.strictEqual(typeof explanationsApi.getAlternatives, 'function');
    assert.strictEqual(typeof explanationsApi.getCounterfactuals, 'function');
    assert.strictEqual(typeof explanationsApi.getGaps, 'function');
    assert.strictEqual(typeof explanationsApi.getSnapshot, 'function');
    assert.strictEqual(typeof explanationsApi.getVerification, 'function');
    assert.strictEqual(typeof explanationsApi.verify, 'function');
    assert.strictEqual(typeof explanationsApi.feedback, 'function');
    assert.strictEqual(typeof explanationsApi.refresh, 'function');
  });
});

test('WhyDidThisHappenView Component (Task 112)', async (t) => {
  // Mock container
  const mockContainer = {
    innerHTML: '',
    querySelector: (selector) => {
      return {
        textContent: '',
        value: 'cluster_prod',
        style: {},
        addEventListener: () => {},
        setAttribute: () => {},
        getAttribute: () => 'chain',
      };
    },
    querySelectorAll: (selector) => {
      return [
        {
          style: {},
          getAttribute: () => 'chain',
          addEventListener: () => {},
        },
        {
          style: {},
          getAttribute: () => 'evidence',
          addEventListener: () => {},
        },
      ];
    },
  };

  const view = new WhyDidThisHappenView({ container: mockContainer });

  await t.test('initializes with default chain tab and null explanation', () => {
    assert.strictEqual(view.activeTab, 'chain');
    assert.strictEqual(view.currentExplanation, null);
  });

  await t.test('renders HTML skeleton with title and navigation tabs', () => {
    view.renderSkeleton();
    assert.ok(mockContainer.innerHTML.includes('Why Did This Happen?'));
    assert.ok(mockContainer.innerHTML.includes('Causal Chain'));
    assert.ok(mockContainer.innerHTML.includes('Evidence Arbitration'));
    assert.ok(mockContainer.innerHTML.includes('Alternative Hypotheses'));
  });

  await t.test('renders causal chain steps', () => {
    view.currentExplanation = {
      why_it_happened: 'Resource limit reached',
      causal_links: [
        {
          source_node: 'node_cpu',
          target_node: 'node_queue',
          relationship_role: 'DIRECT_CAUSE',
          mechanism: 'CPU saturation stalled message processing',
          lag_seconds: 0.5,
          status: 'SUPPORTED',
        }
      ],
      confidence: { composite_confidence: 0.8 },
      contributors: [],
      alternatives: [],
      counterfactuals: [],
      unresolved_gaps: [],
    };
    const mockContent = { innerHTML: '' };
    view.renderCausalChain(mockContent);
    assert.ok(mockContent.innerHTML.includes('node_cpu &rarr; node_queue'));
    assert.ok(mockContent.innerHTML.includes('DIRECT_CAUSE'));
  });

  await t.test('renders competing alternative hypotheses', () => {
    view.currentExplanation.alternatives = [
      {
        name: 'Network Route Flap',
        hypothesis_summary: 'Gateway route flapping induced transient timeouts',
        confidence: 0.4,
        discriminating_observation: 'Check BGP route flap dampening log',
      }
    ];
    const mockContent = { innerHTML: '' };
    view.renderAlternatives(mockContent);
    assert.ok(mockContent.innerHTML.includes('Network Route Flap'));
    assert.ok(mockContent.innerHTML.includes('Discriminating Observation:'));
  });
});
