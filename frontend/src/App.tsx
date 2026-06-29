import { useState } from "react";
import { Watches } from "./pages/Watches";
import { Channels } from "./pages/Channels";
import { History } from "./pages/History";
import { StatusPage } from "./pages/StatusPage";

const TABS = {
  Watches: <Watches />,
  Channels: <Channels />,
  History: <History />,
  Status: <StatusPage />,
} as const;

type Tab = keyof typeof TABS;

export default function App() {
  const [tab, setTab] = useState<Tab>("Watches");

  return (
    <div className="mx-auto max-w-4xl p-4 sm:p-8">
      <header className="mb-6">
        <h1 className="text-2xl font-bold">commit-watcher</h1>
        <p className="text-sm text-slate-500">
          Poll any GitHub repo, filter commits, and get notified.
        </p>
      </header>

      <nav className="mb-6 flex gap-1 border-b border-slate-200 dark:border-slate-800">
        {(Object.keys(TABS) as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium ${
              tab === t
                ? "border-b-2 border-indigo-600 text-indigo-600"
                : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
            }`}
          >
            {t}
          </button>
        ))}
      </nav>

      <main>{TABS[tab]}</main>
    </div>
  );
}
