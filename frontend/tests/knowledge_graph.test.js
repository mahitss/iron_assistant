import test from 'node:test';
import assert from 'node:assert/strict';
import { Endpoints, knowledgeGraphApi } from '../lib/api/endpoints.js';
import { KnowledgeGraphView } from '../components/knowledge_graph/knowledgeGraphView.js';

test('Kairo Personal Knowledge Graph & Relationship Memory Frontend Tests (Task 50)', async (t) => {
  await t.test('Endpoints defines knowledgeGraphApi methods', () => {
    assert.strictEqual(typeof Endpoints.createKnowledgeNode, 'function');
    assert.strictEqual(typeof Endpoints.listKnowledgeNodes, 'function');
    assert.strictEqual(typeof Endpoints.getKnowledgeNode, 'function');
    assert.strictEqual(typeof Endpoints.createKnowledgeEdge, 'function');
    assert.strictEqual(typeof Endpoints.traverseKnowledgeGraph, 'function');
    assert.strictEqual(typeof Endpoints.recordKnowledgeAssertion, 'function');
    assert.strictEqual(typeof Endpoints.findKnowledgeAssertions, 'function');
    assert.strictEqual(typeof Endpoints.recordKnowledgeDecision, 'function');
    assert.strictEqual(typeof Endpoints.listKnowledgeDecisions, 'function');
    assert.strictEqual(typeof Endpoints.setKnowledgePreference, 'function');
    assert.strictEqual(typeof Endpoints.resolveKnowledgePreference, 'function');
    assert.strictEqual(typeof Endpoints.queryKnowledgeAsOf, 'function');
    assert.strictEqual(typeof Endpoints.listKnowledgeContradictions, 'function');
    assert.strictEqual(typeof Endpoints.forgetKnowledgeEntity, 'function');
    assert.strictEqual(typeof Endpoints.getKnowledgeGraphMetrics, 'function');
    assert.strictEqual(typeof Endpoints.getKnowledgeGraphHealth, 'function');

    assert.strictEqual(typeof knowledgeGraphApi.createNode, 'function');
    assert.strictEqual(typeof knowledgeGraphApi.traverse, 'function');
    assert.strictEqual(typeof knowledgeGraphApi.recordDecision, 'function');
    assert.strictEqual(typeof knowledgeGraphApi.setPreference, 'function');
    assert.strictEqual(typeof knowledgeGraphApi.forgetEntity, 'function');
  });

  await t.test('KnowledgeGraphView instantiates and formats dates properly', () => {
    const mockContainer = { innerHTML: '', querySelectorAll: () => [], querySelector: () => null };
    const view = new KnowledgeGraphView(mockContainer);

    assert.strictEqual(view.activeTab, 'explorer');
    assert.strictEqual(view.formatDate(null), 'N/A');
    const validDate = view.formatDate('2026-09-10T12:00:00Z');
    assert.ok(typeof validDate === 'string' && validDate.length > 0);
  });

  await t.test('KnowledgeGraphView status badges map correctly', () => {
    const mockContainer = { innerHTML: '', querySelectorAll: () => [], querySelector: () => null };
    const view = new KnowledgeGraphView(mockContainer);

    assert.strictEqual(view.getStatusBadgeClass('ACTIVE'), 'badge-success');
    assert.strictEqual(view.getStatusBadgeClass('DETECTED'), 'badge-warning');
    assert.strictEqual(view.getStatusBadgeClass('SUPERSEDED'), 'badge-neutral');
    assert.strictEqual(view.getStatusBadgeClass('CONTRADICTED'), 'badge-danger');
  });
});
