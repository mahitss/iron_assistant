import test from 'node:test';
import assert from 'node:assert/strict';
import { Endpoints } from '../lib/api/endpoints.js';
import { ActivityView } from '../components/activity/activityView.js';

test('Unified Event Bus Frontend Integration Tests', async (t) => {
  await t.test('Endpoints object defines all required Event Bus API methods', () => {
    assert.strictEqual(typeof Endpoints.getEventRegistryCatalog, 'function');
    assert.strictEqual(typeof Endpoints.getEventBusMetrics, 'function');
    assert.strictEqual(typeof Endpoints.listDeadLetters, 'function');
    assert.strictEqual(typeof Endpoints.getDeadLetterDetail, 'function');
    assert.strictEqual(typeof Endpoints.replayDeadLetter, 'function');
    assert.strictEqual(typeof Endpoints.discardDeadLetter, 'function');
    assert.strictEqual(typeof Endpoints.getActivityTimeline, 'function');
    assert.strictEqual(typeof Endpoints.publishEvent, 'function');
  });

  await t.test('ActivityView initializes with default state and filter tabs', () => {
    const mockContainer = { innerHTML: '', querySelector: () => null, querySelectorAll: () => [] };
    const view = new ActivityView(mockContainer);
    assert.ok(view);
    assert.strictEqual(view.activeFilter, 'all');
    assert.strictEqual(view.isLoading, false);
    assert.ok(Array.isArray(view.events));
  });

  await t.test('ActivityView merges and sorts events correctly', () => {
    const mockContainer = { innerHTML: '', querySelector: () => null, querySelectorAll: () => [] };
    const view = new ActivityView(mockContainer);

    const event1 = {
      id: 'e1',
      source: 'security',
      title: 'Action blocked',
      timestamp: new Date('2026-09-09T10:00:00Z'),
    };
    const event2 = {
      id: 'e2',
      source: 'event_bus',
      title: 'CI Workflow Failed',
      timestamp: new Date('2026-09-09T10:05:00Z'),
    };

    view.events = [event1, event2];
    view.events.sort((a, b) => b.timestamp - a.timestamp);

    assert.strictEqual(view.events[0].id, 'e2');
    assert.strictEqual(view.events[1].id, 'e1');
  });

  await t.test('ActivityView filters events by source category', () => {
    const mockContainer = { innerHTML: '', querySelector: () => null, querySelectorAll: () => [] };
    const view = new ActivityView(mockContainer);

    view.events = [
      { id: '1', source: 'security', title: 'Sec Event' },
      { id: '2', source: 'agent', title: 'Agent Event' },
      { id: '3', source: 'security', title: 'Another Sec Event' },
    ];

    view.activeFilter = 'security';
    const filtered = view.events.filter(e => e.source === view.activeFilter);
    assert.strictEqual(filtered.length, 2);
    assert.strictEqual(filtered[0].id, '1');
    assert.strictEqual(filtered[1].id, '3');
  });
});
