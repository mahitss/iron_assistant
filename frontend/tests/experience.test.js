import test from 'node:test';
import assert from 'node:assert/strict';
import { Endpoints } from '../lib/api/endpoints.js';
import { MemoryView } from '../components/memory/memoryView.js';

test('Kairo Long-Term Experience and Learning Frontend Tests (Task 29)', async (t) => {
  await t.test('Endpoints object defines all required Feedback & Experience API methods', () => {
    assert.strictEqual(typeof Endpoints.submitFeedback, 'function');
    assert.strictEqual(typeof Endpoints.listFeedback, 'function');
    assert.strictEqual(typeof Endpoints.getFeedback, 'function');
    assert.strictEqual(typeof Endpoints.listExperiences, 'function');
    assert.strictEqual(typeof Endpoints.getExperience, 'function');
    assert.strictEqual(typeof Endpoints.recordCorrection, 'function');
    assert.strictEqual(typeof Endpoints.supersedeExperience, 'function');
    assert.strictEqual(typeof Endpoints.deleteExperience, 'function');
    assert.strictEqual(typeof Endpoints.setPreference, 'function');
    assert.strictEqual(typeof Endpoints.listPreferences, 'function');
    assert.strictEqual(typeof Endpoints.deletePreference, 'function');
    assert.strictEqual(typeof Endpoints.exportExperienceData, 'function');
    assert.strictEqual(typeof Endpoints.listLearningCandidates, 'function');
    assert.strictEqual(typeof Endpoints.reviewLearningCandidate, 'function');
    assert.strictEqual(typeof Endpoints.getFailureAnalytics, 'function');
    assert.strictEqual(typeof Endpoints.getSuccessAnalytics, 'function');
  });

  await t.test('MemoryView initializes with default tabs and user learning control state', () => {
    const mockContainer = { innerHTML: '', querySelector: () => null, querySelectorAll: () => [] };
    const view = new MemoryView(mockContainer);
    assert.ok(view);
    assert.strictEqual(view.activeTab, 'memories');
    assert.strictEqual(typeof view.isLearningEnabled, 'boolean');
    assert.ok(Array.isArray(view.memories));
    assert.ok(Array.isArray(view.preferences));
    assert.ok(Array.isArray(view.corrections));
    assert.ok(Array.isArray(view.experiences));
    assert.ok(Array.isArray(view.feedbacks));
    assert.ok(Array.isArray(view.candidates));
  });

  await t.test('MemoryView empty state generator produces clean semantic markup', () => {
    const mockContainer = { innerHTML: '', querySelector: () => null, querySelectorAll: () => [] };
    const view = new MemoryView(mockContainer);
    const html = view._emptyStateHtml('No experiences', 'Execution outcomes will appear here.');
    assert.ok(html.includes('No experiences'));
    assert.ok(html.includes('Execution outcomes will appear here.'));
  });

  await t.test('MemoryView renders learning toggle and export button in header', async () => {
    let renderedHtml = '';
    const mockContainer = {
      set innerHTML(val) { renderedHtml = val; },
      get innerHTML() { return renderedHtml; },
      querySelector: () => null,
      querySelectorAll: () => [],
    };
    const view = new MemoryView(mockContainer);
    await view.render();
    assert.ok(renderedHtml.includes('Memory &amp; Learning') || renderedHtml.includes('Memory & Learning'));
    assert.ok(renderedHtml.includes('Experience Learning:'));
    assert.ok(renderedHtml.includes('Export Data'));
    assert.ok(renderedHtml.includes('data-tab="preferences"'));
    assert.ok(renderedHtml.includes('data-tab="corrections"'));
    assert.ok(renderedHtml.includes('data-tab="experience"'));
    assert.ok(renderedHtml.includes('data-tab="feedback"'));
    assert.ok(renderedHtml.includes('data-tab="candidates"'));
  });
});
