import test from 'node:test';
import assert from 'node:assert/strict';
import { AgentWorkflowView } from '../agents/agentWorkflowView.js';

test('Frontend Multi-Agent Workflow View Tests', async (t) => {
  await t.test('initializes with default empty state', () => {
    const view = new AgentWorkflowView();
    assert.strictEqual(view.supervisorStatus, 'idle');
    assert.strictEqual(view.tasks.length, 0);
  });

  await t.test('initializes plan with tasks and renders icons', () => {
    const view = new AgentWorkflowView();
    view.initPlan('plan_123', 'Investigate CI Failure', [
      {
        task_id: 't1',
        agent_type: 'RESEARCHER',
        objective: 'Find GitHub docs',
      },
      {
        task_id: 't2',
        agent_type: 'DEVELOPER',
        objective: 'Inspect repository status',
      },
      {
        task_id: 't3',
        agent_type: 'ANALYST',
        objective: 'Compare findings',
        dependencies: ['t1', 't2'],
      },
    ]);

    assert.strictEqual(view.tasks.length, 3);
    assert.strictEqual(view.supervisorStatus, 'running');

    // Update status of researcher
    view.updateTaskStatus('t1', 'COMPLETED', 'Checked documentation');
    assert.strictEqual(view.tasks[0].status, 'COMPLETED');
    assert.strictEqual(view.tasks[0].summary, 'Checked documentation');

    const html = view.renderUI();
    assert.match(html, /KAIRO ORCHESTRATION/);
    assert.match(html, /RESEARCHER/);
    assert.match(html, /DEVELOPER/);
    assert.match(html, /ANALYST/);
    assert.match(html, /SUPERVISOR/);
    assert.match(html, /Checked documentation/);
  });

  await t.test('handles cancellation cleanly', () => {
    const view = new AgentWorkflowView();
    view.initPlan('plan_456', 'Upgrade Python', [
      { task_id: 't1', agent_type: 'RESEARCHER', objective: 'Docs' },
    ]);

    const res = view.cancelTask();
    assert.strictEqual(res.cancelled, true);
    assert.strictEqual(view.supervisorStatus, 'cancelled');
    assert.strictEqual(view.tasks[0].status, 'CANCELLED');
  });
});
