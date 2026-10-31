import clsx from "clsx";
import { Home } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { Badge, Button, Dialog, SaarthiMark, SimulatedBadge, Switch } from "@/components/ui";
import { config } from "@/lib/config";
import { formatINR } from "@/lib/format";
import { LANG_LABEL } from "@/lib/i18n";
import { setKillSwitch } from "@/services/actions";
import { savePref, useStore } from "@/store";
import type { Lang } from "@/types/contracts";

/** Phone frame on desktop; full-bleed on real phones (< 640px). */
export function PhoneFrame({ children, className, height = 760 }: { children: ReactNode; className?: string; height?: number }) {
  return (
    <div
      className={clsx(
        "relative flex w-full flex-col overflow-hidden bg-card text-ink",
        "h-[100dvh] sm:h-[var(--ph)] sm:w-[390px] sm:max-w-full sm:shrink-0 sm:rounded-phone sm:border-[10px] sm:border-[#0B1020] sm:shadow-[0_20px_50px_rgba(7,26,74,.25)]",
        className,
      )}
      style={{ ["--ph" as any]: `min(${height}px, calc(100dvh - 2rem))` }}
    >
      {children}
    </div>
  );
}

export function ConnectionPill() {
  const apiStatus = useStore((s) => s.apiStatus);
  const sockets = useStore((s) => s.sockets);
  const statuses = Object.values(sockets);
  const mock = config.useMocks;
  let tone: "ok" | "warn" | "risk" = "ok";
  let label = "Live";
  if (mock) {
    tone = "ok";
    label = "Live";
  } else if (apiStatus === "down") {
    tone = "risk";
    label = "Offline";
  } else if (statuses.some((s) => s === "reconnecting" || s === "connecting")) {
    tone = "warn";
    label = "Connecting";
  } else if (statuses.some((s) => s === "offline")) {
    tone = "risk";
    label = "Offline";
  } else if (apiStatus === "unknown") {
    tone = "ok";
    label = "Live";
  }
  return (
    <span
      title={`API: ${apiStatus}`}
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-black border shadow-sm",
        tone === "ok" && "bg-emerald-100 text-emerald-950 border-emerald-300",
        tone === "warn" && "bg-amber-100 text-amber-950 border-amber-300",
        tone === "risk" && "bg-red-100 text-red-950 border-red-300",
      )}
    >
      <span className={clsx("h-2 w-2 rounded-full", tone === "ok" ? "bg-emerald-600 animate-pulse" : tone === "warn" ? "bg-amber-600" : "bg-red-600")} />
      {label}
    </span>
  );
}

/** Compact language chip ("हिं ▾"): always visible, one tap to switch. Auto = backend detects. */
export function LanguageChip({ dark }: { dark?: boolean }) {
  const lang = useStore((s) => s.lang);
  const set = useStore((s) => s.set);
  const [open, setOpen] = useState(false);
  const options: (Lang | null)[] = [null, "hi", "hinglish", "en"];
  const label = (o: Lang | null) => (o ? LANG_LABEL[o] : "Auto");
  return (
    <div className="relative">
      <button
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={`Reply language: ${label(lang)}`}
        onClick={() => setOpen(!open)}
        className={clsx(
          "min-h-[32px] whitespace-nowrap rounded-full px-3 text-xs font-black border transition shadow-sm",
          dark ? "bg-slate-800 text-white border-slate-700" : "bg-slate-100 text-slate-900 border-slate-300 hover:bg-slate-200"
        )}
      >
        🌐 {label(lang)} ▾
      </button>
      {open && (
        <ul role="listbox" aria-label="Reply language" className="absolute right-0 top-9 z-30 w-36 rounded-xl border border-line bg-white p-1 text-sm text-ink shadow-card" onMouseLeave={() => setOpen(false)}>
          {options.map((o) => (
            <li key={o ?? "auto"}>
              <button
                role="option"
                aria-selected={lang === o}
                onClick={() => {
                  set({ lang: o });
                  savePref("lang", o);
                  setOpen(false);
                }}
                className={clsx("block min-h-[40px] w-full rounded-lg px-2 text-left hover:bg-slate-100", lang === o && "font-bold text-sky-700")}
              >
                {o ? `${LANG_LABEL[o]} · ${o === "hi" ? "हिंदी" : o === "hinglish" ? "Hinglish" : "English"}` : "Auto (detect)"}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function KillSwitch({ compact }: { compact?: boolean }) {
  const control = useStore((s) => s.control);
  const [ask, setAsk] = useState<null | boolean>(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const active = control?.kill_switch_active ?? false;
  return (
    <div className="flex items-center gap-2 text-xs font-semibold">
      {!compact && <span>Autonomy</span>}
      <Switch checked={!active} onChange={(v) => setAsk(!v)} label={active ? "Autonomy paused — resume" : "Autonomy on — pause (kill switch)"} />
      <b className={active ? "text-red-300" : "text-emerald-300"}>{active ? "PAUSED" : "ON"}</b>
      <Dialog
        open={ask !== null}
        onClose={() => setAsk(null)}
        title={ask ? "Pause all autonomous actions?" : "Resume autonomy?"}
        footer={
          <>
            <Button onClick={() => setAsk(null)}>Cancel</Button>
            <Button
              variant={ask ? "danger" : "ok"}
              loading={busy}
              onClick={async () => {
                setBusy(true);
                await setKillSwitch(!!ask, reason || (ask ? "Paused from console" : "Resumed from console"));
                setBusy(false);
                setAsk(null);
                setReason("");
              }}
            >
              {ask ? "Pause autonomy" : "Resume"}
            </Button>
          </>
        }
      >
        <p className="mb-2 text-sm text-muted">
          {ask
            ? "Reads and explanations continue. Any action (loan applications, learned-playbook fixes) goes to a human. Logged in the audit chain."
            : "Saarthi will resume autonomous safe actions. Logged in the audit chain."}
        </p>
        <label className="text-xs font-semibold" htmlFor="ks-reason">Reason (audit log)</label>
        <input id="ks-reason" value={reason} onChange={(e) => setReason(e.target.value)} className="mt-1 w-full rounded-lg border border-line px-3 py-2" placeholder="e.g. incident drill" />
      </Dialog>
    </div>
  );
}

export function KillBanner() {
  const active = useStore((s) => s.control?.kill_switch_active);
  if (!active) return null;
  return (
    <div role="alert" className="animate-slidedown bg-risk px-4 py-2 text-center text-sm font-bold text-white">
      ⛔ Autonomy paused — every action now goes to a human
    </div>
  );
}

function CountUp({ value, prefix = "", suffix = "" }: { value: number; prefix?: string; suffix?: string }) {
  const prev = useRef(value);
  const [bump, setBump] = useState(false);
  useEffect(() => {
    if (value > prev.current) {
      setBump(true);
      const t = setTimeout(() => setBump(false), 1200);
      prev.current = value;
      return () => clearTimeout(t);
    }
    prev.current = value;
  }, [value]);
  return (
    <span className="relative">
      {prefix}
      {value}
      {suffix}
      {bump && <span className="anim absolute -right-6 -top-2 animate-floatup text-xs font-bold text-ok">+1</span>}
    </span>
  );
}

export function MetricsBar({ dense }: { dense?: boolean }) {
  const m = useStore((s) => s.metrics);
  const tiles: { label: string; value: ReactNode; hint?: string }[] = [
    { label: "Tickets deflected", value: m ? <CountUp value={m.tickets_deflected} /> : "—", hint: "check-ups resolved without a ticket" },
    { label: "Auto-resolved", value: m ? <CountUp value={m.auto_resolved} /> : "—" },
    { label: "Escalation rate", value: m ? `${m.escalation_rate_pct}%` : "—" },
    { label: "Support cost saved", value: m ? formatINR(m.support_cost_saved_inr) : "—" },
    { label: "Loan leads", value: m ? m.loan_leads : "—" },
  ];
  const tier0 = m?.tier_mix?.tier0?.pct;
  return (
    <div className={clsx("grid grid-cols-2 gap-2 border-b border-line bg-card/60 px-4 py-3 sm:grid-cols-3 lg:grid-cols-6")}>
      {tiles.map((t) => (
        <div key={t.label} className="rounded-xl border border-line bg-card px-3 py-2 shadow-sm" title={t.hint}>
          <small className="text-[11px] font-semibold text-muted">{t.label}</small>
          <b className={clsx("block text-ink", dense ? "text-lg" : "text-2xl")}>{t.value}</b>
        </div>
      ))}
      <div className="flex flex-col items-start justify-center gap-1 rounded-xl border border-dashed border-line bg-card px-3 py-2">
        <SimulatedBadge />
        <small className="text-[11px] text-muted">
          {m ? `Tier 0: ${tier0 ?? 0}% · LLM calls ${m.llm_calls} · avoided ${m.llm_calls_avoided}` : "metrics loading…"}
        </small>
      </div>
    </div>
  );
}

export function ThemeToggle({ dark }: { dark?: boolean }) {
  const theme = useStore((s) => s.theme);
  const set = useStore((s) => s.set);
  const toggle = () => {
    const next = theme === "dark" ? "light" : "dark";
    set({ theme: next });
    savePref("theme", next);
  };
  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
      className={clsx(
        "inline-flex h-8 w-8 items-center justify-center rounded-full border transition shadow-sm text-sm font-bold",
        dark ? "bg-slate-800 text-amber-300 border-slate-700 hover:bg-slate-700" : "bg-slate-100 text-slate-800 border-slate-300 hover:bg-slate-200"
      )}
      title={`Toggle theme (current: ${theme})`}
    >
      {theme === "dark" ? "☀️" : "🌙"}
    </button>
  );
}

export function BrandLogo({ size = 32, className }: { size?: number; className?: string }) {
  const [err, setErr] = useState(false);
  if (!err) {
    return (
      <img
        src="/assets/paytm_ai_logo.png"
        alt="Paytm loves AI"
        className={clsx("inline-block rounded-lg bg-white px-2 py-1 object-contain shadow-sm border border-slate-200", className)}
        style={{ height: size, width: "auto", minWidth: 80, maxHeight: 48 }}
        onError={() => setErr(true)}
      />
    );
  }
  return <SaarthiMark size={size} />;
}

export function TopBar({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <header className="sticky top-0 z-30 flex flex-wrap items-center gap-3 bg-white border-b border-slate-200 px-4 py-2.5 text-slate-900 shadow-sm">
      <Link to="/" className="flex items-center gap-2 font-black text-slate-900" aria-label="Home">
        <BrandLogo size={28} />
        <span className="text-base font-black text-slate-900">{title}</span>
      </Link>
      {children}
      <div className="ml-auto flex items-center gap-2">
        <ThemeToggle />
        <Link to="/" className="hidden items-center gap-1 text-xs font-black text-slate-800 hover:text-sky-600 sm:flex">
          <Home className="h-4 w-4" /> Home
        </Link>
      </div>
    </header>
  );
}

export function EnvBadge() {
  return <Badge tone="sim">{config.useMocks ? "MOCK · SIMULATED" : "DEMO · SIMULATED"}</Badge>;
}
