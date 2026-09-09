/**
 * Unit tests for Kairo Cognitive Planning & Adaptive Reasoning (Task 41)
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { endpoints } from '../lib/api/endpoints.js';
import { CognitionView } from '../components/cognition/cognitionView.js';

describe('Cognitive Planning & Adaptive Decision Engine Endpoints (Task 41)', () => {
  test('Endpoints exposes all cognition methods', () => {
    assert.strictEqual(typeof endpoints.createCognitiveGoal, 'function');
    assert.strictEqual(typeof endpoints.getCognitiveGoal, 'function');
    assert.strictEqual(typeof endpoints.buildCognitivePlan, 'function');
    assert.strictEqual(typeof endpoints.getCognitivePlan, 'function');
    assert.strictEqual(typeof endpoints.validateCognitivePlan, 'function');
    assert.strictEqual(typeof endpoints.replanCognitivePlan, 'function');
    assert.strictEqual(typeof endpoints.verifyCognitiveStep, 'function');
    assert.strictEqual(typeof endpoints.getCognitivePlanPreview, 'function');
    assert.strictEqual(typeof endpoints.explainCognitiveStep, 'function');
    assert.strictEqual(typeof endpoints.getCognitiveDashboard, 'function');
    assert.strictEqual(typeof endpoints.listCognitiveTemplates, 'function');
  });

  test('CognitionView initializes with tabs, default state, and KPI containers', () => {
    const mockContainer = {
      innerHTML: '',
      querySelector: () => null,
      querySelectorAll: () => [],
    };

    const view = new CognitionView(mockContainer);
    assert.strictEqual(view.activeTab, 'plans');
    assert.strictEqual(view.isLoading, false);
    assert.strictEqual(view.selectedPlan, null);
  });
});
