const TARGET_SAMPLE_RATE = 24000;
const PLAYBACK_WORKLET_PATH = new URL("./worklets/assistantPlaybackProcessor.js", import.meta.url);

export class AudioPlayer {
  private readonly audioCtx = new AudioContext({ sampleRate: TARGET_SAMPLE_RATE });
  private readonly readyPromise: Promise<void>;
  private node: AudioWorkletNode | null = null;
  private readonly pendingBeforeReady: Float32Array[] = [];
  private bufferedSamples = 0;
  private underrunCount = 0;

  constructor() {
    this.readyPromise = this.initialize();
  }

  playPcm16Chunk(arrayBuffer: ArrayBuffer, sourceSampleRate = TARGET_SAMPLE_RATE): void {
    const pcm = new Int16Array(arrayBuffer);
    const floatData = new Float32Array(pcm.length);
    for (let i = 0; i < pcm.length; i += 1) {
      floatData[i] = pcm[i] / 0x7fff;
    }

    const normalized =
      sourceSampleRate === TARGET_SAMPLE_RATE
        ? floatData
        : this.resampleLinear(floatData, sourceSampleRate, TARGET_SAMPLE_RATE);
    this.enqueue(normalized);
  }

  interruptNow(): void {
    this.pendingBeforeReady.length = 0;
    this.bufferedSamples = 0;
    if (!this.node) return;
    this.node.port.postMessage({ type: "clear" });
  }

  getBufferedMs(): number {
    return (this.bufferedSamples / TARGET_SAMPLE_RATE) * 1000;
  }

  getUnderrunCount(): number {
    return this.underrunCount;
  }

  async close(): Promise<void> {
    this.interruptNow();
    if (this.node) {
      this.node.disconnect();
      this.node = null;
    }
    await this.audioCtx.close();
  }

  private async initialize(): Promise<void> {
    await this.audioCtx.audioWorklet.addModule(PLAYBACK_WORKLET_PATH);
    const node = new AudioWorkletNode(this.audioCtx, "raksha-assistant-playback", {
      numberOfInputs: 0,
      numberOfOutputs: 1,
      outputChannelCount: [1],
    });
    node.connect(this.audioCtx.destination);
    node.port.onmessage = (event: MessageEvent<{ bufferedSamples: number; underrunCount: number }>) => {
      if (!event.data) return;
      this.bufferedSamples = event.data.bufferedSamples ?? this.bufferedSamples;
      this.underrunCount = event.data.underrunCount ?? this.underrunCount;
    };
    this.node = node;

    if (this.pendingBeforeReady.length > 0) {
      for (const samples of this.pendingBeforeReady) {
        this.postSamples(samples);
      }
      this.pendingBeforeReady.length = 0;
    }
  }

  private enqueue(samples: Float32Array): void {
    if (samples.length === 0) return;
    void this.audioCtx.resume();
    if (!this.node) {
      this.pendingBeforeReady.push(samples);
      void this.readyPromise;
      return;
    }
    this.postSamples(samples);
  }

  private postSamples(samples: Float32Array): void {
    if (!this.node) return;
    this.node.port.postMessage({ type: "enqueue", samples: samples.buffer }, [samples.buffer]);
  }

  private resampleLinear(
    input: Float32Array,
    sourceSampleRate: number,
    targetSampleRate: number
  ): Float32Array {
    if (input.length === 0 || sourceSampleRate <= 0 || targetSampleRate <= 0) return input;
    const ratio = sourceSampleRate / targetSampleRate;
    const outputLength = Math.max(1, Math.round(input.length / ratio));
    const output = new Float32Array(outputLength);

    for (let i = 0; i < outputLength; i += 1) {
      const position = i * ratio;
      const left = Math.floor(position);
      const right = Math.min(left + 1, input.length - 1);
      const frac = position - left;
      output[i] = input[left] * (1 - frac) + input[right] * frac;
    }
    return output;
  }
}
