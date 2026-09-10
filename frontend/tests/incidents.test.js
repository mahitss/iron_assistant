/**
 * Unit tests for Kairo Incident Response & Recovery Autonomy Engine (Task 61).
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { endpoints, incidentsApi } from '../lib/api/endpoints.js';
import { IncidentsView } from '../components/incidents/incidentsView.js';

describe('Incident Response Endpoints (Task 61)', () => {
  test('Endpoints exposes all incident response methods', () => {
    assert.strictEqual(typeof endpoints.createIncidentFromSituation, 'function');
    assert.strictEqual(typeof endpoints.listIncidents, 'function');
    assert.strictEqual(typeof endpoints.getIncident, 'function');
    assert.strictEqual(typeof endpoints.triageIncident, 'function');
    assert.strictEqual(typeof endpoints.addIncidentEvidence, 'function');
    assert.strictEqual(typeof endpoints.selectIncidentOption, 'function');
    assert.strictEqual(typeof endpoints.approveIncidentAction, 'function');
    assert.strictEqual(typeof endpoints.verifyRecoveryCheckpoint, 'function');
    assert.strictEqual(typeof endpoints.resolveIncident, 'function');
    assert.strictEqual(typeof endpoints.reopenIncident, 'function');
    assert.strictEqual(typeof endpoints.getIncidentPostmortem, 'function');
    assert.strictEqual(typeof endpoints.getIncidentAudit, 'function');
  });

  test('incidentsApi wrapper exposes mapped methods', () => {
    assert.strictEqual(typeof incidentsApi.createFromSituation, 'function');
    assert.strictEqual(typeof incidentsApi.list, 'function');
    assert.strictEqual(typeof incidentsApi.get, 'function');
    assert.strictEqual(typeof incidentsApi.triage, 'function');
    assert.strictEqual(typeof incidentsApi.addEvidence, 'function');
    assert.strictEqual(typeof incidentsApi.selectOption, 'function');
    assert.strictEqual(typeof incidentsApi.approveAction, 'function');
    assert.strictEqual(typeof incidentsApi.verifyCheckpoint, 'function');
    assert.strictEqual(typeof incidentsApi.resolve, 'function');
    assert.strictEqual(typeof incidentsApi.reopen, 'function');
    assert.strictEqual(typeof incidentsApi.getPostmortem, 'function');
    assert.strictEqual(typeof incidentsApi.getAudit, 'function');
  });
});

describe('IncidentsView Component', () => {
  test('initializes with default tab and empty states', () => {
    const view = new IncidentsView('mock-container');
    assert.strictEqual(view.activeTab, 'incidents');
    assert.strictEqual(view.incidents.length, 0);
    assert.strictEqual(view.auditEvents.length, 0);
    assert.strictEqual(view.selectedIncident, null);
    assert.strictEqual(view.isLoading, false);
  });

  test('switches tabs correctly', () => {
    const view = new IncidentsView('mock-container');
    view.setTab('investigation');
    assert.strictEqual(view.activeTab, 'investigation');
    view.setTab('hypotheses');
    assert.strictEqual(view.activeTab, 'hypotheses');
    view.setTab('options');
    assert.strictEqual(view.activeTab, 'options');
    view.setTab('recovery');
    assert.strictEqual(view.activeTab, 'recovery');
    view.setTab('postmortem');
    assert.strictEqual(view.activeTab, 'postmortem');
    view.setTab('audit');
    assert.strictEqual(view.activeTab, 'audit');
  });

  test('selects incident correctly', () => {
    const view = new IncidentsView('mock-container');
    const mockIncident = {
      incident_id: 'inc_test_789',
      title: 'Database replica synchronization lag',
      status: 'INVESTIGATING',
      severity: 'HIGH',
      urgency: 'IMMEDIATE',
      environment: 'production',
      affected_resources: ['db-replica-2'],
      timeline: [],
      hypotheses: [],
    };
    view.selectIncident(mockIncident);
    assert.strictEqual(view.selectedIncident.incident_id, 'inc_test_789');
    assert.strictEqual(view.selectedIncident.status, 'INVESTIGATING');
    assert.strictEqual(view.selectedIncident.severity, 'HIGH');
  });
});
