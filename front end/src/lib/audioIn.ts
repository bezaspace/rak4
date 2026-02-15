export type AudioInputController = {
  stop: () => void;
};

export async function startMicCapture(onChunk: (chunk: ArrayBuffer) => void): Promise<AudioInputController> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const audioCtx = new AudioContext({ sampleRate: 16000 });
  const source = audioCtx.createMediaStreamSource(stream);

  const processor = audioCtx.createScriptProcessor(4096, 1, 1);
  source.connect(processor);
  processor.connect(audioCtx.destination);

  processor.onaudioprocess = (evt) => {
    const input = evt.inputBuffer.getChannelData(0);
    const pcm16 = new Int16Array(input.length);

    for (let i = 0; i < input.length; i += 1) {
      const s = Math.max(-1, Math.min(1, input[i]));
      pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }

    onChunk(pcm16.buffer);
  };

  return {
    stop: () => {
      processor.disconnect();
      source.disconnect();
      stream.getTracks().forEach((t) => t.stop());
      void audioCtx.close();
    },
  };
}
