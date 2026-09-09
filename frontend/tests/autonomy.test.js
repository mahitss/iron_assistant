/**
 * Unit tests for Kairo Autonomous Execution & Long-Horizon Agency Engine (Task 45)
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { endpoints } from '../lib/api/endpoints.js';
import { AutonomyView } from '../components/autonomy/autonomyView.js';

describe('Autonomous Execution Engine Endpoints & UI (Task 45)', () => {
  test('Endpoints exposes all Task 45 autonomy methods', () => {
    assert.strictEqual(typeof endpoints.createAutonomousGoal, 'function');
    assert.strictEqual(typeof endpoints.getAutonomousGoal, 'function');
    assert.strictEqual(typeof endpoints.createAutonomousRun, 'function');
    assert.strictEqual(typeof endpoints.getAutonomousRun, 'function');
    assert.strictEqual(typeof endpoints.controlAutonomousRun, 'function');
    assert.strictEqual(typeof endpoints.executeAutonomousStep, 'function');
    assert.strictEqual(typeof endpoints.getAutonomousProgress, 'function');
    assert.strictEqual(typeof endpoints.getAutonomousCheckpoints, 'function');
    assert.strictEqual(typeof endpoints.getAutonomousCompletion, 'function');
    assert.strictEqual(typeof endpoints.getAutonomousWatchdog, 'function');
    assert.strictEqual(typeof endpoints.postAutonomousEvent, 'function');
  });

  test('AutonomyView initializes with default state and containers', () => {
    const mockContainer = {
      innerHTML: '',
      querySelector: () => null,
      querySelectorAll: () => [],
    };

    const view = new AutonomyView(mockContainer);
    assert.strictEqual(view.activeTab, 'runs');
    assert.strictEqual(view.isLoading, false);
    assert.deepStrictEqual(view.runs, []);
    assert.deepStrictEqual(view.goals, []);
    assert.deepStrictEqual(view.checkpoints, []);
    assert.strictEqual(view.progress, null);
    assert.strictEqual(view.completion, null);
    assert.strictEqual(view.watchdog, null);
  });

  test('AutonomyView formatPercent formats correctly', () => {
    const view = new AutonomyView({});
    assert.strictEqual(view.formatPercent(null), '0.0%');
    assert.strictEqual(view.formatPercent(45.678), '45.7%');
    assert.strictEqual(view.formatPercent(100), '100.0%');
  });

  test('AutonomyView renders HTML skeleton structure', async () => {
    let htmlOutput = '';
    const mockContainer = {
      set innerHTML(val) {
        htmlOutput = val;
      },
      querySelector: () => null,
      querySelectorAll: () => [],
    };

    const view = new AutonomyView(mockContainer);
    await view.render();
    assert.ok(htmlOutput.includes('Autonomous Execution & Long-Horizon Agency'));
    assert.ok(htmlOutput.includes('metrics-grid'));
    assert.ok(htmlOutput.includes('Durable Checkpoints'));
    assert.ok(htmlOutput.includes('Completion Certificate'));
  });
});
