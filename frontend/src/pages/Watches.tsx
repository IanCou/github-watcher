import { useEffect, useState } from "react";
import { api, Watch } from "../lib/api";
import { Badge, Button, Card } from "../components/ui";

const EXAMPLE = `{
  "name": "simplify-google",
  "repo": "SimplifyJobs/Summer2026-Internships",
  "branch": "dev",
  "interval": 60,
  "channels": ["ntfy-main"],
  "filters": {
    "files": { "include": ["**/listings.json"] },
    "diff": { "include": ["(?i)\\\\bgoogle\\\\b"] }
  },
  "template": {
    "title": "{{ repo }}: {{ matched_keywords | join(', ') }}",
    "body": "{{ commit.message_first_line }} — {{ commit.short_sha }}"
  }
}`;

export function Watches() {
  const [watches, setWatches] = useState<Watch[]>([]);
  const [draft, setDraft] = useState(EXAMPLE);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<number | null>(null);

  const load = () => api.listWatches().then(setWatches).catch((e) => setError(String(e)));
  useEffect(() => {
    load();
  }, []);

  async function create() {
    setError(null);
    try {
      await api.createWatch(JSON.parse(draft));
      load();
    } catch (e) {
      setError(String(e));
    }
  }

  async function act(id: number, fn: () => Promise<unknown>) {
    setBusy(id);
    try {
      await fn();
      load();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <h2 className="mb-2 text-lg font-semibold">New watch</h2>
        <p className="mb-2 text-sm text-slate-500">
          JSON describing one watch. Filters: <code>message</code>/<code>diff</code> use regex,{" "}
          <code>files</code> uses globs (<code>**</code> crosses directories).
        </p>
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          rows={12}
          className="w-full rounded-lg border border-slate-300 bg-transparent p-3 font-mono text-xs dark:border-slate-700"
        />
        <div className="mt-2">
          <Button onClick={create}>Create watch</Button>
        </div>
      </Card>

      {error && <Card><span className="text-sm text-red-600">{error}</span></Card>}

      {watches.map((w) => (
        <Card key={w.id}>
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold">{w.name}</span>
                <Badge tone={w.enabled ? "green" : "slate"}>
                  {w.enabled ? "enabled" : "disabled"}
                </Badge>
              </div>
              <div className="text-sm text-slate-500">
                {w.repo}@{w.branch ?? "default"} · every {w.interval ?? "default"}s ·{" "}
                channels: {w.channels.join(", ") || "—"}
              </div>
              <pre className="mt-2 overflow-x-auto rounded bg-slate-100 p-2 text-xs dark:bg-slate-800">
                {JSON.stringify(w.filters, null, 2)}
              </pre>
            </div>
            <div className="flex shrink-0 flex-col gap-1">
              <Button variant="ghost" onClick={() => act(w.id, () => api.runWatch(w.id))}>
                {busy === w.id ? "…" : "Run now"}
              </Button>
              <Button
                variant="ghost"
                onClick={() => act(w.id, () => api.updateWatch(w.id, { enabled: !w.enabled }))}
              >
                {w.enabled ? "Disable" : "Enable"}
              </Button>
              <Button variant="danger" onClick={() => act(w.id, () => api.deleteWatch(w.id))}>
                Delete
              </Button>
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}
