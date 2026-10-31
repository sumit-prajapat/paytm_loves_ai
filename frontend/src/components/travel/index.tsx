import clsx from "clsx";
import { AlertTriangle, CheckCircle2, ChevronDown, Lock, Plane, ShieldCheck, Volume2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { ScoreBars } from "@/components/console";
import { Badge, Button } from "@/components/ui";
import { api, errorText } from "@/lib/api";
import { playBlob, unlockAudio } from "@/lib/audio";
import { formatDate, formatDuration, formatINR } from "@/lib/format";
import { t } from "@/lib/i18n";
import { toast } from "@/lib/toast";
import { useStore } from "@/store";
import type { BookingSummary, FlightOption, Lang, PersonaId, TravelSlots, TurnResult } from "@/types/contracts";

const CITY: Record<string, string> = { DEL: "Delhi", BOM: "Mumbai", BLR: "Bengaluru", MAA: "Chennai", CCU: "Kolkata", HYD: "Hyderabad", GOI: "Goa", PNQ: "Pune", AMD: "Ahmedabad", JAI: "Jaipur", LKO: "Lucknow", PAT: "Patna", COK: "Kochi", VNS: "Varanasi", IXC: "Chandigarh" };
const WINDOW: Record<string, string> = { morning: "Subah 5–12", afternoon: "Dopahar 12–5", evening: "Shaam 5–9", night: "Raat 9–12" };
const PREF: Record<string, string> = { cheap: "Sasta", fast: "Jaldi", comfort: "Aaraam", balanced: "Sasta + Jaldi" };
const LABEL: Record<string, { text: string; tone: string }> = {
  BEST_BALANCE: { text: "⭐ Best balance · recommended", tone: "text-sky-700" },
  CHEAPEST: { text: "💸 Sabse sasta", tone: "text-ok" },
  FASTEST: { text: "⚡ Sabse jaldi", tone: "text-amber-600" },
};
const RISK: Record<string, string> = { non_refundable: "Non-refundable fare", has_stops: "Stop / layover hai" };

export function SlotChips({ slots, missing }: { slots: TravelSlots; missing?: string | null }) {
  const chip = (key: string, label?: string) => (
    <span key={key} className={clsx("rounded-full border px-2.5 py-1 text-[12.5px]", label ? "border-sky-200 bg-sky-100 font-semibold text-sky-900" : "border-dashed border-slate-400 text-muted", missing === key && "ring-2 ring-sky-500")}>
      {label ?? `? ${key}`}
    </span>
  );
  return (
    <div className="w-full rounded-2xl border border-line bg-card text-ink p-3 shadow-sm">
      <h4 className="mb-2 text-sm font-bold text-ink">🧭 Maine ye samjha</h4>
      <div className="flex flex-wrap items-center gap-1.5">
        {chip("origin", slots.origin ? `${CITY[slots.origin] ?? slots.origin} (${slots.origin})` : undefined)}
        <span className="text-muted">→</span>
        {chip("destination", slots.destination ? `${CITY[slots.destination] ?? slots.destination} (${slots.destination})` : undefined)}
        {chip("date", slots.date ? formatDate(slots.date) : undefined)}
        {slots.window && chip("window", WINDOW[slots.window] ?? slots.window)}
        {slots.preference && chip("preference", PREF[slots.preference] ?? slots.preference)}
      </div>
    </div>
  );
}

const ANSWERS: Record<string, { label: string; value: string }[]> = {
  destination: ["Mumbai", "Bengaluru", "Goa", "Kolkata", "Hyderabad", "Chennai"].map((c) => ({ label: c, value: c })),
  origin: ["Delhi", "Mumbai", "Bengaluru", "Kolkata"].map((c) => ({ label: c, value: c })),
  date: [{ label: "Aaj", value: "aaj" }, { label: "Kal", value: "kal" }, { label: "Parso", value: "parso" }],
};

export function ClarifyQuestion({ question, slot, onAnswer }: { question: string; slot: string; onAnswer: (v: string) => void }) {
  return (
    <div className="w-full">
      <div className="grid grid-cols-3 gap-2">
        {(ANSWERS[slot] ?? []).map((a) => (
          <button
            key={a.value}
            type="button"
            onClick={() => onAnswer(a.value)}
            aria-label={`${question} ${a.label}`}
            className="flex min-h-[44px] items-center justify-center rounded-btn border border-sky-300 dark:border-sky-700 bg-sky-50 dark:bg-sky-950/60 px-3 py-2 text-sm font-bold text-sky-900 dark:text-sky-200 shadow-sm hover:bg-sky-100 dark:hover:bg-sky-900 active:scale-95 transition"
          >
            {a.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export function RoadmapCard({ steps, animate }: { steps: string[]; animate: boolean }) {
  const [done, setDone] = useState(animate ? 0 : steps.length);
  useEffect(() => {
    if (!animate) return;
    setDone(0);
    const iv = setInterval(() => setDone((d) => (d >= steps.length ? (clearInterval(iv), d) : d + 1)), 260);
    return () => clearInterval(iv);
  }, [animate, steps.length]);
  return (
    <div className="w-full rounded-2xl border border-line bg-white p-3">
      <h4 className="mb-1.5 flex items-center gap-2 text-sm font-bold">🗺 Mera plan <Badge tone="sky" className="ml-auto">Planner</Badge></h4>
      <ol className="space-y-1">
        {steps.map((s, i) => (
          <li key={i} className="flex items-start gap-2 text-[12.5px]">
            <span className={clsx("mt-0.5 grid h-[18px] w-[18px] shrink-0 place-items-center rounded-full text-[10px] text-white", i < done ? "bg-ok" : i === done ? "bg-sky-500" : "border-2 border-line")}>
              {i < done ? "✓" : i === done ? "⟳" : ""}
            </span>
            {s}
          </li>
        ))}
      </ol>
    </div>
  );
}

export function SearchProgress({ caseId }: { caseId?: string }) {
  const step = useStore((s) => s.steps.find((x) => x.case_id === caseId && x.agent === "search"));
  const rank = useStore((s) => s.steps.find((x) => x.case_id === caseId && x.agent === "ranker"));
  if (!step) return null;
  return (
    <div className="w-full rounded-2xl border border-line bg-white p-3 text-[12.5px]">
      <h4 className="mb-1 text-sm font-bold">🔎 Search</h4>
      <div className="flex justify-between"><span>✈ Flights (date ±1 din)</span><b>{step.output?.candidates ?? "—"} mili</b></div>
      <div className="flex justify-between text-muted"><span>🚆 Trains · 🚌 Bus</span><span>is demo mein data nahi</span></div>
      {rank && <div className="flex justify-between"><span>Ranker</span><b>score {Number(rank.output?.score ?? 0).toFixed(3)}</b></div>}
    </div>
  );
}

export function OptionCard({ o, recommended, reason, onChoose, lang }: { o: FlightOption; recommended?: boolean; reason?: string; onChoose?: () => void; lang?: Lang }) {
  const [open, setOpen] = useState(false);
  const label = LABEL[o.label ?? ""] ?? { text: o.label ?? "", tone: "" };
  return (
    <div className={clsx("w-full animate-rise rounded-2xl bg-white p-3 text-[12.5px]", recommended ? "border-2 border-sky-500 shadow-[0_0_0_4px_rgba(0,180,230,.12)]" : "border border-line")}>
      <div className={clsx("mb-1 text-[11px] font-extrabold uppercase tracking-wide", label.tone)}>{label.text}</div>
      <div className="flex items-center justify-between">
        <span className="text-base font-bold">{o.dep_time} → {o.arr_time}</span>
        <span className={clsx("num", recommended ? "text-xl" : "text-lg")}>{formatINR(o.price ?? o.price_inr)}</span>
      </div>
      <div className="text-muted">{o.airline} · {formatDuration(o.duration_min)} · {o.stops === 0 ? "Non-stop" : `${o.stops} stop`} · {formatDate(o.date)}</div>
      <div className="mt-1.5 flex flex-wrap gap-1">
        {o.refundable ? <Badge tone="ok">Free cancel</Badge> : <Badge tone="warn"><AlertTriangle className="h-3 w-3" /> Non-refundable</Badge>}
        <Badge tone="sky">On-time {o.on_time_pct}%</Badge>
        {(o.risk_flags ?? []).filter((r) => r !== "non_refundable").map((r) => <Badge key={r} tone="warn">⚠ {RISK[r] ?? r}</Badge>)}
      </div>
      {reason && <div className="mt-2 rounded-lg bg-sky-100 px-2.5 py-1.5 text-[12.5px] text-sky-900">💬 {reason}</div>}
      <button className="mt-1.5 flex items-center gap-1 text-[11.5px] text-sky-700" onClick={() => setOpen(!open)} aria-expanded={open}>
        <ChevronDown className={clsx("h-3.5 w-3.5 transition", open && "rotate-180")} /> {t("why", lang)}
      </button>
      {open && <div className="mt-1"><ScoreBars b={o.score_breakdown} /></div>}
      {onChoose && <Button variant="primary" className="mt-2 w-full" onClick={onChoose}>{t("choose.this", lang)}</Button>}
    </div>
  );
}

export function TravelResults({ r, onChoose, lang }: { r: TurnResult; onChoose: () => void; lang?: Lang }) {
  const recId = r.recommended?.flight_id;
  const opts = useMemo(() => {
    const list = r.top_options ?? [];
    const rec = list.find((o) => o.label === "BEST_BALANCE");
    return rec ? [rec, ...list.filter((o) => o !== rec)] : list;
  }, [r.top_options]);
  const adjusted = r.slots?.date && opts[0] && opts[0].date !== r.slots.date;
  return (
    <div className="flex w-full flex-col gap-2">
      {adjusted && (
        <div className="rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-[12.5px]">
          💡 {formatDate(r.slots!.date)} ko flight nahi mili — {formatDate(opts[0].date)} ke options dikhaye.
        </div>
      )}
      {opts.map((o) => (
        <OptionCard
          key={`${o.label}_${o.flight_id}`}
          o={o}
          lang={lang}
          recommended={o.label === "BEST_BALANCE"}
          reason={o.label === "BEST_BALANCE" ? r.recommended?.reason : undefined}
          onChoose={o.label === "BEST_BALANCE" && o.flight_id === recId && r.booking_summary ? onChoose : undefined}
        />
      ))}
      {opts.length > 1 && <p className="text-[11px] text-muted">Review &amp; Pay summary recommended option ke liye taiyaar hai (Guardian-checked).</p>}
    </div>
  );
}

export function BookingSummaryView({ s, onPay, lang }: { s: BookingSummary; onPay: () => void; lang?: Lang }) {
  const checks = [
    s.cancellation_policy === "refundable" ? "✓ refundable fare" : "⚠ non-refundable fare",
    s.flight.stops === 0 ? "✓ no layover" : "⚠ has a stop",
    "✓ Saarthi never pays — you do",
  ];
  return (
    <div className="flex flex-col gap-1.5 text-[13px]">
      <div className="flex justify-between"><span>Flight</span><b>{s.flight.airline} · {s.flight.flight_id}</b></div>
      <div className="flex justify-between"><span>Kab</span><b>{formatDate(s.flight.date)} · {s.flight.dep_time} → {s.flight.arr_time}</b></div>
      <div className="flex justify-between"><span>Route</span><b>{s.flight.from} → {s.flight.to}</b></div>
      <div className="flex justify-between"><span>Yatri</span><b>{s.passenger_name}</b></div>
      <div className="flex justify-between"><span>Cancellation</span><b>{s.cancellation_policy === "refundable" ? "Refundable" : "Non-refundable"}</b></div>
      <div className="flex justify-between"><span>Convenience fee</span><b className="num">{formatINR(s.convenience_fee)}</b></div>
      <div className="mt-1 flex items-center justify-between border-t border-line pt-2"><span className="font-bold">Total</span><span className="num text-xl">{formatINR(s.total_payable)}</span></div>
      <div className="my-1 rounded-xl bg-ok-bg p-2 text-[12px] text-green-900"><ShieldCheck className="mr-1 inline h-4 w-4" />Guardian: {checks.join(" · ")}</div>
      <Button variant="sky" size="lg" onClick={onPay}>{t("pay", lang)}</Button>
      <p className="text-center text-[11px] text-muted">{t("pay.note", lang)}</p>
    </div>
  );
}

/** Human-only sandbox payment screen. The user taps Pay; Saarthi never does. */
export function PaymentScreen({ s, onClose }: { s: BookingSummary; onClose: () => void }) {
  const [notice, setNotice] = useState<string>("");
  const [paid, setPaid] = useState(false);
  useEffect(() => {
    api.mockCheckout(s.order_id).then((r) => setNotice(r.notice), (e) => setNotice(errorText(e)));
  }, [s.order_id]);
  return (
    <div className="absolute inset-0 z-30 flex flex-col bg-slate-100">
      <div className="bg-amber-100 py-1 text-center text-[11px] font-bold text-amber-800">TEST MODE · SIMULATED PAYMENT</div>
      <div className="flex items-center justify-between bg-slate-700 px-4 py-2.5 font-bold text-white">
        <button onClick={onClose} aria-label="Back">← Payment</button>
        <Lock className="h-4 w-4" />
      </div>
      <div className="flex flex-1 flex-col gap-3 overflow-auto p-4">
        {!paid ? (
          <>
            <div className="rounded-2xl bg-white p-4 text-center shadow-sm">
              <small className="text-muted">Pay to</small>
              <div className="font-bold">Flight booking · {s.flight.airline} {s.flight.flight_id}</div>
              <div className="num mt-1 text-3xl">{formatINR(s.total_payable)}</div>
              <div className="mono mt-1 text-[11px] text-muted">order {s.order_id}</div>
            </div>
            <div className="rounded-2xl bg-white p-4 text-[13px] shadow-sm">
              <b>Pay with</b>
              <label className="mt-2 flex items-center gap-2"><input type="radio" name="pm" defaultChecked /> UPI (test)</label>
              <label className="mt-1 flex items-center gap-2"><input type="radio" name="pm" /> Card (test)</label>
            </div>
            <p className="text-center text-[11.5px] text-muted">Ye screen aap chala rahe hain, Saarthi nahi. {notice}</p>
            <Button variant="primary" size="lg" className="mt-auto" onClick={() => setPaid(true)}>Pay {formatINR(s.total_payable)}</Button>
          </>
        ) : (
          <div className="m-auto max-w-xs rounded-2xl bg-white p-5 text-center shadow-sm">
            <CheckCircle2 className="mx-auto h-12 w-12 text-ok" />
            <b className="mt-2 block text-lg">Simulated payment done</b>
            <p className="mt-1 text-sm text-muted">Test mode — no real money moved. Booking draft {s.booking_draft_id}.</p>
            <Button className="mt-3 w-full" onClick={onClose}>Done</Button>
          </div>
        )}
      </div>
    </div>
  );
}

/** Elder mode (Meena Aunty): one big recommended card, read aloud, two giant buttons. */
export function ElderView({ r, persona, onYes, onMore }: { r: TurnResult; persona: PersonaId; onYes: () => void; onMore: () => void }) {
  const o = r.recommended;
  const [busy, setBusy] = useState(false);
  if (!o) return null;
  const listen = async () => {
    setBusy(true);
    try {
      await unlockAudio();
      const blob = await api.tts(persona, r.reply_text, r.language === "en" ? "en" : "hi", true);
      await playBlob(blob, r.reply_text, r.language, true);
    } catch (e) {
      toast({ title: "Audio", body: errorText(e), tone: "warn" });
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="flex w-full flex-col gap-3">
      <div className="rounded-2xl border-2 border-sky-500 bg-white p-4 text-[17px]">
        <div className="flex items-center gap-2 text-2xl font-bold"><Plane className="h-6 w-6" /> {o.dep_time}</div>
        <div>{CITY[o.from] ?? o.from} → {CITY[o.to] ?? o.to} · {formatDuration(o.duration_min)}</div>
        <div className="num my-1.5 text-3xl">{formatINR(o.price ?? o.price_inr)}</div>
        <Button size="lg" className="w-full" onClick={listen} loading={busy}><Volume2 className="h-5 w-5" /> {t("listen", "hi")}</Button>
      </div>
      <Button variant="sky" size="lg" onClick={onYes}>✓ {t("yes.ok", "hi")}</Button>
      <Button size="lg" onClick={onMore}>{t("no.more", "hi")}</Button>
    </div>
  );
}
