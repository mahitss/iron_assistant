/**
 * AudioCapture: Manages microphone access and raw PCM audio chunk streaming.
 * Adheres to privacy-by-design: Only accesses mic when explicitly started,
 * and releases all media tracks immediately upon stopping.
 */

export class AudioCapture {
  /**
   * @param {Object} options
   * @param {number} [options.sampleRate=16000] - Target PCM audio sample rate in Hz.
   * @param {number} [options.bufferSize=4096] - Audio buffer frame size.
   * @param {function(Uint8Array): void} options.onAudioChunk - Callback receiving 16-bit mono PCM chunks.
   * @param {function(Error): void} [options.onError] - Error callback.
   */
  constructor(options = {}) {
    this.targetSampleRate = options.sampleRate || 16000;
    this.bufferSize = options.bufferSize || 4096;
    this.onAudioChunk = options.onAudioChunk || (() => {});
    this.onError = options.onError || ((err) => console.error('[AudioCapture]', err));

    this.mediaStream = null;
    this.audioContext = null;
    this.sourceNode = null;
    this.processorNode = null;
    this.isRecording = false;
  }

  /**
   * Request microphone permission and begin streaming audio frames.
   * @returns {Promise<boolean>}
   */
  async start() {
    if (this.isRecording) {
      return true;
    }

    try {
      if (!navigator?.mediaDevices?.getUserMedia) {
        throw new Error('Audio recording is not supported in this environment (getUserMedia unavailable).');
      }

      // Explicit user action triggers mic permission prompt
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: this.targetSampleRate,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
        video: false,
      });

      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      this.audioContext = new AudioContextClass({ sampleRate: this.targetSampleRate });
      this.sourceNode = this.audioContext.createMediaStreamSource(this.mediaStream);

      // Create ScriptProcessor or AudioWorklet for raw PCM sample capture
      this.processorNode = this.audioContext.createScriptProcessor(this.bufferSize, 1, 1);

      this.processorNode.onaudioprocess = (event) => {
        if (!this.isRecording) return;
        const inputData = event.inputBuffer.getChannelData(0);
        const pcm16 = this._convertFloat32ToInt16(inputData);
        this.onAudioChunk(new Uint8Array(pcm16.buffer));
      };

      this.sourceNode.connect(this.processorNode);
      this.processorNode.connect(this.audioContext.destination);

      this.isRecording = true;
      return true;
    } catch (err) {
      this.stop();
      this.onError(err);
      return false;
    }
  }

  /**
   * Stop recording and release all microphone tracks and audio context.
   */
  stop() {
    this.isRecording = false;

    if (this.processorNode) {
      try {
        this.processorNode.disconnect();
      } catch (_) {}
      this.processorNode = null;
    }

    if (this.sourceNode) {
      try {
        this.sourceNode.disconnect();
      } catch (_) {}
      this.sourceNode = null;
    }

    if (this.audioContext && this.audioContext.state !== 'closed') {
      try {
        this.audioContext.close();
      } catch (_) {}
      this.audioContext = null;
    }

    // Stop and release all microphone tracks
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
    }
  }

  /**
   * Convert 32-bit float audio buffer (-1.0 to 1.0) to 16-bit signed integer linear PCM.
   * @private
   * @param {Float32Array} float32
   * @returns {Int16Array}
   */
  _convertFloat32ToInt16(float32) {
    const int16 = new Int16Array(float32.length);
    for (let i = 0; i < float32.length; i++) {
      const s = Math.max(-1, Math.min(1, float32[i]));
      int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    return int16;
  }
}
