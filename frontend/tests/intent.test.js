import test from 'node:test';
import assert from 'node:assert/strict';
import { Endpoints } from '../lib/api/endpoints.js';
import { ChatView } from '../components/chat/chatView.js';

test('Kairo Unified Command & Intent Layer Frontend Tests (Task 35)', async (t) => {
  await t.test('Endpoints defines sendCommand, resolveCommand, and getCommand (Spec 122, 123)', () => {
    assert.strictEqual(typeof Endpoints.sendCommand, 'function');
    assert.strictEqual(typeof Endpoints.resolveCommand, 'function');
    assert.strictEqual(typeof Endpoints.getCommand, 'function');
  });

  await t.test('ChatView renders Context Indicator showing active Project and Task (Spec 129)', () => {
    const mockStore = {
      getState: () => ({
        conversations: [],
        isStreaming: false,
        activeProject: {
          name: 'Kairo',
          repositories: ['kairo-core'],
        },
        activeTask: {
          id: 'task_ci_investigate',
          title: 'Investigate CI Failure',
        },
        contextPacket: { total_items: 4 },
      }),
    };

    const chatView = new ChatView({ store: mockStore });
    const html = chatView.render();

    assert.ok(html.includes('Project: Kairo'), 'Header must display active project');
    assert.ok(html.includes('Task: Investigate CI Failure'), 'Header must display active task');
  });

  await t.test('ChatView renders Clarification Card with interactive options when ambiguous (Spec 45, 46, 126)', () => {
    const chatView = new ChatView({
      store: {
        getState: () => ({ conversations: [], isStreaming: false }),
      },
    });

    const msg = {
      role: 'assistant',
      content: 'I found two repositories named Kairo. Which one?',
      clarification: {
        reason: 'Which Kairo repository did you mean?',
        options: [
          { label: 'Kairo-staging', value: 'Kairo-staging' },
          { label: 'Kairo-prod', value: 'Kairo-prod' },
        ],
      },
    };

    const itemHtml = chatView._renderMessageItem(msg, 0);

    assert.ok(itemHtml.includes('clarification-card'), 'Clarification card must be rendered');
    assert.ok(itemHtml.includes('Which Kairo repository did you mean?'), 'Clarification reason must be rendered');
    assert.ok(itemHtml.includes('Kairo-staging'), 'Option button Kairo-staging must be rendered');
    assert.ok(itemHtml.includes('Kairo-prod'), 'Option button Kairo-prod must be rendered');
  });

  await t.test('ChatView renders Intent Preview banner for meaningful operations (Spec 127)', () => {
    const chatView = new ChatView({
      store: {
        getState: () => ({ conversations: [], isStreaming: false }),
      },
    });

    const msg = {
      role: 'assistant',
      content: 'Preparing to execute requested changes.',
      intentPreview: {
        text: "I'll investigate Kairo's failed CI run",
        risk: 'NORMAL',
      },
    };

    const itemHtml = chatView._renderMessageItem(msg, 0);

    assert.ok(itemHtml.includes('intent-preview-banner'), 'Intent preview banner must be rendered');
    assert.ok(itemHtml.includes("I'll investigate Kairo's failed CI run"), 'Preview text must be displayed');
  });
});
