import test from 'node:test';
import assert from 'node:assert/strict';
import { ContextPanel } from '../context/contextPanel.js';

test('Frontend Personal Context Panel Tests', async (t) => {
  await t.test('initializes with default context settings and empty state', () => {
    const panel = new ContextPanel();
    assert.strictEqual(panel.settings.context_enabled, true);
    assert.strictEqual(panel.settings.memory_enabled, true);
    assert.strictEqual(panel.settings.project_context_enabled, true);
    assert.strictEqual(panel.settings.proactive_context_enabled, true);
    assert.strictEqual(panel.activeProject, null);
    assert.strictEqual(panel.contextItems.length, 0);
  });

  await t.test('switches active project and tracks project list', () => {
    const panel = new ContextPanel();
    const proj = {
      id: 'proj_kairo',
      name: 'Kairo Assistant',
      status: 'ACTIVE',
      repositories: ['mahitss/iron_assistant'],
    };

    panel.setActiveProject(proj);
    assert.strictEqual(panel.activeProject.id, 'proj_kairo');
    assert.strictEqual(panel.projects.length, 1);
    assert.strictEqual(panel.projects[0].name, 'Kairo Assistant');
  });

  await t.test('populates context items and groups them cleanly by category', () => {
    const panel = new ContextPanel();
    panel.setContextItems([
      {
        source_type: 'PROJECT_CONTEXT',
        source_id: 'proj_1',
        title: 'Project Kairo',
        content: 'Autonomous AI Assistant',
        reason: 'Active project workspace',
      },
      {
        source_type: 'MEMORY_CONTEXT',
        source_id: 'mem_1',
        title: 'Memory (Fact)',
        content: 'Uses PostgreSQL and pgvector',
        reason: 'Semantic similarity match',
      },
      {
        source_type: 'WORKFLOW_CONTEXT',
        source_id: 'wf_1',
        title: 'Workflow CI Monitor',
        content: 'Status: ACTIVE',
        reason: 'Recently failed workflow run',
      },
      {
        source_type: 'PROACTIVE_CONTEXT',
        source_id: 'pro_1',
        title: 'Alert: CI Failed',
        content: 'Run #104 failed on branch main',
        reason: 'Unread high priority alert',
      },
    ]);

    assert.strictEqual(panel.contextItems.length, 4);
    const grouped = panel.getGroupedContext();
    assert.strictEqual(grouped.project.length, 1);
    assert.strictEqual(grouped.memory.length, 1);
    assert.strictEqual(grouped.workflow.length, 1);
    assert.strictEqual(grouped.proactive.length, 1);
  });

  await t.test('allows user to inspect provenance reason without black-box scores', () => {
    const panel = new ContextPanel();
    panel.setContextItems([
      {
        source_type: 'MEMORY_CONTEXT',
        source_id: 'mem_pg',
        title: 'Tech Stack Memory',
        content: 'PostgreSQL database',
        reason: 'Mentioned in previous turn regarding database migrations',
      },
    ]);

    const info = panel.inspectProvenance('mem_pg');
    assert.notStrictEqual(info, null);
    assert.strictEqual(info.title, 'Tech Stack Memory');
    assert.strictEqual(info.reason, 'Mentioned in previous turn regarding database migrations');
    assert.strictEqual(info.source_type, 'MEMORY_CONTEXT');
  });

  await t.test('toggles context personalization preferences safely', () => {
    const panel = new ContextPanel();
    assert.strictEqual(panel.settings.project_context_enabled, true);
    panel.toggleSetting('project_context_enabled');
    assert.strictEqual(panel.settings.project_context_enabled, false);
    panel.toggleSetting('project_context_enabled');
    assert.strictEqual(panel.settings.project_context_enabled, true);
  });
});
