import { test, describe, beforeEach } from 'node:test';
import assert from 'node:assert';
import { AudioCapture } from '../voice/audioCapture.js';
import { AudioPlayback } from '../voice/audioPlayback.js';
import { VoiceClient } from '../voice/voiceClient.js';

describe('Frontend Voice Pipeline Tests', () => {
  beforeEach(() => {
    // Mock browser globals for Node test environment
    global.window = {
      location: { protocol: 'http:', host: 'localhost:8000' },
      AudioContext: class MockAudioContext {
        constructor() {
          this.state = 'running';
          this.destination = {};
        }
        createMediaStreamSource() {
          return { connect: () => {}, disconnect: () => {} };
        }
        createScriptProcessor() {
          return { connect: () => {}, disconnect: () => {}, onaudioprocess: null };
        }
        createBufferSource() {
          return {
            connect: () => {},
            disconnect: () => {},
            start: () => {},
            stop: () => {},
            onended: null,
          };
        }
        decodeAudioData(buf) {
          return Promise.resolve({ duration: 1.0 });
        }
        close() {
          this.state = 'closed';
          return Promise.resolve();
        }
        resume() {
          this.state = 'running';
          return Promise.resolve();
        }
      },
    };

    let trackStopped = false;
    Object.defineProperty(globalThis.navigator, 'mediaDevices', {
      value: {
        getUserMedia: async (constraints) => {
          assert.strictEqual(constraints.video, false);
          assert.ok(constraints.audio);
          return {
            getTracks: () => [
              {
                stop: () => {
                  trackStopped = true;
                },
              },
            ],
          };
        },
      },
      configurable: true,
      writable: true,
    });


    const MockWebSocket = class {
      static OPEN = 1;
      constructor(url) {
        this.url = url;
        this.readyState = 1;
        this.sent = [];
        setTimeout(() => {
          if (this.onopen) this.onopen();
        }, 10);
      }
      send(data) {
        this.sent.push(data);
      }
      close() {
        this.readyState = 3;
        if (this.onclose) this.onclose();
      }
    };
    global.WebSocket = MockWebSocket;
    global.window.WebSocket = MockWebSocket;

  });

  test('AudioCapture requests microphone and releases tracks on stop', async () => {
    let receivedChunks = 0;
    const capture = new AudioCapture({
      sampleRate: 16000,
      onAudioChunk: () => {
        receivedChunks++;
      },
    });

    assert.strictEqual(capture.isRecording, false);
    const started = await capture.start();
    assert.strictEqual(started, true);
    assert.strictEqual(capture.isRecording, true);

    // Simulate audio process event
    capture.processorNode.onaudioprocess({
      inputBuffer: {
        getChannelData: () => new Float32Array([0.1, -0.2, 0.5, 0.0]),
      },
    });
    assert.strictEqual(receivedChunks, 1);

    capture.stop();
    assert.strictEqual(capture.isRecording, false);
    assert.strictEqual(capture.mediaStream, null);
  });

  test('AudioPlayback queues chunks and handles interruption cleanly', async () => {
    let playbackState = false;
    const playback = new AudioPlayback({
      onPlaybackStateChange: (isPlaying) => {
        playbackState = isPlaying;
      },
    });

    const mockChunk = new Uint8Array([1, 2, 3, 4]);
    await playback.queueChunk(mockChunk);

    assert.strictEqual(playbackState, true);
    assert.strictEqual(playback.isPlaying, true);

    // Immediate interruption / barge-in
    playback.interrupt();
    assert.strictEqual(playback.isPlaying, false);
    assert.strictEqual(playback.queue.length, 0);
    assert.strictEqual(playbackState, false);

    playback.close();
  });

  test('VoiceClient manages WebSocket events, states, and cleanup', async () => {
    const states = [];
    const transcripts = [];
    const client = new VoiceClient({
      wsUrl: 'ws://localhost:8000/api/v1/voice',
      onStateChange: (st) => states.push(st),
      onTranscript: (txt, isFinal) => transcripts.push({ txt, isFinal }),
    });

    await client.start();
    assert.ok(states.includes('LISTENING'));

    // Simulate server events
    client._handleMessage({
      data: JSON.stringify({
        type: 'session_started',
        session_id: 'voice_test_123',
      }),
    });
    assert.strictEqual(client.sessionId, 'voice_test_123');

    client._handleMessage({
      data: JSON.stringify({
        type: 'transcript_final',
        text: 'What is the weather?',
      }),
    });
    assert.strictEqual(transcripts.length, 1);
    assert.strictEqual(transcripts[0].txt, 'What is the weather?');
    assert.strictEqual(transcripts[0].isFinal, true);

    // Test barge-in / interrupt
    client.interrupt();
    assert.strictEqual(client.state, 'LISTENING');

    // Test disconnect
    client.disconnect();
    assert.strictEqual(client.state, 'CLOSED');
    assert.strictEqual(client.isConnected, false);
  });
});
