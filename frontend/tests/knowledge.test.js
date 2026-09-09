import test from 'node:test';
import assert from 'node:assert/strict';
import { KnowledgeView } from '../components/knowledge/knowledgeView.js';

test('Frontend Knowledge Fabric View Tests', async (t) => {
  await t.test('initializes with default search tab and empty results', () => {
    const mockContainer = { innerHTML: '', querySelectorAll: () => [], querySelector: () => null };
    const view = new KnowledgeView(mockContainer);

    assert.strictEqual(view.activeTab, 'search');
    assert.strictEqual(view.searchResults.length, 0);
    assert.strictEqual(view.decisions.length, 0);
  });

  await t.test('renders search results with type pills and relevance scores', () => {
    const mockContainer = { innerHTML: '', querySelectorAll: () => [], querySelector: () => null };
    const view = new KnowledgeView(mockContainer);
    view.searchResults = [
      {
        id: 'node_1',
        title: 'PostgreSQL + pgvector Architecture',
        summary: 'Decision to use pgvector for vector search and long-term memory.',
        type: 'DECISION',
        source_type: 'USER_EXPLICIT',
        relevance: 0.92,
        confidence: 1.0,
        timestamp: '2026-09-09T10:00:00Z',
      },
      {
        id: 'node_2',
        title: 'CI/CD Failure Investigation',
        summary: 'Build failure caused by commit abc123 due to missing dependency.',
        type: 'WORKFLOW_RUN',
        source_type: 'SYSTEM_DERIVED',
        relevance: 0.81,
        confidence: 0.95,
        timestamp: '2026-09-09T10:30:00Z',
      },
    ];

    const html = view._renderSearchResultsList();
    assert.match(html, /PostgreSQL \+ pgvector Architecture/);
    assert.match(html, /92% Match/);
    assert.match(html, /CI\/CD Failure Investigation/);
    assert.match(html, /81% Match/);
    assert.match(html, /USER_EXPLICIT/);
  });

  await t.test('renders decisions with active and superseded badges', () => {
    const mockContainer = { innerHTML: '', querySelectorAll: () => [], querySelector: () => null };
    const view = new KnowledgeView(mockContainer);
    view.decisions = [
      {
        id: 'dec_1',
        decision: 'Use pgvector for vector memory',
        rationale: 'Avoid secondary vector database, unify storage in Postgres.',
        status: 'ACTIVE',
        source: 'USER_EXPLICIT',
        created_at: '2026-09-09T08:00:00Z',
      },
      {
        id: 'dec_2',
        decision: 'Use external cloud vector service',
        rationale: 'Initial draft replaced by local pgvector.',
        status: 'SUPERSEDED',
        source: 'USER_EXPLICIT',
        created_at: '2026-09-08T08:00:00Z',
      },
    ];

    const html = view._renderDecisionsTab();
    assert.match(html, /Use pgvector for vector memory/);
    assert.match(html, /ACTIVE/);
    assert.match(html, /Use external cloud vector service/);
    assert.match(html, /SUPERSEDED/);
  });

  await t.test('renders timeline events chronologically', () => {
    const mockContainer = { innerHTML: '', querySelectorAll: () => [], querySelector: () => null };
    const view = new KnowledgeView(mockContainer);
    view.timelineEvents = [
      {
        node_id: 'tl_1',
        title: 'Release Engineering Implemented',
        summary: 'Task 23 release automation completed.',
        type: 'PROJECT',
        timestamp: '2026-09-09T09:00:00Z',
      },
    ];

    const html = view._renderTimelineTab();
    assert.match(html, /Release Engineering Implemented/);
    assert.match(html, /timeline-stream/);
  });

  await t.test('renders graph view with accessible list alternative', () => {
    const mockContainer = { innerHTML: '', querySelectorAll: () => [], querySelector: () => null };
    const view = new KnowledgeView(mockContainer);

    const html = view._renderGraphTab();
    assert.match(html, /Knowledge Relationship Graph/);
    assert.match(html, /accessible-graph-view/);
    assert.match(html, /Project: Kairo Personal AI Assistant/);
  });
});
