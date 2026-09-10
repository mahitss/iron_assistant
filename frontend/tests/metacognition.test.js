import test from 'node:test';
import assert from 'node:assert/strict';
import { Endpoints, metacognitionApi } from '../lib/api/endpoints.js';
import { MetacognitionView } from '../components/metacognition/metacognitionView.js';

test('Kairo Self-Modeling & Metacognition Engine Frontend Tests (Task 51)', async (t) => {
  await t.test('Endpoints defines metacognitionApi methods', () => {
    assert.strictEqual(typeof Endpoints.getSelfModel, 'function');
    assert.strictEqual(typeof Endpoints.getSelfModelProjection, 'function');
    assert.strictEqual(typeof Endpoints.listCapabilities, 'function');
    assert.strictEqual(typeof Endpoints.listLimitations, 'function');
    assert.strictEqual(typeof Endpoints.registerLimitation, 'function');
    assert.strictEqual(typeof Endpoints.checkActionReadiness, 'function');
    assert.strictEqual(typeof Endpoints.introspect, 'function');
    assert.strictEqual(typeof Endpoints.recordReflection, 'function');
    assert.strictEqual(typeof Endpoints.getMetacognitiveMetrics, 'function');
    assert.strictEqual(typeof Endpoints.reconcileSelfModel, 'function');
    assert.strictEqual(typeof Endpoints.getMetacognitionHealth, 'function');

    assert.strictEqual(typeof metacognitionApi.getSelfModel, 'function');
    assert.strictEqual(typeof metacognitionApi.getProjection, 'function');
    assert.strictEqual(typeof metacognitionApi.listCapabilities, 'function');
    assert.strictEqual(typeof metacognitionApi.listLimitations, 'function');
    assert.strictEqual(typeof metacognitionApi.introspect, 'function');
    assert.strictEqual(typeof metacognitionApi.checkReadiness, 'function');
    assert.strictEqual(typeof metacognitionApi.recordReflection, 'function');
    assert.strictEqual(typeof metacognitionApi.getMetrics, 'function');
  });

  await t.test('MetacognitionView instantiates and formats dates properly', () => {
    const mockContainer = { innerHTML: '', querySelectorAll: () => [], querySelector: () => null };
    const view = new MetacognitionView(mockContainer);

    assert.strictEqual(view.activeTab, 'capabilities');
    assert.strictEqual(view.formatDate(null), 'N/A');
    const validDate = view.formatDate('2026-09-10T12:00:00Z');
    assert.ok(typeof validDate === 'string' && validDate.length > 0);
  });

  await t.test('MetacognitionView capability badge classes map correctly', () => {
    const mockContainer = { innerHTML: '', querySelectorAll: () => [], querySelector: () => null };
    const view = new MetacognitionView(mockContainer);

    assert.strictEqual(view.getCapabilityBadgeClass('AVAILABLE'), 'badge-success');
    assert.strictEqual(view.getCapabilityBadgeClass('RESTRICTED'), 'badge-warning');
    assert.strictEqual(view.getCapabilityBadgeClass('DEGRADED'), 'badge-danger');
    assert.strictEqual(view.getCapabilityBadgeClass('UNAVAILABLE'), 'badge-neutral');
  });

  await t.test('MetacognitionView limitation severity classes map correctly', () => {
    const mockContainer = { innerHTML: '', querySelectorAll: () => [], querySelector: () => null };
    const view = new MetacognitionView(mockContainer);

    assert.strictEqual(view.getLimitationSeverityClass('BLOCKING'), 'badge-danger');
    assert.strictEqual(view.getLimitationSeverityClass('HIGH'), 'badge-warning');
    assert.strictEqual(view.getLimitationSeverityClass('MEDIUM'), 'badge-info');
    assert.strictEqual(view.getLimitationSeverityClass('LOW'), 'badge-neutral');
  });
});
