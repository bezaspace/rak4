import { useEffect, useMemo, useState } from "react";

import { getTodaySchedule } from "../lib/scheduleApi";
import type {
  AdherenceReportSavedEvent,
  AdherenceReportSavedSuccessEvent,
  ScheduleItemCard,
  ScheduleSnapshotPayload,
  ScheduleTimelineEntry,
  ServerEvent,
} from "../lib/liveSocket";

type AdherenceUpdateEvent = AdherenceReportSavedEvent;
type ScheduleSnapshotEvent = Extract<ServerEvent, { type: "schedule_snapshot" }>;

type Props = {
  backendHttpUrl: string;
  userId: string;
  liveSnapshot: ScheduleSnapshotEvent | null;
  liveReportUpdate: AdherenceUpdateEvent | null;
};

const browserTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";

export function SchedulePage({ backendHttpUrl, userId, liveSnapshot, liveReportUpdate }: Props) {
  const [snapshot, setSnapshot] = useState<ScheduleSnapshotPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [mismatchHint, setMismatchHint] = useState("");

  const selectedDate = useMemo(() => new Date().toLocaleDateString("en-CA"), []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    void getTodaySchedule({
      baseUrl: backendHttpUrl,
      userId,
      timezone: browserTimezone,
      date: selectedDate,
    })
      .then((result) => {
        if (!cancelled) {
          setSnapshot(result);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load schedule.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [backendHttpUrl, userId, selectedDate]);

  useEffect(() => {
    if (!liveSnapshot) return;
    const { type: _type, ...rest } = liveSnapshot;
    setSnapshot(rest);
  }, [liveSnapshot]);

  useEffect(() => {
    if (!liveReportUpdate) return;
    if (!liveReportUpdate.saved) {
      return;
    }
    const viewingDate = snapshot?.date ?? selectedDate;
    if (liveReportUpdate.date !== viewingDate) {
      setMismatchHint(
        `A log was saved for ${liveReportUpdate.date}. You are currently viewing ${viewingDate}.`
      );
      return;
    }
    setMismatchHint("");
    setSnapshot((prev) => applyLiveReportUpdate(prev, liveReportUpdate));
  }, [liveReportUpdate, selectedDate, snapshot?.date]);

  return (
    <section className="panel schedule-panel">
      <div className="schedule-header">
        <h2 className="panel-title">Today&apos;s Schedule</h2>
        <p className="panel-subtitle">
          {snapshot ? `${snapshot.date} • ${snapshot.timezone}` : `${selectedDate} • ${browserTimezone}`}
        </p>
      </div>

      {loading ? <p className="panel-subtitle">Loading your schedule...</p> : null}
      {error ? <p className="warning-text">{error}</p> : null}
      {mismatchHint ? <p className="schedule-hint-text">{mismatchHint}</p> : null}

      {!loading && snapshot && snapshot.items.length === 0 ? (
        <p className="panel-subtitle">No schedule items found for today.</p>
      ) : null}

      {!loading && snapshot ? (
        <div className="schedule-accordion-list">
          {snapshot.items.map((item) => {
            const itemLogs = getLogsForItem(snapshot.timeline, item.scheduleItemId);
            return (
              <details className="schedule-accordion" key={item.scheduleItemId}>
                <summary>
                  <div className="accordion-summary-main">
                    <h3 className="accordion-title">{item.title}</h3>
                    <p className="accordion-subtitle">
                      {item.activityType} • {item.windowStartLocal} - {item.windowEndLocal}
                    </p>
                  </div>
                  <span className={`status-pill ${statusClass(item.latestReport?.status)}`}>
                    {item.latestReport?.status ?? "pending"}
                  </span>
                </summary>

                <div className="accordion-body">
                  <h4 className="accordion-section-title">Plan Details</h4>
                  <ul className="schedule-instructions">
                    {item.instructions.map((instruction, idx) => (
                      <li key={`${item.scheduleItemId}-${idx}`}>{instruction}</li>
                    ))}
                  </ul>

                  <h4 className="accordion-section-title">Adherence Logs</h4>
                  {itemLogs.length === 0 ? <p className="panel-subtitle">No adherence logs yet for this activity.</p> : null}
                  {itemLogs.length > 0 ? (
                    <ul className="adherence-log-list">
                      {itemLogs.map((entry) => (
                        <li key={entry.reportId} className={`adherence-log-item alert-${entry.alertLevel}`}>
                          <p className="timeline-title">
                            {entry.status} • {formatReportedTime(entry.reportedAtIso)}
                          </p>
                          <p className="timeline-summary">{entry.summary}</p>
                          <p className="timeline-meta">
                            Plan followed: {entry.followedPlan ? "yes" : "no"}
                            {entry.changesMade ? ` • Changes: ${entry.changesMade}` : ""}
                            {entry.feltAfter ? ` • Felt: ${entry.feltAfter}` : ""}
                            {entry.symptoms ? ` • Symptoms: ${entry.symptoms}` : ""}
                            {entry.notes ? ` • Notes: ${entry.notes}` : ""}
                          </p>
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              </details>
            );
          })}
        </div>
      ) : null}
    </section>
  );
}

const statusClass = (status: string | undefined): string => {
  if (!status) return "status-pending";
  if (status === "done") return "status-done";
  if (status === "partial") return "status-partial";
  if (status === "skipped") return "status-skipped";
  if (status === "delayed") return "status-delayed";
  return "status-pending";
};

const applyLiveReportUpdate = (
  snapshot: ScheduleSnapshotPayload | null,
  event: AdherenceReportSavedSuccessEvent
): ScheduleSnapshotPayload | null => {
  if (!snapshot) return snapshot;
  if (snapshot.date !== event.date) return snapshot;

  const newTimelineEntry: ScheduleTimelineEntry = {
    reportId: event.reportId,
    scheduleItemId: event.scheduleItemId,
    activityType: event.activityType,
    status: event.status,
    followedPlan: event.followedPlan ?? false,
    changesMade: event.changesMade ?? null,
    feltAfter: event.feltAfter ?? null,
    symptoms: event.symptoms ?? null,
    notes: event.notes ?? null,
    alertLevel: event.alertLevel,
    summary: event.summary,
    reportedAtIso: event.reportedAtIso,
    createdAt: event.createdAt,
    conversationTurnId: event.conversationTurnId ?? null,
    sessionId: event.sessionId ?? null,
  };

  const timelineById = new Map<string, ScheduleTimelineEntry>();
  snapshot.timeline.forEach((item) => {
    timelineById.set(item.reportId, item);
  });
  timelineById.set(newTimelineEntry.reportId, newTimelineEntry);
  const updatedTimeline = Array.from(timelineById.values()).sort((a, b) => a.reportedAtIso.localeCompare(b.reportedAtIso));

  const updatedItems: ScheduleItemCard[] = snapshot.items.map((item) => {
    if (item.scheduleItemId !== event.scheduleItemId) return item;
    return {
      ...item,
      latestReport: {
        reportId: event.reportId,
        status: event.status,
        alertLevel: event.alertLevel,
        summary: event.summary,
        reportedAtIso: event.reportedAtIso,
      },
    };
  });

  return {
    ...snapshot,
    items: updatedItems,
    timeline: updatedTimeline,
  };
};

const getLogsForItem = (timeline: ScheduleTimelineEntry[], scheduleItemId: string): ScheduleTimelineEntry[] => {
  return timeline
    .filter((entry) => entry.scheduleItemId === scheduleItemId)
    .sort((a, b) => b.reportedAtIso.localeCompare(a.reportedAtIso));
};

const formatReportedTime = (reportedAtIso: string): string => {
  const date = new Date(reportedAtIso);
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
};
