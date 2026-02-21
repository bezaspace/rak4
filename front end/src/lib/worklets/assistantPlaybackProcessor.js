class RakshaAssistantPlaybackProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.queue = [];
    this.currentBuffer = null;
    this.currentIndex = 0;
    this.bufferedSamples = 0;
    this.underrunCount = 0;
    this.framesUntilStats = 0;

    this.port.onmessage = (event) => {
      const eventType = event.data?.type;
      if (eventType === "enqueue") {
        const arrayBuffer = event.data?.samples;
        if (!(arrayBuffer instanceof ArrayBuffer)) return;
        const buffer = new Float32Array(arrayBuffer);
        if (buffer.length === 0) return;
        this.queue.push(buffer);
        this.bufferedSamples += buffer.length;
        return;
      }

      if (eventType === "clear") {
        this.queue = [];
        this.currentBuffer = null;
        this.currentIndex = 0;
        this.bufferedSamples = 0;
      }
    };
  }

  process(inputs, outputs) {
    const output = outputs?.[0]?.[0];
    if (!output) return true;

    let blockUnderrun = false;
    for (let i = 0; i < output.length; i += 1) {
      if (!this.currentBuffer || this.currentIndex >= this.currentBuffer.length) {
        this.currentBuffer = this.queue.shift() ?? null;
        this.currentIndex = 0;
      }

      if (!this.currentBuffer) {
        output[i] = 0;
        blockUnderrun = true;
        continue;
      }

      output[i] = this.currentBuffer[this.currentIndex];
      this.currentIndex += 1;
      this.bufferedSamples = Math.max(0, this.bufferedSamples - 1);
    }

    if (blockUnderrun) {
      this.underrunCount += 1;
    }

    this.framesUntilStats += output.length;
    if (this.framesUntilStats >= 1200) {
      this.framesUntilStats = 0;
      this.port.postMessage({
        bufferedSamples: this.bufferedSamples,
        underrunCount: this.underrunCount,
      });
    }

    return true;
  }
}

registerProcessor("raksha-assistant-playback", RakshaAssistantPlaybackProcessor);
