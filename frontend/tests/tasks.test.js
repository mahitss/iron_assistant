import test from 'node:test';
import assert from 'node:assert/strict';
import { Endpoints } from '../lib/api/endpoints.js';
import { TasksView } from '../components/tasks/tasksView.js';
import { AppShell } from '../components/layout/shell.js';

test('Kairo Autonomous Task Engine Frontend Tests (Task 31)', async (t) => {
  await t.test('Endpoints object defines all required Autonomous Task API methods (Spec 123)', () => {
    assert.strictEqual(typeof Endpoints.createTask, 'function');
    assert.strictEqual(typeof Endpoints.getTasks, 'function');
    assert.strictEqual(typeof Endpoints.getTask, 'function');
    assert.strictEqual(typeof Endpoints.pauseTask, 'function');
    assert.strictEqual(typeof Endpoints.resumeTask, 'function');
    assert.strictEqual(typeof Endpoints.cancelTask, 'function');
    assert.strictEqual(typeof Endpoints.retryTask, 'function');
    assert.strictEqual(typeof Endpoints.approveTaskStep, 'function');
    assert.strictEqual(typeof Endpoints.respondToTask, 'function');
    assert.strictEqual(typeof Endpoints.getTaskActivity, 'function');
    assert.strictEqual(typeof Endpoints.getTaskPlans, 'function');
  });

  await t.test('TasksView renders page header, action buttons, and filter tabs (Spec 85)', async () => {
    const mockContainer = { innerHTML: '', querySelector: () => null, querySelectorAll: () => [] };
    const view = new TasksView(mockContainer);

    // Mock Endpoints.getTasks
    const origGetTasks = Endpoints.getTasks;
    Endpoints.getTasks = async () => [];

    try {
      await view.render();
      const html = mockContainer.innerHTML;

      assert.ok(html.includes('Autonomous Tasks'), 'Header title must be present');
      assert.ok(html.includes('id="new-task-btn"'), 'New Task button must be present');
      assert.ok(html.includes('id="refresh-tasks-btn"'), 'Refresh button must be present');
      assert.ok(html.includes('data-tab="all"'), 'All tab must be present');
      assert.ok(html.includes('data-tab="active"'), 'Active tab must be present');
      assert.ok(html.includes('data-tab="waiting"'), 'Waiting tab must be present');
      assert.ok(html.includes('data-tab="completed"'), 'Completed tab must be present');
      assert.ok(html.includes('data-tab="failed"'), 'Failed tab must be present');
    } finally {
      Endpoints.getTasks = origGetTasks;
      view.destroy();
    }
  });

  await t.test('TasksView renders task detail with step DAG progress (Spec 86)', () => {
    let renderedHtml = '';
    const mockPanel = {
      set innerHTML(val) { renderedHtml = val; },
      get innerHTML() { return renderedHtml; },
      querySelector: () => null,
      querySelectorAll: () => [],
    };
    const mockContainer = {
      innerHTML: '',
      querySelector: (sel) => (sel === '#task-detail-panel' ? mockPanel : null),
      querySelectorAll: () => [],
    };

    const view = new TasksView(mockContainer);
    const mockTask = {
      id: 'task_ci_001',
      objective: 'Investigate CI failure',
      status: 'RUNNING',
      priority: 'NORMAL',
      autonomy_level: 'SUPERVISED',
      total_steps: 4,
      completed_steps: 2,
      progress_text: '2/4 steps complete',
      plan_version: 1,
      steps: [
        { sequence: 1, title: 'Inspect CI logs', objective: 'Fetch logs', status: 'COMPLETED', risk_level: 'READ' },
        { sequence: 2, title: 'Identify commit', objective: 'Git diff', status: 'COMPLETED', risk_level: 'READ' },
        { sequence: 3, title: 'Propose fix', objective: 'Generate patch', status: 'RUNNING', risk_level: 'READ' },
        { sequence: 4, title: 'Apply fix', objective: 'Write file', status: 'PENDING', risk_level: 'WRITE' },
      ],
    };

    view._renderTaskDetail(mockTask);

    assert.ok(renderedHtml.includes('Investigate CI failure'));
    assert.ok(renderedHtml.includes('2/4 steps complete'));
    assert.ok(renderedHtml.includes('50%')); // 2 of 4 = 50%
    assert.ok(renderedHtml.includes('Inspect CI logs'));
    assert.ok(renderedHtml.includes('Apply fix'));
    assert.ok(renderedHtml.includes('id="pause-task-btn"'));
    assert.ok(renderedHtml.includes('id="cancel-task-btn"'));
  });

  await t.test('TasksView renders human approval card when task is WAITING_APPROVAL (Spec 87)', () => {
    let renderedHtml = '';
    const mockPanel = {
      set innerHTML(val) { renderedHtml = val; },
      get innerHTML() { return renderedHtml; },
      querySelector: () => null,
      querySelectorAll: () => [],
    };
    const mockContainer = {
      innerHTML: '',
      querySelector: (sel) => (sel === '#task-detail-panel' ? mockPanel : null),
      querySelectorAll: () => [],
    };

    const view = new TasksView(mockContainer);
    const mockTask = {
      id: 'task_appr_001',
      objective: 'Fix CI deployment',
      status: 'WAITING_APPROVAL',
      priority: 'HIGH',
      autonomy_level: 'SUPERVISED',
      total_steps: 2,
      completed_steps: 1,
      progress_text: '1/2 steps complete',
      plan_version: 1,
      pending_approval: {
        action: 'Modify deployment configuration',
        target: 'Kairo repository',
        risk: 'WRITE',
      },
      steps: [],
    };

    view._renderTaskDetail(mockTask);

    assert.ok(renderedHtml.includes('ACTION REQUIRES HUMAN APPROVAL'), 'Approval banner must be visible');
    assert.ok(renderedHtml.includes('Modify deployment configuration'), 'Action title must be visible');
    assert.ok(renderedHtml.includes('id="btn-approve-action"'), 'Approve button must be present');
    assert.ok(renderedHtml.includes('id="btn-reject-action"'), 'Reject button must be present');
  });

  await t.test('TasksView renders clarification prompt when task is WAITING_USER (Spec 88)', () => {
    let renderedHtml = '';
    const mockPanel = {
      set innerHTML(val) { renderedHtml = val; },
      get innerHTML() { return renderedHtml; },
      querySelector: () => null,
      querySelectorAll: () => [],
    };
    const mockContainer = {
      innerHTML: '',
      querySelector: (sel) => (sel === '#task-detail-panel' ? mockPanel : null),
      querySelectorAll: () => [],
    };

    const view = new TasksView(mockContainer);
    const mockTask = {
      id: 'task_user_001',
      objective: 'Setup environment',
      status: 'WAITING_USER',
      priority: 'NORMAL',
      autonomy_level: 'SUPERVISED',
      total_steps: 1,
      completed_steps: 0,
      progress_text: '0/1 steps complete',
      plan_version: 1,
      waiting_user_question: 'Which environment should I investigate?',
      steps: [],
    };

    view._renderTaskDetail(mockTask);

    assert.ok(renderedHtml.includes('CLARIFICATION REQUIRED'), 'Clarification banner must be visible');
    assert.ok(renderedHtml.includes('Which environment should I investigate?'), 'Question must be visible');
    assert.ok(renderedHtml.includes('id="user-clarification-input"'), 'Input must be present');
    assert.ok(renderedHtml.includes('id="btn-submit-clarification"'), 'Submit button must be present');
  });

  await t.test('AppShell renders Tasks navigation item under COMMAND CENTER', () => {
    const mockStore = {
      getState: () => ({
        emergencyStop: { is_stopped: false },
        activeProject: null,
        projects: [],
        unreadNotificationCount: 0,
        currentView: 'tasks',
        pendingApprovals: [],
        activeTasksCount: 2,
      }),
    };

    const shell = new AppShell({ store: mockStore });
    const html = shell.render();

    assert.ok(html.includes("navigateTo('tasks')"), 'Must have Tasks navigation action');
    assert.ok(html.includes('Tasks</span>'), 'Tasks label must be rendered');
    assert.ok(html.includes('<span class="pending-pill">2</span>'), 'Active tasks count badge must be rendered');
  });
});
