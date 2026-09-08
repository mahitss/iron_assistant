/**
 * VoiceClient: Coordinates WebSocket communication, audio capture, and audio playback.
 */

import { AudioCapture } from './audioCapture.js';
import { AudioPlayback } from './audioPlayback.js';

export class VoiceClient {
  /**
   * @param {Object} options
   * @param {string} [options.wsUrl] - WebSocket URL (defaults to location host + /api/v1/voice)
   * @param {string} [options.sessionId] - Optional session ID to attach to
   * @param {function(string): void} [options.onStateChange] - Session state callback
   * @param {function(string, boolean): void} [options.onTranscript] - Transcript callback (text, isFinal)
   * @param {function(): void} [options.onThinking] - Thinking indicator callback
   * @param {function(string, string): void} [options.onToolActivity] - Tool activity callback
   * @param {function(string): void} [options.onResponseText] - Streaming response text chunk
   * @param {function(string): void} [options.onResponseComplete] - Turn complete callback
   * @param {function(Error): void} [options.onError] - Error callback
   */
  constructor(options = {}) {
    this.wsUrl = options.wsUrl || this._getDefaultWsUrl();
    this.sessionId = options.sessionId || null;
    this.onStateChange = options.onStateChange || (() => {});
    this.onTranscript = options.onTranscript || (() => {});
    this.onThinking = options.onThinking || (() => {});
    this.onToolActivity = options.onToolActivity || (() => {});
    this.onResponseText = options.onResponseText || (() => {});
    this.onResponseComplete = options.onResponseComplete || (() => {});
    this.onError = options.onError || ((err) => console.error('[VoiceClient]', err));

    this.ws = null;
    this.state = 'IDLE';
    this.isConnected = false;

    // Initialize capture and playback
    this.playback = new AudioPlayback({
      onPlaybackStateChange: (isPlaying) => {
        if (isPlaying) this._setState('SPEAKING');
        else if (this.state === 'SPEAKING') this._setState('LISTENING');
      },
      onError: (err) => this.onError(err),
    });

    this.capture = new AudioCapture({
      sampleRate: 16000,
      onAudioChunk: (chunk) => this._sendAudioChunk(chunk),
      onError: (err) => this.onError(err),
    });
  }

  _getDefaultWsUrl() {
    if (typeof process !== 'undefined' && process.env && process.env.KAIRO_WS_URL) {
      return process.env.KAIRO_WS_URL;
    }
    if (typeof window === 'undefined') return 'ws://127.0.0.1:8000/api/v1/voice';
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${proto}//${window.location.host}/api/v1/voice`;
  }

  _setState(newState) {
    this.state = newState;
    this.onStateChange(newState);
  }

  /**
   * Connect WebSocket and start capturing microphone input.
   */
  async start() {
    if (this.isConnected) return;

    try {
      await this._connectWebSocket();
      const micGranted = await this.capture.start();
      if (!micGranted) {
        this.disconnect();
        return;
      }
      this._setState('LISTENING');
    } catch (err) {
      this.onError(err);
      this.disconnect();
    }
  }

  _connectWebSocket() {
    return new Promise((resolve, reject) => {
      try {
        const WebSocketClass =
          (typeof window !== 'undefined' && window.WebSocket)
            ? window.WebSocket
            : (typeof WebSocket !== 'undefined' ? WebSocket : globalThis.WebSocket);
        this.ws = new WebSocketClass(this.wsUrl);


        this.ws.binaryType = 'arraybuffer';

        this.ws.onopen = () => {
          this.isConnected = true;
          this.ws.send(
            JSON.stringify({
              type: 'start_session',
              session_id: this.sessionId,
              sample_rate: 16000,
            })
          );
          resolve();
        };

        this.ws.onmessage = (event) => this._handleMessage(event);

        this.ws.onerror = (err) => {
          this.onError(err);
          reject(err);
        };

        this.ws.onclose = () => {
          this.isConnected = false;
          this._setState('CLOSED');
        };
      } catch (err) {
        reject(err);
      }
    });
  }

  _sendAudioChunk(chunk) {
    if (this.ws && this.ws.readyState === (window?.WebSocket?.OPEN || 1)) {
      this.ws.send(chunk);
    }
  }

  _handleMessage(event) {
    if (event.data instanceof ArrayBuffer) {
      // Binary synthesized audio frame from server
      this.playback.queueChunk(event.data);
      return;
    }

    if (typeof event.data === 'string') {
      try {
        const msg = JSON.parse(event.data);
        switch (msg.type) {
          case 'session_started':
            this.sessionId = msg.session_id;
            break;
          case 'transcript_partial':
            this.onTranscript(msg.text, false);
            break;
          case 'transcript_final':
            this.onTranscript(msg.text, true);
            this._setState('PROCESSING');
            break;
          case 'thinking':
            this.onThinking();
            break;
          case 'tool_activity':
            this.onToolActivity(msg.tool, msg.status);
            break;
          case 'response_text':
            this.onResponseText(msg.chunk);
            break;
          case 'response_complete':
            this.onResponseComplete(msg.full_text);
            break;
          case 'interrupted':
            this.playback.interrupt();
            this._setState('LISTENING');
            break;
          case 'error':
            this.onError(new Error(`[${msg.code}] ${msg.message}`));
            break;
          case 'session_ended':
            this.disconnect();
            break;
          default:
            break;
        }
      } catch (err) {
        this.onError(err);
      }
    }
  }

  /**
   * User interrupts assistant speech (barge-in).
   */
  interrupt() {
    this.playback.interrupt();
    if (this.ws && this.ws.readyState === (window?.WebSocket?.OPEN || 1)) {
      this.ws.send(JSON.stringify({ type: 'interrupt' }));
    }
    this._setState('LISTENING');
  }

  /**
   * Signal that user has stopped speaking.
   */
  stopSpeaking() {
    if (this.ws && this.ws.readyState === (window?.WebSocket?.OPEN || 1)) {
      this.ws.send(JSON.stringify({ type: 'stop_speaking' }));
    }
    this._setState('PROCESSING');
  }

  /**
   * Cleanly stop recording, playback, and close WebSocket session.
   */
  disconnect() {
    this.capture.stop();
    this.playback.close();

    if (this.ws) {
      if (this.ws.readyState === (window?.WebSocket?.OPEN || 1)) {
        try {
          this.ws.send(JSON.stringify({ type: 'end_session' }));
          this.ws.close();
        } catch (_) {}
      }
      this.ws = null;
    }

    this.isConnected = false;
    this._setState('CLOSED');
  }
}
