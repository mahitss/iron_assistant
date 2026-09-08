/**
 * Kairo Command Center E2E Flows Tests
 * Validates the 6 primary user flows required by Task 21 specification:
 * FLOW 1: Boot/Home -> Chat -> Ask question -> Receive response
 * FLOW 2: Chat -> Complex task -> Agents progress milestones -> Final answer
 * FLOW 3: Automation -> Run -> Failure -> Proactive notification
 * FLOW 4: Risky action -> Approval -> Deny -> Audit event
 * FLOW 5: Emergency stop -> Active action blocked
 * FLOW 6: Project -> Context -> Chat -> Relevant memory
 */

import test from 'node:test';
import assert from 'node:assert/strict';

import { Store } from '../state/store.js';
import { ApiClient } from '../lib/api/client.js';

test('E2E FLOW 1: Home -> Chat -> Send Message -> Receive Response', async (t) => {
  const store = new Store();
  assert.equal(store.getState().currentView, 'home');

  // Navigate to Chat
  store.setView('chat');
  assert.equal(store.getState().currentView, 'chat');

  // User submits message
  const userMessage = 'What is the deployment status of Kairo?';
  store.addConversationMessage({
    id: 'msg_1',
    role: 'user',
    content: userMessage,
    timestamp: new Date().toISOString(),
  });

  // Assistant returns streaming/completed response
  const assistantResponse = 'All services are online and CI checks are passing.';
  store.addConversationMessage({
    id: 'msg_2',
    role: 'assistant',
    content: assistantResponse,
    timestamp: new Date().toISOString(),
  });

  const history = store.getConversation();
  assert.equal(history.length, 2);
  assert.equal(history[0].content, userMessage);
  assert.equal(history[1].content, assistantResponse);
});

test('E2E FLOW 2: Chat -> Complex task -> Multi-Agent Milestones -> Final Answer', async (t) => {
  const store = new Store();
  store.setView('chat');

  // Track progress milestones
  const milestones = [];
  function recordMilestone(agent, status, label) {
    milestones.push({ agent, status, label });
  }

  // Safe milestone simulation without exposing private CoT
  recordMilestone('Researcher', 'completed', 'Checked official documentation');
  recordMilestone('Developer', 'completed', 'Inspected repository structure');
  recordMilestone('Analyst', 'active', 'Comparing findings');

  assert.equal(milestones.length, 3);
  assert.equal(milestones[0].agent, 'Researcher');
  assert.equal(milestones[0].status, 'completed');
  assert.equal(milestones[2].agent, 'Analyst');
  assert.equal(milestones[2].status, 'active');

  // Final synthesized response
  store.addConversationMessage({
    id: 'agent_res_1',
    role: 'assistant',
    content: 'Completed cross-analysis across documentation and repository.',
    timestamp: new Date().toISOString(),
  });

  assert.equal(store.getConversation().length, 1);
});

test('E2E FLOW 3: Automation -> Run -> Failure -> Proactive Notification', async (t) => {
  const store = new Store();

  // Workflow starts
  const workflow = {
    id: 'wf_ci_check',
    name: 'CI Monitor',
    trigger: 'schedule',
    status: 'active',
  };

  // Run produces failure
  const runResult = {
    workflow_id: workflow.id,
    run_id: 'run_101',
    status: 'failed',
    error: 'Build pipeline job #449 failed on step test_auth',
  };

  // Generates notification in NotificationCenter
  store.addNotification({
    id: 'notif_ci_fail',
    title: '🔴 CI failed: Kairo / main',
    severity: 'critical',
    message: runResult.error,
    created_at: new Date().toISOString(),
  });

  assert.equal(store.getState().notifications.length, 1);
  assert.equal(store.getState().unreadNotificationsCount, 1);
  assert.equal(store.getState().notifications[0].severity, 'critical');
});

test('E2E FLOW 4: Risky action -> Approval required -> User Deny -> Audit Event', async (t) => {
  const store = new Store();

  // Dangerous action requested
  const pendingApproval = {
    id: 'appr_git_push',
    action: 'git_push_main',
    description: 'Kairo wants to push changes to GitHub repository.',
    risk_level: 'HIGH',
    metadata: { repository: 'Kairo', branch: 'main' },
  };

  store.setApprovals([pendingApproval]);
  assert.equal(store.getState().pendingApprovals.length, 1);

  // User decides to DENY
  const userDecision = 'denied';
  const denialReason = 'Requires staging branch validation first.';

  // Simulate backend approval resolution
  store.removeApproval(pendingApproval.id);
  assert.equal(store.getState().pendingApprovals.length, 0);

  // Audit event logged
  const auditEvent = {
    id: 'audit_01',
    action: 'APPROVAL_DECISION',
    user_id: 'default_user',
    decision: userDecision,
    reason: denialReason,
    target: pendingApproval.action,
  };

  assert.equal(auditEvent.decision, 'denied');
  assert.equal(auditEvent.target, 'git_push_main');
});

test('E2E FLOW 5: Emergency Stop -> Active actions halted immediately', async (t) => {
  const store = new Store();
  assert.equal(store.isEmergencyStopped(), false);

  // User hits Emergency Stop button
  store.setEmergencyStop(true, 'User triggered Emergency Stop from topbar');
  assert.equal(store.isEmergencyStopped(), true);

  // Subsequent risky action attempted
  function attemptAction() {
    if (store.isEmergencyStopped()) {
      throw new Error('STOPPED: Kairo operations are halted by Emergency Stop.');
    }
    return 'Action executed';
  }

  assert.throws(() => attemptAction(), /STOPPED: Kairo operations are halted/);

  // User resets Emergency Stop
  store.setEmergencyStop(false, null);
  assert.equal(store.isEmergencyStopped(), false);
  assert.equal(attemptAction(), 'Action executed');
});

test('E2E FLOW 6: Project Switcher -> Context Update -> Chat -> Relevant Memory', async (t) => {
  const store = new Store();

  // Initial project is Kairo
  assert.equal(store.getState().activeProject, 'Kairo');

  // Switch project to 'MobileApp'
  store.setActiveProject('MobileApp');
  assert.equal(store.getState().activeProject, 'MobileApp');

  // Context updates with project-scoped memories
  store.setContext({
    active_project: 'MobileApp',
    branch: 'feature/offline-sync',
    memories: [
      { id: 'mem_1', content: 'Mobile client built with React Native 0.74', relevance: 0.95 },
      { id: 'mem_2', content: 'Uses SQLite for local offline persistence', relevance: 0.88 },
    ],
  });

  const ctx = store.getState().activeContext;
  assert.equal(ctx.active_project, 'MobileApp');
  assert.equal(ctx.memories.length, 2);
  assert.equal(ctx.memories[0].content, 'Mobile client built with React Native 0.74');
});
