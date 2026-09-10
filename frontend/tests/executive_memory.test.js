/**
 * Unit tests for Kairo Executive Memory, Long-Horizon Context, and Continuity Engine (Task 53)
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { endpoints, executiveMemoryApi } from '../lib/api/endpoints.js';
import { ExecutiveMemoryView } from '../components/executive_memory/executiveMemoryView.js';

describe('Executive Memory & Long-Horizon Context Endpoints (Task 53)', () => {
  test('Endpoints exposes all executive memory methods', () => {
    assert.strictEqual(typeof endpoints.queryExecutiveContinuity, 'function');
    assert.strictEqual(typeof endpoints.getExecutiveState, 'function');
    assert.strictEqual(typeof endpoints.synthesizeExecutiveState, 'function');
    assert.strictEqual(typeof endpoints.listExecutiveTimeline, 'function');
    assert.strictEqual(typeof endpoints.recordExecutiveTimelineEvent, 'function');
    assert.strictEqual(typeof endpoints.reconstructExecutiveAsOf, 'function');
    assert.strictEqual(typeof endpoints.listExecutiveOpenLoops, 'function');
    assert.strictEqual(typeof endpoints.createExecutiveOpenLoop, 'function');
    assert.strictEqual(typeof endpoints.updateExecutiveOpenLoopStatus, 'function');
    assert.strictEqual(typeof endpoints.closeExecutiveOpenLoop, 'function');
    assert.strictEqual(typeof endpoints.listExecutiveBlockers, 'function');
    assert.strictEqual(typeof endpoints.createExecutiveBlocker, 'function');
    assert.strictEqual(typeof endpoints.resolveExecutiveBlocker, 'function');
    assert.strictEqual(typeof endpoints.listExecutiveMilestones, 'function');
    assert.strictEqual(typeof endpoints.createExecutiveMilestone, 'function');
    assert.strictEqual(typeof endpoints.achieveExecutiveMilestone, 'function');
    assert.strictEqual(typeof endpoints.getExecutiveBrief, 'function');
    assert.strictEqual(typeof endpoints.generateExecutiveBrief, 'function');
    assert.strictEqual(typeof endpoints.getExecutiveNextActions, 'function');
    assert.strictEqual(typeof endpoints.createExecutiveCheckpoint, 'function');
    assert.strictEqual(typeof endpoints.resumeExecutiveCheckpoint, 'function');
    assert.strictEqual(typeof endpoints.reconcileExecutiveState, 'function');
    assert.strictEqual(typeof endpoints.getExecutiveMemoryMetrics, 'function');
  });

  test('executiveMemoryApi wrapper exposes mapped methods', () => {
    assert.strictEqual(typeof executiveMemoryApi.queryContinuity, 'function');
    assert.strictEqual(typeof executiveMemoryApi.getState, 'function');
    assert.strictEqual(typeof executiveMemoryApi.synthesizeState, 'function');
    assert.strictEqual(typeof executiveMemoryApi.listTimeline, 'function');
    assert.strictEqual(typeof executiveMemoryApi.recordEvent, 'function');
    assert.strictEqual(typeof executiveMemoryApi.reconstructAsOf, 'function');
    assert.strictEqual(typeof executiveMemoryApi.listOpenLoops, 'function');
    assert.strictEqual(typeof executiveMemoryApi.createOpenLoop, 'function');
    assert.strictEqual(typeof executiveMemoryApi.updateOpenLoopStatus, 'function');
    assert.strictEqual(typeof executiveMemoryApi.closeOpenLoop, 'function');
    assert.strictEqual(typeof executiveMemoryApi.listBlockers, 'function');
    assert.strictEqual(typeof executiveMemoryApi.createBlocker, 'function');
    assert.strictEqual(typeof executiveMemoryApi.resolveBlocker, 'function');
    assert.strictEqual(typeof executiveMemoryApi.listMilestones, 'function');
    assert.strictEqual(typeof executiveMemoryApi.createMilestone, 'function');
    assert.strictEqual(typeof executiveMemoryApi.achieveMilestone, 'function');
    assert.strictEqual(typeof executiveMemoryApi.getBrief, 'function');
    assert.strictEqual(typeof executiveMemoryApi.generateBrief, 'function');
    assert.strictEqual(typeof executiveMemoryApi.getNextActions, 'function');
    assert.strictEqual(typeof executiveMemoryApi.createCheckpoint, 'function');
    assert.strictEqual(typeof executiveMemoryApi.resumeCheckpoint, 'function');
    assert.strictEqual(typeof executiveMemoryApi.reconcile, 'function');
    assert.strictEqual(typeof executiveMemoryApi.getMetrics, 'function');
  });

  test('ExecutiveMemoryView initializes with Task 53 state', () => {
    const mockContainer = {
      innerHTML: '',
      querySelector: () => null,
      querySelectorAll: () => [],
    };

    const view = new ExecutiveMemoryView(mockContainer);
    assert.strictEqual(view.activeTab, 'brief');
    assert.strictEqual(view.projectId, 'default_project');
    assert.strictEqual(view.isLoading, false);
    assert.deepStrictEqual(view.openLoops, []);
    assert.deepStrictEqual(view.blockers, []);
    assert.deepStrictEqual(view.timelineEvents, []);
    assert.strictEqual(view.brief, null);
  });

  test('ExecutiveMemoryView formats dates safely', () => {
    const mockContainer = {
      innerHTML: '',
      querySelector: () => null,
      querySelectorAll: () => [],
    };

    const view = new ExecutiveMemoryView(mockContainer);
    assert.strictEqual(view.formatDate(null), 'N/A');
    assert.strictEqual(view.formatDate(''), 'N/A');
    const formatted = view.formatDate('2026-09-10T12:00:00Z');
    assert.ok(typeof formatted === 'string' && formatted.length > 0);
  });

  test('ExecutiveMemoryView renders skeleton properly', () => {
    let htmlOutput = '';
    const mockContainer = {
      set innerHTML(val) {
        htmlOutput = val;
      },
      get innerHTML() {
        return htmlOutput;
      },
      querySelector: () => null,
      querySelectorAll: () => [],
    };

    const view = new ExecutiveMemoryView(mockContainer);
    view.renderSkeleton();
    assert.ok(htmlOutput.includes('Executive Memory & Long-Horizon Context'));
    assert.ok(htmlOutput.includes('Loading Executive State...'));
  });
});
