import clsx from "clsx";
import {
  AlertTriangle, BatteryLow, CheckCircle2, CircleDollarSign, Clock, Plug, Search, ShieldAlert, ShieldCheck, Signal, Ticket,
  UserRoundCheck, Wifi,
} from "lucide-react";
import { useState, type ReactNode } from "react";
import { Badge, Button } from "@/components/ui";
import { formatDate, formatINR, maskId } from "@/lib/format";
import { t } from "@/lib/i18n";
import { applyForLoan, raiseIssue, runCheckup, sendText } from "@/services/actions";
import { useStore } from "@/store";
import type { Finding, Lang, LoanQuote, LoanRequest, OfferCard, PersonaId, TravelBooking, TurnResult } from "@/types/contracts";

const ITEM_LABEL: Record<string, string> = {
  refund_adjustment: "Refund adjust",
  fee: "Fees",
  chargeback_hold: "Chargeback hold",
};
const ITEM_COLOR: Record<string, string> = { refund_adjustment: "#F97316", fee: "#94A3B8", chargeback_hold: "#DC2626" };

export function RichCard({ icon, title, children, tone, footer, caseId }: {
  icon: ReactNode; title: string; children: ReactNode; tone?: "risk" | "ok" | "warn" | "offer"; footer?: ReactNode; caseId?: string;
}) {
  const select = useStore((s) => s.set);
  return (
    <div
      className={clsx(
        "w-full animate-rise rounded-2xl border bg-white p-3 text-[13.5px] shadow-sm",
        tone === "risk" && "border-red-200 bg-red-50/40",
        tone === "warn" && "border-amber-200",
        tone === "offer" && "border-pink-200",
        !tone && "border-line",
      )}
    >
      <h4 className="mb-2 flex items-center gap-1.5 text-sm font-bold">{icon}{title}</h4>
      {children}
      {footer && <div className="mt-2.5 flex flex-wrap gap-1.5">{footer}</div>}
      {caseId && (
        <button className="mt-2 flex items-center gap-1 text-[11px] text-sky-700 hover:underline" onClick={() => select({ selectedCase: caseId })}>
          <Search className="h-3 w-3" /> {t("how.known", null)} <span className="mono">{caseId}</span>
        </button>
      )}
    </div>
  );
}

function KV({ k, v, big }: { k: ReactNode; v: ReactNode; big?: boolean }) {
  return (
    <div className={clsx("flex items-center justify-between gap-3 py-0.5", big && "mt-1 border-t border-line pt-1.5 text-[15px]")}>
      <span className="text-slate-600">{k}</span>
      <span className="text-right">{v}</span>
    </div>
  );
}

export function SettlementCard({ f, persona, caseId }: { f: Finding; persona: PersonaId; caseId?: string }) {
  const x = f.facts;
  if (f.code === "settlement_none") return <RichCard icon="💰" title="Settlement">No settlement record yet.</RichCard>;
  const items: { type: string; amount: number; amount_money?: any }[] = x.items ?? [];
  return (
    <RichCard
      icon="💰"
      title={`Settlement · ${x.is_today ? "aaj" : formatDate(x.date)}`}
      tone={f.code === "settlement_gap_unreconciled" ? "warn" : undefined}
      caseId={caseId}
      footer={
        <>
          <Button size="sm" variant="primary" onClick={() => sendText(persona, "Samajh gaya, dhanyavaad")}>Samajh gaya 👍</Button>
          <Button size="sm" onClick={() => runCheckup(persona, "settlement", true)}>Detail / re-check</Button>
        </>
      }
    >
      <KV k="Expected" v={<span className="num">{formatINR(x.expected_money ?? x.expected)}</span>} />
      <KV k="Mila (received)" v={<span className="num">{formatINR(x.actual_money ?? x.actual)}</span>} />
      {items.length > 0 && (
        <div className="my-2 flex h-2.5 overflow-hidden rounded-full bg-slate-100" aria-hidden>
          {items.map((i, n) => (
            <span key={n} style={{ flexGrow: i.amount, background: ITEM_COLOR[i.type] ?? "#64748B" }} />
          ))}
        </div>
      )}
      {items.map((i, n) => (
        <KV key={n} k={<span className="flex items-center gap-1.5"><i className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: ITEM_COLOR[i.type] ?? "#64748B" }} />{ITEM_LABEL[i.type] ?? i.type}</span>} v={<span className="num">{formatINR(i.amount_money ?? i.amount)}</span>} />
      ))}
      {Number(x.gap) > 0 && <KV big k={<b>Kam aaya (short)</b>} v={<span className="num">{formatINR(x.gap_money ?? x.gap)}</span>} />}
      <div className="mt-2">
        {f.code === "settlement_gap_reconciled" && <Badge tone="ok"><CheckCircle2 className="h-3 w-3" /> Aapko kuch karne ki zaroorat nahi</Badge>}
        {f.code === "settlement_gap_unreconciled" && <Badge tone="warn"><AlertTriangle className="h-3 w-3" /> Settlement team check karegi</Badge>}
        {f.code === "settlement_ok" && <Badge tone="ok"><CheckCircle2 className="h-3 w-3" /> Poora settlement aaya</Badge>}
      </div>
    </RichCard>
  );
}

export function DeviceCard({ f, persona, caseId }: { f: Finding; persona: PersonaId; caseId?: string }) {
  const x = f.facts;
  if (f.code === "device_none") return <RichCard icon="🔊" title="Soundbox">No Soundbox linked.</RichCard>;
  const offline = f.code === "device_offline";
  const low = f.code === "device_low_battery";
  return (
    <RichCard
      icon="🔊"
      title={`Soundbox ${offline ? "offline" : low ? "battery low" : "status"}`}
      tone={offline || low ? "warn" : undefined}
      caseId={caseId}
      footer={(offline || low) && (
        <>
          <Button size="sm" variant="ok" onClick={() => runCheckup(persona, "device", true)}>Theek ho gaya ✓</Button>
          <Button size="sm" onClick={() => raiseIssue(persona, true)}>Abhi bhi band hai</Button>
        </>
      )}
    >
      <div className="flex flex-wrap gap-3 text-[13px]">
        <span className="flex items-center gap-1"><BatteryLow className="h-4 w-4" /> <b className="num">{x.battery}%</b></span>
        <span className="flex items-center gap-1"><Signal className="h-4 w-4" /> {x.network}</span>
        <span className="flex items-center gap-1"><Clock className="h-4 w-4" /> {x.minutes_since_seen} min</span>
      </div>
      {(offline || low) && (
        <ol className="mt-2 space-y-1 text-[13px]">
          {low && <li className="flex items-center gap-1.5"><Plug className="h-4 w-4 text-ok" /> Charger lagaiye</li>}
          {offline && <li className="flex items-center gap-1.5"><Plug className="h-4 w-4 text-ok" /> Band karke phir chalu kijiye</li>}
          <li className="flex items-center gap-1.5"><Wifi className="h-4 w-4 text-ok" /> Network check kijiye</li>
        </ol>
      )}
    </RichCard>
  );
}

export function RefundCard({ f, caseId }: { f: Finding; caseId?: string }) {
  const x = f.facts;
  if (f.code === "refunds_none") return <RichCard icon="↩️" title="Refunds" caseId={caseId}><Badge tone="ok">Koi refund pending nahi</Badge></RichCard>;
  const overdue = f.code === "refund_overdue";
  const steps = [
    { label: "Shuru", state: "done" },
    { label: "Process", state: overdue ? "late" : "active" },
    { label: "Khaate mein", state: "todo" },
  ];
  return (
    <RichCard icon="↩️" title="Refund status" tone={overdue ? "warn" : undefined} caseId={caseId}>
      <KV k="Txn" v={<span className="mono">{maskId(x.txn_id)}</span>} />
      <KV k="Amount" v={<span className="num">{formatINR(x.amount_money ?? x.amount)}</span>} />
      <KV k="Bank ref" v={<span className="mono text-xs">{x.bank_ref}</span>} />
      <div className="relative my-3 flex justify-between">
        <div className="absolute left-3 right-3 top-2.5 h-0.5 bg-line" />
        {steps.map((s) => (
          <div key={s.label} className="relative z-10 w-1/3 text-center text-[11px]">
            <span className={clsx("mx-auto mb-1 block h-5 w-5 rounded-full border-2",
              s.state === "done" && "border-ok bg-ok", s.state === "active" && "border-sky-500 bg-sky-500",
              s.state === "late" && "border-risk bg-risk", s.state === "todo" && "border-line bg-white")} />
            {s.label}
          </div>
        ))}
      </div>
      <KV big k={overdue ? "Aana tha" : "Kab tak"} v={<b>{formatDate(x.expected_by)}</b>} />
      <div className="mt-1.5">{overdue ? <Badge tone="risk">Overdue · banking team ko bheja</Badge> : <Badge tone="ok">Process ho raha hai</Badge>}</div>
    </RichCard>
  );
}

export function PaymentsCard({ f, caseId }: { f: Finding; caseId?: string }) {
  const x = f.facts;
  if (f.code === "payments_none") return <RichCard icon="💳" title="Payments" caseId={caseId}><Badge tone="ok">Pichhle {x.days} din mein koi fail nahi</Badge></RichCard>;
  return (
    <RichCard icon="💳" title="Failed payments" caseId={caseId}>
      <KV k={`Pichhle ${x.days} din`} v={<b>{x.count} failed</b>} />
      <KV k="Latest" v={<span className="num">{formatINR(x.amount_money ?? x.amount)}</span>} />
      <KV k="Kaaran" v={<span className="text-xs">{String(x.reason_code).replace(/_/g, " ")}</span>} />
    </RichCard>
  );
}

export function DisputeCard({ f, ticketId, caseId, lang }: { f: Finding; ticketId?: string | null; caseId?: string; lang?: Lang }) {
  const x = f.facts;
  if (f.resolution === "playbook") {
    return (
      <RichCard icon={<ShieldCheck className="h-4 w-4 text-ok" />} title="Chargeback · learned fix" tone="ok" caseId={caseId}>
        <KV k="Amount" v={<span className="num">{formatINR(x.amount_money ?? x.amount)}</span>} />
        <KV k="Deadline" v={<b>{formatDate(x.deadline)}</b>} />
        <p className="mt-1 text-[13px]">Bill aur delivery ka saboot app mein upload kijiye.</p>
        <Badge tone="ok" className="mt-2">🎓 Playbook {f.playbook?.id} · match {f.playbook?.score}</Badge>
      </RichCard>
    );
  }
  return (
    <RichCard icon={<UserRoundCheck className="h-4 w-4" />} title="Hamari team dekh rahi hai" tone="risk" caseId={caseId}>
      <p className="text-[13px]">{t("escalated", lang)}</p>
      <KV k="Chargeback" v={<span className="num">{formatINR(x.amount_money ?? x.amount)}</span>} />
      <KV k="Deadline" v={<b>{formatDate(x.deadline)}</b>} />
      {ticketId && <KV k="Ticket" v={<span className="mono text-xs">{ticketId}</span>} />}
    </RichCard>
  );
}

export function TicketCard({ ticketId, reused, lang }: { ticketId: string; reused?: boolean; lang?: Lang }) {
  return (
    <RichCard icon={<Ticket className="h-4 w-4" />} title="Ticket" tone="risk">
      <KV k="Ticket id" v={<span className="mono text-xs">{ticketId}</span>} />
      <KV k="Status" v={<Badge tone="risk">● Escalated to a person</Badge>} />
      {reused && <p className="mt-1 text-xs text-muted">Pehle se khula ticket hi use kiya (duplicate nahi bana).</p>}
      <p className="mt-1 text-[12.5px]">{t("escalated", lang)}</p>
    </RichCard>
  );
}

export function LoanOfferCard({ offer, persona, lang }: { offer: OfferCard; persona: PersonaId; lang?: Lang }) {
  const key = `saarthi.offer.hidden.${persona}`;
  const [hidden, setHidden] = useState(() => {
    try { return sessionStorage.getItem(key) === "1"; } catch { return false; }
  });
  if (hidden) return null;
  const hide = () => {
    setHidden(true);
    try { sessionStorage.setItem(key, "1"); } catch { /* ignore */ }
  };
  return (
    <RichCard
      icon={<CircleDollarSign className="h-4 w-4 text-pink-600" />}
      title="Business loan · ek offer"
      tone="offer"
      footer={
        <>
          <Button size="sm" variant="primary" onClick={() => { hide(); sendText(persona, "Loan ka EMI batao"); }}>{t("loan.yes", lang)}</Button>
          <Button size="sm" onClick={() => { hide(); sendText(persona, "Nahi chahiye loan, mat do"); }}>{t("loan.no", lang)}</Button>
        </>
      }
    >
      <p>{offer.text}</p>
      <KV k="Up to" v={<span className="num">{formatINR(offer.max_amount)}</span>} />
      <KV k="Byaj (annual)" v={<b className="num">{offer.annual_rate_pct}%</b>} />
      <p className="mt-1 text-[11px] text-muted">Sirf ek baar poochenge.</p>
    </RichCard>
  );
}

const LOAN_TONE: Record<string, "warn" | "ok" | "risk"> = { awaiting_approval: "warn", approved: "ok", rejected: "risk" };

export function EmiCard({ quote, request, persona }: { quote?: LoanQuote | null; request?: LoanRequest; persona: PersonaId }) {
  const live = useStore((s) => (request ? s.loanStatus[request.request_id] : undefined));
  const req = live ?? request;
  return (
    <RichCard icon="🧮" title="EMI">
      {quote && (
        <>
          <KV k="Loan" v={<span className="num">{formatINR(quote.principal)}</span>} />
          <KV k="Muddat" v={`${quote.tenure_months} mahine`} />
          <KV k="Byaj" v={<span className="num">{quote.rate_pct}%</span>} />
          <KV big k="Har mahine" v={<span className="num">{formatINR(quote.monthly_emi_money ?? quote.monthly_emi)}</span>} />
          <KV k="Kul" v={<span className="num">{formatINR(quote.total_payable)}</span>} />
          {!req && (
            <div className="mt-2 flex gap-1.5">
              <Button size="sm" variant="primary" onClick={() => applyForLoan(persona, quote)}>Apply karein</Button>
              <Badge tone="muted">Manzoori ek insaan dega</Badge>
            </div>
          )}
        </>
      )}
      {req && (
        <>
          {!quote && (
            <>
              <KV k="Loan" v={<span className="num">{formatINR(req.amount)}</span>} />
              <KV k="Muddat" v={`${req.tenure_months} mahine`} />
              <KV big k="Har mahine" v={<span className="num">{formatINR(req.emi)}</span>} />
            </>
          )}
          <KV k="Request" v={<span className="mono text-xs">{req.request_id}</span>} />
          <Badge tone={LOAN_TONE[req.status] ?? "warn"} className="mt-1.5">
            {req.status === "awaiting_approval" ? "⏳ Awaiting human approval" : req.status === "approved" ? `✓ Approved${req.approved_by ? ` by ${req.approved_by}` : ""}` : "✗ Rejected"}
          </Badge>
        </>
      )}
    </RichCard>
  );
}

export function PulseCard({ text, facts }: { text: string; facts: Record<string, any> }) {
  const s = facts?.settlement;
  return (
    <RichCard icon="📊" title="Business pulse">
      {s && <KV k="Settlement" v={<span className="num">{formatINR(s.actual)}</span>} />}
      {"pending_refunds" in facts && <KV k="Pending refunds" v={<b>{facts.pending_refunds}</b>} />}
      {"open_disputes" in facts && <KV k="Open disputes" v={<b>{facts.open_disputes}</b>} />}
      {facts?.battery != null && <KV k="Soundbox battery" v={<b className="num">{facts.battery}%</b>} />}
      {facts?.festival && <KV k="Festival" v={<b>{facts.festival} · {facts.days_until} din</b>} />}
      <p className="sr-only">{text}</p>
    </RichCard>
  );
}

export function BookingStatusCard({ b }: { b: TravelBooking }) {
  return (
    <RichCard icon="✈️" title={`Booking ${b.booking_ref}`} tone={b.status === "on_time" ? undefined : "warn"}>
      <KV k="Flight" v={<b>{b.airline} {b.flight_no}</b>} />
      <KV k="Route" v={`${b.from} → ${b.to}`} />
      <KV k="Kab" v={`${formatDate(b.date)} · ${b.dep_time}`} />
      <KV k="Gate" v={b.gate ?? "—"} />
      <Badge tone={b.status === "on_time" ? "ok" : b.status === "delayed" ? "warn" : "risk"} className="mt-1">
        {b.status === "on_time" ? "On time" : b.status === "delayed" ? `Delayed ${b.delay_minutes} min` : "Cancelled"}
      </Badge>
    </RichCard>
  );
}

export function ScamWarning({ lang, onDismiss }: { lang?: Lang | null; onDismiss?: () => void }) {
  return (
    <div className="flex items-start gap-2 bg-ok-bg px-3 py-1.5 text-[12px] text-emerald-900">
      <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
      <span className="flex-1">{t("scam", lang)}</span>
      {onDismiss && <button aria-label="Dismiss" onClick={onDismiss} className="text-emerald-800">✕</button>}
    </div>
  );
}

/** Choose the cards for a merchant turn result. */
export function MerchantResultCards({ r, persona }: { r: TurnResult & { kind?: string; facts?: any }; persona: PersonaId }) {
  const out: ReactNode[] = [];
  const kind = (r as any).kind;
  if (kind === "pulse" || kind === "advice") return <PulseCard text={r.reply_text} facts={(r as any).facts} />;
  if (kind === "loan_request" && r.loan_request) return <EmiCard request={r.loan_request} persona={persona} />;
  const findings = r.checkup?.findings ?? [];
  const issues = findings.filter((f) => f.is_issue);
  const shown = issues.length ? issues : r.checkup?.scope === "all" ? [] : findings;
  shown.forEach((f, i) => {
    const k = `${f.code}_${i}`;
    if (f.code.startsWith("settlement")) out.push(<SettlementCard key={k} f={f} persona={persona} caseId={r.case_id} />);
    else if (f.code.startsWith("device")) out.push(<DeviceCard key={k} f={f} persona={persona} caseId={r.case_id} />);
    else if (f.code.startsWith("refund")) out.push(<RefundCard key={k} f={f} caseId={r.case_id} />);
    else if (f.code.startsWith("payments")) out.push(<PaymentsCard key={k} f={f} caseId={r.case_id} />);
    else if (f.code === "dispute_open") out.push(<DisputeCard key={k} f={f} ticketId={r.escalation?.ticket_id} caseId={r.case_id} lang={r.language} />);
  });
  if (r.escalation?.ticket_id && !findings.some((f) => f.code === "dispute_open" && f.resolution !== "playbook")) {
    out.push(<TicketCard key="ticket" ticketId={r.escalation.ticket_id} reused={r.escalation.reused} lang={r.language} />);
  }
  if (r.loan_quote) out.push(<EmiCard key="emi" quote={r.loan_quote} persona={persona} />);
  if (r.loan_request) out.push(<EmiCard key="req" request={r.loan_request} persona={persona} />);
  if (r.offer) out.push(<LoanOfferCard key="offer" offer={r.offer} persona={persona} lang={r.language} />);
  if (r.booking) out.push(<BookingStatusCard key="bk" b={r.booking} />);
  if (r.status === "refused" && r.sensitive_data_blocked) {
    out.push(<RichCard key="scam" icon={<ShieldAlert className="h-4 w-4 text-risk" />} title="Suraksha chetavani" tone="risk"><p>{t("scam", r.language)}</p></RichCard>);
  }
  return <>{out}</>;
}
