import test from 'node:test';
import assert from 'node:assert/strict';
import { Endpoints, communicationApi } from '../lib/api/endpoints.js';
import { CommunicationView } from '../components/communication/communicationView.js';

test('Kairo Social & Communication Intelligence Engine Frontend Tests (Task 49)', async (t) => {
  await t.test('Endpoints defines communicationApi methods', () => {
    assert.strictEqual(typeof Endpoints.ingestInboundCommunication, 'function');
    assert.strictEqual(typeof Endpoints.listCommunicationThreads, 'function');
    assert.strictEqual(typeof Endpoints.getCommunicationThread, 'function');
    assert.strictEqual(typeof Endpoints.generateCommunicationDraft, 'function');
    assert.strictEqual(typeof Endpoints.listCommunicationDrafts, 'function');
    assert.strictEqual(typeof Endpoints.approveCommunicationDraft, 'function');
    assert.strictEqual(typeof Endpoints.sendCommunication, 'function');
    assert.strictEqual(typeof Endpoints.listCommunicationContacts, 'function');
    assert.strictEqual(typeof Endpoints.addCommunicationContact, 'function');
    assert.strictEqual(typeof Endpoints.listCommunicationCommitments, 'function');
    assert.strictEqual(typeof Endpoints.listCommunicationFollowups, 'function');
    assert.strictEqual(typeof Endpoints.getCommunicationMetrics, 'function');
    assert.strictEqual(typeof Endpoints.getCommunicationHealth, 'function');

    assert.strictEqual(typeof communicationApi.ingestInbound, 'function');
    assert.strictEqual(typeof communicationApi.listThreads, 'function');
    assert.strictEqual(typeof communicationApi.generateDraft, 'function');
    assert.strictEqual(typeof communicationApi.approveDraft, 'function');
    assert.strictEqual(typeof communicationApi.send, 'function');
  });

  await t.test('CommunicationView instantiates and formats dates properly', () => {
    const mockContainer = { innerHTML: '', querySelectorAll: () => [], querySelector: () => null };
    const view = new CommunicationView(mockContainer);

    assert.strictEqual(view.activeTab, 'threads');
    assert.strictEqual(view.formatDate(null), 'N/A');
    const validDate = view.formatDate('2026-09-10T12:00:00Z');
    assert.ok(typeof validDate === 'string' && validDate.length > 0);
  });

  await t.test('CommunicationView badge classes reflect status mappings', () => {
    const mockContainer = { innerHTML: '', querySelectorAll: () => [], querySelector: () => null };
    const view = new CommunicationView(mockContainer);

    assert.strictEqual(view.getStatusBadgeClass('DELIVERED'), 'badge-success');
    assert.strictEqual(view.getStatusBadgeClass('DRAFT'), 'badge-warning');
    assert.strictEqual(view.getStatusBadgeClass('FAILED'), 'badge-danger');
    assert.strictEqual(view.getStatusBadgeClass('SENT'), 'badge-primary');
    assert.strictEqual(view.getStatusBadgeClass('UNKNOWN'), 'badge-neutral');
  });
});
