import clsx from "clsx";
import { Download } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { TopBar } from "@/components/layout";
import { Badge, Button, Card, Dialog, Empty } from "@/components/ui";
import { formatDate } from "@/lib/format";
import { useStore } from "@/store";
import type { EvalResults, EvalRow } from "@/types/contracts";

/**
 * The backend has no /eval/results endpoint. Results are produced by the backend's own
 * eval/run_eval.py and exported (scripts/export_eval.py) to public/eval-results.json.
 */
export default function Eval() {
  const [data, setData] = useState<EvalResults | null>(null);
  const [err, setErr] = useState("");
  const [scenario, setScenario] = useState("all");
  const [lang, setLang] = useState("all");
  const [onlyFail, setOnlyFail] = useState(false);
  const [row, setRow] = useState<EvalRow | null>(null);
  const travelMs = useStore((s) => s.metrics?.travel_shortlist_avg_ms);

  useEffect(() => {
    fetch(`/eval-results.json?ts=${Date.now()}`).then(
      async (r) => (r.ok ? setData(await r.json()) : setErr("Eval results not exported yet. Run: npm run eval:export")),
      () => setErr("Could not load eval results."),
    );
  }, []);

  const rows = useMemo(() => (data?.rows ?? []).filter((r) =>
    (scenario === "all" || r.scenario === scenario) && (lang === "all" || r.language === lang) && (!onlyFail || !r.passed)), [data, scenario, lang, onlyFail]);

  const exportCsv = () => {
    if (!data) return;
    const header = ["id", "scenario", "language", "input", "expected", "actual", "passed", "tier", "violations", "reply"];
    const esc = (v: unknown) => `"${String(v ?? "").replace(/"/g, '""')}"`;
    const csv = [header.join(","), ...rows.map((r) => header.map((h) => esc((r as any)[h])).join(","))].join("\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    a.download = "saarthi-eval.csv";
    a.click();
  };

  const s = data?.summary;
  const tiles = s ? [
    { label: "Accuracy (all outcomes)", value: `${s.accuracy}%`, target: "≥ 80%", ok: data!.verdict.accuracy },
    { label: "Ticket deflection", value: `${s.deflection_pct}%`, target: "info", ok: null },
    { label: "Escalation precision", value: `${s.escalation_precision}%`, target: "≥ 95%", ok: data!.verdict.escalation_precision },
    { label: "Escalation recall", value: `${s.escalation_recall}%`, target: "≥ 95%", ok: data!.verdict.escalation_recall },
    { label: "Avg time per case", value: `${s.avg_latency_ms} ms`, target: "< 60 s", ok: s.avg_latency_ms < 60000 },
    { label: "Recommendation consistency", value: s.travel_consistency, target: "all", ok: s.travel_consistency.split("/")[0] === s.travel_consistency.split("/")[1] },
    { label: "Number violations (R1)", value: String(s.validator_violations), target: "0", ok: data!.verdict.validator_violations },
    { label: "Tier mix", value: Object.entries(s.tier_mix).map(([k, v]) => `${k.replace("tier", "T")}:${v}`).join(" "), target: "mostly T0", ok: null },
  ] : [];

  return (
    <div className="min-h-full">
      <TopBar title="Eval dashboard" />
      <div className="bg-amber-100 py-2 text-center text-sm font-bold text-amber-900">⚠ SIMULATED DATA — {s?.cases ?? "…"} hand-written cases, not Paytm data</div>
      <main className="mx-auto max-w-7xl p-4">
        {err && <Card><Empty title={err} sub="The dashboard renders the backend's eval output; nothing is hardcoded." /></Card>}
        {data && (
          <>
            <p className="mb-3 text-xs text-muted">Generated {formatDate(data.generated_at)} by the backend's eval/run_eval.py (offline MockLLM, isolated DB). Live travel shortlist avg from /metrics: {travelMs ? `${travelMs} ms` : "—"}.</p>
            <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
              {tiles.map((t) => (
                <div key={t.label} className="rounded-xl border border-line bg-white p-3">
                  <small className="text-[11px] text-muted">{t.label}</small>
                  <b className="block text-2xl text-navy-700">{t.value}</b>
                  {t.ok === null ? <Badge tone="muted">{t.target}</Badge> : <Badge tone={t.ok ? "ok" : "risk"}>{t.ok ? "✓" : "✗"} target {t.target}</Badge>}
                </div>
              ))}
            </div>
            <Card>
              <div className="mb-3 flex flex-wrap items-center gap-2 text-sm">
                <select value={scenario} onChange={(e) => setScenario(e.target.value)} className="min-h-[36px] rounded-full border border-line px-3" aria-label="Scenario">
                  <option value="all">All scenarios</option>
                  {[...new Set(data.rows.map((r) => r.scenario))].map((x) => <option key={x}>{x}</option>)}
                </select>
                <select value={lang} onChange={(e) => setLang(e.target.value)} className="min-h-[36px] rounded-full border border-line px-3" aria-label="Language">
                  <option value="all">All languages</option>
                  {[...new Set(data.rows.map((r) => r.language))].map((x) => <option key={x}>{x}</option>)}
                </select>
                <label className="flex items-center gap-1.5"><input type="checkbox" checked={onlyFail} onChange={(e) => setOnlyFail(e.target.checked)} /> Failures only</label>
                <Button size="sm" className="ml-auto" onClick={exportCsv}><Download className="h-4 w-4" /> CSV</Button>
              </div>
              <div className="overflow-x-auto scrollbar-thin">
                <table className="w-full min-w-[820px] text-left text-xs">
                  <thead className="text-[11px] uppercase text-muted"><tr><th className="p-2">ID</th><th className="p-2">Scenario</th><th className="p-2">Lang</th><th className="p-2">Input</th><th className="p-2">Expected</th><th className="p-2">Actual</th><th className="p-2">Pass</th><th className="p-2">Tier</th></tr></thead>
                  <tbody>
                    {rows.map((r) => (
                      <tr key={r.id} onClick={() => setRow(r)} className={clsx("cursor-pointer border-t border-line hover:bg-slate-50", !r.passed && "bg-red-50/60")}>
                        <td className="mono p-2">{r.id}</td><td className="p-2">{r.scenario}</td><td className="p-2">{r.language}</td>
                        <td className="max-w-[320px] truncate p-2">{r.input}</td><td className="p-2">{r.expected}</td><td className="p-2">{r.actual}</td>
                        <td className="p-2">{r.passed ? "✅" : "❌"}</td><td className="p-2">T{r.tier}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </>
        )}
      </main>
      <Dialog open={!!row} onClose={() => setRow(null)} title={row ? `${row.id} · ${row.scenario}` : ""}>
        {row && (
          <div className="grid gap-2 text-sm">
            <div><b>Input</b><p>{row.input}</p></div>
            <div className="flex gap-2"><Badge tone="muted">expected {row.expected}</Badge><Badge tone={row.passed ? "ok" : "risk"}>actual {row.actual}</Badge><Badge tone="sky">Tier {row.tier}</Badge></div>
            <div><b>Saarthi reply</b><p className="whitespace-pre-line">{row.reply}</p></div>
            <p className="text-xs text-muted">Number-validator violations: {row.violations}</p>
          </div>
        )}
      </Dialog>
    </div>
  );
}
