import { useEffect, useMemo, useRef, useState } from "react";

import { startMicCapture, type AudioInputController } from "./lib/audioIn";
import { AudioPlayer } from "./lib/audioOut";
import { LiveSocket } from "./lib/liveSocket";

type ConnectionState = "idle" | "connecting" | "ready" | "error";
type VoiceVisualState = "idle" | "listening" | "speaking" | "error";

const wsUrl = import.meta.env.VITE_BACKEND_WS_URL ?? "ws://localhost:8000/ws/live";
const appName = import.meta.env.VITE_APP_NAME ?? "Raksha";
const BARGE_IN_RMS_THRESHOLD = 0.015;
const BARGE_IN_CONSECUTIVE_CHUNKS = 2;

export default function App() {
  const [state, setState] = useState<ConnectionState>("idle");
  const [warning, setWarning] = useState("");
  const [visualState, setVisualState] = useState<VoiceVisualState>("idle");

  const socket = useMemo(() => new LiveSocket(), []);
  const playerRef = useRef<AudioPlayer | null>(null);
  const micRef = useRef<AudioInputController | null>(null);
  const assistantSampleRateRef = useRef<number>(24000);
  const speakingTimeoutRef = useRef<number | null>(null);
  const isAssistantSpeakingRef = useRef(false);
  const loudMicChunkCountRef = useRef(0);

  useEffect(() => {
    return () => {
      if (speakingTimeoutRef.current !== null) {
        window.clearTimeout(speakingTimeoutRef.current);
      }
    };
  }, []);

  const setListeningVisual = () => {
    setVisualState("listening");
    isAssistantSpeakingRef.current = false;
  };

  const markAssistantSpeaking = () => {
    setVisualState("speaking");
    isAssistantSpeakingRef.current = true;
  };

  const stopAssistantPlaybackNow = () => {
    playerRef.current?.interruptNow();
    if (speakingTimeoutRef.current !== null) {
      window.clearTimeout(speakingTimeoutRef.current);
      speakingTimeoutRef.current = null;
    }
    setListeningVisual();
  };

  const connect = async () => {
    setState("connecting");
    setVisualState("idle");
    setWarning("");

    playerRef.current = new AudioPlayer();
    socket.connect(wsUrl, {
      onOpen: () => {
        setState("ready");
        setListeningVisual();
      },
      onClose: () => {
        setState("idle");
        setVisualState("idle");
        isAssistantSpeakingRef.current = false;
      },
      onError: () => {
        setWarning("Connection error. Check backend logs.");
        setState("error");
        setVisualState("error");
        isAssistantSpeakingRef.current = false;
      },
      onEvent: (evt) => {
        if (evt.type === "assistant_audio_format" && evt.sampleRate) {
          assistantSampleRateRef.current = evt.sampleRate;
        }
        if (evt.type === "assistant_interrupted") {
          stopAssistantPlaybackNow();
        }
        if (evt.type === "warning") setWarning(evt.message ?? "");
      },
      onAudioChunk: (chunk) => {
        playerRef.current?.playPcm16Chunk(chunk, assistantSampleRateRef.current);
        markAssistantSpeaking();
        if (speakingTimeoutRef.current !== null) {
          window.clearTimeout(speakingTimeoutRef.current);
        }
        speakingTimeoutRef.current = window.setTimeout(() => {
          setListeningVisual();
          speakingTimeoutRef.current = null;
        }, 380);
      },
    });

    try {
      micRef.current = await startMicCapture((chunk) => {
        const pcm = new Int16Array(chunk);
        let energy = 0;
        for (let i = 0; i < pcm.length; i += 1) {
          const sample = pcm[i] / 0x7fff;
          energy += sample * sample;
        }
        const rms = Math.sqrt(energy / Math.max(1, pcm.length));
        if (rms > BARGE_IN_RMS_THRESHOLD) {
          loudMicChunkCountRef.current += 1;
        } else {
          loudMicChunkCountRef.current = 0;
        }
        if (
          isAssistantSpeakingRef.current &&
          loudMicChunkCountRef.current >= BARGE_IN_CONSECUTIVE_CHUNKS
        ) {
          stopAssistantPlaybackNow();
          loudMicChunkCountRef.current = 0;
        }
        socket.sendAudioChunk(chunk);
      });
    } catch {
      setWarning("Microphone unavailable.");
      setVisualState("error");
    }
  };

  const disconnect = async () => {
    if (speakingTimeoutRef.current !== null) {
      window.clearTimeout(speakingTimeoutRef.current);
      speakingTimeoutRef.current = null;
    }
    isAssistantSpeakingRef.current = false;
    loudMicChunkCountRef.current = 0;
    micRef.current?.stop();
    micRef.current = null;
    socket.disconnect();
    if (playerRef.current) {
      await playerRef.current.close();
      playerRef.current = null;
    }
    setState("idle");
    setVisualState("idle");
  };

  const toggleConnection = () => {
    if (state === "idle" || state === "error") {
      void connect();
      return;
    }
    void disconnect();
  };

  const statusText =
    state === "connecting"
      ? "Connecting..."
      : visualState === "speaking"
        ? "Raksha is speaking"
        : state === "ready"
          ? "Listening"
          : state === "error"
            ? "Connection error"
            : "Tap to start";

  return (
    <main className="app-shell">
      <h1 className="app-title">{appName}</h1>
      <p className="app-subtitle">General health guidance only. Not diagnosis or emergency care.</p>

      <button
        className={`orb orb-${visualState}`}
        onClick={toggleConnection}
        disabled={state === "connecting"}
        aria-label={state === "idle" ? "Start Raksha voice assistant" : "Stop Raksha voice assistant"}
      >
        <span className="orb-core" />
      </button>

      <p className="status-text">{statusText}</p>
      {warning ? <p className="warning-text">{warning}</p> : null}
    </main>
  );
}
