import clsx from "clsx";
import { MoreVertical, Plane, WifiOff, X } from "lucide-react";
import { useMemo, useState } from "react";
import { BookingStatusCard, ScamWarning } from "@/components/cards";
import { Bubble, ChatThread, Composer, QuickReplies } from "@/components/chat";
import { BrandLogo, LanguageChip, PhoneFrame } from "@/components/layout";
import { BookingSummaryView, ClarifyQuestion, ElderView, PaymentScreen, RoadmapCard, SearchProgress, SlotChips, TravelResults } from "@/components/travel";
import { t } from "@/lib/i18n";
import { PERSONAS, TRAVEL_PERSONAS } from "@/lib/personas";
import { sendText, sendVoice } from "@/services/actions";
import { useStore, type UiMessage } from "@/store";
import type { BookingSummary, PersonaId } from "@/types/contracts";

const EXAMPLES: Record<string, string[]> = {
  arjun: ["Delhi se Mumbai kal shaam ka flight, sasta aur jaldi", "Meri booking BK-ARJ-1001 ka status"],
  meena: ["दिल्ली से मुंबई कल सुबह की फ़्लाइट, आराम वाली", "Meri booking BK-MEE-2001 ka status"],
  priya: ["Flight from Bangalore to Delhi day after tomorrow morning", "Status of my booking BK-ARJ-1001"],
};

export function TravelChat({ persona, onPersona, height }: { persona: PersonaId; onPersona?: (p: PersonaId) => void; height?: number }) {
  const p = PERSONAS[persona];
  const lang = useStore((s) => s.lang) ?? p.defaultLang;
  const apiStatus = useStore((s) => s.apiStatus);
  const messages = useStore((s) => s.threads[persona]) ?? [];
  const clear = useStore((s) => s.clearThread);
  const [menu, setMenu] = useState(false);
  const [summary, setSummary] = useState<BookingSummary | null>(null);
  const [paying, setPaying] = useState(false);
  const [elderAll, setElderAll] = useState(false);
  const elder = !!p.elder && !elderAll;

  const lastResultId = useMemo(() => [...messages].reverse().find((m) => m.role === "saarthi" && m.result)?.id, [messages]);
  const lastQuery = useMemo(() => [...messages].reverse().find((m) => m.role === "user" && m.text && m.text.length > 12)?.text, [messages]);

  const renderSaarthi = (m: UiMessage) => {
    const r = m.result;
    if (!r) return null;
    const latest = m.id === lastResultId;
    return (
      <>
        {r.slots && (r.status === "needs_input" || r.status === "ready_for_review_and_pay") && <SlotChips slots={r.slots} missing={r.missing_slot} />}
        {r.status === "needs_input" && r.missing_slot && latest && (
          <ClarifyQuestion question={r.reply_text} slot={r.missing_slot} onAnswer={(v) => sendText(persona, v)} />
        )}
        {r.roadmap && r.roadmap.length > 0 && <RoadmapCard steps={r.roadmap} animate={latest} />}
        {r.status === "ready_for_review_and_pay" && <SearchProgress caseId={r.case_id} />}
        {r.status === "ready_for_review_and_pay" && (
          elder && r.recommended ? (
            <ElderView
              r={r}
              persona={persona}
              onYes={() => r.booking_summary && setSummary(r.booking_summary)}
              onMore={() => { setElderAll(true); if (lastQuery) sendText(persona, lastQuery, { elder: false }); }}
            />
          ) : (
            <TravelResults r={r} lang={lang} onChoose={() => r.booking_summary && setSummary(r.booking_summary)} />
          )
        )}
        {r.booking && <BookingStatusCard b={r.booking} />}
      </>
    );
  };

  return (
    <PhoneFrame height={height} className={clsx(p.elder && !elderAll && "elder")}>
      <header className="flex items-center gap-2.5 bg-navy-700 px-3 py-2.5 text-white">
        <BrandLogo size={28} />
        <div className="min-w-0 flex-1 leading-tight">
          <b className="flex items-center gap-1.5 text-[15px]">
            Saarthi Travel <Plane className="h-4 w-4 text-sky-400 inline" />
          </b>
          <small className="text-[11px] opacity-85">{p.label}{p.elder ? " · elder mode" : ""}</small>
        </div>
        <LanguageChip dark />
        <div className="relative">
          <button aria-label="Menu" aria-expanded={menu} onClick={() => setMenu(!menu)} className="grid h-9 w-9 place-items-center rounded-full hover:bg-white/10"><MoreVertical className="h-5 w-5" /></button>
          {menu && (
            <div className="absolute right-0 top-10 z-20 w-60 rounded-xl border border-line bg-white p-1.5 text-sm text-ink shadow-card" onMouseLeave={() => setMenu(false)}>
              {onPersona && TRAVEL_PERSONAS.map((id) => (
                <button key={id} onClick={() => { onPersona(id); setElderAll(false); setMenu(false); }} className={clsx("block w-full rounded-lg px-2 py-2 text-left hover:bg-slate-100", id === persona && "font-bold")}>
                  {PERSONAS[id].label}{PERSONAS[id].elder ? " (elder mode)" : ""}
                </button>
              ))}
              <button className="block w-full rounded-lg px-2 py-2 text-left text-risk hover:bg-slate-100" onClick={() => { clear(persona); setMenu(false); }}>{t("clear", lang)}</button>
            </div>
          )}
        </div>
      </header>
      <ScamWarning lang={lang} />
      {p.note && <div className="bg-slate-100 px-3 py-1 text-[11px] text-muted">{p.note}</div>}
      {apiStatus === "down" && <div role="alert" className="flex items-center gap-1.5 bg-risk-bg px-3 py-1.5 text-xs text-risk"><WifiOff className="h-4 w-4" /> {t("offline", lang)}</div>}
      {messages.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-3 overflow-y-auto bg-bg text-ink p-4 text-center">
          <Plane className="h-10 w-10 text-sky-500" />
          <b className="phone-text text-ink">{t("trip.placeholder", lang)}</b>
          <p className="text-xs text-muted">Saarthi plan banata hai, options tolta hai, aur summary deta hai. Payment hamesha aap khud karte hain.</p>
          {EXAMPLES[persona]?.map((ex) => (
            <button key={ex} onClick={() => sendText(persona, ex)} className="min-h-[44px] rounded-full border border-sky-300 dark:border-sky-700 bg-sky-100 dark:bg-sky-950/80 px-4 text-[13px] font-bold text-sky-900 dark:text-sky-200 hover:bg-sky-200 transition">{ex}</button>
          ))}
        </div>
      ) : (
        <ChatThread persona={persona} render={(m) => <Bubble m={m}>{m.role === "saarthi" && renderSaarthi(m)}</Bubble>} />
      )}
      <QuickReplies items={messages.length ? (EXAMPLES[persona] ?? []).map((ex) => ({ label: ex, onClick: () => sendText(persona, ex) })) : []} />
      <Composer lang={lang} placeholder={t("trip.placeholder", lang)} onSend={(x) => sendText(persona, x)} onAudio={(b, s) => sendVoice(persona, b, s)} />

      {summary && !paying && (
        <div className="absolute inset-0 z-20 flex flex-col justify-end bg-slate-900/35" onClick={() => setSummary(null)}>
          <div role="dialog" aria-label="Booking summary" onClick={(e) => e.stopPropagation()} className="animate-rise rounded-t-3xl bg-white px-4 pb-5 pt-3 shadow-2xl">
            <div className="mx-auto mb-2 h-1.5 w-10 rounded bg-line" />
            <div className="mb-1 flex items-center justify-between">
              <b className="text-base">Booking summary</b>
              <button aria-label="Close" onClick={() => setSummary(null)}><X className="h-5 w-5" /></button>
            </div>
            <BookingSummaryView s={summary} lang={lang} onPay={() => setPaying(true)} />
          </div>
        </div>
      )}
      {summary && paying && <PaymentScreen s={summary} onClose={() => { setPaying(false); setSummary(null); }} />}
    </PhoneFrame>
  );
}
