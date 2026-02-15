export type ServerEvent = {
  type: string;
  text?: string;
  message?: string;
  sessionId?: string;
  sampleRate?: number;
};

export type LiveSocketHandlers = {
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
  onEvent?: (event: ServerEvent) => void;
  onAudioChunk?: (chunk: ArrayBuffer) => void;
};

export class LiveSocket {
  private socket: WebSocket | null = null;

  connect(url: string, handlers: LiveSocketHandlers): void {
    this.socket = new WebSocket(url);
    this.socket.binaryType = "arraybuffer";

    this.socket.onopen = () => handlers.onOpen?.();
    this.socket.onclose = () => handlers.onClose?.();
    this.socket.onerror = (err) => handlers.onError?.(err);
    this.socket.onmessage = (evt) => {
      if (typeof evt.data === "string") {
        try {
          handlers.onEvent?.(JSON.parse(evt.data) as ServerEvent);
        } catch {
          handlers.onEvent?.({ type: "error", message: "Invalid server message" });
        }
      } else if (evt.data instanceof ArrayBuffer) {
        handlers.onAudioChunk?.(evt.data);
      }
    };
  }

  sendEvent(event: Record<string, unknown>): void {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) return;
    this.socket.send(JSON.stringify(event));
  }

  sendAudioChunk(chunk: ArrayBuffer): void {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) return;
    this.socket.send(chunk);
  }

  disconnect(): void {
    if (!this.socket) return;
    this.sendEvent({ type: "stop_session" });
    this.socket.close();
    this.socket = null;
  }
}
