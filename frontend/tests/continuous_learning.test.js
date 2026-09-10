/**
 * Unit tests for Kairo Continuous Learning & Experience Consolidation Engine (Task 52)
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { endpoints, continuousLearningApi } from '../lib/api/endpoints.js';
import { LearningView } from '../components/learning/learningView.js';

describe('Continuous Learning & Experience Consolidation Engine Endpoints (Task 52)', () => {
  test('Endpoints exposes all continuous learning methods', () => {
    assert.strictEqual(typeof endpoints.getContinuousLearningMetrics, 'function');
    assert.strictEqual(typeof endpoints.evaluateLearningOutcome, 'function');
    assert.strictEqual(typeof endpoints.extractLearningLesson, 'function');
    assert.strictEqual(typeof endpoints.listLearningLessons, 'function');
    assert.strictEqual(typeof endpoints.consolidateLearningLessons, 'function');
    assert.strictEqual(typeof endpoints.runLearningReplay, 'function');
    assert.strictEqual(typeof endpoints.registerLearningWorkflow, 'function');
    assert.strictEqual(typeof endpoints.listLearningWorkflows, 'function');
    assert.strictEqual(typeof endpoints.registerLearningHeuristic, 'function');
    assert.strictEqual(typeof endpoints.listLearningHeuristics, 'function');
    assert.strictEqual(typeof endpoints.submitLearningCorrection, 'function');
    assert.strictEqual(typeof endpoints.getLearningGovernancePolicy, 'function');
  });

  test('continuousLearningApi wrapper exposes mapped methods', () => {
    assert.strictEqual(typeof continuousLearningApi.getMetrics, 'function');
    assert.strictEqual(typeof continuousLearningApi.evaluateOutcome, 'function');
    assert.strictEqual(typeof continuousLearningApi.extractLesson, 'function');
    assert.strictEqual(typeof continuousLearningApi.listLessons, 'function');
    assert.strictEqual(typeof continuousLearningApi.consolidateLessons, 'function');
    assert.strictEqual(typeof continuousLearningApi.runReplay, 'function');
    assert.strictEqual(typeof continuousLearningApi.registerWorkflow, 'function');
    assert.strictEqual(typeof continuousLearningApi.listWorkflows, 'function');
    assert.strictEqual(typeof continuousLearningApi.registerHeuristic, 'function');
    assert.strictEqual(typeof continuousLearningApi.listHeuristics, 'function');
    assert.strictEqual(typeof continuousLearningApi.submitCorrection, 'function');
    assert.strictEqual(typeof continuousLearningApi.getGovernancePolicy, 'function');
  });

  test('LearningView initializes with Task 52 continuous learning state', () => {
    const mockContainer = {
      innerHTML: '',
      querySelector: () => null,
      querySelectorAll: () => [],
    };

    const view = new LearningView(mockContainer);
    assert.strictEqual(view.activeTab, 'strategies');
    assert.strictEqual(view.isLoading, false);
    assert.deepStrictEqual(view.lessons, []);
    assert.deepStrictEqual(view.workflows, []);
    assert.deepStrictEqual(view.heuristics, []);
    assert.strictEqual(view.governancePolicy, null);
  });

  test('LearningView status badge maps Task 52 lesson and strategy statuses accurately', () => {
    const mockContainer = {
      innerHTML: '',
      querySelector: () => null,
      querySelectorAll: () => [],
    };

    const view = new LearningView(mockContainer);
    assert.match(view.getStatusBadge('ACTIVE'), /badge-success/);
    assert.match(view.getStatusBadge('EXPERIMENTAL'), /badge-info/);
    assert.match(view.getStatusBadge('CANDIDATE'), /badge-warning/);
    assert.match(view.getStatusBadge('WEAKENED'), /badge-warning/);
    assert.match(view.getStatusBadge('SUPERSEDED'), /badge-secondary/);
    assert.match(view.getStatusBadge('DEPRECATED'), /badge-secondary/);
    assert.match(view.getStatusBadge('BLOCKED'), /badge-danger/);
    assert.match(view.getStatusBadge('ROLLED_BACK'), /badge-danger/);
    assert.match(view.getStatusBadge('REJECTED'), /badge-danger/);
  });

  test('LearningView formatting helpers format numeric values safely', () => {
    const mockContainer = {
      innerHTML: '',
      querySelector: () => null,
      querySelectorAll: () => [],
    };

    const view = new LearningView(mockContainer);
    assert.strictEqual(view.formatPercent(0.925), '92.5%');
    assert.strictEqual(view.formatPercent(null), '0.0%');
    assert.strictEqual(view.formatLatency(350), '350ms');
    assert.strictEqual(view.formatLatency(1500), '1.50s');
    assert.strictEqual(view.formatCost(0.0125), '$0.0125');
  });
});
