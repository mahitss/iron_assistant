/**
 * Unit tests for Task 68: Kairo Autonomous Knowledge & Memory Consolidation Engine.
 * Tests Endpoints definitions, wrapper mappings, and MemoryCenterView UI lifecycle.
 */

import { test, describe } from 'node:test';
import assert from 'node:assert';
import { Endpoints, memoryConsolidationApi } from '../lib/api/endpoints.js';
import { MemoryCenterView } from '../components/memory/memoryCenterView.js';

describe('Autonomous Knowledge & Memory Consolidation Endpoints (Task 68)', () => {
  test('Endpoints exposes all Task 68 consolidation methods', () => {
    const required = [
      'captureMemory',
      'searchConsolidatedMemories',
      'getMemoryConflicts',
      'getStaleMemories',
      'getExpiringMemories',
      'getMemoryHealth',
      'assembleMemoryContext',
      'triggerConsolidationSweep',
      'getMemoryProvenance',
      'getMemoryHistory',
      'validateMemory',
      'promoteMemory',
      'consolidateMemories',
      'quarantineMemory',
      'forgetMemory',
    ];

    for (const method of required) {
      assert.strictEqual(
        typeof Endpoints[method],
        'function',
        `Expected Endpoints.${method} to be a function`
      );
    }
  });

  test('memoryConsolidationApi wrapper exposes mapped methods', () => {
    assert.strictEqual(typeof memoryConsolidationApi.capture, 'function');
    assert.strictEqual(typeof memoryConsolidationApi.search, 'function');
    assert.strictEqual(typeof memoryConsolidationApi.getConflicts, 'function');
    assert.strictEqual(typeof memoryConsolidationApi.getStale, 'function');
    assert.strictEqual(typeof memoryConsolidationApi.getExpiring, 'function');
    assert.strictEqual(typeof memoryConsolidationApi.getHealth, 'function');
    assert.strictEqual(typeof memoryConsolidationApi.assembleContext, 'function');
    assert.strictEqual(typeof memoryConsolidationApi.triggerSweep, 'function');
    assert.strictEqual(typeof memoryConsolidationApi.getProvenance, 'function');
    assert.strictEqual(typeof memoryConsolidationApi.getHistory, 'function');
    assert.strictEqual(typeof memoryConsolidationApi.validate, 'function');
    assert.strictEqual(typeof memoryConsolidationApi.promote, 'function');
    assert.strictEqual(typeof memoryConsolidationApi.consolidate, 'function');
    assert.strictEqual(typeof memoryConsolidationApi.quarantine, 'function');
    assert.strictEqual(typeof memoryConsolidationApi.forget, 'function');
  });
});

describe('MemoryCenterView Component (Task 68)', () => {
  function createMockContainer() {
    return {
      innerHTML: '',
      querySelectorAll: () => [],
      querySelector: () => null,
    };
  }

  test('initializes with overview tab and default state', () => {
    const container = createMockContainer();
    const view = new MemoryCenterView(container);
    assert.strictEqual(view.activeTab, 'overview');
    assert.strictEqual(view.tenantId, 'default');
    assert.deepStrictEqual(view.memories, []);
    assert.deepStrictEqual(view.conflicts, []);
    assert.strictEqual(view.selectedMemory, null);
  });

  test('setTab updates active tab appropriately', () => {
    const container = createMockContainer();
    const view = new MemoryCenterView(container);
    view.setTab('conflicts');
    assert.strictEqual(view.activeTab, 'conflicts');
    assert.ok(container.innerHTML.includes('Autonomous Memory Center'));
  });

  test('selectMemory assigns memory and switches to detail tab', () => {
    const container = createMockContainer();
    const view = new MemoryCenterView(container);
    const mockMem = {
      memory_id: 'mem_test_123',
      content: 'Server cluster deployed in us-east-1 with Redis caching.',
      confidence: 0.95,
      importance: 0.8,
      cognitive_type: 'VERIFIED_FACT',
      memory_type: 'SEMANTIC_MEMORY',
      freshness: 'FRESH',
      trust_level: 'VERIFIED',
      status: 'ACTIVE',
    };
    view.selectMemory(mockMem);
    assert.strictEqual(view.activeTab, 'detail');
    assert.strictEqual(view.selectedMemory.memory_id, 'mem_test_123');
    assert.ok(container.innerHTML.includes('mem_test_123'));
    assert.ok(container.innerHTML.includes('Redis caching'));
  });
});
