class RakshaMicCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.streaming = false;
    this.port.onmessage = (event) => {
      const eventType = event.data?.type;
      if (eventType === "start") {
        this.streaming = true;
      } else if (eventType === "pause") {
        this.streaming = false;
      }
    };
  }

  process(inputs) {
    if (!this.streaming) {
      return true;
    }

    const channel = inputs?.[0]?.[0];
    if (!channel || channel.length === 0) {
      return true;
    }

    const pcm16 = new Int16Array(channel.length);
    for (let i = 0; i < channel.length; i += 1) {
      const sample = Math.max(-1, Math.min(1, channel[i]));
      pcm16[i] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
    }
    this.port.postMessage(pcm16.buffer, [pcm16.buffer]);
    return true;
  }
}

registerProcessor("raksha-mic-capture", RakshaMicCaptureProcessor);
