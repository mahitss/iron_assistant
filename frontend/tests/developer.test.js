import { test, describe } from 'node:test';
import assert from 'node:assert';
import { DeveloperPanel } from '../developer/developerPanel.js';

describe('Frontend Developer Panel Tests', () => {
  test('initializes with default values', () => {
    const panel = new DeveloperPanel();
    const state = panel.render();

    assert.strictEqual(state.repository, 'No repository selected');
    assert.strictEqual(state.branch, 'HEAD');
    assert.strictEqual(state.statusBadge, 'clean');
    assert.strictEqual(state.activeTab, 'status');
    assert.strictEqual(state.summary.stagedCount, 0);
  });

  test('updates repository and git status properly', () => {
    const panel = new DeveloperPanel();
    panel.setSelectedRepo('/workspace/my-project');
    panel.setBranch('feature/awesome-ui');
    panel.updateStatus({
      is_clean: false,
      modified_files: ['src/index.js', 'src/App.jsx'],
      staged_files: ['README.md'],
      untracked_files: ['test.log'],
    });

    const state = panel.render();
    assert.strictEqual(state.repository, '/workspace/my-project');
    assert.strictEqual(state.branch, 'feature/awesome-ui');
    assert.strictEqual(state.statusBadge, 'dirty');
    assert.strictEqual(state.summary.modifiedCount, 2);
    assert.strictEqual(state.summary.stagedCount, 1);
    assert.strictEqual(state.summary.untrackedCount, 1);
  });

  test('manages diffs, commits, issues, PRs, and checks', () => {
    const panel = new DeveloperPanel();
    panel.setCommits([
      { sha: 'abc1234', author: 'Dev', date: '2026-09-08', subject: 'Initial commit' }
    ]);
    panel.setDiff({
      diff_type: 'working_tree',
      diff_content: '+ new line\n- old line',
      is_truncated: false,
    });
    panel.setIssues([
      { number: 42, title: 'Bug in navbar', state: 'open' }
    ]);
    panel.setPullRequests([
      { number: 10, title: 'Add auth provider', state: 'open' }
    ]);
    panel.setChecks([
      { name: 'CI / Test', status: 'completed', conclusion: 'success' }
    ]);

    const state = panel.render();
    assert.strictEqual(state.summary.commitsCount, 1);
    assert.strictEqual(state.summary.issuesCount, 1);
    assert.strictEqual(state.summary.prsCount, 1);
    assert.strictEqual(state.summary.checksCount, 1);
    assert.strictEqual(state.content.diff.diff_content, '+ new line\n- old line');
  });

  test('enforces proposed changes review and approval lifecycle', () => {
    const panel = new DeveloperPanel();
    const change = panel.proposeChange({
      description: 'Fix typo in README',
      diff: '--- README.md\n+++ README.md\n-typo\n+fixed',
      targetFile: 'README.md',
    });

    assert.ok(change.id.startsWith('change_'));
    assert.strictEqual(change.lifecycle, 'PROPOSED CHANGE');
    assert.strictEqual(change.status, 'pending_approval');

    // Approve the change
    const approved = panel.approveChange(change.id);
    assert.strictEqual(approved.lifecycle, 'APPROVAL');
    assert.strictEqual(approved.status, 'approved');

    const state = panel.render();
    assert.strictEqual(state.summary.proposedChangesCount, 1);
  });
});
