export type AudioInputController = {
  startStream: () => void;
  pauseStream: () => void;
  stop: () => void;
  isStreaming: () => boolean;
};

const WORKLET_MODULE_PATH = new URL("./worklets/micCaptureProcessor.js", import.meta.url);
const TARGET_CHUNK_SAMPLES = 800; // 50ms at 16kHz

export async function startMicCapture(onChunk: (chunk: ArrayBuffer) => void): Promise<AudioInputController> {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      channelCount: 1,
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    },
  });

  const audioCtx = new AudioContext({ sampleRate: 16000 });
  await audioCtx.audioWorklet.addModule(WORKLET_MODULE_PATH);

  const source = audioCtx.createMediaStreamSource(stream);
  const workletNode = new AudioWorkletNode(audioCtx, "raksha-mic-capture", {
    numberOfInputs: 1,
    numberOfOutputs: 0,
    channelCount: 1,
  });

  source.connect(workletNode);

  let streaming = false;
  let pending = new Int16Array(0);
  let delayedFlushTimer: number | null = null;

  const appendAndEmit = (incoming: Int16Array) => {
    if (incoming.length === 0) return;
    const merged = new Int16Array(pending.length + incoming.length);
    merged.set(pending);
    merged.set(incoming, pending.length);
    pending = merged;

    while (pending.length >= TARGET_CHUNK_SAMPLES) {
      const frame = pending.slice(0, TARGET_CHUNK_SAMPLES);
      onChunk(frame.buffer);
      pending = pending.slice(TARGET_CHUNK_SAMPLES);
    }
  };

  const flushPending = () => {
    if (pending.length === 0) return;
    const tail = pending.slice();
    pending = new Int16Array(0);
    onChunk(tail.buffer);
  };

  workletNode.port.onmessage = (evt: MessageEvent<ArrayBuffer>) => {
    if (!streaming) return;
    if (!(evt.data instanceof ArrayBuffer)) return;
    appendAndEmit(new Int16Array(evt.data));
  };

  const startStream = () => {
    if (streaming) return;
    if (delayedFlushTimer !== null) {
      window.clearTimeout(delayedFlushTimer);
      delayedFlushTimer = null;
    }
    streaming = true;
    void audioCtx.resume();
    workletNode.port.postMessage({ type: "start" });
  };

  const pauseStream = () => {
    if (!streaming) return;
    streaming = false;
    workletNode.port.postMessage({ type: "pause" });
    flushPending();
    delayedFlushTimer = window.setTimeout(() => {
      flushPending();
      delayedFlushTimer = null;
    }, 24);
  };

  return {
    startStream,
    pauseStream,
    isStreaming: () => streaming,
    stop: () => {
      pauseStream();
      if (delayedFlushTimer !== null) {
        window.clearTimeout(delayedFlushTimer);
        delayedFlushTimer = null;
      }
      workletNode.disconnect();
      source.disconnect();
      stream.getTracks().forEach((track) => track.stop());
      void audioCtx.close();
    },
  };
}
