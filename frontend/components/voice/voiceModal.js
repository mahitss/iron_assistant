/**
 * Kairo Voice Modal
 * Clean voice interaction interface with explicit state management:
 * Idle, Listening, Processing, Speaking, Error.
 * Never activates microphone automatically. User must explicitly click to start.
 */

import { store } from '../../state/store.js';

export class VoiceModal {
  constructor() {
    this.modalEl = null;
    this.state = 'idle'; // 'idle', 'listening', 'processing', 'speaking', 'error'
    this.transcript = '';
    this.recognition = null;
    this.onSendTranscript = null;
  }

  open({ onSend } = {}) {
    this.onSendTranscript = onSend;
    this.state = 'idle';
    this.transcript = '';

    this.modalEl = document.createElement('div');
    this.modalEl.className = 'modal-backdrop';
    this.modalEl.id = 'voice-modal-backdrop';
    this.modalEl.innerHTML = `
      <div class="voice-modal-card" role="dialog" aria-labelledby="voice-modal-title">
        <button class="voice-close-btn" aria-label="Close voice">&times;</button>
        <h2 id="voice-modal-title" class="sr-only">Voice Interaction</h2>

        <div class="voice-orb-wrapper">
          <div class="voice-orb ${this.state}" id="voice-orb" role="status" aria-live="polite">
            <div class="orb-core"></div>
            <div class="orb-wave"></div>
          </div>
        </div>

        <div class="voice-status-label" id="voice-status-text">Tap microphone to speak</div>
        <div class="voice-transcript-box" id="voice-transcript-text">
          <span class="transcript-placeholder">"Ask Kairo a question..."</span>
        </div>

        <div class="voice-controls">
          <button class="btn btn-primary btn-round" id="voice-toggle-btn" aria-label="Start listening">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="22"/><line x1="8" y1="22" x2="16" y2="22"/></svg>
          </button>
          <button class="btn btn-secondary" id="voice-send-btn" disabled>Send to Chat</button>
        </div>
      </div>
    `;

    document.body.appendChild(this.modalEl);
    this._bindEvents();
  }

  _bindEvents() {
    if (!this.modalEl) return;

    const closeBtn = this.modalEl.querySelector('.voice-close-btn');
    closeBtn.addEventListener('click', () => this.close());

    const toggleBtn = this.modalEl.querySelector('#voice-toggle-btn');
    toggleBtn.addEventListener('click', () => {
      if (this.state === 'listening') {
        this.stopListening();
      } else {
        this.startListening();
      }
    });

    const sendBtn = this.modalEl.querySelector('#voice-send-btn');
    sendBtn.addEventListener('click', () => {
      if (this.transcript.trim() && this.onSendTranscript) {
        this.onSendTranscript(this.transcript.trim());
        this.close();
      }
    });
  }

  startListening() {
    this._setState('listening', 'Listening...', 'Go ahead, I am listening...');

    // Web Speech API check
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      try {
        this.recognition = new SpeechRecognition();
        this.recognition.continuous = false;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';

        this.recognition.onresult = (event) => {
          let text = '';
          for (let i = 0; i < event.results.length; i++) {
            text += event.results[i][0].transcript;
          }
          this.transcript = text;
          this._updateTranscript(text);
        };

        this.recognition.onerror = (e) => {
          this._setState('error', 'Audio Error', `Microphone error: ${e.error || 'Permission denied'}`);
        };

        this.recognition.onend = () => {
          if (this.transcript.trim()) {
            this._setState('idle', 'Ready to send', this.transcript);
          } else {
            this._setState('idle', 'Tap microphone to speak', '');
          }
        };

        this.recognition.start();
      } catch (err) {
        this._setState('error', 'Error', err.message);
      }
    } else {
      // Fallback message
      this._setState('listening', 'Listening (Simulated)', 'How can I assist with your workspace?');
      this.transcript = 'How can I assist with your workspace?';
      setTimeout(() => {
        this._setState('idle', 'Captured', this.transcript);
      }, 1800);
    }
  }

  stopListening() {
    if (this.recognition) {
      try { this.recognition.stop(); } catch {}
    }
    this._setState('idle', 'Tap microphone to speak', this.transcript);
  }

  _setState(state, statusText, transcriptText) {
    this.state = state;
    if (!this.modalEl) return;

    const orb = this.modalEl.querySelector('#voice-orb');
    if (orb) {
      orb.className = `voice-orb ${state}`;
    }

    const label = this.modalEl.querySelector('#voice-status-text');
    if (label) label.innerText = statusText;

    if (transcriptText !== undefined) {
      this._updateTranscript(transcriptText);
    }

    const sendBtn = this.modalEl.querySelector('#voice-send-btn');
    if (sendBtn) {
      sendBtn.disabled = !this.transcript.trim();
    }
  }

  _updateTranscript(text) {
    if (!this.modalEl) return;
    const box = this.modalEl.querySelector('#voice-transcript-text');
    if (box) {
      box.innerText = text || '"Ask Kairo a question..."';
    }
  }

  close() {
    this.stopListening();
    if (this.modalEl) {
      this.modalEl.remove();
      this.modalEl = null;
    }
  }
}
