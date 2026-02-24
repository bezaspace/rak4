import type { ScheduleSnapshotPayload, ScheduleTimelineEntry } from "./liveSocket";

export type ScheduleSnapshotResponse = ScheduleSnapshotPayload;

export type ScheduleItemReportsResponse = {
  scheduleItemId: string;
  date: string;
  timezone: string;
  reports: ScheduleTimelineEntry[];
};

const buildUrl = (baseUrl: string, path: string, params: Record<string, string | undefined>): string => {
  const url = new URL(path, baseUrl);
  Object.entries(params).forEach(([key, value]) => {
    if (value && value.trim()) {
      url.searchParams.set(key, value);
    }
  });
  return url.toString();
};

const fetchJson = async <T>(url: string): Promise<T> => {
  const response = await fetch(url, { method: "GET" });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Request failed (${response.status}): ${body || "unknown error"}`);
  }
  return (await response.json()) as T;
};

export const getTodaySchedule = async ({
  baseUrl,
  userId,
  timezone,
  date,
}: {
  baseUrl: string;
  userId: string;
  timezone: string;
  date?: string;
}): Promise<ScheduleSnapshotResponse> => {
  const url = buildUrl(baseUrl, "/api/schedule/today", {
    user_id: userId,
    timezone,
    date,
  });
  return fetchJson<ScheduleSnapshotResponse>(url);
};

export const getScheduleItemReports = async ({
  baseUrl,
  userId,
  scheduleItemId,
  timezone,
  date,
}: {
  baseUrl: string;
  userId: string;
  scheduleItemId: string;
  timezone: string;
  date?: string;
}): Promise<ScheduleItemReportsResponse> => {
  const url = buildUrl(baseUrl, `/api/schedule/items/${encodeURIComponent(scheduleItemId)}/reports`, {
    user_id: userId,
    timezone,
    date,
  });
  return fetchJson<ScheduleItemReportsResponse>(url);
};
