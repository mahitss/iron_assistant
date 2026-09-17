/**
 * Unit tests for Kairo Autonomous Cognitive Memory, Experience Consolidation & Lifelong Learning Fabric (Task 103).
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { cognitiveMemoryApi } from '../lib/api/endpoints.js';
import { CognitiveMemoryView } from '../components/cognitive_memory/cognitiveMemoryView.js';

describe('Cognitive Memory API Endpoints (Task 103)', () => {
  test('cognitiveMemoryApi exposes all required fabric methods', () => {
    assert.strictEqual(typeof cognitiveMemoryApi.getStatus, 'function');
    assert.strictEqual(typeof cognitiveMemoryApi.listMemories, 'function');
    assert.strictEqual(typeof cognitiveMemoryApi.getMemory, 'function');
    assert.strictEqual(typeof cognitiveMemoryApi.getMemoryHistory, 'function');
    assert.strictEqual(typeof cognitiveMemoryApi.getMemoryEvidence, 'function');
    assert.strictEqual(typeof cognitiveMemoryApi.captureExperience, 'function');
    assert.strictEqual(typeof cognitiveMemoryApi.searchMemories, 'function');
    assert.strictEqual(typeof cognitiveMemoryApi.assembleContextPack, 'function');
    assert.strictEqual(typeof cognitiveMemoryApi.listConflicts, 'function');
    assert.strictEqual(typeof cognitiveMemoryApi.listPatterns, 'function');
    assert.strictEqual(typeof cognitiveMemoryApi.listStale, 'function');
    assert.strictEqual(typeof cognitiveMemoryApi.revalidateMemory, 'function');
    assert.strictEqual(typeof cognitiveMemoryApi.invalidateMemory, 'function');
    assert.strictEqual(typeof cognitiveMemoryApi.supersedeMemory, 'function');
    assert.strictEqual(typeof cognitiveMemoryApi.replayMemories, 'function');
    assert.strictEqual(typeof cognitiveMemoryApi.createSnapshot, 'function');
  });
});

describe('CognitiveMemoryView Component', () => {
  test('initializes with default state and default memories tab', () => {
    const mockContainer = { innerHTML: '', addEventListener: () => {}, querySelectorAll: () => [], querySelector: () => null };
    const view = new CognitiveMemoryView(mockContainer);
    assert.strictEqual(view.activeTab, 'memories');
    assert.strictEqual(view.status, null);
    assert.deepStrictEqual(view.memories, []);
    assert.deepStrictEqual(view.conflicts, []);
    assert.deepStrictEqual(view.patterns, []);
    assert.deepStrictEqual(view.staleMemories, []);
    assert.strictEqual(view.selectedMemory, null);
    assert.strictEqual(view.replayResult, null);
    assert.strictEqual(view.isLoading, false);
    assert.strictEqual(view.error, null);
  });

  test('switches tabs correctly across all memory panels', () => {
    const mockContainer = { innerHTML: '', addEventListener: () => {}, querySelectorAll: () => [], querySelector: () => null };
    const view = new CognitiveMemoryView(mockContainer);
    view.setTab('conflicts');
    assert.strictEqual(view.activeTab, 'conflicts');
    view.setTab('patterns');
    assert.strictEqual(view.activeTab, 'patterns');
    view.setTab('stale');
    assert.strictEqual(view.activeTab, 'stale');
    view.setTab('replay');
    assert.strictEqual(view.activeTab, 'replay');
    view.setTab('memories');
    assert.strictEqual(view.activeTab, 'memories');
  });

  test('renders metrics grid and tab headers accurately', () => {
    const mockContainer = { innerHTML: '', addEventListener: () => {}, querySelectorAll: () => [], querySelector: () => null };
    const view = new CognitiveMemoryView(mockContainer);
    view.status = {
      total_experiences: 42,
      total_memories: 18,
      active_memories: 14,
      candidate_memories: 3,
      stale_memories: 1,
      superseded_memories: 2,
      active_conflicts: 1,
      patterns_discovered: 4,
      total_applications: 35,
      feedback_recorded: 30,
    };
    view.memories = [
      {
        memory_id: 'cmem_test001',
        version: 1,
        lifecycle_state: 'ACTIVE',
        freshness: 'CURRENT',
        memory_type: 'PROCEDURAL',
        scope: 'PROJECT',
        confidence: 0.88,
        content: 'Service recovery sequence verified via restart and cache warmup.',
        provenance_trust: 'SYSTEM_VERIFIED',
      },
    ];
    view.conflicts = [
      {
        conflict_id: 'ccnf_001',
        status: 'ACTIVE',
        entity_reference: 'api_gateway',
        discrepancy_summary: 'Port discrepancy: 8000 vs 8080',
        competing_memory_a: 'cmem_a',
        competing_memory_b: 'cmem_b',
        scope: 'PROJECT',
      },
    ];
    view.patterns = [
      {
        pattern_id: 'cpat_001',
        title: 'Transient DB Connection Timeout Pattern',
        pattern_summary: 'Occurs under resource spikes when pool size is exceeded.',
        recurrence_count: 5,
        confidence: 0.9,
        scope: 'PROJECT',
        known_exceptions: [],
      },
    ];

    view.render();
    assert.ok(mockContainer.innerHTML.includes('Cognitive Memory & Lifelong Learning Fabric'));
    assert.ok(mockContainer.innerHTML.includes('42'));
    assert.ok(mockContainer.innerHTML.includes('18'));
    assert.ok(mockContainer.innerHTML.includes('cmem_test001'));
    assert.ok(mockContainer.innerHTML.includes('PROCEDURAL'));
  });

  test('renders conflicts tab with competing claims', () => {
    const mockContainer = { innerHTML: '', addEventListener: () => {}, querySelectorAll: () => [], querySelector: () => null };
    const view = new CognitiveMemoryView(mockContainer);
    view.setTab('conflicts');
    view.conflicts = [
      {
        conflict_id: 'ccnf_999',
        discrepancy_summary: 'Configuration divergence on auth_timeout',
        entity_reference: 'auth_service',
        competing_memory_a: 'cmem_old',
        competing_memory_b: 'cmem_new',
        memory_a_claim: 'auth_timeout is 30s',
        memory_b_claim: 'auth_timeout is 60s',
        scope: 'PROJECT',
        status: 'ACTIVE',
      },
    ];
    view.render();
    assert.ok(mockContainer.innerHTML.includes('ccnf_999'));
    assert.ok(mockContainer.innerHTML.includes('Configuration divergence on auth_timeout'));
    assert.ok(mockContainer.innerHTML.includes('auth_timeout is 30s'));
    assert.ok(mockContainer.innerHTML.includes('auth_timeout is 60s'));
  });

  test('renders deterministic replay tab results', () => {
    const mockContainer = { innerHTML: '', addEventListener: () => {}, querySelectorAll: () => [], querySelector: () => null };
    const view = new CognitiveMemoryView(mockContainer);
    view.setTab('replay');
    view.replayResult = {
      total_experiences_replayed: 10,
      candidates_formed: 10,
      memories_consolidated: 4,
      conflicts_detected: 1,
      simulated_evolution: [
        { timestamp: '2026-09-18T00:00:00Z', event: 'EXPERIENCE_REPLAYED', detail: 'Replayed exp 1' },
      ],
    };
    view.render();
    assert.ok(mockContainer.innerHTML.includes('Replay Simulation Result'));
    assert.ok(mockContainer.innerHTML.includes('10'));
    assert.ok(mockContainer.innerHTML.includes('Replayed exp 1'));
  });
});
