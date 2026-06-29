import { useEffect, useState } from "react";
import { api, Channel } from "../lib/api";
import { Button, Card, Input } from "../components/ui";

export function Channels() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [msg, setMsg] = useState<string | null>(null);

  const load = () => api.listChannels().then(setChannels);
  useEffect(() => {
    load();
  }, []);

  async function add() {
    setMsg(null);
    try {
      await api.createChannel({ name, url });
      setName("");
      setUrl("");
      load();
    } catch (e) {
      setMsg(String(e));
    }
  }

  async function test(n: string) {
    const r = await api.testChannel(n);
    setMsg(r.ok ? `✅ ${n}: sent` : `❌ ${n}: ${r.error}`);
  }

  return (
    <div className="space-y-4">
      <Card>
        <h2 className="mb-2 text-lg font-semibold">Add channel</h2>
        <p className="mb-2 text-sm text-slate-500">
          Apprise URL — e.g. <code>ntfy://token@host/topic</code> or{" "}
          <code>discord://id/token</code>. <code>${"{ENV}"}</code> placeholders are resolved at
          send time.
        </p>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-[1fr_2fr_auto]">
          <Input placeholder="name" value={name} onChange={(e) => setName(e.target.value)} />
          <Input placeholder="apprise url" value={url} onChange={(e) => setUrl(e.target.value)} />
          <Button onClick={add}>Add</Button>
        </div>
      </Card>

      {msg && <Card><span className="text-sm">{msg}</span></Card>}

      {channels.map((c) => (
        <Card key={c.id}>
          <div className="flex items-center justify-between">
            <div>
              <div className="font-semibold">{c.name}</div>
              <div className="font-mono text-xs text-slate-500">{c.url}</div>
            </div>
            <div className="flex gap-1">
              <Button variant="ghost" onClick={() => test(c.name)}>Test</Button>
              <Button
                variant="danger"
                onClick={() => api.deleteChannel(c.name).then(load)}
              >
                Delete
              </Button>
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}
