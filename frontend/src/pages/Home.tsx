import {
  ArrowRight,
  BarChart3,
  CheckCircle2,
  ChevronDown,
  Gauge,
  HelpCircle,
  Layers,
  Lock,
  Mic,
  Monitor,
  Plane,
  Radio,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  Smartphone,
  Sparkles,
  Volume2,
  Zap,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { BrandLogo, ConnectionPill, LanguageChip, ThemeToggle } from "@/components/layout";
import { Badge, Button, Card, SimulatedBadge } from "@/components/ui";
import { api } from "@/lib/api";
import { config } from "@/lib/config";
import { formatINR } from "@/lib/format";
import { t } from "@/lib/i18n";
import { resetDemo, runCheckup } from "@/services/actions";
import { useStore } from "@/store";
import type { Metrics } from "@/types/contracts";

const DEMO_TILES = [
  { to: "/stage", icon: Monitor, title: "Demo Stage", sub: "Phone + Soundbox + live agent crew on projector", badge: "Live" },
  { to: "/merchant", icon: Smartphone, title: "Saarthi Care", sub: "Ramesh kirana chat · zero-ticket settlements", badge: "Merchant" },
  { to: "/travel", icon: Plane, title: "Saarthi Travel", sub: "Autonomous flight roadmap & 'Review and Pay'", badge: "Consumer" },
  { to: "/soundbox", icon: Radio, title: "Soundbox", sub: "Chime + neural Indic voice + LED hardware state", badge: "Hardware" },
  { to: "/console", icon: ShieldCheck, title: "Ops Console", sub: "Glass-box trace, escalations, kill switch", badge: "Ops" },
  { to: "/inject", icon: Zap, title: "Inject Scenarios", sub: "Trigger mock anomalies, network faults, bank disputes", badge: "Testing" },
  { to: "/eval", icon: BarChart3, title: "Benchmark Eval", sub: "Gold-standard test suites & accuracy metrics", badge: "Metrics" },
];

export default function Home() {
  const navigate = useNavigate();
  const lang = useStore((s) => s.lang);
  const apiStatus = useStore((s) => s.apiStatus);
  const storeMetrics = useStore((s) => s.metrics);
  const elderMode = useStore((s) => s.elderMode);
  const setStore = useStore((s) => s.set);

  const [metrics, setMetrics] = useState<Metrics | null>(storeMetrics);
  const [metricsLoading, setMetricsLoading] = useState(false);
  const [metricsError, setMetricsError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [openFaq, setOpenFaq] = useState<number | null>(0);
  const [bgFailed, setBgFailed] = useState(false);

  // Fetch metrics on-demand upon component mount (no auto-polling loops!)
  useEffect(() => {
    let active = true;
    const fetchMetrics = async () => {
      setMetricsLoading(true);
      setMetricsError(null);
      try {
        const data = await api.metrics();
        if (active) {
          setMetrics(data);
          setStore({ metrics: data });
        }
      } catch (err: any) {
        if (active) {
          setMetricsError(err?.message || "Failed to load metrics");
        }
      } finally {
        if (active) setMetricsLoading(false);
      }
    };
    fetchMetrics();
    return () => {
      active = false;
    };
  }, [setStore]);

  const handleSettlementCta = async () => {
    // Navigates directly to merchant chat and triggers settlement check
    navigate("/merchant");
    setTimeout(() => {
      runCheckup("ramesh", "settlement");
    }, 150);
  };

  const handleVoiceCta = () => {
    navigate("/merchant");
  };

  return (
    <div className="min-h-screen bg-bg text-ink transition-colors duration-200">
      {/* 1. STICKY NAVBAR */}
      <header className="sticky top-0 z-40 border-b border-line/60 bg-navy-900/95 backdrop-blur-md px-4 py-3 text-white shadow-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-3">
          <Link to="/" className="flex items-center gap-2.5 transition hover:opacity-95" aria-label="Saarthi Home">
            <BrandLogo size={34} />
            <div className="flex flex-col">
              <span className="text-lg font-black tracking-tight text-white flex items-center gap-1.5">
                Saarthi
                <span className="rounded-md bg-sky-500/20 px-1.5 py-0.5 text-[10px] font-extrabold text-sky-300 border border-sky-400/30">
                  AI Teammate
                </span>
              </span>
              <span className="hidden sm:inline text-[10.5px] text-slate-300 font-medium">Paytm AI Hackathon</span>
            </div>
          </Link>

          <div className="flex items-center gap-2 sm:gap-3">
            <ConnectionPill />
            <LanguageChip dark />
            <ThemeToggle dark />
            
            <button
              onClick={() => setStore({ elderMode: !elderMode })}
              title="Elder Mode: Increases typography size & touch targets"
              className={`hidden md:inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-semibold border transition ${
                elderMode ? "bg-amber-400 text-navy-900 border-amber-300" : "bg-white/10 text-white border-white/20 hover:bg-white/20"
              }`}
            >
              👵 {t("elder", lang)} {elderMode ? "ON" : "OFF"}
            </button>

            <Link
              to="/stage"
              className="inline-flex items-center gap-1.5 rounded-btn bg-sky-500 px-3.5 py-1.5 text-xs sm:text-sm font-bold text-navy-900 shadow hover:bg-sky-400 transition"
            >
              <Sparkles className="h-4 w-4" />
              <span>{t("landing.hero.cta.try", lang)}</span>
            </Link>
          </div>
        </div>
      </header>

      {/* 2. HERO SECTION WITH ATTACHED IMAGE FULL-BLEED BACKGROUND */}
      <section className="relative overflow-hidden border-b border-line/60 bg-navy-900 text-white">
        {/* Full-bleed background texture */}
        <div className="absolute inset-0 z-0">
          {!bgFailed ? (
            <img
              src="/assets/paytm_ai_hero.jpg"
              alt="Paytm Loves AI background"
              onError={() => setBgFailed(true)}
              className="h-full w-full object-cover object-center opacity-30 mix-blend-luminosity filter blur-[1px] transform scale-105"
            />
          ) : (
            <div className="h-full w-full rangoli-pattern opacity-40" />
          )}
          {/* Dark gradient overlay for ultra-crisp readable typography */}
          <div className="absolute inset-0 bg-gradient-to-b from-navy-900/90 via-navy-900/85 to-navy-900/98" />
          <div className="absolute inset-0 bg-radial-gradient from-transparent via-navy-900/60 to-navy-900" />
        </div>

        <div className="relative z-10 mx-auto max-w-6xl px-4 py-16 sm:py-24 lg:py-28">
          <div className="inline-flex items-center gap-2 rounded-full border border-sky-400/30 bg-sky-500/10 px-3.5 py-1 text-xs font-semibold text-sky-300 backdrop-blur-sm mb-6">
            <span className="flex h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>Paytm ❤️ AI · Autonomous AI Teammates (Track 3)</span>
          </div>

          <h1 className="max-w-4xl text-3xl font-extrabold tracking-tight sm:text-5xl lg:text-6xl text-white leading-tight">
            {t("landing.hero.title", lang)}
          </h1>

          <p className="mt-5 max-w-2xl text-base sm:text-lg text-slate-300 leading-relaxed">
            {t("landing.hero.sub", lang)}
          </p>

          {/* Action CTAs */}
          <div className="mt-8 flex flex-wrap items-center gap-3.5">
            <Button
              variant="sky"
              size="lg"
              onClick={handleSettlementCta}
              className="font-bold text-navy-900 shadow-lg shadow-sky-500/20 hover:scale-[1.02] active:scale-95 transition"
            >
              💰 {t("landing.hero.cta.settlement", lang)}
            </Button>

            <Button
              variant="secondary"
              size="lg"
              onClick={handleVoiceCta}
              className="border-white/30 bg-white/10 text-white backdrop-blur-sm hover:bg-white/20 active:scale-95 transition font-semibold"
            >
              <Mic className="h-5 w-5 text-sky-400" />
              {t("landing.hero.cta.voice", lang)}
            </Button>

            <Link
              to="/travel"
              className="inline-flex items-center gap-2 rounded-btn border border-white/20 bg-transparent px-4 py-3 text-sm font-semibold text-slate-200 hover:bg-white/10 transition"
            >
              <Plane className="h-4 w-4 text-sky-300" />
              <span>{t("landing.travel.cta", lang)}</span>
            </Link>
          </div>

          {/* Trust Badges */}
          <div className="mt-12 flex flex-wrap items-center gap-3 pt-6 border-t border-white/10 text-xs text-slate-300">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-white/5 border border-white/10 px-3 py-1">
              <ShieldCheck className="h-4 w-4 text-emerald-400" />
              {t("landing.badge.humanApproval", lang)}
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-white/5 border border-white/10 px-3 py-1">
              <Layers className="h-4 w-4 text-sky-400" />
              {t("landing.badge.auditLog", lang)}
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-white/5 border border-white/10 px-3 py-1">
              <ShieldAlert className="h-4 w-4 text-amber-400" />
              {t("landing.badge.killSwitch", lang)}
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 border border-emerald-400/20 px-3 py-1 text-emerald-300 font-semibold">
              🔒 {t("landing.badge.onDemand", lang)}
            </span>
          </div>
        </div>
      </section>

      {/* 3. PROBLEM & WHY CHATBOTS FAIL IN BHARAT */}
      <section className="py-16 sm:py-20 border-b border-line bg-card">
        <div className="mx-auto max-w-6xl px-4">
          <div className="text-center max-w-2xl mx-auto">
            <Badge tone="risk">The Problem</Badge>
            <h2 className="mt-2 text-2xl sm:text-3xl font-extrabold text-ink">
              {t("landing.problem.title", lang)}
            </h2>
            <p className="mt-2 text-muted text-sm sm:text-base">
              {t("landing.problem.sub", lang)}
            </p>
          </div>

          <div className="mt-10 grid gap-6 md:grid-cols-2">
            <div className="rounded-card border border-red-200 dark:border-red-900/40 bg-red-50/50 dark:bg-red-950/20 p-6 shadow-sm">
              <div className="flex items-center gap-3">
                <div className="grid h-10 w-10 place-items-center rounded-xl bg-red-100 dark:bg-red-900/40 text-red-600 dark:text-red-400">
                  <ShieldAlert className="h-6 w-6" />
                </div>
                <div>
                  <h3 className="font-bold text-red-900 dark:text-red-300">{t("landing.problem.botTitle", lang)}</h3>
                  <small className="text-red-700/80 dark:text-red-400/80">Static & Disconnected</small>
                </div>
              </div>
              <p className="mt-4 text-sm text-red-800 dark:text-red-300/90 leading-relaxed">
                {t("landing.problem.botDesc", lang)}
              </p>
              <ul className="mt-4 space-y-2 text-xs text-red-700 dark:text-red-400">
                <li className="flex items-center gap-1.5">❌ Creates support tickets instead of answering</li>
                <li className="flex items-center gap-1.5">❌ Cannot check hardware status of Soundbox</li>
                <li className="flex items-center gap-1.5">❌ Invents settlement amounts (hallucination)</li>
              </ul>
            </div>

            <div className="rounded-card border border-emerald-200 dark:border-emerald-900/40 bg-emerald-50/50 dark:bg-emerald-950/20 p-6 shadow-sm">
              <div className="flex items-center gap-3">
                <div className="grid h-10 w-10 place-items-center rounded-xl bg-emerald-100 dark:bg-emerald-900/40 text-emerald-600 dark:text-emerald-400">
                  <CheckCircle2 className="h-6 w-6" />
                </div>
                <div>
                  <h3 className="font-bold text-emerald-900 dark:text-emerald-300">{t("landing.problem.saarthiTitle", lang)}</h3>
                  <small className="text-emerald-700/80 dark:text-emerald-400/80">Autonomous & Accountable</small>
                </div>
              </div>
              <p className="mt-4 text-sm text-emerald-800 dark:text-emerald-300/90 leading-relaxed">
                {t("landing.problem.saarthiDesc", lang)}
              </p>
              <ul className="mt-4 space-y-2 text-xs text-emerald-700 dark:text-emerald-400">
                <li className="flex items-center gap-1.5">✅ Zero-ticket instant ledger reconciliation</li>
                <li className="flex items-center gap-1.5">✅ Live Soundbox SIM/battery hardware diagnostic</li>
                <li className="flex items-center gap-1.5">✅ Transparent human escalation with 1-page summary</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* 4. HOW IT WORKS: 5 TRANSPARENT STEPS */}
      <section className="py-16 sm:py-20 border-b border-line bg-bg">
        <div className="mx-auto max-w-6xl px-4">
          <div className="text-center max-w-2xl mx-auto">
            <Badge tone="sky">Architecture</Badge>
            <h2 className="mt-2 text-2xl sm:text-3xl font-extrabold text-ink">
              {t("landing.how.title", lang)}
            </h2>
            <p className="mt-2 text-muted text-sm sm:text-base">
              {t("landing.how.sub", lang)}
            </p>
          </div>

          <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            {[
              { num: "01", title: t("landing.how.step1.title", lang), desc: t("landing.how.step1.desc", lang), icon: Mic },
              { num: "02", title: t("landing.how.step2.title", lang), desc: t("landing.how.step2.desc", lang), icon: Zap },
              { num: "03", title: t("landing.how.step3.title", lang), desc: t("landing.how.step3.desc", lang), icon: RefreshCw },
              { num: "04", title: t("landing.how.step4.title", lang), desc: t("landing.how.step4.desc", lang), icon: ShieldCheck },
              { num: "05", title: t("landing.how.step5.title", lang), desc: t("landing.how.step5.desc", lang), icon: Sparkles },
            ].map((step) => (
              <div
                key={step.num}
                className="relative rounded-card border border-line bg-card p-5 shadow-sm hover:border-sky-500/50 hover:-translate-y-1 transition duration-200"
              >
                <div className="flex items-center justify-between">
                  <span className="mono text-xs font-bold text-sky-500">{step.num}</span>
                  <step.icon className="h-5 w-5 text-muted" />
                </div>
                <h3 className="mt-3 text-base font-bold text-ink">{step.title}</h3>
                <p className="mt-2 text-xs text-muted leading-relaxed">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 5. PRODUCT PILLARS: SAARTHI CARE & SAARTHI TRAVEL */}
      <section className="py-16 sm:py-20 border-b border-line bg-card">
        <div className="mx-auto max-w-6xl px-4">
          <div className="text-center max-w-2xl mx-auto">
            <Badge tone="ok">Two Faces · One Multi-Agent Core</Badge>
            <h2 className="mt-2 text-2xl sm:text-3xl font-extrabold text-ink">
              Saarthi Care & Saarthi Travel
            </h2>
            <p className="mt-2 text-muted text-sm sm:text-base">
              Built on a shared multi-agent backbone: Captain, Guardian, Diagnostician, and Handover.
            </p>
          </div>

          <div className="mt-12 grid gap-8 md:grid-cols-2">
            {/* Saarthi Care */}
            <div className="group rounded-card border border-line bg-gradient-to-br from-card via-card to-sky-50/30 dark:to-sky-950/20 p-6 sm:p-8 shadow-card flex flex-col justify-between hover:border-sky-500 transition">
              <div>
                <div className="flex items-center justify-between">
                  <Badge tone="sky">{t("landing.care.tag", lang)}</Badge>
                  <span className="text-2xl">🏪</span>
                </div>
                <h3 className="mt-4 text-2xl font-black text-ink">{t("landing.care.title", lang)}</h3>
                <p className="mt-2 text-sm text-muted leading-relaxed">
                  {t("landing.care.desc", lang)}
                </p>
                <div className="mt-6 space-y-2.5 text-xs text-ink">
                  <div className="flex items-center gap-2 rounded-lg bg-bg p-2.5 border border-line">
                    <span className="font-bold text-sky-600 dark:text-sky-400">💰 Settlement Breakdown</span>
                    <span className="text-muted ml-auto">Net, MDR, Pending</span>
                  </div>
                  <div className="flex items-center gap-2 rounded-lg bg-bg p-2.5 border border-line">
                    <span className="font-bold text-emerald-600 dark:text-emerald-400">🔊 Soundbox Diagnostics</span>
                    <span className="text-muted ml-auto">Battery, SIM, Signal</span>
                  </div>
                  <div className="flex items-center gap-2 rounded-lg bg-bg p-2.5 border border-line">
                    <span className="font-bold text-amber-600 dark:text-amber-400">🤝 Consent-First Loans</span>
                    <span className="text-muted ml-auto">Two-step confirmation</span>
                  </div>
                </div>
              </div>
              <div className="mt-8 pt-4 border-t border-line flex items-center justify-between">
                <Link
                  to="/merchant"
                  className="inline-flex items-center gap-2 font-bold text-sm text-sky-600 dark:text-sky-400 hover:gap-3 transition"
                >
                  <span>{t("landing.care.cta", lang)}</span>
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <Link to="/soundbox" className="text-xs text-muted hover:text-ink">
                  View Soundbox →
                </Link>
              </div>
            </div>

            {/* Saarthi Travel */}
            <div className="group rounded-card border border-line bg-gradient-to-br from-card via-card to-blue-50/30 dark:to-blue-950/20 p-6 sm:p-8 shadow-card flex flex-col justify-between hover:border-sky-500 transition">
              <div>
                <div className="flex items-center justify-between">
                  <Badge tone="ok">{t("landing.travel.tag", lang)}</Badge>
                  <span className="text-2xl">✈️</span>
                </div>
                <h3 className="mt-4 text-2xl font-black text-ink">{t("landing.travel.title", lang)}</h3>
                <p className="mt-2 text-sm text-muted leading-relaxed">
                  {t("landing.travel.desc", lang)}
                </p>
                <div className="mt-6 space-y-2.5 text-xs text-ink">
                  <div className="flex items-center gap-2 rounded-lg bg-bg p-2.5 border border-line">
                    <span className="font-bold text-sky-600 dark:text-sky-400">🗺️ 4-Stage Travel Roadmap</span>
                    <span className="text-muted ml-auto">Search, Rank, Present</span>
                  </div>
                  <div className="flex items-center gap-2 rounded-lg bg-bg p-2.5 border border-line">
                    <span className="font-bold text-emerald-600 dark:text-emerald-400">🏆 3 Ranked Options</span>
                    <span className="text-muted ml-auto">Cheapest, Fastest, Recommended</span>
                  </div>
                  <div className="flex items-center gap-2 rounded-lg bg-bg p-2.5 border border-line">
                    <span className="font-bold text-indigo-600 dark:text-indigo-400">🛡️ Strict Human Handoff</span>
                    <span className="text-muted ml-auto">"Review & Pay" only</span>
                  </div>
                </div>
              </div>
              <div className="mt-8 pt-4 border-t border-line flex items-center justify-between">
                <Link
                  to="/travel"
                  className="inline-flex items-center gap-2 font-bold text-sm text-sky-600 dark:text-sky-400 hover:gap-3 transition"
                >
                  <span>{t("landing.travel.cta", lang)}</span>
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <span className="text-xs text-muted">Never pays automatically</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 6. INDIC VOICE & ACCESSIBILITY SECTION */}
      <section className="py-16 sm:py-20 border-b border-line bg-bg">
        <div className="mx-auto max-w-6xl px-4">
          <div className="rounded-2xl border border-line bg-gradient-to-r from-navy-900 to-navy-700 p-8 sm:p-12 text-white shadow-xl relative overflow-hidden">
            <div className="absolute right-0 top-0 bottom-0 w-1/3 opacity-10 rangoli-pattern pointer-events-none" />
            <div className="max-w-2xl relative z-10">
              <Badge tone="sky">Inclusivity</Badge>
              <h2 className="mt-2 text-2xl sm:text-4xl font-extrabold text-white">
                {t("landing.voice.title", lang)}
              </h2>
              <p className="mt-3 text-sm sm:text-base text-slate-300">
                {t("landing.voice.sub", lang)}
              </p>

              <div className="mt-6 flex flex-wrap gap-2 text-xs">
                <span className="rounded-full bg-white/10 px-3 py-1 font-semibold border border-white/20">
                  🇮🇳 {t("landing.voice.tag1", lang)}
                </span>
                <span className="rounded-full bg-white/10 px-3 py-1 font-semibold border border-white/20">
                  👓 {t("landing.voice.tag2", lang)}
                </span>
                <span className="rounded-full bg-white/10 px-3 py-1 font-semibold border border-white/20">
                  ⚡ {t("landing.voice.tag3", lang)}
                </span>
              </div>

              <div className="mt-8 flex flex-wrap gap-3">
                <Link
                  to="/merchant"
                  className="inline-flex items-center gap-2 rounded-btn bg-sky-500 px-4 py-2.5 text-sm font-bold text-navy-900 shadow hover:bg-sky-400 transition"
                >
                  <Volume2 className="h-4 w-4" />
                  Try Voice Flow
                </Link>
                <button
                  onClick={() => setStore({ elderMode: !elderMode })}
                  className="inline-flex items-center gap-2 rounded-btn border border-white/30 bg-white/10 px-4 py-2.5 text-sm font-semibold text-white hover:bg-white/20 transition"
                >
                  Toggle Elder Mode ({elderMode ? "Active" : "Standard"})
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 7. ZERO-TRUST SECURITY & SAFETY */}
      <section className="py-16 sm:py-20 border-b border-line bg-card">
        <div className="mx-auto max-w-6xl px-4">
          <div className="text-center max-w-2xl mx-auto">
            <Badge tone="warn">Security & Control</Badge>
            <h2 className="mt-2 text-2xl sm:text-3xl font-extrabold text-ink">
              {t("landing.trust.title", lang)}
            </h2>
            <p className="mt-2 text-muted text-sm sm:text-base">
              {t("landing.trust.sub", lang)}
            </p>
          </div>

          <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-card border border-line bg-bg p-5 shadow-sm">
              <div className="grid h-10 w-10 place-items-center rounded-xl bg-sky-100 dark:bg-sky-950/40 text-sky-600 dark:text-sky-400">
                <Zap className="h-5 w-5" />
              </div>
              <h3 className="mt-3 text-base font-bold text-ink">Strictly On-Demand</h3>
              <p className="mt-1.5 text-xs text-muted leading-relaxed">{t("landing.trust.point1", lang)}</p>
            </div>

            <div className="rounded-card border border-line bg-bg p-5 shadow-sm">
              <div className="grid h-10 w-10 place-items-center rounded-xl bg-emerald-100 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400">
                <Lock className="h-5 w-5" />
              </div>
              <h3 className="mt-3 text-base font-bold text-ink">Human Approval</h3>
              <p className="mt-1.5 text-xs text-muted leading-relaxed">{t("landing.trust.point2", lang)}</p>
            </div>

            <div className="rounded-card border border-line bg-bg p-5 shadow-sm">
              <div className="grid h-10 w-10 place-items-center rounded-xl bg-indigo-100 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400">
                <Layers className="h-5 w-5" />
              </div>
              <h3 className="mt-3 text-base font-bold text-ink">Cryptographic Hash</h3>
              <p className="mt-1.5 text-xs text-muted leading-relaxed">{t("landing.trust.point3", lang)}</p>
            </div>

            <div className="rounded-card border border-line bg-bg p-5 shadow-sm">
              <div className="grid h-10 w-10 place-items-center rounded-xl bg-red-100 dark:bg-red-950/40 text-red-600 dark:text-red-400">
                <ShieldAlert className="h-5 w-5" />
              </div>
              <h3 className="mt-3 text-base font-bold text-ink">Global Kill Switch</h3>
              <p className="mt-1.5 text-xs text-muted leading-relaxed">{t("landing.trust.point4", lang)}</p>
            </div>
          </div>
        </div>
      </section>

      {/* 8. TELEMETRY & LIVE IMPACT METRICS (from /metrics endpoint) */}
      <section className="py-16 sm:py-20 border-b border-line bg-bg">
        <div className="mx-auto max-w-6xl px-4">
          <div className="flex flex-wrap items-end justify-between gap-4 mb-8">
            <div>
              <div className="flex items-center gap-2">
                <Badge tone="sim">SIMULATED</Badge>
                <span className="text-xs text-muted">GET /api/v1/metrics</span>
              </div>
              <h2 className="mt-2 text-2xl sm:text-3xl font-extrabold text-ink">
                {t("landing.metrics.title", lang)}
              </h2>
              <p className="text-xs sm:text-sm text-muted">
                {t("landing.metrics.sub", lang)}
              </p>
            </div>
            <SimulatedBadge />
          </div>

          {/* Metrics loading/error/data view */}
          {metricsLoading && !metrics ? (
            <div className="grid h-36 place-items-center rounded-card border border-line bg-card p-6 text-muted">
              <RefreshCw className="h-6 w-6 animate-spin text-sky-500" />
              <span className="mt-2 text-xs">Fetching telemetry metrics…</span>
            </div>
          ) : metricsError && !metrics ? (
            <div className="rounded-card border border-red-200 bg-red-50 p-6 text-center text-xs text-red-700">
              <p>Could not fetch /metrics ({metricsError}). Backend might be offline.</p>
              <button
                onClick={() => window.location.reload()}
                className="mt-2 underline font-semibold"
              >
                Retry
              </button>
            </div>
          ) : metrics ? (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
              <div className="rounded-xl border border-line bg-card p-4 shadow-sm">
                <small className="text-[11px] font-semibold text-muted">Tickets Deflected</small>
                <b className="mt-1 block text-2xl font-black text-sky-600 dark:text-sky-400">
                  {metrics.tickets_deflected}
                </b>
                <span className="text-[10px] text-muted">zero-ticket resolved</span>
              </div>

              <div className="rounded-xl border border-line bg-card p-4 shadow-sm">
                <small className="text-[11px] font-semibold text-muted">Auto Resolved</small>
                <b className="mt-1 block text-2xl font-black text-emerald-600 dark:text-emerald-400">
                  {metrics.auto_resolved}
                </b>
                <span className="text-[10px] text-muted">instant closures</span>
              </div>

              <div className="rounded-xl border border-line bg-card p-4 shadow-sm">
                <small className="text-[11px] font-semibold text-muted">Escalation Rate</small>
                <b className="mt-1 block text-2xl font-black text-navy-700 dark:text-slate-200">
                  {metrics.escalation_rate_pct}%
                </b>
                <span className="text-[10px] text-muted">to human ops</span>
              </div>

              <div className="rounded-xl border border-line bg-card p-4 shadow-sm">
                <small className="text-[11px] font-semibold text-muted">Support Saved</small>
                <b className="mt-1 block text-2xl font-black text-indigo-600 dark:text-indigo-400">
                  {formatINR(metrics.support_cost_saved_inr)}
                </b>
                <span className="text-[10px] text-muted">est. operational</span>
              </div>

              <div className="rounded-xl border border-line bg-card p-4 shadow-sm">
                <small className="text-[11px] font-semibold text-muted">Tier 0 Rules</small>
                <b className="mt-1 block text-2xl font-black text-amber-600 dark:text-amber-400">
                  {metrics.tier_mix?.tier0?.pct ?? 0}%
                </b>
                <span className="text-[10px] text-muted">zero-LLM cost</span>
              </div>

              <div className="rounded-xl border border-line bg-card p-4 shadow-sm">
                <small className="text-[11px] font-semibold text-muted">LLM Avoided</small>
                <b className="mt-1 block text-2xl font-black text-emerald-600 dark:text-emerald-400">
                  {metrics.llm_calls_avoided}
                </b>
                <span className="text-[10px] text-muted">calls saved</span>
              </div>
            </div>
          ) : null}

          <p className="mt-3 text-[11px] text-muted italic">
            * {t("landing.metrics.disclaimer", lang)}
          </p>
        </div>
      </section>

      {/* 9. DEMO HUB & EXPLORER TILES (PRESERVING ALL EXISTING ROUTES) */}
      <section className="py-16 sm:py-20 border-b border-line bg-card">
        <div className="mx-auto max-w-6xl px-4">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-8">
            <div>
              <Badge tone="sky">Interactive Hub</Badge>
              <h2 className="mt-2 text-2xl sm:text-3xl font-extrabold text-ink">
                Hackathon Demo Explorer
              </h2>
              <p className="text-xs sm:text-sm text-muted">
                Direct access to every persona, phone simulator, hardware Soundbox, and ops view.
              </p>
            </div>
          </div>

          <div className="grid gap-3.5 sm:grid-cols-2 lg:grid-cols-4">
            {DEMO_TILES.map((t) => (
              <Link
                key={t.to}
                to={t.to}
                className="group relative rounded-card border border-line bg-bg p-5 shadow-sm transition hover:-translate-y-1 hover:border-sky-500 hover:shadow-card flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <t.icon className="h-6 w-6 text-sky-500 group-hover:scale-110 transition" />
                    <span className="rounded-full bg-slate-200/70 dark:bg-slate-800 px-2 py-0.5 text-[10px] font-bold text-muted">
                      {t.badge}
                    </span>
                  </div>
                  <b className="mt-3 block text-base text-ink group-hover:text-sky-600 dark:group-hover:text-sky-400 transition">
                    {t.title}
                  </b>
                  <p className="mt-1 text-xs text-muted leading-relaxed">{t.sub}</p>
                </div>
                <div className="mono mt-4 text-[11px] font-semibold text-slate-400 group-hover:text-sky-600">
                  {t.to} →
                </div>
              </Link>
            ))}

            {/* System Status Tile */}
            <Card className="flex flex-col justify-between gap-3 bg-bg">
              <div>
                <div className="flex items-center justify-between">
                  <Gauge className="h-6 w-6 text-sky-500" />
                  <span className="rounded-full bg-slate-200/70 dark:bg-slate-800 px-2 py-0.5 text-[10px] font-bold text-muted">
                    Engine
                  </span>
                </div>
                <b className="mt-3 block text-base text-ink">Backend & Database</b>
                <div className="mt-2 flex flex-wrap gap-1.5 text-xs">
                  <Badge tone={apiStatus === "ok" ? "ok" : apiStatus === "down" ? "risk" : "warn"}>
                    API {apiStatus}
                  </Badge>
                  <Badge tone={config.useMocks ? "warn" : "sky"}>
                    {config.useMocks ? "Mock Adapter" : "Live FastAPI"}
                  </Badge>
                </div>
                <small className="mono mt-2 block break-all text-[11px] text-muted">
                  {config.apiUrl}
                </small>
              </div>

              <Button
                variant="danger"
                size="sm"
                loading={busy}
                onClick={async () => {
                  setBusy(true);
                  await resetDemo();
                  setBusy(false);
                }}
                className="w-full text-xs"
              >
                Reset Demo Database
              </Button>
            </Card>
          </div>
        </div>
      </section>

      {/* 10. FREQUENTLY ASKED QUESTIONS */}
      <section className="py-16 sm:py-20 border-b border-line bg-bg">
        <div className="mx-auto max-w-4xl px-4">
          <div className="text-center max-w-xl mx-auto mb-10">
            <Badge tone="sky">Clarity</Badge>
            <h2 className="mt-2 text-2xl sm:text-3xl font-extrabold text-ink">
              {t("landing.faq.title", lang)}
            </h2>
            <p className="mt-2 text-muted text-sm">
              {t("landing.faq.sub", lang)}
            </p>
          </div>

          <div className="space-y-3">
            {[
              { q: t("landing.faq.q1", lang), a: t("landing.faq.a1", lang) },
              { q: t("landing.faq.q2", lang), a: t("landing.faq.a2", lang) },
              { q: t("landing.faq.q3", lang), a: t("landing.faq.a3", lang) },
              { q: t("landing.faq.q4", lang), a: t("landing.faq.a4", lang) },
            ].map((faq, idx) => (
              <div
                key={idx}
                className="rounded-xl border border-line bg-card overflow-hidden shadow-sm"
              >
                <button
                  onClick={() => setOpenFaq(openFaq === idx ? null : idx)}
                  className="flex w-full items-center justify-between p-4 text-left font-bold text-sm sm:text-base text-ink hover:bg-slate-50 dark:hover:bg-slate-800/40 transition"
                >
                  <span className="flex items-center gap-2.5">
                    <HelpCircle className="h-4 w-4 text-sky-500 shrink-0" />
                    {faq.q}
                  </span>
                  <ChevronDown
                    className={`h-4 w-4 text-muted transition-transform duration-200 ${
                      openFaq === idx ? "rotate-180" : ""
                    }`}
                  />
                </button>
                {openFaq === idx && (
                  <div className="px-4 pb-4 pt-1 text-xs sm:text-sm text-muted border-t border-line/60 bg-slate-50/50 dark:bg-slate-900/30 leading-relaxed">
                    {faq.a}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 11. FOOTER WITH CREDITS */}
      <footer className="bg-navy-900 text-slate-300 py-12 border-t border-line/40">
        <div className="mx-auto max-w-6xl px-4 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <BrandLogo size={32} />
            <div>
              <b className="block text-white text-base">Saarthi · Paytm Loves AI</b>
              <small className="text-slate-400 text-xs">
                {t("landing.footer.builtFor", lang)}
              </small>
            </div>
          </div>

          <div className="text-center md:text-right text-xs text-slate-400 space-y-1">
            <p>{t("landing.footer.credits", lang)}</p>
            <p className="text-slate-500">
              Strictly on-demand · Zero telemetry tracking · Hackathon simulated evaluation
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
