import test from 'node:test';
import assert from 'node:assert/strict';
import { Endpoints } from '../lib/api/endpoints.js';
import { Composer } from '../components/chat/composer.js';
import { ChatView } from '../components/chat/chatView.js';

test('Kairo Multimodal Intelligence Layer Frontend Tests (Task 30)', async (t) => {
  await t.test('Endpoints object defines all required Multimodal API methods (Spec 79)', () => {
    assert.strictEqual(typeof Endpoints.analyzeMultimodal, 'function');
    assert.strictEqual(typeof Endpoints.transcribeAudio, 'function');
    assert.strictEqual(typeof Endpoints.processMultimodal, 'function');
    assert.strictEqual(typeof Endpoints.getMultimodalRequest, 'function');
  });

  await t.test('Composer renders explicit action buttons [＋] [Image] [File] [Voice] [Share Screen] (Specs 81, 82)', () => {
    const composer = new Composer();
    const html = composer.render();

    assert.ok(html.includes('id="multimodalMenuBtn"'), 'Must have add button [＋]');
    assert.ok(html.includes('id="imageAttachmentInput"'), 'Must have image input [Image]');
    assert.ok(html.includes('id="docAttachmentInput"'), 'Must have file input [File]');
    assert.ok(html.includes('id="voiceBtn"'), 'Must have voice button [Voice]');
    assert.ok(html.includes('id="screenShareBtn"'), 'Must have visibly separate [Share Screen] button');
  });

  await t.test('Composer pre-send preview bar displays attachment with replace and remove controls (Spec 83)', () => {
    const composer = new Composer();
    composer.setAttachment({ name: 'architecture_diagram.png', size: 1048576 }, 'image');
    const html = composer.render();

    assert.ok(html.includes('attachment-preview-bar'), 'Preview bar must be rendered');
    assert.ok(html.includes('architecture_diagram.png'), 'File name must be visible');
    assert.ok(html.includes('1.0 MB'), 'File size must be formatted');
    assert.ok(html.includes('btn-replace'), 'Replace button must be present');
    assert.ok(html.includes('attachment-remove-btn'), 'Remove button must be present');
  });

  await t.test('Composer renders active screen sharing state when enabled (Spec 82)', () => {
    const composer = new Composer();
    composer.setScreenContext(true, 'companion-pc-01');
    const html = composer.render();

    assert.ok(html.includes('screen-context-badge'), 'Screen badge must be rendered');
    assert.ok(html.includes('Screen Sharing Active'));
    assert.ok(html.includes('companion-pc-01'));
  });

  await t.test('ChatView renders user attachment and screen context pills in message turns', () => {
    const mockStore = {
      getState: () => ({
        conversations: [
          {
            role: 'user',
            content: 'What is wrong with this screenshot?',
            attachment: { name: 'error.png', type: 'image' },
            screenContext: { device_id: 'companion-pc-01' },
            timestamp: new Date().toISOString(),
          },
        ],
        isStreaming: false,
      }),
    };

    const chatView = new ChatView({ store: mockStore });
    const html = chatView.render();

    assert.ok(html.includes('user-attachment-pill'), 'User attachment pill must be rendered');
    assert.ok(html.includes('error.png'));
    assert.ok(html.includes('user-screen-pill'), 'User screen pill must be rendered');
    assert.ok(html.includes('companion-pc-01'));
  });

  await t.test('ChatView renders grounded citations and uncertainty warning callouts in assistant messages (Specs 61, 63, 85-89)', () => {
    const mockStore = {
      getState: () => ({
        conversations: [
          {
            role: 'assistant',
            content: 'Architecture Analysis: Database cluster is isolated.',
            citations: ['architecture.pdf (Page 4)', 'architecture.pdf (Page 7)'],
            uncertainty_note: 'Text in diagram was partially blurred.',
            timestamp: new Date().toISOString(),
          },
        ],
        isStreaming: false,
      }),
    };

    const chatView = new ChatView({ store: mockStore });
    const html = chatView.render();

    assert.ok(html.includes('multimodal-evidence-footer'), 'Evidence footer must be rendered');
    assert.ok(html.includes('architecture.pdf (Page 4)'));
    assert.ok(html.includes('architecture.pdf (Page 7)'));
    assert.ok(html.includes('uncertainty-callout'), 'Uncertainty callout must be rendered');
    assert.ok(html.includes('Text in diagram was partially blurred.'));
  });
});
