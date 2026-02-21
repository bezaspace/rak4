export type SlotCard = {
  slotId: string;
  startIso: string;
  displayLabel: string;
  timezone: string;
  isAvailable: boolean;
};

export type DoctorCard = {
  doctorId: string;
  name: string;
  specialty: string;
  experienceYears: number;
  languages: string[];
  matchReason: string;
  slots: SlotCard[];
};

export type BookingCard = {
  bookingId: string;
  doctorId: string;
  doctorName: string;
  slotId: string;
  startIso: string;
  displayLabel: string;
  timezone: string;
  createdAtIso: string;
};

export type ServerEvent =
  | { type: "session_ready"; sessionId: string }
  | { type: "partial_transcript"; text: string }
  | { type: "assistant_text"; text: string }
  | { type: "assistant_audio_format"; sampleRate: number }
  | { type: "assistant_interrupted" }
  | { type: "warning"; message: string }
  | { type: "fallback_started"; reason: string; turnId: string }
  | { type: "fallback_completed"; turnId: string; result: "ok" | "failed" }
  | { type: "session_recovering"; mode: string }
  | { type: "error"; message: string }
  | {
      type: "doctor_recommendations";
      requestId: string;
      symptomsSummary: string;
      doctors: DoctorCard[];
    }
  | {
      type: "booking_update";
      status: "confirmed" | "failed" | "unavailable" | "needs_confirmation";
      booking?: BookingCard;
      message: string;
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
  private eventSeq = 0;
  private audioSeq = 0;

  private log(message: string, payload?: unknown): void {
    if (payload === undefined) {
      console.info(`[raksha.ui] ${message}`);
      return;
    }
    console.info(`[raksha.ui] ${message}`, payload);
  }

  connect(url: string, handlers: LiveSocketHandlers): void {
    this.eventSeq = 0;
    this.audioSeq = 0;
    this.log("WS_CONNECT", { url });
    this.socket = new WebSocket(url);
    this.socket.binaryType = "arraybuffer";

    this.socket.onopen = () => {
      this.log("WS_OPEN");
      handlers.onOpen?.();
    };
    this.socket.onclose = () => {
      this.log("WS_CLOSE");
      handlers.onClose?.();
    };
    this.socket.onerror = (err) => {
      this.log("WS_ERROR", err);
      handlers.onError?.(err);
    };
    this.socket.onmessage = (evt) => {
      if (typeof evt.data === "string") {
        try {
          const parsed = JSON.parse(evt.data) as ServerEvent;
          this.log("WS_RX_EVENT", { type: parsed.type });
          handlers.onEvent?.(parsed);
        } catch {
          handlers.onEvent?.({ type: "error", message: "Invalid server message" });
        }
      } else if (evt.data instanceof ArrayBuffer) {
        this.log("WS_RX_AUDIO", { bytes: evt.data.byteLength });
        handlers.onAudioChunk?.(evt.data);
      }
    };
  }

  sendEvent(event: Record<string, unknown>): void {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      this.log("WS_TX_EVENT_DROPPED_SOCKET_NOT_OPEN", event);
      return;
    }
    this.eventSeq += 1;
    this.log("WS_TX_EVENT", { seq: this.eventSeq, ...event });
    this.socket.send(JSON.stringify(event));
  }

  sendAudioChunk(chunk: ArrayBuffer): void {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      this.log("WS_TX_AUDIO_DROPPED_SOCKET_NOT_OPEN", { bytes: chunk.byteLength });
      return;
    }
    this.audioSeq += 1;
    this.log("WS_TX_AUDIO", { seq: this.audioSeq, bytes: chunk.byteLength });
    this.socket.send(chunk);
  }

  disconnect(): void {
    if (!this.socket) return;
    this.log("WS_DISCONNECT_REQUESTED");
    this.sendEvent({ type: "stop_session" });
    this.socket.close();
    this.socket = null;
  }
}
