// Typed client for the github-watcher REST API.

export interface Watch {
  id: number;
  name: string;
  repo: string;
  branch: string | null;
  interval: number | null;
  enabled: boolean;
  filters: Record<string, unknown>;
  template: Record<string, unknown>;
  channels: string[];
}

export interface Channel {
  id: number;
  name: string;
  url: string;
}

export interface Match {
  id: number;
  watch_id: number;
  sha: string;
  repo: string;
  author: string | null;
  message: string | null;
  url: string | null;
  matched_keywords: string[];
  changed_files: string[];
  notified: boolean;
  notify_error: string | null;
  created_at: string;
}

export interface Status {
  watch_id: number;
  name: string;
  enabled: boolean;
  primed: boolean;
  last_polled_at: string | null;
  last_status: number | null;
  rate_remaining: number | null;
  last_error: string | null;
  seen_count: number;
  match_count: number;
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  listWatches: () => req<Watch[]>("/api/v1/watches"),
  createWatch: (body: unknown) =>
    req<Watch>("/api/v1/watches", { method: "POST", body: JSON.stringify(body) }),
  updateWatch: (id: number, body: unknown) =>
    req<Watch>(`/api/v1/watches/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteWatch: (id: number) => req<void>(`/api/v1/watches/${id}`, { method: "DELETE" }),
  runWatch: (id: number) => req<Match[]>(`/api/v1/watches/${id}/run`, { method: "POST" }),
  dryRun: (id: number) => req<unknown[]>(`/api/v1/watches/${id}/dry-run`, { method: "POST" }),

  listChannels: () => req<Channel[]>("/api/v1/channels"),
  createChannel: (body: { name: string; url: string }) =>
    req<Channel>("/api/v1/channels", { method: "POST", body: JSON.stringify(body) }),
  deleteChannel: (name: string) => req<void>(`/api/v1/channels/${name}`, { method: "DELETE" }),
  testChannel: (name: string) =>
    req<{ ok: boolean; error: string | null }>(`/api/v1/channels/${name}/test`, {
      method: "POST",
    }),

  listMatches: (watchId?: number) =>
    req<Match[]>(`/api/v1/matches${watchId ? `?watch_id=${watchId}` : ""}`),
  status: () => req<Status[]>("/api/v1/status"),
};
