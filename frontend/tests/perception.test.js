/**
 * Unit tests for Kairo Perception & Environmental Awareness Engine (Task 46)
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { endpoints } from '../lib/api/endpoints.js';
import { PerceptionView } from '../components/perception/perceptionView.js';

describe('Perception & Environmental Awareness Engine Endpoints & UI (Task 46)', () => {
  test('Endpoints exposes all Task 46 perception methods', () => {
    assert.strictEqual(typeof endpoints.registerPerceptionSource, 'function');
    assert.strictEqual(typeof endpoints.listPerceptionSources, 'function');
    assert.strictEqual(typeof endpoints.disablePerceptionSource, 'function');
    assert.strictEqual(typeof endpoints.ingestPerceptionEvent, 'function');
    assert.strictEqual(typeof endpoints.getRecentObservations, 'function');
    assert.strictEqual(typeof endpoints.getRecentChanges, 'function');
    assert.strictEqual(typeof endpoints.captureEnvironmentSnapshot, 'function');
    assert.strictEqual(typeof endpoints.getLatestSnapshot, 'function');
    assert.strictEqual(typeof endpoints.getLiveSituation, 'function');
    assert.strictEqual(typeof endpoints.getPerceptionHealth, 'function');
  });

  test('PerceptionView initializes with default state and environment', () => {
    const mockContainer = {
      innerHTML: '',
      querySelector: () => null,
      querySelectorAll: () => [],
    };

    const view = new PerceptionView(mockContainer);
    assert.strictEqual(view.activeTab, 'observations');
    assert.strictEqual(view.selectedEnvironment, 'DEVELOPMENT');
    assert.strictEqual(view.isLoading, false);
    assert.deepStrictEqual(view.sources, []);
    assert.deepStrictEqual(view.observations, []);
    assert.deepStrictEqual(view.changes, []);
    assert.strictEqual(view.situation, null);
    assert.strictEqual(view.snapshot, null);
    assert.strictEqual(view.health, null);
  });

  test('PerceptionView helper formatters function as expected', () => {
    const view = new PerceptionView({});
    assert.strictEqual(view.formatConfidence(null), '100%');
    assert.strictEqual(view.formatConfidence(0.95), '95%');
    assert.strictEqual(view.formatConfidence(0.5), '50%');
    assert.strictEqual(view.formatDate(null), 'N/A');
  });

  test('PerceptionView renders HTML skeleton structure', async () => {
    let htmlOutput = '';
    const mockContainer = {
      set innerHTML(val) {
        htmlOutput = val;
      },
      querySelector: () => null,
      querySelectorAll: () => [],
    };

    const view = new PerceptionView(mockContainer);
    await view.render();

    assert.ok(htmlOutput.includes('Perception & Environmental Awareness Engine'));
    assert.ok(htmlOutput.includes('Live Environmental Situational Awareness'));
    assert.ok(htmlOutput.includes('Verified Telemetry Facts'));
    assert.ok(htmlOutput.includes('data-tab="observations"'));
    assert.ok(htmlOutput.includes('data-tab="sources"'));
    assert.ok(htmlOutput.includes('data-tab="changes"'));
    assert.ok(htmlOutput.includes('data-tab="snapshots"'));
  });

  test('PerceptionView renders different tab contents correctly', () => {
    const view = new PerceptionView({});
    
    // Observations
    view.activeTab = 'observations';
    const obsHtml = view.renderActiveTab();
    assert.ok(obsHtml.includes('No observations recorded yet'));

    // Sources
    view.activeTab = 'sources';
    view.sources = [{
      source_id: 'src_dev_1',
      name: 'Local Workstation',
      type: 'DEVICE',
      status: 'HEALTHY',
      reliability: 0.99,
      privacy_level: 'INTERNAL',
      last_seen: new Date().toISOString(),
    }];
    const srcHtml = view.renderActiveTab();
    assert.ok(srcHtml.includes('Local Workstation'));
    assert.ok(srcHtml.includes('Trust Weight:'));
    assert.ok(srcHtml.includes('99%'));

    // Changes
    view.activeTab = 'changes';
    view.changes = [{
      change_id: 'chg_1',
      subject: 'service:api',
      change_type: 'HEALTH_CHANGE',
      significance: 'HIGH',
      environment: 'PRODUCTION',
      timestamp: new Date().toISOString(),
    }];
    const chgHtml = view.renderActiveTab();
    assert.ok(chgHtml.includes('service:api'));
    assert.ok(chgHtml.includes('HIGH'));

    // Snapshots
    view.activeTab = 'snapshots';
    const snapHtml = view.renderActiveTab();
    assert.ok(snapHtml.includes('Latest Environment Snapshot'));
  });
});
