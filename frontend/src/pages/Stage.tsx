import clsx from "clsx";
import { Keyboard } from "lucide-react";
import { useEffect, useState } from "react";
import { useRealtime } from "@/app/realtime";
import { CaseDrawer, EscalationChart, EscalationQueue } from "@/components/console";
import { AgentCrewBar, DecisionBox, TraceTimeline } from "@/components/crew";
import { ConnectionPill, KillBanner, KillSwitch, MetricsBar, TopBar } from "@/components/layout";
import { MerchantChat } from "@/components/panels/MerchantChat";
import { SoundboxPanel } from "@/components/panels/SoundboxPanel";
import { TravelChat } from "@/components/panels/TravelChat";
import { Badge, Card } from "@/components/ui";
import { config } from "@/lib/config";
import { INJECTS, resetDemo, runInject, setKillSwitch } from "@/services/actions";
import { useStore } from "@/store";
import type { Escalation } from "@/types/contracts";

export default function Stage() {
  const phone = useStore((s) => s.stagePhone);
  const set = useStore((s) => s.set);
  const selected = useStore((s) => s.selectedCase);
  const lastInject = useStore((s) => s.injectLog[0]);
  const killed = useStore((s) => s.control?.kill_switch_active);
  const [open, setOpen] = useState<Escalation | null>(null);
  useRealtime({ trace: true, console: true, merchant: "ramesh" });

  useEffect(() => {
    if (!config.demoMode) return;
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || e.metaKey || e.ctrlKey || e.altKey) return;
      const def = INJECTS.find((d) => d.key === e.key);
      if (def) {
        if (def.persona === "arjun") set({ stagePhone: "arjun" });
        else if (def.persona === "ramesh") set({ stagePhone: "ramesh" });
        runInject(def);
      } else if (e.key.toLowerCase() === "k") {
        const active = !useStore.getState().control?.kill_switch_active;
        setKillSwitch(active, "Presenter shortcut (K)");
      } else if (e.key.toLowerCase() === "r") {
        resetDemo();
      } else if (e.key.toLowerCase() === "t") {
        set({ stagePhone: useStore.getState().stagePhone === "ramesh" ? "arjun" : "ramesh" });
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [set]);

  return (
    <div className={clsx("min-h-full", killed && "desaturate")}>
      <TopBar title="Saarthi">
        <Badge tone="sky">{lastInject ? `${lastInject.label}${lastInject.outcome ? ` · ${lastInject.outcome}` : ""}` : "Waiting for a user trigger"}</Badge>
        <ConnectionPill />
        <div role="radiogroup" aria-label="Phone" className="flex rounded-full bg-white/10 p-0.5 text-xs font-bold">
          {(["ramesh", "arjun"] as const).map((p) => (
            <button key={p} role="radio" aria-checked={phone === p} onClick={() => set({ stagePhone: p })} className={clsx("min-h-[32px] rounded-full px-3", phone === p ? "bg-white text-navy-900" : "text-white/80")}>
              {p === "ramesh" ? "Ramesh (Care)" : "Arjun (Travel)"}
            </button>
          ))}
        </div>
        <KillSwitch />
      </TopBar>
      <KillBanner />
      <MetricsBar dense />
      <div className="grid gap-4 p-4 xl:grid-cols-[auto_auto_minmax(0,1fr)]">
        <div className="flex justify-center">
          {phone === "ramesh" ? <MerchantChat persona="ramesh" height={660} /> : <TravelChat persona="arjun" height={660} />}
        </div>
        <div className="flex justify-center"><SoundboxPanel persona="ramesh" compact /></div>
        <div className="flex min-w-0 flex-col gap-3">
          <Card className="!p-3">
            <h2 className="mb-2 text-[11px] font-bold uppercase tracking-wider text-muted">Saarthi crew</h2>
            <AgentCrewBar />
          </Card>
          <Card className="!p-3">
            <h2 className="mb-2 text-[11px] font-bold uppercase tracking-wider text-muted">Live trace {selected && <span className="mono normal-case">· {selected}</span>}</h2>
            <div className="max-h-[300px] overflow-y-auto pr-1 scrollbar-thin"><TraceTimeline caseId={selected} max={14} /></div>
            <DecisionBox caseId={selected} />
          </Card>
          <div className="grid gap-3 2xl:grid-cols-2">
            <Card className="!p-3">
              <h2 className="mb-2 text-[11px] font-bold uppercase tracking-wider text-muted">Escalation queue</h2>
              <EscalationQueue compact onOpen={setOpen} />
            </Card>
            <Card className="!p-3">
              <h2 className="mb-2 text-[11px] font-bold uppercase tracking-wider text-muted">Learning (repeat case)</h2>
              <EscalationChart height={150} />
            </Card>
          </div>
          {config.demoMode && (
            <p className="flex items-center gap-1.5 text-[11px] text-muted">
              <Keyboard className="h-3.5 w-3.5" /> Presenter keys: 1–8 scenarios · K kill switch · R reset demo · T toggle phone
            </p>
          )}
        </div>
      </div>
      <CaseDrawer esc={open} onClose={() => setOpen(null)} />
    </div>
  );
}
