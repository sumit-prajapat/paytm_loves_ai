import clsx from "clsx";
import { MoreVertical, WifiOff } from "lucide-react";
import { useMemo, useState } from "react";
import { MerchantResultCards, ScamWarning } from "@/components/cards";
import { Bubble, ChatThread, Composer, PHRASE_BANK, QuickReplies } from "@/components/chat";
import { BrandLogo, LanguageChip, PhoneFrame } from "@/components/layout";
import { Card } from "@/components/ui";
import { t } from "@/lib/i18n";
import { MERCHANT_PERSONAS, PERSONAS } from "@/lib/personas";
import { raiseIssue, requestPulse, runCheckup, sendText, sendVoice } from "@/services/actions";
import { savePref, useStore } from "@/store";
import type { PersonaId, Scope } from "@/types/contracts";

const SHORTCUTS: { scope: Scope; emoji: string; key: "settlement" | "soundbox" | "refund" | "payments" }[] = [
  { scope: "settlement", emoji: "💰", key: "settlement" },
  { scope: "device", emoji: "🔊", key: "soundbox" },
  { scope: "refunds", emoji: "↩️", key: "refund" },
];

function Welcome({ persona }: { persona: PersonaId }) {
  const lang = useStore((s) => s.lang) ?? PERSONAS[persona].defaultLang;
  const first = PERSONAS[persona].label.split(" ")[0];
  return (
    <div className="m-auto flex max-w-[320px] flex-col items-center gap-2 py-6 text-center">
      <div className="flex items-center justify-center rounded-2xl bg-white p-3 shadow-md border border-line">
        <BrandLogo size={52} className="min-w-[110px]" />
      </div>
      <div className="text-lg font-bold">{t("welcome", lang)} {first} ji 🙏</div>
      <p className="text-sm text-muted">{t("welcome.sub", lang)}</p>
      <div className="mt-2 grid w-full grid-cols-3 gap-2">
        {SHORTCUTS.map((s) => (
          <button key={s.scope} onClick={() => runCheckup(persona, s.scope)} className="flex min-h-[88px] flex-col items-center justify-center gap-1 rounded-2xl border border-line bg-card text-ink p-2 shadow-sm hover:border-sky-500 hover:bg-sky-50 dark:hover:bg-sky-950 transition">
            <span className="text-2xl" aria-hidden>{s.emoji}</span>
            <small className="text-[11.5px] font-semibold leading-tight text-ink">{t(s.key, lang)}</small>
          </button>
        ))}
      </div>
      <div className="mt-1 grid w-full grid-cols-3 gap-2 text-[11.5px]">
        <button onClick={() => runCheckup(persona, "all")} className="min-h-[48px] rounded-xl border border-line bg-card text-ink font-semibold px-1 hover:border-sky-500 hover:bg-sky-50 dark:hover:bg-sky-950 transition">✅ {t("check.all", lang)}</button>
        <button onClick={() => requestPulse(persona, "pulse")} className="min-h-[48px] rounded-xl border border-line bg-card text-ink font-semibold px-1 hover:border-sky-500 hover:bg-sky-50 dark:hover:bg-sky-950 transition">📊 {t("pulse", lang)}</button>
        <button onClick={() => requestPulse(persona, "advice")} className="min-h-[48px] rounded-xl border border-line bg-card text-ink font-semibold px-1 hover:border-sky-500 hover:bg-sky-50 dark:hover:bg-sky-950 transition">🪔 {t("advice", lang)}</button>
      </div>
    </div>
  );
}

export function MerchantChat({ persona, onPersona, height }: { persona: PersonaId; onPersona?: (p: PersonaId) => void; height?: number }) {
  const p = PERSONAS[persona];
  const lang = useStore((s) => s.lang);
  const uiLang = lang ?? p.defaultLang;
  const { elderMode, lowBandwidth, apiStatus, set, clearThread } = useStore();
  const killed = useStore((s) => s.control?.kill_switch_active);
  const messages = useStore((s) => s.threads[persona]) ?? [];
  const [menu, setMenu] = useState(false);
  const [trust, setTrust] = useState(true);

  const last = useMemo(() => [...messages].reverse().find((m) => m.role === "saarthi")?.result, [messages]);
  const lastUser = [...messages].reverse().find((m) => m.role === "user");
  const sttFailed = !!lastUser?.voice?.failed;
  const escalated = last?.status === "escalated";

  const quick = useMemo(() => {
    if (sttFailed) return PHRASE_BANK.slice(0, 6).map((ph) => ({ label: ph, onClick: () => sendText(persona, ph) }));
    if (!last) return [];
    const q: { label: string; onClick: () => void }[] = [];
    if (last.checkup) {
      q.push({ label: t("understood", uiLang), onClick: () => sendText(persona, "Samajh gaya, dhanyavaad") });
      q.push({ label: t("recheck", uiLang), onClick: () => runCheckup(persona, (last.checkup!.scope.includes(",") ? "payments" : last.checkup!.scope) as Scope, true) });
    }
    if (last.status === "needs_input") {
      SHORTCUTS.forEach((s) => q.push({ label: `${s.emoji} ${t(s.key, uiLang)}`, onClick: () => runCheckup(persona, s.scope) }));
    }
    if (last.status !== "escalated") q.push({ label: t("human", uiLang), onClick: () => raiseIssue(persona, true) });
    else q.push({ label: "Status dekhein", onClick: () => runCheckup(persona, "all") });
    return q;
  }, [last, sttFailed, persona, uiLang]);

  return (
    <PhoneFrame height={height} className={clsx(elderMode && "elder", lowBandwidth && "low-data")}>
      <header className="flex items-center gap-2.5 bg-navy-700 px-3 py-2.5 text-white">
        <BrandLogo size={28} />
        <div className="min-w-0 flex-1 leading-tight">
          <b className="block text-[15px]">Saarthi</b>
          <small className="flex items-center gap-1 text-[11px] opacity-85"><i className="inline-block h-2 w-2 rounded-full bg-emerald-400" />{t("online", uiLang)}</small>
        </div>
        <LanguageChip dark />
        <div className="relative">
          <button aria-label="Menu" aria-expanded={menu} onClick={() => setMenu(!menu)} className="grid h-9 w-9 place-items-center rounded-full hover:bg-white/10"><MoreVertical className="h-5 w-5" /></button>
          {menu && (
            <div className="absolute right-0 top-10 z-20 w-56 rounded-xl border border-line bg-white p-1.5 text-sm text-ink shadow-card" onMouseLeave={() => setMenu(false)}>
              {onPersona && (
                <div className="border-b border-line pb-1">
                  <small className="px-2 text-[11px] text-muted">Merchant</small>
                  {MERCHANT_PERSONAS.map((id) => (
                    <button key={id} onClick={() => { onPersona(id); setMenu(false); }} className={clsx("block w-full rounded-lg px-2 py-2 text-left hover:bg-slate-100", id === persona && "font-bold")}>
                      {PERSONAS[id].label}
                    </button>
                  ))}
                </div>
              )}
              <label className="flex items-center justify-between rounded-lg px-2 py-2 hover:bg-slate-100">{t("lowdata", uiLang)}
                <input type="checkbox" checked={lowBandwidth} onChange={(e) => { set({ lowBandwidth: e.target.checked }); savePref("lowBandwidth", e.target.checked); }} />
              </label>
              <label className="flex items-center justify-between rounded-lg px-2 py-2 hover:bg-slate-100">{t("elder", uiLang)}
                <input type="checkbox" checked={elderMode} onChange={(e) => { set({ elderMode: e.target.checked }); savePref("elderMode", e.target.checked); }} />
              </label>
              <button className="block w-full rounded-lg px-2 py-2 text-left hover:bg-slate-100" onClick={() => { raiseIssue(persona, false); setMenu(false); }}>🎫 {t("raise.issue", uiLang)}</button>
              <button className="block w-full rounded-lg px-2 py-2 text-left text-risk hover:bg-slate-100" onClick={() => { clearThread(persona); setMenu(false); }}>{t("clear", uiLang)}</button>
            </div>
          )}
        </div>
      </header>
      {trust && <ScamWarning lang={uiLang} onDismiss={() => setTrust(false)} />}
      {apiStatus === "down" && <div role="alert" className="flex items-center gap-1.5 bg-risk-bg px-3 py-1.5 text-xs text-risk"><WifiOff className="h-4 w-4" /> {t("offline", uiLang)}</div>}
      {killed && <div className="bg-amber-100 px-3 py-1 text-[11.5px] text-amber-900">Saarthi abhi team ke saath kaam kar raha hai (autonomy paused).</div>}
      {escalated && <div className="bg-risk-bg px-3 py-1 text-[11.5px] font-semibold text-risk">🧑‍💼 Insaan dekh rahe hain · {last?.escalation?.ticket_id}</div>}
      <span className="sr-only">{p.label}</span>
      {messages.length === 0 ? (
        <div className="flex flex-1 overflow-y-auto bg-bg text-ink p-3"><Welcome persona={persona} /></div>
      ) : (
        <ChatThread
          persona={persona}
          render={(m) => (
            <Bubble m={m}>
              {m.role === "saarthi" && m.result && <MerchantResultCards r={m.result} persona={persona} />}
            </Bubble>
          )}
        />
      )}
      {sttFailed && <div className="bg-amber-50 px-3 pt-1.5 text-[11.5px] text-amber-900">{t("type.instead", uiLang)}</div>}
      <QuickReplies items={quick} />
      <Composer lang={uiLang} onSend={(text) => sendText(persona, text)} onAudio={(b, s) => sendVoice(persona, b, s)} />
    </PhoneFrame>
  );
}

export function MerchantSideTools({ persona }: { persona: PersonaId }) {
  return (
    <Card className="!p-3 text-xs">
      <b className="mb-1 block">Merchant quick checks (user triggers)</b>
      <div className="flex flex-wrap gap-1.5">
        {(["settlement", "device", "payments", "refunds", "all"] as Scope[]).map((s) => (
          <button key={s} onClick={() => runCheckup(persona, s)} className="min-h-[36px] rounded-full border border-line px-3 hover:bg-sky-100">{s}</button>
        ))}
      </div>
    </Card>
  );
}
