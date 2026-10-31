import clsx from "clsx";
import { useState } from "react";
import { useRealtime } from "@/app/realtime";
import { AuditTable, CaseDrawer, EscalationChart, EscalationQueue, LoanApprovals, PlaybookList, RankingFormula } from "@/components/console";
import { AgentCrewBar, CaseFeed, DecisionBox, TraceTimeline } from "@/components/crew";
import { ConnectionPill, EnvBadge, KillBanner, KillSwitch, MetricsBar, TopBar } from "@/components/layout";
import { Card, Tabs } from "@/components/ui";
import { useStore } from "@/store";
import type { Escalation } from "@/types/contracts";

type Bottom = "chart" | "playbooks" | "ranking" | "audit";
type Mobile = "feed" | "trace" | "queue";
type Filter = "all" | "auto" | "escalated" | "pending";

export default function Console() {
  useRealtime({ trace: true, console: true });
  const selected = useStore((s) => s.selectedCase);
  const killed = useStore((s) => s.control?.kill_switch_active);
  const escCount = useStore((s) => s.escalations.length);
  const loanCount = useStore((s) => s.loans.length);
  const [open, setOpen] = useState<Escalation | null>(null);
  const [bottom, setBottom] = useState<Bottom>("chart");
  const [mobile, setMobile] = useState<Mobile>("trace");
  const [filter, setFilter] = useState<Filter>("all");

  const feed = (
    <section aria-label="Cases" className={clsx("min-w-0 border-line p-3 xl:border-r", mobile !== "feed" && "hidden xl:block")}>
      <h2 className="mb-2 text-[11px] font-bold uppercase tracking-wider text-muted">Cases</h2>
      <Tabs<Filter> tabs={[{ id: "all", label: "All" }, { id: "auto", label: "Auto" }, { id: "escalated", label: "Escalated" }, { id: "pending", label: "Pending" }]} value={filter} onChange={setFilter} />
      <div className="mt-2 max-h-[62vh] overflow-y-auto scrollbar-thin"><CaseFeed filter={filter} /></div>
    </section>
  );
  const trace = (
    <section aria-label="Glass-box trace" className={clsx("min-w-0 border-line p-3 xl:border-r", mobile !== "trace" && "hidden xl:block")}>
      <h2 className="mb-2 text-[11px] font-bold uppercase tracking-wider text-muted">Glass-box trace {selected && <span className="mono normal-case">· {selected}</span>}</h2>
      <AgentCrewBar />
      <div className="mt-3 max-h-[52vh] overflow-y-auto pr-1 scrollbar-thin"><TraceTimeline caseId={selected} /></div>
      <DecisionBox caseId={selected} />
    </section>
  );
  const queue = (
    <section aria-label="Escalations and approvals" className={clsx("min-w-0 p-3", mobile !== "queue" && "hidden xl:block")}>
      <h2 className="mb-2 text-[11px] font-bold uppercase tracking-wider text-muted">Escalation queue ({escCount})</h2>
      <div className="max-h-[34vh] overflow-y-auto scrollbar-thin"><EscalationQueue onOpen={setOpen} /></div>
      <h2 className="mb-2 mt-4 text-[11px] font-bold uppercase tracking-wider text-muted">Loan approvals ({loanCount})</h2>
      <div className="max-h-[26vh] overflow-y-auto scrollbar-thin"><LoanApprovals /></div>
    </section>
  );

  return (
    <div className={clsx("min-h-full", killed && "desaturate")}>
      <TopBar title="Saarthi Ops">
        <EnvBadge />
        <ConnectionPill />
        <div className="ml-auto sm:ml-0"><KillSwitch /></div>
      </TopBar>
      <KillBanner />
      <MetricsBar />
      <div className="px-3 pt-3 xl:hidden">
        <Tabs<Mobile> tabs={[{ id: "feed", label: "Feed" }, { id: "trace", label: "Trace" }, { id: "queue", label: `Queue (${escCount})` }]} value={mobile} onChange={setMobile} />
      </div>
      <div className="m-3 grid rounded-card border border-line bg-white shadow-card xl:grid-cols-[260px_minmax(0,1fr)_340px]">
        {feed}
        {trace}
        {queue}
      </div>
      <Card className="m-3">
        <Tabs<Bottom> tabs={[{ id: "chart", label: "Escalation rate" }, { id: "playbooks", label: "Playbooks" }, { id: "ranking", label: "Ranking formula" }, { id: "audit", label: "Audit log" }]} value={bottom} onChange={setBottom} />
        <div className="mt-3">
          {bottom === "chart" && <EscalationChart height={200} />}
          {bottom === "playbooks" && <PlaybookList />}
          {bottom === "ranking" && <RankingFormula />}
          {bottom === "audit" && <AuditTable />}
        </div>
      </Card>
      <CaseDrawer esc={open} onClose={() => setOpen(null)} />
    </div>
  );
}
