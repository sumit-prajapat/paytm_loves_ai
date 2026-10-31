/**
 * Business-facing actions. Every action is a USER trigger (button, chat, voice, Soundbox, ops
 * decision) sent to the existing backend; results are rendered as returned (no client maths).
 */
import { api, ApiError, errorText } from "@/lib/api";
import { broadcast, TAB_ID } from "@/lib/bus";
import { PERSONAS } from "@/lib/personas";
import { toast } from "@/lib/toast";
import { uid, useStore, type UiMessage } from "@/store";
import type { LoanQuote, PersonaId, Scope, TurnResult } from "@/types/contracts";

const st = () => useStore.getState();

function sessionId(persona: PersonaId): string {
  const key = `saarthi.session.${persona}`;
  try {
    let v = sessionStorage.getItem(key);
    if (!v) {
      v = uid("sess");
      sessionStorage.setItem(key, v);
    }
    return v;
  } catch {
    return `sess_${persona}`;
  }
}

function langParam(persona: PersonaId): string | null {
  return st().lang ?? (PERSONAS[persona].id === "priya" ? "en" : null);
}

/** Render a backend turn result into the persona's thread (+ Soundbox, charts). */
export function applyTurn(persona: PersonaId, result: TurnResult, opts: { tag?: string; local?: boolean } = {}): void {
  const s = st();
  s.setTyping(persona, null);
  const msg: UiMessage = {
    id: result.case_id ? `r_${result.case_id}` : uid("r"),
    role: "saarthi",
    ts: Date.now(),
    lang: result.language,
    text: result.reply_text,
    audio: result.audio,
    result,
    tag: opts.tag,
  };
  const thread = s.threads[persona] ?? [];
  if (!thread.some((m) => m.id === msg.id)) s.pushMessage(persona, msg);

  // Soundbox speaks only when the trigger came from the Soundbox channel.
  const p = PERSONAS[persona];
  if (result.channel === "soundbox" && p.deviceId) {
    s.enqueueSoundbox({
      id: `sb_${result.case_id}`,
      text: result.spoken_text || result.reply_text,
      lang: result.language,
      audio_url: result.audio?.audio_url,
      bytes: result.audio?.bytes,
      device_id: p.deviceId,
      ts: Date.now(),
    });
  }
  // Repeat-case learning chart: track outcomes of the chargeback case type.
  if (result.checkup?.findings?.some((f) => f.code === "dispute_open") && !result.checkup.cached) {
    s.addSeriesPoint(result.status);
  }
  if (result.loan_request) s.upsertLoan(result.loan_request);
}

function relay(persona: PersonaId, result: TurnResult, userText?: string, label?: string) {
  broadcast({ kind: "turn", persona, result, userText, origin: TAB_ID, label });
}

function pushUser(persona: PersonaId, text: string, extra: Partial<UiMessage> = {}): string {
  const id = uid("u");
  st().pushMessage(persona, { id, role: "user", ts: Date.now(), text, ...extra });
  return id;
}

function fail(persona: PersonaId, e: unknown) {
  st().setTyping(persona, null);
  st().pushMessage(persona, { id: uid("e"), role: "system", ts: Date.now(), text: errorText(e), error: true });
}

export async function sendText(persona: PersonaId, text: string, opts: { elder?: boolean } = {}): Promise<TurnResult | null> {
  const message = text.trim();
  if (!message) return null;
  pushUser(persona, message);
  st().setTyping(persona, "listener");
  try {
    const result = await api.chat(persona, {
      message, language: langParam(persona), session_id: sessionId(persona), elder_mode: opts.elder ?? PERSONAS[persona].elder ?? false,
    });
    applyTurn(persona, result);
    relay(persona, result, message);
    return result;
  } catch (e) {
    fail(persona, e);
    return null;
  }
}

export async function sendVoice(persona: PersonaId, blob: Blob, seconds: number): Promise<TurnResult | null> {
  const id = pushUser(persona, "", { voice: { seconds, pending: true } });
  st().setTyping(persona, "listener");
  try {
    const result = await api.voiceTurn(persona, blob, {
      language: langParam(persona), session_id: sessionId(persona), slow: st().slowSpeech || !!PERSONAS[persona].elder,
    });
    st().patchMessage(persona, id, {
      text: result.transcript ?? "",
      voice: { seconds, pending: false, failed: !!result.transcript_unavailable },
    });
    applyTurn(persona, result);
    relay(persona, result, result.transcript);
    return result;
  } catch (e) {
    st().patchMessage(persona, id, { voice: { seconds, pending: false, failed: true } });
    fail(persona, e);
    return null;
  }
}

const SCOPE_LABEL: Record<Scope, string> = {
  settlement: "💰 Settlement check", device: "🔊 Soundbox check", refunds: "↩️ Refund check",
  payments: "💳 Payments check", all: "✅ Sab check",
};

export async function runCheckup(persona: PersonaId, scope: Scope, force = false): Promise<TurnResult | null> {
  pushUser(persona, `${SCOPE_LABEL[scope]}${force ? " (re-check)" : ""}`, { tag: "button" });
  st().setTyping(persona, "diagnostician");
  try {
    const result = await api.checkup(persona, { scope, channel: "app", language: langParam(persona), force_refresh: force });
    applyTurn(persona, result);
    relay(persona, result, SCOPE_LABEL[scope]);
    return result;
  } catch (e) {
    fail(persona, e);
    return null;
  }
}

export async function raiseIssue(persona: PersonaId, insist: boolean): Promise<void> {
  pushUser(persona, insist ? "🎫 Ticket banaiye (insist)" : "🎫 Shikayat darj karein", { tag: "button" });
  st().setTyping(persona, "diagnostician");
  try {
    const result = await api.raiseIssue(persona, { scope: "all", insist, language: langParam(persona) });
    applyTurn(persona, result);
    relay(persona, result);
  } catch (e) {
    fail(persona, e);
  }
}

export async function soundboxPress(persona: PersonaId, button: Scope): Promise<TurnResult | null> {
  const p = PERSONAS[persona];
  if (!p.deviceId) return null;
  try {
    const result = await api.soundboxAsk(persona, p.deviceId, { button, language: langParam(persona) });
    applyTurn(persona, result, { tag: "soundbox" });
    relay(persona, result, undefined, "soundbox");
    return result;
  } catch (e) {
    toast({ title: "Soundbox", body: errorText(e), tone: "risk" });
    return null;
  }
}

export async function requestPulse(persona: PersonaId, kind: "pulse" | "advice"): Promise<void> {
  const p = PERSONAS[persona];
  if (!p.merchantId) return;
  pushUser(persona, kind === "pulse" ? "📊 Aaj ka hisaab" : "🪔 Tyohaar salah", { tag: "button" });
  try {
    const r = kind === "pulse"
      ? await api.pulse(persona, p.merchantId, { audio: true, language: langParam(persona) })
      : await api.advice(persona, p.merchantId, "all", langParam(persona));
    st().pushMessage(persona, {
      id: uid("p"), role: "saarthi", ts: Date.now(), lang: r.language, text: r.text, audio: r.audio,
      result: { kind, facts: r.facts } as any,
    });
  } catch (e) {
    fail(persona, e);
  }
}

export async function applyForLoan(persona: PersonaId, quote: LoanQuote): Promise<void> {
  const p = PERSONAS[persona];
  if (!p.merchantId) return;
  pushUser(persona, "📝 Apply", { tag: "button" });
  try {
    const req = await api.loanApply(persona, { merchant_id: p.merchantId, amount: quote.principal, tenure_months: quote.tenure_months });
    st().upsertLoan(req);
    st().pushMessage(persona, {
      id: uid("l"), role: "saarthi", ts: Date.now(), text: "", result: { loan_request: req, kind: "loan_request" } as any,
    });
    broadcast({ kind: "loan", request: req });
  } catch (e) {
    fail(persona, e);
  }
}

// ------------------------------------------------------------------ demo (DEMO_MODE)
export interface InjectDef {
  key: string;
  emoji: string;
  title: string;
  sub: string;
  persona: PersonaId;
  scenario?: string;
  channel?: "app" | "soundbox" | "chat";
  message?: string;
  risky?: boolean;
}

export const INJECTS: InjectDef[] = [
  { key: "1", emoji: "💰", title: "Settlement short", sub: "Ramesh presses Soundbox: 'settlement check'", persona: "ramesh", scenario: "settlement_short", channel: "soundbox" },
  { key: "2", emoji: "🔇", title: "Soundbox offline", sub: "Ramesh presses Soundbox: device check", persona: "ramesh", scenario: "soundbox_offline", channel: "soundbox" },
  { key: "3", emoji: "❌", title: "Payment failed", sub: "Ramesh taps 'Payments' check", persona: "ramesh", scenario: "payment_failed", channel: "app" },
  { key: "4", emoji: "⚠️", title: "Chargeback", sub: "Gupta taps 'Payments' check · risky", persona: "gupta", scenario: "chargeback", channel: "app", risky: true },
  { key: "5", emoji: "❓", title: "Unknown case", sub: "Merchant types something new", persona: "ramesh", message: "Mera QR sticker phat gaya hai, kya karun?" },
  { key: "6", emoji: "🪔", title: "Festival tips", sub: "Ramesh asks for festival advice", persona: "ramesh", scenario: "festival_low_battery" },
  { key: "7", emoji: "✈️", title: "Travel request", sub: "Arjun · DEL→BOM", persona: "arjun", scenario: "travel_search" },
  { key: "8", emoji: "🔁", title: "Repeat case", sub: "Same chargeback again (learning)", persona: "gupta", scenario: "chargeback", channel: "app" },
];

export async function runInject(def: InjectDef, merchantOverride?: PersonaId): Promise<void> {
  const s = st();
  const entryId = uid("inj");
  s.upsertInject({ id: entryId, ts: Date.now(), scenario: def.scenario ?? "chat", label: def.title, status: "running" });
  const persona = def.scenario ? def.persona : merchantOverride ?? def.persona;
  try {
    let result: TurnResult;
    if (!def.scenario) {
      pushUser(persona, def.message!, {});
      result = await api.chat(persona, { message: def.message!, language: langParam(persona), session_id: sessionId(persona) });
    } else {
      // 1) set up the world (data only)  2) simulate the user's own trigger
      if (def.key !== "8") await api.demoScenario(def.scenario);
      const raw: any = await api.demoTrigger(def.scenario, { channel: def.channel ?? "app", language: st().lang });
      result = raw.case_id ? raw : normalisePlain(raw);
    }
    applyTurn(persona, result, { tag: "demo" });
    relay(persona, result, def.message, "demo");
    s.upsertInject({ id: entryId, ts: Date.now(), scenario: def.scenario ?? "chat", label: def.title, status: "done", outcome: result.status, case_id: result.case_id });
  } catch (e) {
    s.upsertInject({ id: entryId, ts: Date.now(), scenario: def.scenario ?? "chat", label: def.title, status: "error", detail: errorText(e) });
    toast({ title: def.title, body: errorText(e), tone: "risk" });
  }
}

/** /demo/trigger for festival / flight_delay returns {status, reply_text, ...} without a case. */
function normalisePlain(raw: any): TurnResult {
  return {
    case_id: uid("plain"), channel: "app", status: raw.status, language: (raw.language ?? "hi") as any,
    reply_text: raw.reply_text, degraded: false, degrade_reasons: [],
    cost: { tier: raw.tier ?? 0, llm_calls: 0, tokens: 0, cost_inr: 0, tool_calls: 0, duration_ms: 0 },
    booking: raw.booking, ...(raw.facts ? { facts: raw.facts } : {}),
  } as TurnResult;
}

export async function resetDemo(): Promise<void> {
  try {
    await api.demoReset();
    st().resetDemoState();
    broadcast({ kind: "reset" });
    await refreshConsole();
    toast({ title: "Demo reset", body: "Hero data restored on the backend.", tone: "ok" });
  } catch (e) {
    toast({ title: "Reset failed", body: errorText(e), tone: "risk" });
  }
}

// ------------------------------------------------------------------ console
export async function refreshConsole(parts: ("esc" | "loans" | "pb" | "metrics" | "control")[] = ["esc", "loans", "pb", "metrics", "control"]): Promise<void> {
  const tasks: Promise<unknown>[] = [];
  if (parts.includes("esc")) tasks.push(api.escalations().then((escalations) => st().set({ escalations })));
  if (parts.includes("loans")) tasks.push(api.loanRequests().then((loans) => st().set({ loans })));
  if (parts.includes("pb")) tasks.push(api.playbooks().then((playbooks) => st().set({ playbooks })));
  if (parts.includes("metrics")) tasks.push(api.metrics().then((metrics) => st().set({ metrics })));
  if (parts.includes("control")) tasks.push(api.controlState().then((control) => st().set({ control })));
  const results = await Promise.allSettled(tasks);
  // Only a network failure means the backend is down (429/403 etc. are not outages).
  const offline = results.some((r) => r.status === "rejected" && r.reason instanceof ApiError && r.reason.status === 0);
  if (offline) st().set({ apiStatus: "down" });
  else if (results.some((r) => r.status === "fulfilled")) st().set({ apiStatus: "ok" });
}

export async function setKillSwitch(active: boolean, reason: string): Promise<void> {
  try {
    const control = await api.setKillSwitch(active, reason);
    st().set({ control });
    toast({ title: active ? "Autonomy paused" : "Autonomy resumed", body: reason, tone: active ? "risk" : "ok" });
  } catch (e) {
    toast({ title: "Kill switch", body: errorText(e), tone: "risk" });
  }
}

export async function resolveEscalation(ticketId: string, resolution: string, savePlaybook: boolean, action?: string | null): Promise<boolean> {
  try {
    const r = await api.resolveEscalation(ticketId, { resolution, save_as_playbook: savePlaybook, playbook_action: action || null });
    if (r.saved_as_playbook) st().markPlaybookPoint();
    toast({ title: `Ticket ${ticketId} resolved`, body: r.saved_as_playbook ? "Saved as playbook — next similar case auto-resolves." : undefined, tone: "ok" });
    await refreshConsole(["esc", "pb", "metrics"]);
    return true;
  } catch (e) {
    toast({ title: "Resolve failed", body: errorText(e), tone: "risk" });
    return false;
  }
}

export async function decideLoan(id: string, approve: boolean): Promise<void> {
  try {
    const r = await api.decideLoan(id, approve, approve ? "Approved in ops console" : "Rejected in ops console");
    st().upsertLoan(r);
    broadcast({ kind: "loan", request: r });
    await refreshConsole(["loans", "metrics"]);
  } catch (e) {
    toast({ title: "Loan decision failed", body: errorText(e), tone: "risk" });
  }
}
