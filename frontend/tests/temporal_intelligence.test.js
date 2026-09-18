/**
 * Unit tests for Kairo Task 111:
 * Autonomous Temporal Intelligence, Event History, Change Reconstruction & "What Changed?" Engine.
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { temporalApi } from '../lib/api/endpoints.js';
import { TemporalIntelligenceView } from '../components/temporal/temporalIntelligenceView.js';

describe('Temporal Intelligence API Endpoints (Task 111)', () => {
  test('temporalApi exposes all required Task 111 endpoints', () => {
    assert.strictEqual(typeof temporalApi.query, 'function');
    assert.strictEqual(typeof temporalApi.getTimeline, 'function');
    assert.strictEqual(typeof temporalApi.getCurrentState, 'function');
    assert.strictEqual(typeof temporalApi.getStateAsOf, 'function');
    assert.strictEqual(typeof temporalApi.computeDiff, 'function');
    assert.strictEqual(typeof temporalApi.listChanges, 'function');
    assert.strictEqual(typeof temporalApi.listGaps, 'function');
    assert.strictEqual(typeof temporalApi.listAnomalies, 'function');
    assert.strictEqual(typeof temporalApi.listWatermarks, 'function');
    assert.strictEqual(typeof temporalApi.listCheckpoints, 'function');
    assert.strictEqual(typeof temporalApi.createCheckpoint, 'function');
    assert.strictEqual(typeof temporalApi.reconstructOffline, 'function');
    assert.strictEqual(typeof temporalApi.getEvent, 'function');
    assert.strictEqual(typeof temporalApi.getHealth, 'function');
  });
});

describe('TemporalIntelligenceView Component (Task 111)', () => {
  test('initializes with default diff tab and empty collections', () => {
    const view = new TemporalIntelligenceView();
    assert.strictEqual(view.activeTab, 'diff');
    assert.strictEqual(view.selectedEntity, 'global');
    assert.strictEqual(view.activeChangeset, null);
    assert.strictEqual(view.asOfResult, null);
    assert.deepStrictEqual(view.anomalies, []);
    assert.deepStrictEqual(view.gaps, []);
  });

  test('generates complete HTML with header, metric cards, and navigation tabs', () => {
    const view = new TemporalIntelligenceView();
    view.timelineData = {
      timeline_id: 'time_test_01',
      total_events: 14,
      total_transitions: 6,
      events: [],
      transitions: [],
    };
    view.anomalies = [
      { anomaly_type: 'RAPID_OSCILLATION', explanation: 'Flip-flop in state', detected_at: new Date().toISOString() },
    ];
    view.gaps = [
      { subsystem: 'telemetry', duration_seconds: 420.0, gap_start: new Date().toISOString(), gap_end: new Date().toISOString(), reason: 'Silent window' },
    ];

    const html = view.template();
    assert.ok(html.includes('Kairo Temporal Intelligence & Event History'));
    assert.ok(html.includes('Task 111'));
    assert.ok(html.includes('14'));
    assert.ok(html.includes('State Transitions'));
    assert.ok(html.includes('What Changed?'));
    assert.ok(html.includes('Chronological Timeline'));
    assert.ok(html.includes('State-at-Time (As-Of)'));
  });

  test('renders diff view results with category badges', () => {
    const view = new TemporalIntelligenceView();
    view.activeChangeset = {
      from_reference: 'checkpoint_a',
      to_reference: 'checkpoint_b',
      from_time: new Date().toISOString(),
      to_time: new Date().toISOString(),
      added_count: 1,
      removed_count: 0,
      modified_count: 1,
      degraded_count: 1,
      recovered_count: 0,
      unattributed_count: 1,
      changes: [
        {
          attribute_path: 'service_health',
          previous_value: 'READY',
          new_value: 'DEGRADED',
          category: 'DEGRADED',
          attribution: 'DIRECTLY_ATTRIBUTED',
        },
      ],
    };

    const diffHtml = view.renderDiffResults();
    assert.ok(diffHtml.includes('checkpoint_a ➔ checkpoint_b'));
    assert.ok(diffHtml.includes('service_health'));
    assert.ok(diffHtml.includes('DEGRADED'));
    assert.ok(diffHtml.includes('DIRECTLY_ATTRIBUTED'));
  });

  test('renders historical As-Of result with PAST STATE badge', () => {
    const view = new TemporalIntelligenceView();
    view.asOfResult = {
      entity_id: 'mission_99',
      state: 'ACTIVE',
      as_of_time: '2026-09-18T05:00:00Z',
      effective_from: '2026-09-18T04:45:00Z',
      confidence: 1.0,
      is_historical_reconstruction: true,
      source: 'operator',
    };

    const asOfHtml = view.renderAsOfResult(view.asOfResult);
    assert.ok(asOfHtml.includes('Entity: mission_99'));
    assert.ok(asOfHtml.includes('State: ACTIVE'));
    assert.ok(asOfHtml.includes('PAST STATE'));
  });
});
