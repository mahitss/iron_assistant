/**
 * Unit tests for Kairo Autonomous World Model & Long-Horizon Foresight Engine (Task 65).
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { endpoints, foresightApi, worldModelApi } from '../lib/api/endpoints.js';
import { WorldModelView } from '../components/world/worldModelView.js';

describe('Autonomous World Model & Foresight Endpoints (Task 65)', () => {
  test('Endpoints exposes all world model and foresight methods', () => {
    assert.strictEqual(typeof endpoints.getWorldModelOverview, 'function');
    assert.strictEqual(typeof endpoints.queryWorldModel, 'function');
    assert.strictEqual(typeof endpoints.listWorldEntities, 'function');
    assert.strictEqual(typeof endpoints.getWorldEntity, 'function');
    assert.strictEqual(typeof endpoints.listWorldRelationships, 'function');
    assert.strictEqual(typeof endpoints.getWorldDiff, 'function');
    assert.strictEqual(typeof endpoints.reassessWorldModel, 'function');
    assert.strictEqual(typeof endpoints.createForecast, 'function');
    assert.strictEqual(typeof endpoints.listForecasts, 'function');
    assert.strictEqual(typeof endpoints.getForecast, 'function');
    assert.strictEqual(typeof endpoints.getForecastEvidence, 'function');
    assert.strictEqual(typeof endpoints.getForecastAssumptions, 'function');
    assert.strictEqual(typeof endpoints.getForecastScenarios, 'function');
    assert.strictEqual(typeof endpoints.getForecastOutcomes, 'function');
    assert.strictEqual(typeof endpoints.createScenario, 'function');
    assert.strictEqual(typeof endpoints.listScenarios, 'function');
    assert.strictEqual(typeof endpoints.listStrategicRisks, 'function');
    assert.strictEqual(typeof endpoints.listStrategicOpportunities, 'function');
    assert.strictEqual(typeof endpoints.listEarlyWarnings, 'function');
    assert.strictEqual(typeof endpoints.getForesightAudit, 'function');
    assert.strictEqual(typeof endpoints.getForesightHealth, 'function');
  });

  test('foresightApi and worldModelApi wrappers expose mapped methods', () => {
    assert.strictEqual(typeof foresightApi.getOverview, 'function');
    assert.strictEqual(typeof foresightApi.query, 'function');
    assert.strictEqual(typeof foresightApi.listEntities, 'function');
    assert.strictEqual(typeof foresightApi.getEntity, 'function');
    assert.strictEqual(typeof foresightApi.listRelationships, 'function');
    assert.strictEqual(typeof foresightApi.getDiff, 'function');
    assert.strictEqual(typeof foresightApi.reassess, 'function');
    assert.strictEqual(typeof foresightApi.createForecast, 'function');
    assert.strictEqual(typeof foresightApi.listForecasts, 'function');
    assert.strictEqual(typeof foresightApi.getForecast, 'function');
    assert.strictEqual(typeof foresightApi.createScenario, 'function');
    assert.strictEqual(typeof foresightApi.listScenarios, 'function');
    assert.strictEqual(typeof foresightApi.listRisks, 'function');
    assert.strictEqual(typeof foresightApi.listOpportunities, 'function');
    assert.strictEqual(typeof foresightApi.listEarlyWarnings, 'function');
    assert.strictEqual(typeof foresightApi.getAudit, 'function');
    assert.strictEqual(typeof foresightApi.getHealth, 'function');

    // Alias equality
    assert.strictEqual(worldModelApi, foresightApi);
  });
});

describe('WorldModelView Component (Task 65)', () => {
  test('initializes with overview tab and empty initial collections', () => {
    const view = new WorldModelView('mock-world-container');
    assert.strictEqual(view.activeTab, 'overview');
    assert.strictEqual(view.overview, null);
    assert.strictEqual(view.entities.length, 0);
    assert.strictEqual(view.relationships.length, 0);
    assert.strictEqual(view.forecasts.length, 0);
    assert.strictEqual(view.scenarios.length, 0);
    assert.strictEqual(view.risks.length, 0);
    assert.strictEqual(view.opportunities.length, 0);
    assert.strictEqual(view.earlyWarnings.length, 0);
    assert.strictEqual(view.auditTrail.length, 0);
    assert.strictEqual(view.isLoading, false);
  });

  test('setTab switches activeTab correctly', () => {
    const view = new WorldModelView('mock-container');
    view.setTab('forecasts');
    assert.strictEqual(view.activeTab, 'forecasts');
    view.setTab('scenarios');
    assert.strictEqual(view.activeTab, 'scenarios');
    view.setTab('strategic');
    assert.strictEqual(view.activeTab, 'strategic');
    view.setTab('early_warnings');
    assert.strictEqual(view.activeTab, 'early_warnings');
    view.setTab('verification_audit');
    assert.strictEqual(view.activeTab, 'verification_audit');
  });

  test('selection methods update selected pointers', () => {
    const view = new WorldModelView('mock-container');
    view.entities = [
      { entity_id: 'ent-1', name: 'Database Node', state: 'HEALTHY' },
      { entity_id: 'ent-2', name: 'Auth Gateway', state: 'DEGRADED' },
    ];
    view.forecasts = [
      { forecast_id: 'fct-1', topic: 'Storage Growth', horizon: 'MID_FUTURE_1M' },
    ];
    view.scenarios = [
      { scenario_id: 'scn-1', name: 'Black Friday Spike', type: 'ADVERSE' },
    ];

    view.selectEntity('ent-2');
    assert.strictEqual(view.selectedEntity.name, 'Auth Gateway');

    view.selectForecast('fct-1');
    assert.strictEqual(view.selectedForecast.topic, 'Storage Growth');

    view.selectScenario('scn-1');
    assert.strictEqual(view.selectedScenario.name, 'Black Friday Spike');
  });

  test('handles container absence gracefully without throwing', async () => {
    const view = new WorldModelView('nonexistent-element-id');
    assert.doesNotThrow(() => {
      view.renderSkeleton();
      view.render();
    });
  });
});
