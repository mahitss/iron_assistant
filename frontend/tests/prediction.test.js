/**
 * Unit tests for Kairo Predictive Intelligence & Anticipation Engine (Task 47)
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { endpoints } from '../lib/api/endpoints.js';
import { PredictionView } from '../components/prediction/predictionView.js';

describe('Predictive Intelligence & Anticipation Engine Endpoints & UI (Task 47)', () => {
  test('Endpoints exposes all Task 47 prediction methods', () => {
    assert.strictEqual(typeof endpoints.createPrediction, 'function');
    assert.strictEqual(typeof endpoints.listPredictions, 'function');
    assert.strictEqual(typeof endpoints.getPrediction, 'function');
    assert.strictEqual(typeof endpoints.evaluatePredictionOutcome, 'function');
    assert.strictEqual(typeof endpoints.createForecast, 'function');
    assert.strictEqual(typeof endpoints.issueEarlyWarning, 'function');
    assert.strictEqual(typeof endpoints.listActiveWarnings, 'function');
    assert.strictEqual(typeof endpoints.evaluatePredictedRisk, 'function');
    assert.strictEqual(typeof endpoints.listPredictedRisks, 'function');
    assert.strictEqual(typeof endpoints.simulateScenarios, 'function');
    assert.strictEqual(typeof endpoints.evaluateCounterfactual, 'function');
    assert.strictEqual(typeof endpoints.getCalibrationMetrics, 'function');
    assert.strictEqual(typeof endpoints.getPredictionHealth, 'function');
  });

  test('PredictionView initializes with default state', () => {
    const mockContainer = {
      innerHTML: '',
      querySelector: () => null,
      querySelectorAll: () => [],
    };

    const view = new PredictionView(mockContainer);
    assert.strictEqual(view.activeTab, 'predictions');
    assert.strictEqual(view.isLoading, false);
    assert.deepStrictEqual(view.predictions, []);
    assert.deepStrictEqual(view.warnings, []);
    assert.deepStrictEqual(view.risks, []);
    assert.strictEqual(view.calibration, null);
    assert.strictEqual(view.health, null);
  });

  test('PredictionView formatters function correctly', () => {
    const view = new PredictionView({});
    assert.strictEqual(view.formatProbability(null), '50%');
    assert.strictEqual(view.formatProbability(0.852), '85.2%');
    assert.strictEqual(view.formatProbability(1.0), '100.0%');
    assert.strictEqual(view.formatDate(null), 'N/A');
  });

  test('PredictionView renders HTML skeleton structure', async () => {
    let htmlOutput = '';
    const mockContainer = {
      set innerHTML(val) {
        htmlOutput = val;
      },
      querySelector: () => null,
      querySelectorAll: () => [],
    };

    const view = new PredictionView(mockContainer);
    await view.render();

    assert.ok(htmlOutput.includes('Predictive Intelligence & Anticipation Engine'));
    assert.ok(htmlOutput.includes('Prediction != Observation'));
    assert.ok(htmlOutput.includes('data-tab="predictions"'));
    assert.ok(htmlOutput.includes('data-tab="warnings"'));
    assert.ok(htmlOutput.includes('data-tab="risks"'));
    assert.ok(htmlOutput.includes('data-tab="calibration"'));
  });

  test('PredictionView renders active tabs correctly', () => {
    const view = new PredictionView({});

    // Predictions tab
    view.activeTab = 'predictions';
    view.predictions = [{
      prediction_id: 'pred_1',
      subject: 'service:redis:memory',
      event: 'CAPACITY_EXHAUSTED',
      prediction_window: 'short-term',
      confidence: 0.88,
      model_reference: 'trend_linear_v1',
      status: 'ACTIVE',
      expires_at: new Date().toISOString(),
    }];
    const predHtml = view.renderActiveTab();
    assert.ok(predHtml.includes('service:redis:memory'));
    assert.ok(predHtml.includes('CAPACITY_EXHAUSTED'));

    // Warnings tab
    view.activeTab = 'warnings';
    view.warnings = [{
      warning_id: 'ew_1',
      target: 'kairo_api',
      signal: 'latency_surge',
      predicted_event: 'SERVICE_DEGRADATION',
      severity: 'HIGH',
      confidence: 0.75,
      status: 'OPEN',
      expires_at: new Date().toISOString(),
    }];
    const warnHtml = view.renderActiveTab();
    assert.ok(warnHtml.includes('kairo_api'));
    assert.ok(warnHtml.includes('SERVICE_DEGRADATION'));

    // Risks tab
    view.activeTab = 'risks';
    view.risks = [{
      risk_id: 'risk_1',
      subject: 'database_storage',
      event: 'DISK_FULL',
      likelihood: 0.8,
      impact: 0.9,
      risk_score: 0.72,
      timeframe: 'medium-term',
      mitigations: ['Provision disk space', 'Archive old logs'],
    }];
    const riskHtml = view.renderActiveTab();
    assert.ok(riskHtml.includes('database_storage'));
    assert.ok(riskHtml.includes('Provision disk space'));

    // Calibration tab
    view.activeTab = 'calibration';
    view.calibration = {
      model_reference: 'trend_linear_v1',
      brier_score: 0.0421,
      log_loss: 0.125,
      accuracy: 0.94,
    };
    const calibHtml = view.renderActiveTab();
    assert.ok(calibHtml.includes('Statistical Probability Calibration'));
    assert.ok(calibHtml.includes('0.0421'));
  });
});
