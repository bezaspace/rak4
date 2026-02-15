export class AudioPlayer {
  private readonly audioCtx = new AudioContext();
  private nextTime = 0;
  private readonly activeSources = new Set<AudioBufferSourceNode>();

  playPcm16Chunk(arrayBuffer: ArrayBuffer, sourceSampleRate = 24000): void {
    const pcm = new Int16Array(arrayBuffer);
    const floatData = new Float32Array(pcm.length);

    for (let i = 0; i < pcm.length; i += 1) {
      floatData[i] = pcm[i] / 0x7fff;
    }

    const buffer = this.audioCtx.createBuffer(1, floatData.length, sourceSampleRate);
    buffer.copyToChannel(floatData, 0);

    const source = this.audioCtx.createBufferSource();
    source.buffer = buffer;
    source.connect(this.audioCtx.destination);
    this.activeSources.add(source);
    source.onended = () => {
      this.activeSources.delete(source);
    };

    const now = this.audioCtx.currentTime;
    this.nextTime = Math.max(this.nextTime, now + 0.01);
    source.start(this.nextTime);
    this.nextTime += buffer.duration;
  }

  interruptNow(): void {
    for (const source of this.activeSources) {
      try {
        source.stop();
      } catch {
        // Ignore stop race conditions on already-ended sources.
      }
    }
    this.activeSources.clear();
    this.nextTime = this.audioCtx.currentTime + 0.01;
  }

  async close(): Promise<void> {
    this.interruptNow();
    await this.audioCtx.close();
  }
}
