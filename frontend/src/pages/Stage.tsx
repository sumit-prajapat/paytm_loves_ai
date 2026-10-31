import clsx from "clsx";
import { Home } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useRealtime } from "@/app/realtime";
import { CaseDrawer, EscalationChart, EscalationQueue } from "@/components/console";
import { AgentCrewBar, DecisionBox, TraceTimeline } from "@/components/crew";
import { BrandLogo, ConnectionPill, KillBanner, KillSwitch, LanguageChip, MetricsBar, ThemeToggle } from "@/components/layout";
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
  const [viewTab, setViewTab] = useState<"assistant" | "trace" | "all">("assistant");
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
    <div className={clsx("min-h-full bg-bg text-ink", killed && "desaturate")}>
      <header className="sticky top-0 z-40 border-b border-line/60 bg-navy-900/95 backdrop-blur-md px-4 py-2.5 text-white shadow-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-3">
          <Link to="/" className="flex items-center gap-2.5 transition hover:opacity-95 shrink-0" aria-label="Saarthi Home">
            <BrandLogo size={32} />
            <div className="flex flex-col">
              <span className="text-base font-black tracking-tight text-white flex items-center gap-1.5">
                Saarthi
                <span className="rounded-md bg-sky-500/20 px-1.5 py-0.5 text-[10px] font-extrabold text-sky-300 border border-sky-400/30">
                  AI Teammate
                </span>
              </span>
            </div>
          </Link>

          {/* Central Persona Switcher */}
          <div role="radiogroup" aria-label="Phone Persona" className="flex rounded-full bg-white/10 p-0.5 text-xs font-bold border border-white/10">
            {(["ramesh", "arjun"] as const).map((p) => (
              <button
                key={p}
                role="radio"
                aria-checked={phone === p}
                onClick={() => set({ stagePhone: p })}
                className={clsx(
                  "min-h-[32px] rounded-full px-3.5 transition flex items-center gap-1.5",
                  phone === p ? "bg-white text-navy-900 shadow-sm font-black" : "text-white/80 hover:text-white"
                )}
              >
                {p === "ramesh" ? "🏪 Ramesh (Care)" : "✈️ Arjun (Travel)"}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2 sm:gap-2.5">
            <ConnectionPill />
            <LanguageChip dark />
            <ThemeToggle dark />
            <Link to="/" className="hidden sm:inline-flex items-center gap-1 rounded-full bg-white/10 px-3 py-1.5 text-xs font-semibold hover:bg-white/20 transition">
              <Home className="h-3.5 w-3.5" /> Home
            </Link>
          </div>
        </div>
      </header>
      <KillBanner />

      {/* Clean & Professional Tab Navigation */}
      <div className="mx-auto max-w-7xl px-4 pt-4">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-3">
          <div className="flex rounded-2xl bg-card border border-line p-1 shadow-sm">
            <button
              type="button"
              onClick={() => setViewTab("assistant")}
              className={`rounded-xl px-4 py-2 text-xs sm:text-sm font-bold transition flex items-center gap-2 ${
                viewTab === "assistant" ? "bg-sky-500 text-navy-900 shadow-md font-extrabold" : "text-muted hover:text-ink"
              }`}
            >
              <span className="text-base">📱</span> Saarthi Assistant (Simple)
            </button>

            <button
              type="button"
              onClick={() => setViewTab("trace")}
              className={`rounded-xl px-4 py-2 text-xs sm:text-sm font-bold transition flex items-center gap-2 ${
                viewTab === "trace" ? "bg-sky-500 text-navy-900 shadow-md font-extrabold" : "text-muted hover:text-ink"
              }`}
            >
              <span className="text-base">🔬</span> Live Glass-Box Tracing & Ops
            </button>

            <button
              type="button"
              onClick={() => setViewTab("all")}
              className={`hidden md:flex rounded-xl px-4 py-2 text-xs sm:text-sm font-bold transition items-center gap-2 ${
                viewTab === "all" ? "bg-sky-500 text-navy-900 shadow-md font-extrabold" : "text-muted hover:text-ink"
              }`}
            >
              <span className="text-base">🖥️</span> Side-by-Side (Presenter)
            </button>
          </div>

          <div className="flex items-center gap-2">
            <Badge tone="sky">{phone === "ramesh" ? "🏪 Kirana Mode" : "✈️ Travel Mode"}</Badge>
            {config.demoMode && (
              <span className="hidden lg:inline text-[11px] text-muted">
                Press <b>1–8</b> for demo injects · <b>K</b>: Kill switch
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Main Content Area based on View Tab */}
      <main className="mx-auto max-w-7xl p-4">
        {viewTab === "assistant" && (
          <div className="flex flex-col lg:flex-row items-center lg:items-start justify-center gap-8 py-4">
            <div className="flex justify-center shrink-0">
              {phone === "ramesh" ? <MerchantChat persona="ramesh" height={680} /> : <TravelChat persona="arjun" height={680} />}
            </div>

            {/* Side Companion: Hardware Soundbox & One-Tap Test Triggers */}
            <div className="flex flex-col items-center gap-4 w-full max-w-[360px]">
              <div className="w-full">
                <div className="text-center mb-2">
                  <b className="text-sm font-black text-ink">🏪 Hardware Soundbox</b>
                  <p className="text-xs text-muted">Real audio feedback for merchants</p>
                </div>
                <SoundboxPanel persona="ramesh" compact />
              </div>

              {/* One-Tap Presenter Demo Scenarios */}
              <Card className="w-full !p-3.5 shadow-sm">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-muted">⚡ Quick Scenarios (One-Tap)</h3>
                  <span className="text-[10px] text-muted font-mono">ON-DEMAND</span>
                </div>
                <div className="flex flex-col gap-2">
                  {INJECTS.slice(0, 4).map((inj) => (
                    <button
                      key={inj.key}
                      onClick={() => {
                        if (inj.persona === "arjun") set({ stagePhone: "arjun" });
                        else set({ stagePhone: "ramesh" });
                        runInject(inj);
                      }}
                      className="flex items-center justify-between rounded-xl border border-line bg-card p-2 text-left hover:border-sky-500 hover:bg-sky-50/50 dark:hover:bg-sky-950/40 transition active:scale-[0.99]"
                    >
                      <div className="min-w-0 pr-2">
                        <b className="block text-xs text-ink">{inj.title}</b>
                        <span className="text-[11px] text-muted line-clamp-1">{inj.sub}</span>
                      </div>
                      <Badge tone="muted" className="shrink-0">{inj.persona}</Badge>
                    </button>
                  ))}
                </div>
              </Card>
            </div>
          </div>
        )}

        {viewTab === "trace" && (
          <div className="flex flex-col gap-4">
            {/* Enterprise Safety & Ops Controller */}
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-card border border-line p-3 shadow-sm">
              <div className="flex flex-wrap items-center gap-3">
                <KillSwitch />
                <Badge tone="sky">
                  {lastInject ? `${lastInject.label ?? (lastInject as any).title}${lastInject.outcome ? ` · ${lastInject.outcome}` : ""}` : "Waiting for trigger"}
                </Badge>
              </div>
              <span className="text-xs text-muted font-medium">
                Live Glass-Box Operations & Audit Controller
              </span>
            </div>

            {/* Live Metrics Telemetry inside the Tracing View */}
            <MetricsBar dense />

            {/* Quick inject toolbar inside Tracing view */}
            <div className="flex flex-wrap items-center gap-2 rounded-2xl bg-card border border-line p-2.5 shadow-sm">
              <span className="text-xs font-bold text-muted mr-1">Simulate Triggers:</span>
              {INJECTS.map((inj) => (
                <button
                  key={inj.key}
                  onClick={() => {
                    if (inj.persona === "arjun") set({ stagePhone: "arjun" });
                    else set({ stagePhone: "ramesh" });
                    runInject(inj);
                  }}
                  className="rounded-lg border border-line bg-bg px-2.5 py-1 text-xs font-medium text-ink hover:border-sky-500 hover:bg-sky-50 dark:hover:bg-sky-950 transition"
                >
                  <span className="font-bold text-sky-600 dark:text-sky-400 mr-1">{inj.key}:</span>
                  {inj.title}
                </button>
              ))}
            </div>

            <Card className="!p-4 shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <h2 className="text-xs font-bold uppercase tracking-wider text-muted">Saarthi Autonomous Agent Crew</h2>
                <Badge tone="ok">All Systems Active</Badge>
              </div>
              <AgentCrewBar />
            </Card>

            <Card className="!p-4 shadow-sm">
              <h2 className="mb-2 text-xs font-bold uppercase tracking-wider text-muted">
                Live Glass-Box Trace {selected && <span className="mono normal-case">· {selected}</span>}
              </h2>
              <div className="max-h-[380px] overflow-y-auto pr-1 scrollbar-thin">
                <TraceTimeline caseId={selected} max={18} />
              </div>
              <DecisionBox caseId={selected} />
            </Card>

            <div className="grid gap-4 md:grid-cols-2">
              <Card className="!p-4 shadow-sm">
                <h2 className="mb-2 text-xs font-bold uppercase tracking-wider text-muted">Human Escalation Queue</h2>
                <EscalationQueue compact onOpen={setOpen} />
              </Card>
              <Card className="!p-4 shadow-sm">
                <h2 className="mb-2 text-xs font-bold uppercase tracking-wider text-muted">Autonomous Learning (Repeat Cases)</h2>
                <EscalationChart height={180} />
              </Card>
            </div>
          </div>
        )}

        {viewTab === "all" && (
          <div className="flex flex-col gap-4">
            <MetricsBar dense />
            <div className="grid gap-4 xl:grid-cols-[auto_auto_minmax(0,1fr)]">
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
              </div>
            </div>
          </div>
        )}
      </main>

      <CaseDrawer esc={open} onClose={() => setOpen(null)} />
    </div>
  );
}
