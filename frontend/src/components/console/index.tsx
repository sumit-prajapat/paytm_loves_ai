import clsx from "clsx";
import { GraduationCap, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge, Button, Empty, Sheet } from "@/components/ui";
import { api, errorText } from "@/lib/api";
import { ago, formatINR, formatTime } from "@/lib/format";
import { MERCHANT_NAMES } from "@/lib/personas";
import { decideLoan, resolveEscalation } from "@/services/actions";
import { useStore } from "@/store";
import type { AuditEntry, Escalation, FlightOption } from "@/types/contracts";

function amountOf(e: Escalation): string | null {
  const f = e.dossier?.findings?.find((x) => x.facts && ("amount" in x.facts || "gap" in x.facts));
  if (!f) return null;
  return formatINR(f.facts.amount_money ?? f.facts.amount ?? f.facts.gap_money ?? f.facts.gap);
}

function risk(e: Escalation): "high" | "medium" | "low" {
  const types = e.dossier?.issue_types ?? [];
  if (types.includes("chargeback_dispute")) return "high";
  if (e.priority === "high") return "medium";
  return "low";
}

export function EscalationQueue({ onOpen, compact }: { onOpen: (e: Escalation) => void; compact?: boolean }) {
  const list = useStore((s) => s.escalations);
  if (!list.length) return <Empty title="Queue khaali hai" sub="Risky cases (e.g. chargebacks) land here with a full dossier." />;
  return (
    <ul className="flex flex-col gap-2">
      {list.slice(0, compact ? 3 : 50).map((e) => {
        const r = risk(e);
        return (
          <li key={e.ticket_id} className={clsx("rounded-xl border border-line border-l-4 bg-white p-2.5 text-xs", r === "high" ? "border-l-risk" : "border-l-warn")}>
            <div className="flex items-center justify-between gap-2">
              <b className="truncate">{e.ticket_id} · {(e.dossier?.issue_types ?? ["case"]).join(", ")}</b>
              <Badge tone={r === "high" ? "risk" : "warn"}>{r}</Badge>
            </div>
            <div className="mt-0.5 text-slate-600">
              {MERCHANT_NAMES[e.merchant_id] ?? e.merchant_id}
              {amountOf(e) && <> · <span className="num">{amountOf(e)}</span></>} · {ago(e.created_at)}
            </div>
            {!compact && <p className="mt-1 line-clamp-2 text-slate-700">{e.dossier?.summary}</p>}
            <Button size="sm" className="mt-1.5" onClick={() => onOpen(e)}>Open →</Button>
          </li>
        );
      })}
    </ul>
  );
}

const SAFE_ACTIONS: Record<string, string[]> = {
  chargeback_dispute: ["request_evidence_upload"],
  settlement_short: ["explain_breakdown"],
  soundbox_offline: ["guide_charger", "guide_restart"],
};

export function CaseDrawer({ esc, onClose }: { esc: Escalation | null; onClose: () => void }) {
  const d = esc?.dossier;
  const issue = d?.issue_types?.find((i) => SAFE_ACTIONS[i]);
  const [fix, setFix] = useState("");
  const [editing, setEditing] = useState(false);
  const [save, setSave] = useState(true);
  const [action, setAction] = useState<string>("");
  const [rootCause, setRootCause] = useState("resolved_by_specialist");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    setFix(d?.suggested_next_step ?? "");
    setEditing(false);
    setSave(!!issue);
    setAction(issue ? SAFE_ACTIONS[issue][0] : "");
    setRootCause(issue === "chargeback_dispute" ? "delivery_proof_verified" : "resolved_by_specialist");
  }, [esc?.ticket_id]); // eslint-disable-line react-hooks/exhaustive-deps

  const submit = async (approve: boolean) => {
    if (!esc) return;
    setBusy(true);
    const ok = await resolveEscalation(
      esc.ticket_id,
      approve ? fix || "Approved suggested fix" : `Rejected suggested fix. ${fix}`.trim(),
      approve && save && !!issue,
      approve && save ? action : null,
    );
    setBusy(false);
    if (ok) onClose();
  };

  return (
    <Sheet open={!!esc} onClose={onClose} title={esc ? `${esc.ticket_id} · ${(d?.issue_types ?? []).join(", ")}` : ""}>
      {esc && d && (
        <div className="flex flex-col gap-3 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={risk(esc) === "high" ? "risk" : "warn"}>{risk(esc)} risk</Badge>
            <span className="text-muted">{MERCHANT_NAMES[esc.merchant_id] ?? esc.merchant_id} · {d.merchant_language}</span>
            <span className="mono text-xs text-muted">case {d.case_id}</span>
          </div>
          <section>
            <h3 className="mb-1 text-[11px] font-bold uppercase tracking-wide text-muted">Summary <Badge tone="muted">{d.summary_source}</Badge></h3>
            <p>{d.summary}</p>
            {d.user_message && <p className="mt-1 text-xs text-muted">Merchant said: “{d.user_message}”</p>}
          </section>
          <section>
            <h3 className="mb-1 text-[11px] font-bold uppercase tracking-wide text-muted">Evidence (tool outputs)</h3>
            {d.findings.map((f, i) => (
              <details key={i} className="rounded-lg border border-line px-2 py-1 text-xs">
                <summary className="cursor-pointer font-semibold">🔧 {f.code}</summary>
                <pre className="mono mt-1 max-h-48 overflow-auto text-[11px] scrollbar-thin">{JSON.stringify(f.facts, null, 1)}</pre>
              </details>
            ))}
            <div className="mt-1 flex flex-wrap gap-1">{d.evidence.map((e) => <span key={e} className="mono rounded bg-slate-100 px-1.5 text-[11px]">{e}</span>)}</div>
          </section>
          <section>
            <h3 className="mb-1 text-[11px] font-bold uppercase tracking-wide text-muted">Why escalated</h3>
            <p className="text-xs">{d.reason}</p>
          </section>
          <section>
            <h3 className="mb-1 text-[11px] font-bold uppercase tracking-wide text-muted">Suggested fix {editing ? "(editing)" : ""}</h3>
            <textarea
              value={fix}
              readOnly={!editing}
              onChange={(e) => setFix(e.target.value)}
              className={clsx("min-h-[70px] w-full rounded-lg border p-2 text-sm", editing ? "border-sky-500" : "border-line bg-slate-50")}
            />
          </section>
          <div className="rounded-xl border border-lime-300 bg-lime-50 p-3">
            <label className="flex items-center gap-2 font-semibold">
              <input type="checkbox" checked={save && !!issue} disabled={!issue} onChange={(e) => setSave(e.target.checked)} className="h-5 w-5" />
              <GraduationCap className="h-4 w-4 text-lime-700" /> Save as playbook
            </label>
            {issue ? (
              <div className="mt-2 grid gap-1.5 text-xs">
                <div className="flex justify-between"><span>Issue type</span><b>{issue}</b></div>
                <label className="flex items-center justify-between gap-2">Root cause
                  <input value={rootCause} onChange={(e) => setRootCause(e.target.value)} className="w-44 rounded border border-line px-2 py-1" />
                </label>
                <label className="flex items-center justify-between gap-2">Safe action
                  <select value={action} onChange={(e) => setAction(e.target.value)} className="rounded border border-line px-2 py-1">
                    {SAFE_ACTIONS[issue].map((a) => <option key={a}>{a}</option>)}
                  </select>
                </label>
                <p className="text-[11px] text-muted">Conditions are copied from this case, so only similar cases auto-resolve. Playbooks never move money.</p>
              </div>
            ) : (
              <p className="mt-1 text-xs text-muted">This issue type cannot become an automatic playbook (it needs a person every time).</p>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="primary" loading={busy} onClick={() => submit(true)}>Approve fix</Button>
            <Button onClick={() => setEditing(true)} disabled={editing}>Edit &amp; approve</Button>
            <Button variant="danger" loading={busy} onClick={() => submit(false)}>Reject</Button>
          </div>
        </div>
      )}
    </Sheet>
  );
}

export function LoanApprovals() {
  const loans = useStore((s) => s.loans);
  const [busy, setBusy] = useState<string | null>(null);
  if (!loans.length) return <Empty title="Koi loan approval pending nahi" />;
  return (
    <ul className="flex flex-col gap-2">
      {loans.map((l) => (
        <li key={l.request_id} className="rounded-xl border border-line border-l-4 border-l-pink-600 bg-white p-2.5 text-xs">
          <b>{MERCHANT_NAMES[l.merchant_id ?? ""] ?? l.merchant_id}</b> · <span className="num">{formatINR(l.amount)}</span> · {l.tenure_months} mo
          <div>EMI <span className="num">{formatINR(l.emi)}</span> · <Badge tone="warn">Awaiting · {l.rate_pct}%</Badge></div>
          <div className="mono text-[10.5px] text-muted">{l.request_id}</div>
          <div className="mt-1.5 flex gap-1.5">
            <Button size="sm" variant="primary" loading={busy === l.request_id + "a"} onClick={async () => { setBusy(l.request_id + "a"); await decideLoan(l.request_id, true); setBusy(null); }}>Approve</Button>
            <Button size="sm" loading={busy === l.request_id + "r"} onClick={async () => { setBusy(l.request_id + "r"); await decideLoan(l.request_id, false); setBusy(null); }}>Reject</Button>
          </div>
        </li>
      ))}
    </ul>
  );
}

export function EscalationChart({ height = 160 }: { height?: number }) {
  const series = useStore((s) => s.series);
  const pb = series.find((p) => p.playbook);
  if (!series.length) {
    return <Empty title="Repeat-case chart" sub="Run the chargeback case, resolve it with “Save as playbook”, then run the repeat case: the escalation rate drops 100% → 0%." />;
  }
  return (
    <div style={{ height }} aria-label="Escalation rate for repeat chargeback runs">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={series} margin={{ top: 16, right: 16, bottom: 4, left: -16 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
          <XAxis dataKey="run" tick={{ fontSize: 11 }} label={{ value: "repeat run", fontSize: 10, position: "insideBottomRight", offset: -2 }} />
          <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} unit="%" />
          <Tooltip formatter={(v: number) => [`${v}%`, "escalation"]} labelFormatter={(l) => `Run ${l}`} />
          {pb && <ReferenceLine x={pb.run} stroke="#65A30D" strokeDasharray="4 3" label={{ value: "🎓 playbook saved", fontSize: 11, fill: "#3F6212", position: "top" }} />}
          <Line type="stepAfter" dataKey="rate" stroke="var(--sky-500)" strokeWidth={3} dot={{ r: 4 }} isAnimationActive />
        </LineChart>
      </ResponsiveContainer>
      <p className="text-[11px] text-muted">Measured in this session from real check-up outcomes (escalated = 100%, auto-resolved = 0%).</p>
    </div>
  );
}

export function PlaybookList() {
  const pbs = useStore((s) => s.playbooks);
  if (!pbs.length) return <Empty title="No playbooks yet" />;
  return (
    <div className="overflow-x-auto scrollbar-thin">
      <table className="w-full min-w-[560px] text-left text-xs">
        <thead className="text-[11px] uppercase text-muted"><tr><th className="p-2">Issue type</th><th className="p-2">Root cause</th><th className="p-2">Action</th><th className="p-2">Created from</th><th className="p-2">Times used</th></tr></thead>
        <tbody>
          {pbs.map((p) => (
            <tr key={p.playbook_id} className="border-t border-line">
              <td className="p-2 font-semibold">{p.issue_type}</td><td className="p-2">{p.root_cause}</td>
              <td className="mono p-2">{p.action}</td><td className="mono p-2">{p.created_from_case ?? "—"}</td><td className="p-2 num">{p.times_used}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function AuditTable({ caseId }: { caseId?: string | null }) {
  const [rows, setRows] = useState<AuditEntry[]>([]);
  const [verified, setVerified] = useState<string>("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  const load = async () => {
    setLoading(true);
    setErr("");
    try {
      const [r, v] = await Promise.all([api.audit(caseId ?? undefined), api.auditVerify()]);
      setRows(r);
      setVerified(v.chain_intact ? `✓ hash chain intact (${v.total_records ?? r.length} records)` : "✗ chain broken");
    } catch (e) {
      setErr(errorText(e));
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, [caseId]); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <div>
      <div className="mb-2 flex items-center gap-2 text-xs">
        <Badge tone={verified.startsWith("✓") ? "ok" : "risk"}>{verified || "…"}</Badge>
        <Button size="sm" variant="ghost" onClick={load} loading={loading}><RefreshCw className="h-3.5 w-3.5" /> Refresh</Button>
        <span className="text-muted">Read-only. No edit or delete exists.</span>
      </div>
      {err && <p className="text-xs text-risk">{err}</p>}
      <div className="max-h-72 overflow-auto scrollbar-thin">
        <table className="w-full min-w-[640px] text-left text-xs">
          <thead className="sticky top-0 bg-white text-[11px] uppercase text-muted"><tr><th className="p-2">Time</th><th className="p-2">Case</th><th className="p-2">Actor</th><th className="p-2">Action</th><th className="p-2">Detail</th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-t border-line align-top">
                <td className="mono p-2">{formatTime(r.timestamp)}</td><td className="mono p-2">{r.case_id}</td>
                <td className="p-2">{r.actor}</td><td className="p-2 font-semibold">{r.action}</td>
                <td className="mono max-w-[280px] truncate p-2" title={JSON.stringify(r.detail)}>{JSON.stringify(r.detail)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const FACTORS: { key: keyof FlightOption["score_breakdown"]; label: string }[] = [
  { key: "price_score", label: "Price" }, { key: "duration_score", label: "Duration" }, { key: "time_fit_score", label: "Dep. fit" },
  { key: "stops_score", label: "Stops" }, { key: "refundable_score", label: "Refundable" }, { key: "ontime_score", label: "On-time" },
];

export function ScoreBars({ b }: { b: FlightOption["score_breakdown"] }) {
  return (
    <div className="grid gap-1">
      {FACTORS.map((f) => (
        <div key={f.key} className="grid grid-cols-[78px_1fr_44px] items-center gap-2 text-[11px]">
          <span>{f.label}</span>
          <span className="h-1.5 overflow-hidden rounded bg-slate-100"><span className="block h-full rounded bg-sky-500" style={{ width: `${Math.min(100, b[f.key] * 200)}%` }} /></span>
          <span className="mono text-right">{b[f.key].toFixed(3)}</span>
        </div>
      ))}
      <div className="mono text-right text-[11px] font-bold">total {b.total_score.toFixed(3)}</div>
    </div>
  );
}

export function RankingFormula() {
  const threads = useStore((s) => s.threads);
  const last = useMemo(() => {
    const all = [...(threads.arjun ?? []), ...(threads.meena ?? []), ...(threads.priya ?? [])].filter((m) => m.result?.recommended);
    return all.sort((a, b) => b.ts - a.ts)[0]?.result?.recommended;
  }, [threads]);
  return (
    <div className="grid gap-3 text-xs md:grid-cols-2">
      <div>
        <b>Travel ranking formula (deterministic, backend)</b>
        <p className="mono my-1">score = Σ wᵢ · normᵢ  (price, duration, departure fit, stops, refundable, on-time)</p>
        <p className="text-muted">“sasta” → price weight ↑ · “jaldi” → duration weight ↑ · elder mode → stops/on-time ↑. Weights live in the backend; the values on the right are the backend’s own weighted factors for the latest recommendation.</p>
      </div>
      <div>
        {last ? (
          <>
            <b>{last.airline} · {last.from}→{last.to} · {last.dep_time}</b>
            <ScoreBars b={last.score_breakdown} />
          </>
        ) : (
          <Empty title="No travel search yet" sub="Run a travel request to see live factor scores." />
        )}
      </div>
    </div>
  );
}
