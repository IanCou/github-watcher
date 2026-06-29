import { useEffect, useState } from "react";
import { api, Status } from "../lib/api";
import { Badge, Card } from "../components/ui";

export function StatusPage() {
  const [rows, setRows] = useState<Status[]>([]);

  useEffect(() => {
    const tick = () => api.status().then(setRows);
    tick();
    const id = setInterval(tick, 5000);
    return () => clearInterval(id);
  }, []);

  return (
    <Card>
      <table className="w-full text-sm">
        <thead className="text-left text-slate-500">
          <tr>
            <th className="py-1">Watch</th>
            <th>State</th>
            <th>Last poll</th>
            <th>HTTP</th>
            <th>Rate left</th>
            <th>Seen</th>
            <th>Matches</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((s) => (
            <tr key={s.watch_id} className="border-t border-slate-100 dark:border-slate-800">
              <td className="py-1 font-medium">{s.name}</td>
              <td>
                <Badge tone={s.last_error ? "red" : s.primed ? "green" : "slate"}>
                  {s.last_error ? "error" : s.primed ? "live" : "priming"}
                </Badge>
              </td>
              <td>{s.last_polled_at ? new Date(s.last_polled_at).toLocaleTimeString() : "—"}</td>
              <td>{s.last_status ?? "—"}</td>
              <td>{s.rate_remaining ?? "—"}</td>
              <td>{s.seen_count}</td>
              <td>{s.match_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}
