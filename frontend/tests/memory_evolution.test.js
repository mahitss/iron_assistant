/**
 * Unit tests for Task 92: KAIRO Knowledge Consolidation, Memory Reconstruction & Context Evolution UI.
 * Tests MemoryEvolutionView initialization, 12 tab states, and forensic timeline rendering.
 */

import { test, describe } from 'node:test';
import assert from 'node:assert';
import { MemoryEvolutionView } from '../components/memory/memoryEvolutionView.js';

describe('MemoryEvolutionView Component (Task 92 Phase 31)', () => {
  function createMockContainer() {
    return {
      innerHTML: '',
      querySelectorAll: () => [],
      querySelector: () => null,
    };
  }

  test('initializes with overview tab and default state', () => {
    const container = createMockContainer();
    const view = new MemoryEvolutionView(container);
    assert.strictEqual(view.activeTab, 'overview');
    assert.strictEqual(view.tenantId, 'default');
    assert.deepStrictEqual(view.memories, []);
    assert.deepStrictEqual(view.conflicts, []);
    assert.strictEqual(view.selectedMemory, null);
    assert.strictEqual(view.reconstructionResult, null);
  });

  test('supports all 12 operational view tabs', () => {
    const container = createMockContainer();
    const view = new MemoryEvolutionView(container);

    const tabs = [
      'overview',
      'active',
      'recent',
      'conflicts',
      'stale',
      'hypotheses',
      'evidence',
      'provenance',
      'consolidation',
      'revalidation',
      'timeline',
      'graph',
    ];

    for (const tab of tabs) {
      view.setTab(tab);
      assert.strictEqual(view.activeTab, tab);
      assert.ok(container.innerHTML.includes('Autonomous Knowledge &amp; Memory Evolution') || container.innerHTML.includes('Autonomous Knowledge & Memory Evolution'));
    }
  });

  test('renders cognitive invariants alert banner in every tab', () => {
    const container = createMockContainer();
    const view = new MemoryEvolutionView(container);
    view.render();
    assert.ok(container.innerHTML.includes('MEMORY != TRUTH'));
    assert.ok(container.innerHTML.includes('VECTOR SIMILARITY != TRUTH'));
    assert.ok(container.innerHTML.includes('MODEL OUTPUT != FACT'));
  });

  test('renders forensic reconstruction result with certainty indicator', () => {
    const container = createMockContainer();
    const view = new MemoryEvolutionView(container);
    view.activeTab = 'timeline';
    view.reconstructionResult = {
      query: 'Service X deployment',
      timeline: [
        {
          timestamp: new Date().toISOString(),
          memory_id: 'mem_1',
          type: 'OBSERVATION',
          summary: 'Service X proposed with port 8000',
          status: 'SUPERSEDED',
          confidence: 0.8,
          certainty: 'KNOWN',
          source_type: 'OBSERVED',
          evidence_count: 1,
        },
        {
          timestamp: new Date().toISOString(),
          memory_id: 'mem_2',
          type: 'SEMANTIC',
          summary: 'Service X finalized on port 8443',
          status: 'ACTIVE',
          confidence: 0.95,
          certainty: 'KNOWN',
          source_type: 'SYSTEM_VERIFIED',
          evidence_count: 2,
        },
      ],
      current_state: 'Service X finalized on port 8443',
      superseded_states: ['Service X proposed with port 8000'],
      unresolved_conflicts: [],
      confidence: 0.95,
      certainty: 'KNOWN',
      evidence_references: ['spec.yaml: port 8443'],
      synthesized_narrative: 'Forensic reconstruction completed cleanly.',
    };

    view.render();
    assert.ok(container.innerHTML.includes('Forensic Reconstruction Narrative'));
    assert.ok(container.innerHTML.includes('Certainty: KNOWN'));
    assert.ok(container.innerHTML.includes('Service X finalized on port 8443'));
  });
});
