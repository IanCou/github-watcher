import { useEffect, useState } from "react";
import { api, Match } from "../lib/api";
import { Badge, Card } from "../components/ui";

export function History() {
  const [matches, setMatches] = useState<Match[]>([]);

  useEffect(() => {
    api.listMatches().then(setMatches);
  }, []);

  if (matches.length === 0) {
    return <Card><span className="text-sm text-slate-500">No matches yet.</span></Card>;
  }

  return (
    <div className="space-y-2">
      {matches.map((m) => (
        <Card key={m.id}>
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <a
                  href={m.url ?? "#"}
                  target="_blank"
                  rel="noreferrer"
                  className="font-mono text-sm text-indigo-600 hover:underline"
                >
                  {m.sha.slice(0, 7)}
                </a>
                <span className="text-sm text-slate-500">{m.repo}</span>
                {m.matched_keywords.map((k) => (
                  <Badge key={k} tone="indigo">{k}</Badge>
                ))}
              </div>
              <div className="truncate text-sm">{m.message?.split("\n")[0]}</div>
              <div className="text-xs text-slate-500">
                {m.author} · {new Date(m.created_at).toLocaleString()}
              </div>
            </div>
            <Badge tone={m.notified ? "green" : "red"}>
              {m.notified ? "notified" : m.notify_error ? "error" : "no channel"}
            </Badge>
          </div>
        </Card>
      ))}
    </div>
  );
}
