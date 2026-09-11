/**
 * Unit tests for Kairo Autonomous Goal Management & Self-Directed Mission Engine (Task 66).
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { endpoints, missionsApi, missionControlApi } from '../lib/api/endpoints.js';
import { MissionControlView } from '../components/missions/missionControlView.js';

describe('Autonomous Goal Management & Mission Engine Endpoints (Task 66)', () => {
  test('Endpoints exposes all mission control methods', () => {
    assert.strictEqual(typeof endpoints.createMission, 'function');
    assert.strictEqual(typeof endpoints.listMissions, 'function');
    assert.strictEqual(typeof endpoints.getMissionOverview, 'function');
    assert.strictEqual(typeof endpoints.getMission, 'function');
    assert.strictEqual(typeof endpoints.startMission, 'function');
    assert.strictEqual(typeof endpoints.pauseMission, 'function');
    assert.strictEqual(typeof endpoints.resumeMission, 'function');
    assert.strictEqual(typeof endpoints.cancelMission, 'function');
    assert.strictEqual(typeof endpoints.replanMission, 'function');
    assert.strictEqual(typeof endpoints.executeSupervisoryCycle, 'function');
    assert.strictEqual(typeof endpoints.completeMission, 'function');
    assert.strictEqual(typeof endpoints.getMissionAuditTrail, 'function');
    assert.strictEqual(typeof endpoints.verifyMissionAuditChain, 'function');
    assert.strictEqual(typeof endpoints.getMissionControlHealth, 'function');
    assert.strictEqual(typeof endpoints.getMissionGoals, 'function');
    assert.strictEqual(typeof endpoints.getMissionTasks, 'function');
    assert.strictEqual(typeof endpoints.getMissionProgress, 'function');
    assert.strictEqual(typeof endpoints.getMissionBlockers, 'function');
    assert.strictEqual(typeof endpoints.getMissionTimeline, 'function');
    assert.strictEqual(typeof endpoints.getMissionDecisions, 'function');
    assert.strictEqual(typeof endpoints.getMissionRisks, 'function');
    assert.strictEqual(typeof endpoints.reassessMission, 'function');
    assert.strictEqual(typeof endpoints.verifyMission, 'function');
  });

  test('missionsApi and missionControlApi wrappers expose mapped methods', () => {
    assert.strictEqual(typeof missionsApi.createMission, 'function');
    assert.strictEqual(typeof missionsApi.listMissions, 'function');
    assert.strictEqual(typeof missionsApi.getOverview, 'function');
    assert.strictEqual(typeof missionsApi.getMission, 'function');
    assert.strictEqual(typeof missionsApi.startMission, 'function');
    assert.strictEqual(typeof missionsApi.pauseMission, 'function');
    assert.strictEqual(typeof missionsApi.resumeMission, 'function');
    assert.strictEqual(typeof missionsApi.cancelMission, 'function');
    assert.strictEqual(typeof missionsApi.replanMission, 'function');
    assert.strictEqual(typeof missionsApi.executeSupervisoryCycle, 'function');
    assert.strictEqual(typeof missionsApi.completeMission, 'function');
    assert.strictEqual(typeof missionsApi.getAuditTrail, 'function');
    assert.strictEqual(typeof missionsApi.verifyAuditChain, 'function');
    assert.strictEqual(typeof missionsApi.getHealth, 'function');
    assert.strictEqual(typeof missionsApi.getGoals, 'function');
    assert.strictEqual(typeof missionsApi.getTasks, 'function');
    assert.strictEqual(typeof missionsApi.getProgress, 'function');
    assert.strictEqual(typeof missionsApi.getBlockers, 'function');
    assert.strictEqual(typeof missionsApi.getTimeline, 'function');
    assert.strictEqual(typeof missionsApi.getDecisions, 'function');
    assert.strictEqual(typeof missionsApi.getRisks, 'function');
    assert.strictEqual(typeof missionsApi.reassess, 'function');
    assert.strictEqual(typeof missionsApi.verify, 'function');

    // Alias equality
    assert.strictEqual(missionControlApi, missionsApi);
  });
});

describe('MissionControlView Component (Task 66)', () => {
  test('initializes with active_missions tab and default state', () => {
    const view = new MissionControlView(null);
    assert.strictEqual(view.activeTab, 'active_missions');
    assert.deepStrictEqual(view.missions, []);
    assert.strictEqual(view.selectedMission, null);
    assert.strictEqual(view.overview, null);
    assert.strictEqual(view.isLoading, false);
    assert.strictEqual(view.error, null);
  });

  test('setTab updates active tab appropriately', () => {
    const view = new MissionControlView(null);
    assert.strictEqual(view.activeTab, 'active_missions');
    view.setTab('goal_hierarchy');
    assert.strictEqual(view.activeTab, 'goal_hierarchy');
    view.setTab('milestone_verification');
    assert.strictEqual(view.activeTab, 'milestone_verification');
    view.setTab('drift_goodhart');
    assert.strictEqual(view.activeTab, 'drift_goodhart');
    view.setTab('blockers_escalation');
    assert.strictEqual(view.activeTab, 'blockers_escalation');
    view.setTab('supervisory_loop');
    assert.strictEqual(view.activeTab, 'supervisory_loop');
    view.setTab('audit_provenance');
    assert.strictEqual(view.activeTab, 'audit_provenance');
  });

  test('selectMission assigns object directly when provided', async () => {
    const view = new MissionControlView(null);
    const mockMission = {
      mission_id: 'mis-test-999',
      title: 'Strategic Autonomous Infrastructure Upgrade',
      status: 'RUNNING',
      health: 'ON_TRACK',
      progress_pct: 0.45,
      authority_scope: 'SUPERVISED',
      version: 1,
      goal: {
        goal_id: 'goal-root',
        description: 'Upgrade infrastructure components safely',
        hierarchy_level: 'MISSION',
        authority_scope: 'SUPERVISED',
        success_criteria: [{ name: 'Latency', target_value: '< 50ms' }],
        failure_conditions: [{ condition: 'Downtime > 0s' }],
      },
      active_plan: {
        milestones: [{ name: 'Pre-flight checks', is_verified: true, progress_weight: 0.5 }],
      },
      blockers: [],
      checkpoints: [{ checkpoint_id: 'chk-1' }],
    };

    await view.selectMission(mockMission);
    assert.strictEqual(view.selectedMission, mockMission);
    assert.strictEqual(view.selectedMission.mission_id, 'mis-test-999');
    assert.strictEqual(view.selectedMission.health, 'ON_TRACK');
  });
});
