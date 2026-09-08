/**
 * AudioPlayback: Manages streamed audio chunk playback, queueing, and barge-in / interruption.
 */

export class AudioPlayback {
  /**
   * @param {Object} options
   * @param {function(boolean): void} [options.onPlaybackStateChange] - Called with isPlaying state.
   * @param {function(Error): void} [options.onError] - Error callback.
   */
  constructor(options = {}) {
    this.onPlaybackStateChange = options.onPlaybackStateChange || (() => {});
    this.onError = options.onError || ((err) => console.error('[AudioPlayback]', err));

    this.audioContext = null;
    this.queue = [];
    this.isPlaying = false;
    this.currentSource = null;
    this.interrupted = false;
  }

  _ensureContext() {
    if (!this.audioContext || this.audioContext.state === 'closed') {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      this.audioContext = new AudioContextClass();
    }
    if (this.audioContext.state === 'suspended') {
      this.audioContext.resume();
    }
    return this.audioContext;
  }

  /**
   * Enqueue a raw audio array buffer (WAV/MP3) for sequential playback.
   * @param {ArrayBuffer|Uint8Array} chunk
   */
  async queueChunk(chunk) {
    if (this.interrupted) return;

    const buffer = chunk instanceof Uint8Array ? chunk.buffer.slice(chunk.byteOffset, chunk.byteOffset + chunk.byteLength) : chunk;
    this.queue.push(buffer);

    if (!this.isPlaying) {
      this._playNext();
    }
  }

  async _playNext() {
    if (this.interrupted || this.queue.length === 0) {
      this.isPlaying = false;
      this.onPlaybackStateChange(false);
      return;
    }

    this.isPlaying = true;
    this.onPlaybackStateChange(true);

    const rawBuffer = this.queue.shift();
    const ctx = this._ensureContext();

    try {
      // Decode audio data asynchronously
      const audioBuffer = await ctx.decodeAudioData(rawBuffer.slice(0));
      if (this.interrupted) {
        this.isPlaying = false;
        this.onPlaybackStateChange(false);
        return;
      }

      this.currentSource = ctx.createBufferSource();
      this.currentSource.buffer = audioBuffer;
      this.currentSource.connect(ctx.destination);

      this.currentSource.onended = () => {
        this.currentSource = null;
        if (!this.interrupted) {
          this._playNext();
        }
      };

      this.currentSource.start(0);
    } catch (err) {
      this.onError(err);
      this._playNext();
    }
  }

  /**
   * Immediate interruption / barge-in.
   * Stops current playback node, clears all queued buffers, and releases audio resources.
   */
  interrupt() {
    this.interrupted = true;
    this.queue = [];

    if (this.currentSource) {
      try {
        this.currentSource.stop(0);
        this.currentSource.disconnect();
      } catch (_) {}
      this.currentSource = null;
    }

    this.isPlaying = false;
    this.onPlaybackStateChange(false);

    // Reset interrupted flag for future playback turns
    setTimeout(() => {
      this.interrupted = false;
    }, 50);
  }

  /**
   * Cleanly close audio context.
   */
  close() {
    this.interrupt();
    if (this.audioContext && this.audioContext.state !== 'closed') {
      try {
        this.audioContext.close();
      } catch (_) {}
      this.audioContext = null;
    }
  }
}
