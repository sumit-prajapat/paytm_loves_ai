import clsx from "clsx";
import { Loader2 } from "lucide-react";
import { useRef, useState } from "react";
import { useRealtime } from "@/app/realtime";
import { ConnectionPill, TopBar } from "@/components/layout";
import { Badge, Button, Card, Empty } from "@/components/ui";
import { formatTime } from "@/lib/format";
import { MERCHANT_PERSONAS, PERSONAS } from "@/lib/personas";
import { INJECTS, resetDemo, runInject, type InjectDef } from "@/services/actions";
import { useStore } from "@/store";
import type { PersonaId } from "@/types/contracts";

const OUTCOME_TONE: Record<string, "ok" | "risk" | "warn" | "sky"> = {
  resolved: "ok", no_issue: "ok", escalated: "risk", needs_input: "warn", ready_for_review_and_pay: "sky",
};

export function InjectGrid({ merchant, compact }: { merchant: PersonaId; compact?: boolean }) {
  const [running, setRunning] = useState<string | null>(null);
  const last = useRef<Record<string, number>>({});
  const log = useStore((s) => s.injectLog);
  const fire = async (d: InjectDef) => {
    const now = Date.now();
    if (running || now - (last.current[d.key] ?? 0) < 2000) return; // debounce: 1 tap / 2 s
    last.current[d.key] = now;
    setRunning(d.key);
    await runInject(d, merchant);
    setRunning(null);
  };
  return (
    <div className={clsx("grid gap-3", compact ? "grid-cols-2 sm:grid-cols-4" : "grid-cols-1 sm:grid-cols-2 lg:grid-cols-4")}>
      {INJECTS.map((d) => {
        const entry = log.find((e) => e.label === d.title);
        return (
          <button
            key={d.key}
            onClick={() => fire(d)}
            disabled={!!running}
            className={clsx(
              "flex flex-col items-start gap-1 rounded-2xl border-2 bg-white p-4 text-left transition hover:-translate-y-0.5 disabled:opacity-70",
              compact ? "min-h-[110px]" : "min-h-[150px]",
              d.risky ? "border-red-200 bg-red-50/40" : entry?.status === "done" ? "border-green-300 bg-green-50/50" : "border-line",
            )}
          >
            <span className="text-3xl" aria-hidden>{d.emoji}</span>
            <b className="text-[15px]">{d.key} · {d.title}</b>
            <small className="text-muted">{d.sub}{!d.scenario ? ` (${PERSONAS[merchant].label.split(" ")[0]})` : ""}</small>
            {running === d.key ? (
              <Badge tone="warn"><Loader2 className="h-3 w-3 animate-spin" /> Running…</Badge>
            ) : entry?.status === "done" ? (
              <Badge tone={OUTCOME_TONE[entry.outcome ?? ""] ?? "sky"}>✓ {entry.outcome}</Badge>
            ) : entry?.status === "error" ? (
              <Badge tone="risk">✗ error</Badge>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}

export function InjectLog() {
  const log = useStore((s) => s.injectLog);
  if (!log.length) return <Empty title="No events yet" sub="Each tap first sets up simulated data, then simulates the user's own button press." />;
  return (
    <div className="overflow-x-auto scrollbar-thin">
      <table className="w-full min-w-[520px] text-left text-xs">
        <thead className="text-[11px] uppercase text-muted"><tr><th className="p-2">Time</th><th className="p-2">Event</th><th className="p-2">Case</th><th className="p-2">Status</th></tr></thead>
        <tbody>
          {log.map((e) => (
            <tr key={e.id} className="border-t border-line">
              <td className="mono p-2">{formatTime(new Date(e.ts).toISOString())}</td>
              <td className="p-2">{e.label}</td>
              <td className="mono p-2">{e.case_id ?? "—"}</td>
              <td className="p-2">
                {e.status === "running" ? <Badge tone="warn">running</Badge> : e.status === "error" ? <Badge tone="risk" className="max-w-[240px] truncate">{e.detail}</Badge> : <Badge tone={OUTCOME_TONE[e.outcome ?? ""] ?? "sky"}>{e.outcome}</Badge>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function Inject() {
  useRealtime({ console: true });
  const killed = useStore((s) => s.control?.kill_switch_active);
  const [merchant, setMerchant] = useState<PersonaId>("ramesh");
  const [busy, setBusy] = useState(false);
  return (
    <div className="min-h-full">
      <TopBar title="Inject panel"><ConnectionPill /></TopBar>
      <main className="mx-auto max-w-[1040px] p-4">
        <Card className="!p-5">
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-extrabold">Judge, try it 👇</h1>
            <label className="ml-auto flex items-center gap-2 text-sm">
              Merchant (for “Unknown case”)
              <select value={merchant} onChange={(e) => setMerchant(e.target.value as PersonaId)} className="min-h-[40px] rounded-full border border-sky-200 bg-sky-100 px-3 font-semibold text-sky-900">
                {MERCHANT_PERSONAS.map((id) => <option key={id} value={id}>{PERSONAS[id].label}</option>)}
              </select>
            </label>
            <Badge tone={killed ? "risk" : "ok"}>{killed ? "Autonomy PAUSED" : "Autonomy ON"}</Badge>
          </div>
          <p className="mb-4 text-xs text-muted">On-demand by design: each button sets up simulated data on the backend, then presses the hero user’s own button (same code path as the real app). Nothing runs on its own.</p>
          <InjectGrid merchant={merchant} />
          <div className="mt-5 flex items-center justify-between">
            <h2 className="text-sm font-bold">Event log (last 10)</h2>
            <Button size="sm" variant="danger" loading={busy} onClick={async () => { setBusy(true); await resetDemo(); setBusy(false); }}>Reset demo</Button>
          </div>
          <InjectLog />
        </Card>
      </main>
    </div>
  );
}
