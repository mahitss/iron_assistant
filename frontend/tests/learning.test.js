/**
 * Unit tests for Kairo Adaptive Learning & Strategy Optimization Engine (Task 43)
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { endpoints } from '../lib/api/endpoints.js';
import { LearningView } from '../components/learning/learningView.js';

describe('Adaptive Learning & Strategy Optimization Engine Endpoints (Task 43)', () => {
  test('Endpoints exposes all learning methods', () => {
    assert.strictEqual(typeof endpoints.listLearningStrategies, 'function');
    assert.strictEqual(typeof endpoints.getLearningStrategy, 'function');
    assert.strictEqual(typeof endpoints.registerLearningStrategy, 'function');
    assert.strictEqual(typeof endpoints.getLearningRecommendations, 'function');
    assert.strictEqual(typeof endpoints.listLearningExperiences, 'function');
    assert.strictEqual(typeof endpoints.recordLearningExperience, 'function');
    assert.strictEqual(typeof endpoints.listLearningFailures, 'function');
    assert.strictEqual(typeof endpoints.checkPreFlightWarning, 'function');
    assert.strictEqual(typeof endpoints.listLearningExperiments, 'function');
    assert.strictEqual(typeof endpoints.createLearningExperiment, 'function');
    assert.strictEqual(typeof endpoints.promoteLearningStrategy, 'function');
    assert.strictEqual(typeof endpoints.rollbackLearningStrategy, 'function');
    assert.strictEqual(typeof endpoints.submitLearningFeedback, 'function');
    assert.strictEqual(typeof endpoints.getLearningStats, 'function');
  });

  test('LearningView initializes with default state and containers', () => {
    const mockContainer = {
      innerHTML: '',
      querySelector: () => null,
      querySelectorAll: () => [],
    };

    const view = new LearningView(mockContainer);
    assert.strictEqual(view.activeTab, 'strategies');
    assert.strictEqual(view.isLoading, false);
    assert.deepStrictEqual(view.strategies, []);
    assert.deepStrictEqual(view.experiences, []);
    assert.deepStrictEqual(view.failurePatterns, []);
    assert.deepStrictEqual(view.experiments, []);
    assert.deepStrictEqual(view.recommendations, []);
  });

  test('LearningView status badge helper maps strategy statuses accurately', () => {
    const mockContainer = {
      innerHTML: '',
      querySelector: () => null,
      querySelectorAll: () => [],
    };

    const view = new LearningView(mockContainer);
    assert.match(view.getStatusBadge('ACTIVE'), /badge-success/);
    assert.match(view.getStatusBadge('EXPERIMENTAL'), /badge-info/);
    assert.match(view.getStatusBadge('CANDIDATE'), /badge-warning/);
    assert.match(view.getStatusBadge('DEPRECATED'), /badge-secondary/);
    assert.match(view.getStatusBadge('BLOCKED'), /badge-danger/);
    assert.match(view.getStatusBadge('ROLLED_BACK'), /badge-danger/);
  });

  test('LearningView formatting helpers format numbers and rates safely', () => {
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
