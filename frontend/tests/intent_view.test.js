/**
 * Unit and component tests for Task 108:
 * Autonomous Intent Understanding, Goal Inference & Request Semantics Console
 */

import test from 'node:test';
import assert from 'node:assert';
import { intentApi } from '../lib/api/endpoints.js';
import { IntentView } from '../components/intent/intentView.js';

test('Task 108 - Intent API client surface', async (t) => {
  await t.test('intentApi exposes all required Task 108 methods', () => {
    assert.strictEqual(typeof intentApi.getDashboard, 'function');
    assert.strictEqual(typeof intentApi.submitRequest, 'function');
    assert.strictEqual(typeof intentApi.listRequests, 'function');
    assert.strictEqual(typeof intentApi.getRequest, 'function');
    assert.strictEqual(typeof intentApi.correctRequest, 'function');
    assert.strictEqual(typeof intentApi.cancelRequest, 'function');
    assert.strictEqual(typeof intentApi.listIntents, 'function');
    assert.strictEqual(typeof intentApi.getCurrentIntents, 'function');
    assert.strictEqual(typeof intentApi.getIntentsHistory, 'function');
    assert.strictEqual(typeof intentApi.getAmbiguousIntents, 'function');
    assert.strictEqual(typeof intentApi.searchIntents, 'function');
    assert.strictEqual(typeof intentApi.getIntent, 'function');
    assert.strictEqual(typeof intentApi.getVersions, 'function');
    assert.strictEqual(typeof intentApi.getEvidence, 'function');
    assert.strictEqual(typeof intentApi.getCorrections, 'function');
    assert.strictEqual(typeof intentApi.getClarifications, 'function');
    assert.strictEqual(typeof intentApi.createSnapshot, 'function');
    assert.strictEqual(typeof intentApi.getSnapshot, 'function');
    assert.strictEqual(typeof intentApi.answerClarificationQuery, 'function');
  });
});

test('Task 108 - IntentView Component Initialization and Rendering', async (t) => {
  function createMockContainer() {
    const listeners = {};
    const elements = {};

    function makeElement(tag, className = '') {
      return {
        tagName: tag,
        className,
        dataset: {},
        textContent: '',
        innerHTML: '',
        value: '',
        classList: {
          add(c) { this.classes = this.classes || new Set(); this.classes.add(c); },
          remove(c) { this.classes = this.classes || new Set(); this.classes.delete(c); },
          contains(c) { return this.classes ? this.classes.has(c) : false; },
        },
        addEventListener(evt, fn) {
          listeners[evt] = listeners[evt] || [];
          listeners[evt].push(fn);
        },
        querySelector(sel) {
          if (sel.startsWith('#')) return elements[sel.substring(1)] || null;
          return null;
        },
        querySelectorAll(sel) {
          return [];
        },
      };
    }

    const container = makeElement('div');
    container.innerHTML = '';
    return container;
  }

  await t.test('IntentView instantiates with default tab and options', () => {
    const container = createMockContainer();
    const view = new IntentView({ container, activeTab: 'dashboard' });
    assert.strictEqual(view.activeTab, 'dashboard');
    assert.strictEqual(view.intents.length, 0);
    assert.strictEqual(view.requests.length, 0);
  });

  await t.test('IntentView renders container layout and metric cards', () => {
    const container = createMockContainer();
    const view = new IntentView({ container });
    view.renderContainer();

    assert.ok(container.innerHTML.includes('intent-console'));
    assert.ok(container.innerHTML.includes('TASK 108'));
    assert.ok(container.innerHTML.includes('Autonomous Intent Understanding & Request Semantics'));
    assert.ok(container.innerHTML.includes('metric-total-requests'));
    assert.ok(container.innerHTML.includes('metric-total-intents'));
    assert.ok(container.innerHTML.includes('metric-pending-clarifications'));
    assert.ok(container.innerHTML.includes('metric-unresolved-ambiguities'));
    assert.ok(container.innerHTML.includes('metric-external-effect'));
  });

  await t.test('IntentView renders Dashboard tab with Epistemic Badges', () => {
    const container = createMockContainer();
    const view = new IntentView({ container });
    view.dashboardData = {
      total_requests: 3,
      total_intents: 5,
      pending_clarifications: 1,
      unresolved_ambiguities: 2,
      epistemic_summary: {
        explicit: 2,
        inferred: 2,
        unknown: 1,
        confirmed: 0,
      },
      categories_breakdown: {
        CODE_MODIFICATION: 2,
        ANALYSIS: 1,
      },
      recent_requests: [
        {
          request_id: 'req_001',
          raw_text: 'Refactor database models',
          source: 'DIRECT_USER',
          status: 'UNDERSTOOD',
        },
      ],
    };

    const html = view.renderDashboardTab();
    assert.ok(html.includes('EXPLICIT'));
    assert.ok(html.includes('INFERRED'));
    assert.ok(html.includes('UNKNOWN'));
    assert.ok(html.includes('CONFIRMED'));
    assert.ok(html.includes('CODE_MODIFICATION'));
    assert.ok(html.includes('Refactor database models'));
  });

  await t.test('IntentView renders Clarifications tab with consequence callout', () => {
    const container = createMockContainer();
    const view = new IntentView({ container });
    view.dashboardData = {
      clarification_queue: [
        {
          clarification_id: 'clr_001',
          intent_id: 'int_001',
          question: 'Do you want to deploy to staging or production?',
          rationale: 'Target environment affects live workloads.',
          options: ['staging', 'production'],
          status: 'PENDING',
        },
      ],
    };

    const html = view.renderClarificationsTab();
    assert.ok(html.includes('Consequence-Aware Clarification Queue'));
    assert.ok(html.includes('Do you want to deploy to staging or production?'));
    assert.ok(html.includes('Target environment affects live workloads.'));
    assert.ok(html.includes('staging'));
    assert.ok(html.includes('production'));
  });

  await t.test('IntentView renders Detail tab with non-goals and epistemic status', () => {
    const container = createMockContainer();
    const view = new IntentView({ container });
    view.selectedIntent = {
      intent_id: 'int_123',
      summary: 'Optimize query performance',
      category: 'OPTIMIZATION',
      target: 'db_queries',
      target_epistemic: 'EXPLICIT',
      scope: 'CURRENT_PROJECT',
      external_effect: 'NO_EXTERNAL_EFFECT',
      overall_confidence: 0.95,
      status: 'UNDERSTOOD',
      non_goals: ['Do not change existing REST API contract', 'Do not drop indexes without approval'],
    };
    view.selectedSnapshot = {
      snapshot_id: 'snap_123',
      intent_id: 'int_123',
      intent_summary: 'Optimize query performance',
    };

    const html = view.renderDetailTab();
    assert.ok(html.includes('Optimize query performance'));
    assert.ok(html.includes('Explicit Non-Goals (Preserved Boundaries)'));
    assert.ok(html.includes('Do not change existing REST API contract'));
    assert.ok(html.includes('Do not drop indexes without approval'));
    assert.ok(html.includes('snap_123'));
  });

  await t.test('getStatusBadgeClass maps statuses correctly', () => {
    const view = new IntentView({});
    assert.strictEqual(view.getStatusBadgeClass('UNDERSTOOD'), 'badge-success');
    assert.strictEqual(view.getStatusBadgeClass('CONFIRMED'), 'badge-success');
    assert.strictEqual(view.getStatusBadgeClass('CLARIFICATION_REQUIRED'), 'badge-warning');
    assert.strictEqual(view.getStatusBadgeClass('AMBIGUOUS'), 'badge-warning');
    assert.strictEqual(view.getStatusBadgeClass('CANCELLED'), 'badge-danger');
    assert.strictEqual(view.getStatusBadgeClass('REJECTED'), 'badge-danger');
    assert.strictEqual(view.getStatusBadgeClass('SUPERSEDED'), 'badge-neutral');
  });
});
