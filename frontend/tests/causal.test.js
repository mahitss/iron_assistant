/**
 * Unit tests for Kairo Causal Reasoning and Causal Graph Engine (Task 55)
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { endpoints, causalApi } from '../lib/api/endpoints.js';
import { CausalView } from '../components/causal/causalView.js';

describe('Causal Reasoning & Causal Graph Endpoints (Task 55)', () => {
  test('Endpoints exposes all causal reasoning methods', () => {
    assert.strictEqual(typeof endpoints.getCausalGraph, 'function');
    assert.strictEqual(typeof endpoints.addCausalNode, 'function');
    assert.strictEqual(typeof endpoints.addCausalEdge, 'function');
    assert.strictEqual(typeof endpoints.analyzeCausalRootCause, 'function');
    assert.strictEqual(typeof endpoints.getCausalAnalysis, 'function');
    assert.strictEqual(typeof endpoints.getCausalExplanation, 'function');
    assert.strictEqual(typeof endpoints.askCausalQuestion, 'function');
    assert.strictEqual(typeof endpoints.proposeCausalIntervention, 'function');
    assert.strictEqual(typeof endpoints.evaluateCausalIntervention, 'function');
    assert.strictEqual(typeof endpoints.evaluateCausalCounterfactual, 'function');
    assert.strictEqual(typeof endpoints.detectCausalFallacies, 'function');
    assert.strictEqual(typeof endpoints.getCausalBlastRadius, 'function');
  });

  test('causalApi wrapper exposes mapped methods', () => {
    assert.strictEqual(typeof causalApi.getGraph, 'function');
    assert.strictEqual(typeof causalApi.addNode, 'function');
    assert.strictEqual(typeof causalApi.addEdge, 'function');
    assert.strictEqual(typeof causalApi.analyzeRootCause, 'function');
    assert.strictEqual(typeof causalApi.getAnalysis, 'function');
    assert.strictEqual(typeof causalApi.getExplanation, 'function');
    assert.strictEqual(typeof causalApi.askQuestion, 'function');
    assert.strictEqual(typeof causalApi.proposeIntervention, 'function');
    assert.strictEqual(typeof causalApi.evaluateIntervention, 'function');
    assert.strictEqual(typeof causalApi.evaluateCounterfactual, 'function');
    assert.strictEqual(typeof causalApi.detectFallacies, 'function');
    assert.strictEqual(typeof causalApi.getBlastRadius, 'function');
  });
});

describe('CausalView Component', () => {
  test('initializes and renders causal tabs without crashing', () => {
    const mockContainer = {
      innerHTML: '',
      querySelector: (selector) => {
        if (selector === '#causal-tab-content') {
          return { innerHTML: '' };
        }
        return null;
      },
      querySelectorAll: () => [],
    };

    const view = new CausalView({ container: mockContainer });
    assert.strictEqual(view.state.activeTab, 'graph');
    assert.strictEqual(view.state.selectedIncident, 'inc-latency-p99-db-saturation');
    
    // Test template and tabs rendering
    const html = view._template();
    assert.ok(html.includes('Causal Reasoning & Causal Graph Engine'));
    assert.ok(html.includes('Strict Invariant: Observation ≠ Correlation ≠ Dependency ≠ Causation'));
    
    const rcaHtml = view._renderRootCauseTab();
    assert.ok(rcaHtml.includes('5-Stage Causal Chain'));
    
    const intvHtml = view._renderInterventionsTab();
    assert.ok(intvHtml.includes('Intervention Testing Workbench'));
    
    const fallaciesHtml = view._renderFallaciesTab();
    assert.ok(fallaciesHtml.includes('Causal Fallacy Inspector'));
  });
});

