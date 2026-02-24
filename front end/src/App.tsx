import { useEffect, useMemo, useRef, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";

import { BookingUpdates, type BookingUpdate } from "./components/BookingUpdates";
import { DoctorRecommendations } from "./components/DoctorRecommendations";
import { startMicCapture, type AudioInputController } from "./lib/audioIn";
import { AudioPlayer } from "./lib/audioOut";
import { LiveSocket, type AdherenceReportSavedEvent, type DoctorCard, type ServerEvent } from "./lib/liveSocket";
import { SchedulePage } from "./pages/SchedulePage";

type ConnectionState = "idle" | "connecting" | "ready" | "error";
type VoiceVisualState = "idle" | "listening" | "holding" | "awaiting" | "speaking" | "error";
type ScheduleSnapshotEvent = Extract<ServerEvent, { type: "schedule_snapshot" }>;

const wsUrl = import.meta.env.VITE_BACKEND_WS_URL ?? "ws://localhost:8000/ws/live";
const backendHttpUrl = import.meta.env.VITE_BACKEND_HTTP_URL ?? "http://localhost:8000";
const appName = import.meta.env.VITE_APP_NAME ?? "Raksha";
const defaultUserId = import.meta.env.VITE_USER_ID ?? "raksha-user";
const browserTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";

const withSessionParams = (url: string, userId: string, timezone: string): string => {
  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}user_id=${encodeURIComponent(userId)}&timezone=${encodeURIComponent(timezone)}`;
};

export default function App() {
  const [state, setState] = useState<ConnectionState>("idle");
  const [warning, setWarning] = useState("");
  const [visualState, setVisualState] = useState<VoiceVisualState>("idle");
  const [symptomsSummary, setSymptomsSummary] = useState("");
  const [recommendedDoctors, setRecommendedDoctors] = useState<DoctorCard[]>([]);
  const [bookingUpdates, setBookingUpdates] = useState<BookingUpdate[]>([]);
  const [isPttActive, setIsPttActive] = useState(false);
  const [liveScheduleSnapshot, setLiveScheduleSnapshot] = useState<ScheduleSnapshotEvent | null>(null);
  const [latestAdherenceEvent, setLatestAdherenceEvent] = useState<AdherenceReportSavedEvent | null>(null);

  const socket = useMemo(() => new LiveSocket(), []);
  const playerRef = useRef<AudioPlayer | null>(null);
  const micRef = useRef<AudioInputController | null>(null);
  const assistantSampleRateRef = useRef<number>(24000);
  const speakingTimeoutRef = useRef<number | null>(null);
  const isPttActiveRef = useRef(false);
  const pttSeqRef = useRef(0);

  const logUi = (message: string, payload?: unknown) => {
    if (payload === undefined) {
      console.info(`[raksha.ui] ${message}`);
      return;
    }
    console.info(`[raksha.ui] ${message}`, payload);
  };

  useEffect(() => {
    return () => {
      if (speakingTimeoutRef.current !== null) {
        window.clearTimeout(speakingTimeoutRef.current);
      }
    };
  }, []);

  const setListeningVisual = () => {
    setVisualState("listening");
  };

  const stopAssistantPlaybackNow = () => {
    logUi("ASSISTANT_PLAYBACK_INTERRUPT");
    playerRef.current?.interruptNow();
    if (speakingTimeoutRef.current !== null) {
      window.clearTimeout(speakingTimeoutRef.current);
      speakingTimeoutRef.current = null;
    }
  };

  const markPttActive = (active: boolean) => {
    isPttActiveRef.current = active;
    setIsPttActive(active);
  };

  const connect = async () => {
    logUi("SESSION_CONNECT_START");
    setState("connecting");
    setVisualState("idle");
    setWarning("");
    setSymptomsSummary("");
    setRecommendedDoctors([]);
    setBookingUpdates([]);
    setLiveScheduleSnapshot(null);
    setLatestAdherenceEvent(null);
    markPttActive(false);

    playerRef.current = new AudioPlayer();
    socket.connect(withSessionParams(wsUrl, defaultUserId, browserTimezone), {
      onOpen: () => {
        logUi("SESSION_READY");
        setState("ready");
        setListeningVisual();
      },
      onClose: () => {
        logUi("SESSION_CLOSED");
        setState("idle");
        setVisualState("idle");
        markPttActive(false);
      },
      onError: () => {
        logUi("SESSION_ERROR");
        setWarning("Connection error. Check backend logs.");
        setState("error");
        setVisualState("error");
        markPttActive(false);
      },
      onEvent: (evt) => {
        logUi("SERVER_EVENT", { type: evt.type });
        if (evt.type === "session_ready") {
          setState("ready");
          setWarning("");
          if (!isPttActiveRef.current) {
            setListeningVisual();
          }
          return;
        }
        if (evt.type === "profile_status") {
          if (!evt.loaded) {
            setWarning(evt.message);
          }
          return;
        }
        if (evt.type === "warning") {
          setWarning(evt.message);
          return;
        }
        if (evt.type === "fallback_started") {
          setWarning("Recovering your previous request after live tool interruption...");
          setVisualState("awaiting");
          return;
        }
        if (evt.type === "fallback_completed") {
          setWarning(
            evt.result === "ok"
              ? "Recovered your request. Reconnecting voice session..."
              : "Could not recover automatically. Please repeat your request."
          );
          return;
        }
        if (evt.type === "session_recovering") {
          setVisualState("awaiting");
          return;
        }
        if (evt.type === "error") {
          setWarning(evt.message);
          return;
        }
        if (evt.type === "assistant_audio_format") {
          assistantSampleRateRef.current = evt.sampleRate;
          return;
        }
        if (evt.type === "assistant_interrupted") {
          stopAssistantPlaybackNow();
          if (!isPttActiveRef.current) {
            setVisualState("awaiting");
          }
          return;
        }
        if (evt.type === "doctor_recommendations") {
          setSymptomsSummary(evt.symptomsSummary);
          setRecommendedDoctors(evt.doctors);
          return;
        }
        if (evt.type === "booking_update") {
          setBookingUpdates((prev) => [...prev, { status: evt.status, message: evt.message, booking: evt.booking }]);
          return;
        }
        if (evt.type === "schedule_snapshot") {
          setLiveScheduleSnapshot(evt);
          return;
        }
        if (evt.type === "adherence_report_saved") {
          if (!evt.saved) {
            setWarning(evt.message || "Could not save adherence report.");
            return;
          }
          setLatestAdherenceEvent(evt);
        }
      },
      onAudioChunk: (chunk) => {
        logUi("AUDIO_RX_CHUNK", { bytes: chunk.byteLength });
        playerRef.current?.playPcm16Chunk(chunk, assistantSampleRateRef.current);
        if (!isPttActiveRef.current) {
          setVisualState("speaking");
        }
        if (speakingTimeoutRef.current !== null) {
          window.clearTimeout(speakingTimeoutRef.current);
        }
        speakingTimeoutRef.current = window.setTimeout(() => {
          if (!isPttActiveRef.current) {
            setListeningVisual();
          }
          speakingTimeoutRef.current = null;
        }, 280);
      },
    });

    try {
      micRef.current = await startMicCapture((chunk) => {
        socket.sendAudioChunk(chunk);
      });
      micRef.current.pauseStream();
      logUi("MIC_READY");
    } catch {
      logUi("MIC_UNAVAILABLE");
      setWarning("Microphone unavailable.");
      setVisualState("error");
      setState("error");
    }
  };

  const disconnect = async () => {
    if (isPttActiveRef.current) {
      logUi("PTT_END_ON_DISCONNECT");
      markPttActive(false);
      micRef.current?.pauseStream();
      logUi("MIC_PAUSE");
      socket.sendEvent({ type: "ptt_end" });
    }
    if (speakingTimeoutRef.current !== null) {
      window.clearTimeout(speakingTimeoutRef.current);
      speakingTimeoutRef.current = null;
    }
    micRef.current?.pauseStream();
    logUi("MIC_PAUSE");
    micRef.current?.stop();
    logUi("MIC_STOP");
    micRef.current = null;
    socket.disconnect();
    if (playerRef.current) {
      await playerRef.current.close();
      playerRef.current = null;
      logUi("AUDIO_PLAYER_CLOSED");
    }
    setState("idle");
    setVisualState("idle");
  };

  const beginPtt = () => {
    if (state !== "ready" || isPttActiveRef.current) return;
    pttSeqRef.current += 1;
    logUi("PTT_BEGIN", { turn: pttSeqRef.current });
    stopAssistantPlaybackNow();
    markPttActive(true);
    setVisualState("holding");
    micRef.current?.startStream();
    logUi("MIC_START");
    socket.sendEvent({ type: "ptt_start" });
  };

  const endPtt = () => {
    if (!isPttActiveRef.current) return;
    logUi("PTT_END", { turn: pttSeqRef.current });
    markPttActive(false);
    micRef.current?.pauseStream();
    logUi("MIC_PAUSE");
    socket.sendEvent({ type: "ptt_end" });
    if (state === "ready") {
      setVisualState("awaiting");
    }
  };

  return (
    <main className="app-shell">
      <h1 className="app-title">{appName}</h1>
      <p className="app-subtitle">General health guidance only. Not diagnosis or emergency care.</p>

      <nav className="top-nav">
        <NavLink to="/" className={({ isActive }) => (isActive ? "nav-link nav-link-active" : "nav-link")}>
          Voice
        </NavLink>
        <NavLink to="/schedule" className={({ isActive }) => (isActive ? "nav-link nav-link-active" : "nav-link")}>
          Schedule
        </NavLink>
      </nav>

      <Routes>
        <Route
          path="/"
          element={
            <VoiceSessionPage
              state={state}
              visualState={visualState}
              warning={warning}
              symptomsSummary={symptomsSummary}
              recommendedDoctors={recommendedDoctors}
              bookingUpdates={bookingUpdates}
              isPttActive={isPttActive}
              onConnect={connect}
              onDisconnect={disconnect}
              onBeginPtt={beginPtt}
              onEndPtt={endPtt}
            />
          }
        />
        <Route
          path="/schedule"
          element={
            <SchedulePage
              backendHttpUrl={backendHttpUrl}
              userId={defaultUserId}
              liveSnapshot={liveScheduleSnapshot}
              liveReportUpdate={latestAdherenceEvent}
            />
          }
        />
      </Routes>
    </main>
  );
}

function VoiceSessionPage({
  state,
  visualState,
  warning,
  symptomsSummary,
  recommendedDoctors,
  bookingUpdates,
  isPttActive,
  onConnect,
  onDisconnect,
  onBeginPtt,
  onEndPtt,
}: {
  state: ConnectionState;
  visualState: VoiceVisualState;
  warning: string;
  symptomsSummary: string;
  recommendedDoctors: DoctorCard[];
  bookingUpdates: BookingUpdate[];
  isPttActive: boolean;
  onConnect: () => Promise<void>;
  onDisconnect: () => Promise<void>;
  onBeginPtt: () => void;
  onEndPtt: () => void;
}) {
  const statusText =
    state === "connecting"
      ? "Connecting..."
      : state === "error"
        ? "Connection error"
        : state !== "ready"
          ? "Start session"
          : isPttActive
            ? "Listening (hold active)"
            : visualState === "speaking"
              ? "Raksha is speaking"
              : visualState === "awaiting"
                ? "Awaiting response..."
                : "Press and hold to speak";
  const isSessionReady = state === "ready";

  return (
    <>
      <button
        className="session-btn"
        onClick={() => {
          if (state === "idle" || state === "error") {
            void onConnect();
          } else {
            void onDisconnect();
          }
        }}
        disabled={state === "connecting"}
      >
        {state === "idle" || state === "error" ? "Start Session" : "End Session"}
      </button>

      <button
        className={`orb orb-${visualState}`}
        disabled={!isSessionReady}
        aria-label="Hold to talk"
        onPointerDown={(evt) => {
          evt.currentTarget.setPointerCapture(evt.pointerId);
          onBeginPtt();
        }}
        onPointerUp={onEndPtt}
        onPointerCancel={onEndPtt}
        onLostPointerCapture={onEndPtt}
        onKeyDown={(evt) => {
          if ((evt.key === " " || evt.key === "Enter") && !evt.repeat) {
            evt.preventDefault();
            onBeginPtt();
          }
        }}
        onKeyUp={(evt) => {
          if (evt.key === " " || evt.key === "Enter") {
            evt.preventDefault();
            onEndPtt();
          }
        }}
      >
        <span className="orb-core" />
      </button>

      <p className="status-text">{statusText}</p>
      {warning ? <p className="warning-text">{warning}</p> : null}

      <div className="conversation-panels">
        <DoctorRecommendations symptomsSummary={symptomsSummary} doctors={recommendedDoctors} />
        <BookingUpdates updates={bookingUpdates} />
      </div>
    </>
  );
}
