/**
 * Frontend Unit & Component Tests for Task 117:
 * Kairo Autonomous Evidence Graph, Provenance Intelligence & Verification Dependency Engine
 */

import test from 'node:test';
import assert from 'node:assert';
import { evidenceGraphApi } from '../lib/api/endpoints.js';
import { EvidenceGraphWorkspace } from '../components/evidence_graph/evidenceGraphWorkspace.js';

test('Evidence Graph API Endpoints (Task 117)', async (t) => {
  await t.test('evidenceGraphApi exposes all required Task 117 methods', () => {
    assert.strictEqual(typeof evidenceGraphApi.listNodes, 'function');
    assert.strictEqual(typeof evidenceGraphApi.getNode, 'function');
    assert.strictEqual(typeof evidenceGraphApi.createNode, 'function');
    assert.strictEqual(typeof evidenceGraphApi.listEdges, 'function');
    assert.strictEqual(typeof evidenceGraphApi.createEdge, 'function');
    assert.strictEqual(typeof evidenceGraphApi.getUpstream, 'function');
    assert.strictEqual(typeof evidenceGraphApi.getDownstream, 'function');
    assert.strictEqual(typeof evidenceGraphApi.getLineage, 'function');
    assert.strictEqual(typeof evidenceGraphApi.getSources, 'function');
    assert.strictEqual(typeof evidenceGraphApi.getDependents, 'function');
    assert.strictEqual(typeof evidenceGraphApi.assessImpact, 'function');
    assert.strictEqual(typeof evidenceGraphApi.invalidateNode, 'function');
    assert.strictEqual(typeof evidenceGraphApi.assessFragility, 'function');
    assert.strictEqual(typeof evidenceGraphApi.getConcentrations, 'function');
    assert.strictEqual(typeof evidenceGraphApi.getCycles, 'function');
    assert.strictEqual(typeof evidenceGraphApi.getProvenanceGaps, 'function');
    assert.strictEqual(typeof evidenceGraphApi.getRevalidationQueue, 'function');
    assert.strictEqual(typeof evidenceGraphApi.createSnapshot, 'function');
    assert.strictEqual(typeof evidenceGraphApi.getSnapshot, 'function');
    assert.strictEqual(typeof evidenceGraphApi.diffSnapshots, 'function');
    assert.strictEqual(typeof evidenceGraphApi.ingestLineage, 'function');
    assert.strictEqual(typeof evidenceGraphApi.getHealth, 'function');
  });
});

test('EvidenceGraphWorkspace Component (Task 117)', async (t) => {
  await t.test('instantiates with default configuration and explorer tab', () => {
    const ws = new EvidenceGraphWorkspace('test-viewport');
    assert.strictEqual(ws.containerId, 'test-viewport');
    assert.strictEqual(ws.activeTab, 'explorer');
    assert.deepStrictEqual(ws.nodes, []);
    assert.strictEqual(ws.selectedNodeId, null);
  });

  await t.test('renders severity badges accurately', () => {
    const ws = new EvidenceGraphWorkspace();
    const directBadge = ws.getSeverityBadge('DIRECT');
    assert.match(directBadge, /#ef4444/);

    const indirectBadge = ws.getSeverityBadge('INDIRECT');
    assert.match(indirectBadge, /#f59e0b/);

    const lowBadge = ws.getSeverityBadge('LOW');
    assert.match(lowBadge, /#10b981/);
  });

  await t.test('renders freshness badges accurately', () => {
    const ws = new EvidenceGraphWorkspace();
    const freshBadge = ws.getFreshnessBadge('FRESH');
    assert.match(freshBadge, /#10b981/);

    const staleBadge = ws.getFreshnessBadge('STALE');
    assert.match(staleBadge, /#f59e0b/);

    const invalidBadge = ws.getFreshnessBadge('INVALID');
    assert.match(invalidBadge, /#dc2626/);
  });

  await t.test('renders tab navigation buttons correctly', () => {
    const ws = new EvidenceGraphWorkspace();
    const explorerBtn = ws.renderTabBtn('explorer', 'Explorer');
    assert.match(explorerBtn, /#2563eb/); // Active background

    const lineageBtn = ws.renderTabBtn('lineage', 'Lineage');
    assert.match(lineageBtn, /transparent/); // Inactive background
  });
});
