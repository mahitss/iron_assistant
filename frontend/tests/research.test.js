/**
 * Unit tests for Kairo Knowledge Synthesis & Research Intelligence Engine (Task 63).
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { endpoints, researchApi } from '../lib/api/endpoints.js';
import { ResearchView } from '../components/research/researchView.js';

describe('Knowledge Synthesis & Research Intelligence Endpoints (Task 63)', () => {
  test('Endpoints exposes all research methods', () => {
    assert.strictEqual(typeof endpoints.startResearch, 'function');
    assert.strictEqual(typeof endpoints.listResearchSessions, 'function');
    assert.strictEqual(typeof endpoints.getResearch, 'function');
    assert.strictEqual(typeof endpoints.getResearchSources, 'function');
    assert.strictEqual(typeof endpoints.getResearchClaims, 'function');
    assert.strictEqual(typeof endpoints.getResearchEvidence, 'function');
    assert.strictEqual(typeof endpoints.getResearchConflicts, 'function');
    assert.strictEqual(typeof endpoints.getResearchGaps, 'function');
    assert.strictEqual(typeof endpoints.getResearchTimeline, 'function');
    assert.strictEqual(typeof endpoints.continueResearch, 'function');
    assert.strictEqual(typeof endpoints.verifyResearchClaim, 'function');
    assert.strictEqual(typeof endpoints.ingestResearchDocument, 'function');
    assert.strictEqual(typeof endpoints.getResearchClaim, 'function');
    assert.strictEqual(typeof endpoints.getResearchSource, 'function');
    assert.strictEqual(typeof endpoints.retractResearchSource, 'function');
    assert.strictEqual(typeof endpoints.getResearchDecisionPackage, 'function');
    assert.strictEqual(typeof endpoints.getResearchKnowledgeChanges, 'function');
    assert.strictEqual(typeof endpoints.getResearchAudit, 'function');
  });

  test('researchApi wrapper exposes mapped methods', () => {
    assert.strictEqual(typeof researchApi.start, 'function');
    assert.strictEqual(typeof researchApi.list, 'function');
    assert.strictEqual(typeof researchApi.get, 'function');
    assert.strictEqual(typeof researchApi.getSources, 'function');
    assert.strictEqual(typeof researchApi.getClaims, 'function');
    assert.strictEqual(typeof researchApi.getEvidence, 'function');
    assert.strictEqual(typeof researchApi.getConflicts, 'function');
    assert.strictEqual(typeof researchApi.getGaps, 'function');
    assert.strictEqual(typeof researchApi.getTimeline, 'function');
    assert.strictEqual(typeof researchApi.continue, 'function');
    assert.strictEqual(typeof researchApi.verifyClaim, 'function');
    assert.strictEqual(typeof researchApi.ingestDocument, 'function');
    assert.strictEqual(typeof researchApi.getClaim, 'function');
    assert.strictEqual(typeof researchApi.getSource, 'function');
    assert.strictEqual(typeof researchApi.retractSource, 'function');
    assert.strictEqual(typeof researchApi.getDecisionPackage, 'function');
    assert.strictEqual(typeof researchApi.getChanges, 'function');
    assert.strictEqual(typeof researchApi.getAudit, 'function');
  });
});

describe('ResearchView Component', () => {
  test('initializes with default workspace tab and empty state collections', () => {
    const view = new ResearchView('mock-container');
    assert.strictEqual(view.activeTab, 'workspace');
    assert.strictEqual(view.sessions.length, 0);
    assert.strictEqual(view.sources.length, 0);
    assert.strictEqual(view.claims.length, 0);
    assert.strictEqual(view.evidence.length, 0);
    assert.strictEqual(view.conflicts.length, 0);
    assert.strictEqual(view.gaps.length, 0);
    assert.strictEqual(view.auditTrail.length, 0);
    assert.strictEqual(view.changes.length, 0);
    assert.strictEqual(view.isLoading, false);
  });

  test('switches tabs correctly across all research intelligence views', () => {
    const view = new ResearchView('mock-container');
    view.setTab('sources');
    assert.strictEqual(view.activeTab, 'sources');
    view.setTab('claims');
    assert.strictEqual(view.activeTab, 'claims');
    view.setTab('conflicts');
    assert.strictEqual(view.activeTab, 'conflicts');
    view.setTab('uncertainty');
    assert.strictEqual(view.activeTab, 'uncertainty');
    view.setTab('synthesis');
    assert.strictEqual(view.activeTab, 'synthesis');
    view.setTab('audit');
    assert.strictEqual(view.activeTab, 'audit');
    view.setTab('workspace');
    assert.strictEqual(view.activeTab, 'workspace');
  });

  test('selects claim and source models with full metadata', () => {
    const view = new ResearchView('mock-container');
    const mockClaim = {
      claim_id: 'clm_edge_001',
      claim_text: 'Kernel bypass socket reduces UDP packet jitter to under 12 microseconds.',
      subject: 'Kernel bypass socket',
      predicate: 'reduces',
      object: 'UDP packet jitter',
      claim_type: 'MEASURED',
      status: 'VERIFIED',
      confidence: 'HIGH',
      evidence_refs: ['ev_bench_001', 'ev_bench_002'],
    };
    view.selectClaim(mockClaim);
    assert.strictEqual(view.selectedClaim.claim_id, 'clm_edge_001');
    assert.strictEqual(view.selectedClaim.claim_type, 'MEASURED');
    assert.strictEqual(view.selectedClaim.evidence_refs.length, 2);

    const mockSource = {
      source_id: 'src_ieee_001',
      title: 'Real-Time Linux Network Performance',
      publisher: 'IEEE Transactions',
      source_type: 'ACADEMIC_PAPER',
      authority_score: 0.94,
      freshness_score: 0.88,
      citation_sources: [],
    };
    view.selectSource(mockSource);
    assert.strictEqual(view.selectedSource.source_id, 'src_ieee_001');
    assert.strictEqual(view.selectedSource.publisher, 'IEEE Transactions');
  });
});
