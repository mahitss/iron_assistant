import test from 'node:test';
import assert from 'node:assert/strict';
import { SkillsView } from '../components/skills/skillsView.js';
import { SettingsView } from '../components/settings/settingsView.js';
import { SecurityView } from '../components/security/securityView.js';
import { ChatView } from '../components/chat/chatView.js';
import { CommandPalette } from '../components/layout/commandPalette.js';

test('Frontend Skills & Capability System Tests', async (t) => {
  const mockSkills = [
    {
      id: 'research.web',
      name: 'Web Research',
      description: 'Autonomous multi-source web intelligence, query generation, content extraction, and citation preservation.',
      version: '1.0.0',
      category: 'RESEARCH',
      risk_level: 'READ_ONLY',
      health_status: 'HEALTHY',
      enabled: true,
      requires_approval: false,
      capabilities: ['web_search', 'content_extraction', 'citation_synthesis'],
      required_tools: ['web_search', 'fetch_webpage'],
      optional_tools: ['summarize_content'],
      required_permissions: ['web.read'],
      source: 'BUILTIN',
      author: 'Kairo Core Team',
    },
    {
      id: 'developer.repository',
      name: 'Repository Analysis',
      description: 'Repository inspection, branch analysis, commit diffing, CI failure investigation, and test review.',
      version: '1.0.0',
      category: 'DEVELOPER',
      risk_level: 'READ_ONLY',
      health_status: 'HEALTHY',
      enabled: true,
      requires_approval: false,
      capabilities: ['inspect_files', 'inspect_git', 'inspect_ci'],
      required_tools: ['git_status', 'git_diff', 'inspect_file'],
      optional_tools: ['read_test_report'],
      required_permissions: ['developer.read'],
      source: 'BUILTIN',
      author: 'Kairo Core Team',
    },
    {
      id: 'computer.assist',
      name: 'Computer Assistance',
      description: 'Local companion hardware orchestration for authorized screen, mouse, and keyboard interactions.',
      version: '1.0.0',
      category: 'COMPUTER',
      risk_level: 'HIGH_RISK',
      health_status: 'DEGRADED',
      enabled: false,
      requires_approval: true,
      capabilities: ['screen_inspection', 'mouse_control', 'keyboard_input'],
      required_tools: ['screen_capture', 'mouse_click', 'key_press'],
      optional_tools: ['drag_drop'],
      required_permissions: ['computer.control'],
      source: 'BUILTIN',
      author: 'Kairo Core Team',
    },
  ];

  await t.test('SkillsView renders base layout structure', () => {
    const mockContainer = { innerHTML: '', querySelectorAll: () => [], querySelector: () => null };
    const view = new SkillsView(mockContainer);
    const html = view._renderLayout();

    assert.match(html, /KAIRO SKILLS &amp; CAPABILITIES/);
    assert.match(html, /skills-search-input/);
    assert.match(html, /skills-category-filters/);
    assert.match(html, /skills-grid/);
    assert.match(html, /data-category="ALL"/);
    assert.match(html, /data-category="RESEARCH"/);
  });

  await t.test('SkillsView filters skills by search query and category', () => {
    const mockContainer = { innerHTML: '', querySelectorAll: () => [], querySelector: () => null };
    const view = new SkillsView(mockContainer);
    view.skills = mockSkills;

    // All category, no query
    assert.equal(view._getFilteredSkills().length, 3);

    // Search query 'repo'
    view.searchQuery = 'repo';
    const repoFiltered = view._getFilteredSkills();
    assert.equal(repoFiltered.length, 1);
    assert.equal(repoFiltered[0].id, 'developer.repository');

    // Category filter 'COMPUTER'
    view.searchQuery = '';
    view.selectedCategory = 'COMPUTER';
    const computerFiltered = view._getFilteredSkills();
    assert.equal(computerFiltered.length, 1);
    assert.equal(computerFiltered[0].id, 'computer.assist');
  });

  await t.test('SkillsView renders skill cards with risk badges and tool counts', () => {
    const mockContainer = { innerHTML: '', querySelectorAll: () => [], querySelector: () => null };
    const view = new SkillsView(mockContainer);

    const cardReadOnly = view._renderSkillCard(mockSkills[0]);
    assert.match(cardReadOnly, /Web Research/);
    assert.match(cardReadOnly, /research\.web/);
    assert.match(cardReadOnly, /READ ONLY/);
    assert.match(cardReadOnly, /badge-risk-read-only/);
    assert.match(cardReadOnly, /badge-health-healthy/);
    assert.match(cardReadOnly, /3 tools/); // 2 required + 1 optional

    const cardHighRisk = view._renderSkillCard(mockSkills[2]);
    assert.match(cardHighRisk, /Computer Assistance/);
    assert.match(cardHighRisk, /HIGH RISK/);
    assert.match(cardHighRisk, /badge-risk-high-risk/);
    assert.match(cardHighRisk, /DEGRADED/);
    assert.match(cardHighRisk, /Requires Approval/);
  });

  await t.test('SettingsView renders Skills tab navigation and placeholder', () => {
    const mockContainer = { innerHTML: '', querySelectorAll: () => [], querySelector: () => null };
    const view = new SettingsView(mockContainer);
    view.activeTab = 'skills';
    const html = view._renderSkillsTab();

    assert.match(html, /skills-catalog-mount/);
    assert.match(html, /Loading Kairo Skills Catalog/);
  });

  await t.test('SecurityView renders Skills & Capabilities Governance section', () => {
    const view = new SecurityView();
    const html = view.render();

    assert.match(html, /SKILLS &amp; CAPABILITIES GOVERNANCE/);
    assert.match(html, /11 Registered/);
    assert.match(html, /3 Levels/);
    assert.match(html, /20 Steps/);
    assert.match(html, /Authoritative/);
  });

  await t.test('ChatView renders subtle skill indicator and execution steps', () => {
    const view = new ChatView();
    const msgWithSkill = {
      role: 'assistant',
      content: 'I analyzed the repository CI failure.',
      timestamp: '2026-09-09T11:00:00Z',
      skill: {
        id: 'developer.repository',
        name: 'Repository Analysis',
        state: 'COMPLETED',
        steps: [
          { title: 'Repository metadata inspected', completed: true },
          { title: 'Recent commits diffed', completed: true },
        ],
      },
    };

    const rendered = view._renderMessageItem(msgWithSkill, 0);
    assert.match(rendered, /skill-activity-container/);
    assert.match(rendered, /Using:/);
    assert.match(rendered, /Repository Analysis/);
    assert.match(rendered, /COMPLETED/);
    assert.match(rendered, /Repository metadata inspected/);
    assert.match(rendered, /Recent commits diffed/);
  });

  await t.test('CommandPalette contains Skill items for fast search (Ctrl+K)', () => {
    const palette = new CommandPalette();
    palette.setQuery('research');
    const filtered = palette.getFilteredCommands();

    const hasWebResearchSkill = filtered.some(c => c.id === 'skill-research-web');
    const hasKnowledgeSearchSkill = filtered.some(c => c.id === 'skill-knowledge-search');
    assert.ok(hasWebResearchSkill, 'CommandPalette should surface Web Research skill');
    assert.ok(hasKnowledgeSearchSkill, 'CommandPalette should surface Knowledge Search skill');
  });
});
