import clsx from "clsx";
import { Check } from "lucide-react";
import { useMemo } from "react";
import { Badge, Empty } from "@/components/ui";
import { AGENTS, crewAgentFor } from "@/lib/agents";
import { ago, formatTime } from "@/lib/format";
import { useStore } from "@/store";
import type { TraceStep } from "@/types/contracts";

export function AgentCrewBar({ compact }: { compact?: boolean }) {
  const states = useStore((s) => s.agentStates);
  const paused = useStore((s) => s.control?.kill_switch_active);
  const groups: { id: string; label: string }[] = [
    { id: "care", label: "Care crew" },
    { id: "travel", label: "Travel crew" },
    { id: "safety", label: "Safety" },
  ];
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-2" aria-label="Agent crew">
      {groups.map((g) => (
        <div key={g.id}>
          {!compact && <div className="mb-1 text-[10px] font-bold uppercase tracking-wider text-muted">{g.label}</div>}
          <div className="flex flex-wrap gap-1.5">
            {AGENTS.filter((a) => a.group === g.id).map((a) => {
              const s = states[a.name];
              const Icon = a.icon;
              return (
                <div key={a.name} className="flex w-[54px] flex-col items-center text-center" title={`${a.label}: ${s}`}>
                  <div
                    className={clsx(
                      "relative grid h-9 w-9 place-items-center rounded-full text-white transition",
                      paused ? "opacity-25 grayscale" : s === "idle" ? "opacity-30" : "opacity-100",
                      s === "working" && !paused && "scale-110",
                      s === "blocked" && "ring-2 ring-risk ring-offset-2",
                    )}
                    style={{ background: a.color, boxShadow: s === "working" && !paused ? `0 0 0 4px rgba(0,180,230,.25), 0 0 16px ${a.color}` : undefined }}
                  >
                    <Icon className="h-4 w-4" />
                    {s === "done" && <Check className="absolute -right-1 -top-1 h-3.5 w-3.5 rounded-full bg-ok p-0.5 text-white" />}
                  </div>
                  <span className={clsx("mt-0.5 text-[10px]", s === "idle" ? "text-slate-400" : "font-bold text-ink")}>{a.label}</span>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

export function ConfidenceMeter({ value, clarify = 0.6, auto = 0.85 }: { value: number; clarify?: number; auto?: number }) {
  const zone = value < clarify ? "risk" : value < auto ? "warn" : "ok";
  return (
    <div className="mt-1" aria-label={`confidence ${value}`}>
      <div className="relative h-2 rounded-full" style={{ background: `linear-gradient(90deg, var(--risk) 0 ${clarify * 100}%, var(--warn) ${clarify * 100}% ${auto * 100}%, var(--ok) ${auto * 100}%)` }}>
        <i className="absolute -top-1 h-4 w-[3px] rounded bg-ink" style={{ left: `calc(${Math.min(1, Math.max(0, value)) * 100}% - 1px)` }} />
      </div>
      <small className={clsx("mono text-[10.5px]", zone === "risk" ? "text-risk" : zone === "warn" ? "text-warn" : "text-ok")}>confidence {value.toFixed(2)}</small>
    </div>
  );
}

function chips(output: any): string[] {
  if (!output || typeof output !== "object") return [];
  const out: string[] = [];
  for (const [k, v] of Object.entries(output)) {
    if (v == null) continue;
    if (typeof v === "number" || typeof v === "boolean") out.push(`${k} ${v}`);
    else if (typeof v === "string" && v.length <= 40) out.push(`${k} ${v}`);
    else if (Array.isArray(v) && v.length && typeof v[0] === "object" && "code" in v[0]) v.forEach((f: any) => out.push(f.code));
    else if (Array.isArray(v) && v.length && typeof v[0] === "string") out.push(`${k}: ${v.slice(0, 3).join(", ")}${v.length > 3 ? "…" : ""}`);
  }
  return out.slice(0, 8);
}

function summary(step: TraceStep): string {
  const i = step.input || {};
  if (step.tool === "captain_plan") return i.trigger ? `${i.trigger.request_type} via ${i.trigger.channel} → plan ${(step.output?.plan ?? []).join(" → ")}` : `slot fill: ${i.slot_fill}`;
  if (step.tool === "classify_intent_and_extract_slots") return `“${String(i.message ?? "").slice(0, 60)}”`;
  if (step.tool === "evaluate_action_policy") return `${i.action_class} · ${i.finding ?? i.subject ?? ""}`;
  if (step.tool === "run_checkup_diagnostics") return `merchant ${i.merchant_id} · scope ${i.scope}`;
  const keys = Object.entries(i).filter(([, v]) => typeof v !== "object").slice(0, 3);
  return keys.map(([k, v]) => `${k}=${v}`).join(" · ");
}

export function TraceStepRow({ step }: { step: TraceStep }) {
  const a = AGENTS.find((x) => x.name === crewAgentFor(step))!;
  const Icon = a.icon;
  const decision = step.output?.decision as string | undefined;
  return (
    <div className="grid animate-rise grid-cols-[24px_1fr] gap-2">
      <div className="mt-0.5 grid h-6 w-6 place-items-center rounded-full text-white" style={{ background: a.color }}><Icon className="h-3.5 w-3.5" /></div>
      <div className="min-w-0 rounded-xl border border-line bg-white px-2.5 py-1.5 text-xs">
        <div className="flex flex-wrap items-center gap-x-2">
          <b>{a.label}</b>
          {step.agent !== a.name && <span className="text-muted">({step.agent})</span>}
          {step.tool && <span className="mono truncate text-slate-600">· {step.tool}</span>}
          <span className="ml-auto flex items-center gap-1.5 text-[10.5px] text-slate-400">
            {step.cost_tier > 0 && <Badge tone="warn">Tier {step.cost_tier}{step.tokens ? ` · ${step.tokens} tok` : ""}</Badge>}
            {step.latency_ms ? `${step.latency_ms} ms` : ""}
          </span>
        </div>
        <div className="mt-0.5 break-words text-slate-700">{summary(step)}</div>
        {decision && (
          <div className={clsx("mt-1 font-bold", decision === "allow" ? "text-ok" : decision === "needs_input" ? "text-warn" : "text-risk")}>
            {decision.toUpperCase()} — <span className="font-normal">{step.output?.reason}</span>
          </div>
        )}
        <div className="mt-1 flex flex-wrap gap-1">
          {chips(step.output).map((c) => <span key={c} className="rounded-md bg-indigo-50 px-1.5 py-0.5 text-[11px] font-bold text-navy-700">{c}</span>)}
        </div>
        {step.confidence < 1 && <ConfidenceMeter value={step.confidence} />}
        <details className="mt-1">
          <summary className="cursor-pointer text-[10.5px] text-sky-700">raw JSON ▸</summary>
          <pre className="mono mt-1 max-h-48 overflow-auto rounded bg-slate-50 p-1.5 text-[10.5px] scrollbar-thin">{JSON.stringify({ input: step.input, output: step.output }, null, 1)}</pre>
        </details>
      </div>
    </div>
  );
}

export function useCaseSteps(caseId: string | null): TraceStep[] {
  const steps = useStore((s) => s.steps);
  return useMemo(() => (caseId ? steps.filter((s) => s.case_id === caseId) : []), [steps, caseId]);
}

export function TraceTimeline({ caseId, max = 40 }: { caseId: string | null; max?: number }) {
  const steps = useCaseSteps(caseId);
  if (!caseId || !steps.length)
    return <Empty title="Abhi koi trace nahi" sub="Kisi screen par check-up, chat ya Soundbox button dabaiye — steps yahan live aayenge." />;
  return <div className="flex flex-col gap-1.5">{steps.slice(-max).map((s) => <TraceStepRow key={s.run_id} step={s} />)}</div>;
}

export function DecisionBox({ caseId }: { caseId: string | null }) {
  const steps = useCaseSteps(caseId);
  const control = useStore((s) => s.control);
  const guards = steps.filter((s) => s.agent === "guardian" && s.output?.decision);
  if (!guards.length) return null;
  // Routing outcome for the case: block > escalate (ticket / non-allow) > clarify > auto.
  const blocked = guards.find((g) => g.output.decision === "block");
  const escalated = guards.find((g) => g.output.decision === "escalate") ?? guards.find((g) => g.input?.action_class === "create_ticket");
  const clarify = guards.find((g) => g.output.decision === "needs_input");
  const g = blocked ?? escalated ?? clarify ?? guards[guards.length - 1];
  const outcome = blocked ? "BLOCK (human-only action)" : escalated ? "ESCALATE TO HUMAN" : clarify ? "ASK ONE QUESTION" : "AUTO-RESOLVE";
  const tone = blocked || escalated ? "risk" : clarify ? "warn" : "ok";
  const why = escalated && escalated.output.decision === "allow"
    ? `${escalated.input?.finding ?? "finding"} needs a specialist; ticket creation allowed by Guardian`
    : g.output.reason;
  return (
    <div className={clsx("mt-2 rounded-xl border px-3 py-2 text-xs", tone === "ok" ? "border-green-300 bg-ok-bg text-green-900" : tone === "warn" ? "border-amber-300 bg-warn-bg text-amber-900" : "border-red-300 bg-risk-bg text-red-900")}>
      ⚖️ Router: confidence <b>{Number(g.input?.confidence ?? 1).toFixed(2)}</b>
      {control && <> (auto ≥ {control.auto_resolve_confidence_threshold}, clarify ≥ {control.clarify_confidence_threshold})</>}, action <b>{g.input?.action_class}</b> → <b>{outcome}</b>
      <div className="opacity-80">{why}</div>
    </div>
  );
}

const STATUS_TONE: Record<string, "ok" | "warn" | "risk" | "sky" | "muted"> = {
  resolved: "ok", no_issue: "ok", escalated: "risk", needs_input: "warn", refused: "risk",
  ready_for_review_and_pay: "sky", awaiting_human_approval: "warn", quota_exceeded: "warn",
};

export function CaseFeed({ filter = "all" }: { filter?: "all" | "auto" | "escalated" | "pending" }) {
  const cases = useStore((s) => s.cases);
  const selected = useStore((s) => s.selectedCase);
  const set = useStore((s) => s.set);
  const rows = Object.values(cases)
    .sort((a, b) => b.first.localeCompare(a.first))
    .filter((c) =>
      filter === "all" ? true
        : filter === "auto" ? ["resolved", "no_issue"].includes(c.status ?? "")
          : filter === "escalated" ? c.status === "escalated"
            : !c.status || ["needs_input", "awaiting_human_approval"].includes(c.status));
  if (!rows.length) return <Empty title="No cases yet" sub="Cases appear only after a user triggers something." />;
  return (
    <ul className="flex flex-col gap-1.5">
      {rows.map((c) => (
        <li key={c.case_id}>
          <button
            onClick={() => set({ selectedCase: c.case_id })}
            className={clsx("w-full rounded-xl border px-2.5 py-2 text-left text-xs", selected === c.case_id ? "border-sky-500 bg-sky-100" : "border-line bg-white hover:bg-slate-50")}
          >
            <div className="flex items-center justify-between gap-2">
              <b className="mono truncate">{c.case_id}</b>
              <small className="text-muted">{formatTime(c.first)}</small>
            </div>
            <div className="truncate text-slate-600">{c.title || "…"}</div>
            <div className="mt-1 flex flex-wrap gap-1">
              <Badge tone={STATUS_TONE[c.status ?? ""] ?? "muted"}>{c.status ?? "running"}</Badge>
              {c.tier != null && <Badge tone={c.tier === 0 ? "ok" : "warn"}>Tier {c.tier}</Badge>}
              <small className="text-muted">{c.steps} steps · {ago(c.last)}</small>
            </div>
          </button>
        </li>
      ))}
    </ul>
  );
}
