/**
 * Unit tests for Kairo Simulation, Digital World Model & Counterfactual Planning (Task 56).
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { endpoints, simulationApi } from '../lib/api/endpoints.js';
import { SimulationView } from '../components/simulation/simulationView.js';

describe('Simulation & Counterfactual Planning Endpoints (Task 56)', () => {
  test('Endpoints exposes all simulation methods', () => {
    assert.strictEqual(typeof endpoints.captureSimulationSnapshot, 'function');
    assert.strictEqual(typeof endpoints.listSimulationSnapshots, 'function');
    assert.strictEqual(typeof endpoints.getSimulationSnapshot, 'function');
    assert.strictEqual(typeof endpoints.createSimulationScenario, 'function');
    assert.strictEqual(typeof endpoints.listSimulationScenarios, 'function');
    assert.strictEqual(typeof endpoints.getSimulationScenario, 'function');
    assert.strictEqual(typeof endpoints.runSimulation, 'function');
    assert.strictEqual(typeof endpoints.listSimulationRuns, 'function');
    assert.strictEqual(typeof endpoints.getSimulationRun, 'function');
    assert.strictEqual(typeof endpoints.compareSimulations, 'function');
    assert.strictEqual(typeof endpoints.rankSimulations, 'function');
    assert.strictEqual(typeof endpoints.exploreCounterfactual, 'function');
    assert.strictEqual(typeof endpoints.runMonteCarlo, 'function');
    assert.strictEqual(typeof endpoints.replaySimulation, 'function');
    assert.strictEqual(typeof endpoints.evaluateExecutionGate, 'function');
    assert.strictEqual(typeof endpoints.recordSimulationCalibration, 'function');
    assert.strictEqual(typeof endpoints.getSimulationCalibrationReport, 'function');
  });

  test('simulationApi wrapper exposes mapped methods', () => {
    assert.strictEqual(typeof simulationApi.captureSnapshot, 'function');
    assert.strictEqual(typeof simulationApi.listSnapshots, 'function');
    assert.strictEqual(typeof simulationApi.getSnapshot, 'function');
    assert.strictEqual(typeof simulationApi.createScenario, 'function');
    assert.strictEqual(typeof simulationApi.listScenarios, 'function');
    assert.strictEqual(typeof simulationApi.getScenario, 'function');
    assert.strictEqual(typeof simulationApi.runSimulation, 'function');
    assert.strictEqual(typeof simulationApi.listRuns, 'function');
    assert.strictEqual(typeof simulationApi.getRun, 'function');
    assert.strictEqual(typeof simulationApi.compareSimulations, 'function');
    assert.strictEqual(typeof simulationApi.rankSimulations, 'function');
    assert.strictEqual(typeof simulationApi.exploreCounterfactual, 'function');
    assert.strictEqual(typeof simulationApi.runMonteCarlo, 'function');
    assert.strictEqual(typeof simulationApi.replay, 'function');
    assert.strictEqual(typeof simulationApi.evaluateGate, 'function');
    assert.strictEqual(typeof simulationApi.calibrate, 'function');
    assert.strictEqual(typeof simulationApi.getCalibrationReport, 'function');
  });
});

describe('SimulationView Component', () => {
  test('initializes and renders simulation tabs and safety markers', () => {
    const mockContainer = {
      innerHTML: '',
      addEventListener: () => {},
    };

    const view = new SimulationView({ container: mockContainer });
    assert.strictEqual(view.state.activeTab, 'workbench');

    const html = view._template();
    assert.ok(html.includes('Simulation & Counterfactual Planning Engine'));
    assert.ok(html.includes('SIMULATION_ONLY'));
    assert.ok(html.includes('Capture Snapshot'));
    assert.ok(html.includes('Run Simulation'));
  });

  test('renders all tab contents without errors', () => {
    const mockContainer = { innerHTML: '', addEventListener: () => {} };
    const view = new SimulationView({ container: mockContainer });

    const tabs = ['workbench', 'comparison', 'future_state', 'counterfactuals', 'execution_gate', 'calibration'];
    for (const tab of tabs) {
      view.state.activeTab = tab;
      const content = view._renderActiveTabContent();
      assert.ok(content.length > 0);
    }
  });
});
