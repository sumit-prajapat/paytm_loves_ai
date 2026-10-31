/**
 * Offline mock of the backend (VITE_USE_MOCKS=true only). Responses copy the REAL backend's
 * shapes and hero seed values (Ramesh gap 1800 = 1200 + 600, Sunita refund 1450, Gupta
 * chargeback 6500, DEL->BOM flights). Deterministic: same input, same output.
 */
import type { Finding, PersonaId, TokenResponse, TurnResult } from "@/types/contracts";
import { emitFake } from "./fakeSocket";

const money = (v: number) => ({ amount_paise: Math.round(v * 100), formatted: `₹${v.toLocaleString("en-IN")}` });
let seq = 0;
const id = (p: string) => `${p}_mock${(++seq).toString(36).padStart(4, "0")}`;
const now = () => new Date().toISOString();

const ROLE: Record<PersonaId, TokenResponse["role"]> = {
  ramesh: "merchant", sunita: "merchant", gupta: "merchant", arjun: "traveller", meena: "traveller", priya: "traveller", ops: "ops_agent", admin: "admin",
};
const SUBJECT: Partial<Record<PersonaId, string>> = { ramesh: "m_ramesh", sunita: "m_sunita", gupta: "m_disputed", arjun: "c_arjun", meena: "c_meena", priya: "c_arjun" };

export function mockToken(p: PersonaId): TokenResponse {
  return {
    access_token: `mock.${p}.token`, refresh_token: "mock", token_type: "bearer", role: ROLE[p], user_id: `usr_${p}`, username: p,
    merchant_id: ROLE[p] === "merchant" ? SUBJECT[p]! : null, customer_id: ROLE[p] === "traveller" ? SUBJECT[p]! : null,
  };
}

// ------------------------------------------------------------------ world state
const world = {
  kill: false,
  battery: 12,
  offlineMin: 15,
  escalations: [] as any[],
  playbooks: [
    { playbook_id: "pb_settlement_reconciled", issue_type: "settlement_short", root_cause: "refund_adjustment_and_fee", action: "explain_breakdown", conditions_json: {}, times_used: 14, created_from_case: "historical_resolution" },
  ] as any[],
  loans: [] as any[],
  declined: false,
  offered: false,
  checkups: { resolved: 0, escalated: 0, no_issue: 0 },
  audit: [] as any[],
  booking: { status: "on_time", delay: 0 },
  pendingTravel: {} as Record<string, any>,
};

function audit(case_id: string, actor: string, action: string, detail: any) {
  world.audit.unshift({ id: world.audit.length + 1, case_id, actor, action, detail, previous_hash: "mock", hash: "mock", ip_address: null, correlation_id: null, timestamp: now() });
}

function trace(case_id: string, steps: [string, string, any, any, number?][]) {
  steps.forEach(([agent, tool, input, output, confidence], i) =>
    emitFake("/ws/trace", {
      type: "agent_step", run_id: id("run"), case_id, agent, tool, input, output, confidence: confidence ?? 1,
      cost_tier: 0, tokens: 0, cost_inr: 0, latency_ms: 3 + i, ts: now(),
    }, 120 * i));
}

function base(case_id: string, channel: any, lang: any, extra: Partial<TurnResult>): TurnResult {
  return { case_id, channel, status: "resolved", language: lang ?? "hinglish", reply_text: "", degraded: false, degrade_reasons: [], cost: { tier: 0, llm_calls: 0, tokens: 0, cost_inr: 0, tool_calls: 8, duration_ms: 12 }, ...extra } as TurnResult;
}

const F = {
  settlement: (): Finding => ({
    scope: "settlement", code: "settlement_gap_reconciled", issue_type: "settlement_short", resolution: "explain", is_issue: true, confidence: 0.98,
    evidence: ["settlement:set_ramesh_today", "reconciled_items", "playbook:pb_settlement_reconciled"],
    facts: { id: "set_ramesh_today", date: new Date().toISOString().slice(0, 10), is_today: true, expected: 24500, actual: 22700, gap: 1800, expected_money: money(24500), actual_money: money(22700), gap_money: money(1800),
      items: [{ type: "refund_adjustment", amount: 1200, amount_money: money(1200) }, { type: "fee", amount: 600, amount_money: money(600) }] },
  }),
  device: (): Finding => world.offlineMin > 120
    ? { scope: "device", code: "device_offline", issue_type: "soundbox_offline", resolution: "guide", is_issue: true, confidence: 0.9, evidence: ["device:soundbox_ramesh_01"], facts: { device_id: "soundbox_ramesh_01", battery: world.battery, network: "4G Airtel", minutes_since_seen: world.offlineMin } }
    : { scope: "device", code: world.battery <= 20 ? "device_low_battery" : "device_ok", issue_type: "soundbox_offline", resolution: world.battery <= 20 ? "guide" : "info", is_issue: world.battery <= 20, confidence: 0.96, evidence: ["device:soundbox_ramesh_01"], facts: { device_id: "soundbox_ramesh_01", battery: world.battery, network: "4G Airtel", minutes_since_seen: world.offlineMin } },
  refundSunita: (): Finding => ({ scope: "refunds", code: "refund_overdue", issue_type: "refund_status", resolution: "escalate", is_issue: true, confidence: 0.95, evidence: ["refund:ref_sunita_overdue_01"], facts: { refund_id: "ref_sunita_overdue_01", txn_id: "txn_sunita_refund_01", amount: 1450, amount_money: money(1450), bank_ref: "REF9876543210IN", expected_by: new Date(Date.now() - 2 * 864e5).toISOString().slice(0, 10), status: "overdue" } }),
  noRefund: (): Finding => ({ scope: "refunds", code: "refunds_none", issue_type: null, resolution: "info", is_issue: false, confidence: 1, evidence: [], facts: {} }),
  dispute: (learned: boolean): Finding => ({
    scope: "payments", code: "dispute_open", issue_type: "chargeback_dispute", resolution: learned ? "playbook" : "escalate", is_issue: true, confidence: learned ? 1 : 0.55,
    evidence: ["dispute:disp_case_7701", "txn:txn_chargeback_99"],
    facts: { dispute_id: "disp_case_7701", txn_id: "txn_chargeback_99", amount: 6500, amount_money: money(6500), deadline: new Date(Date.now() + 4 * 864e5).toISOString().slice(0, 10), reason: "Cardholder claims card was stolen" },
    playbook: learned ? { id: world.playbooks.find((p) => p.issue_type === "chargeback_dispute").playbook_id, action: "request_evidence_upload", score: 1, root_cause: "delivery_proof_verified" } : null,
  }),
};

function checkup(persona: PersonaId, scope: string, channel: any, lang: any): TurnResult {
  const case_id = id("case");
  const merchant = SUBJECT[persona]!;
  const findings: Finding[] = [];
  if (merchant === "m_ramesh") {
    if (scope === "settlement" || scope === "all") findings.push(F.settlement());
    if (scope === "device" || scope === "all") findings.push(F.device());
    if (scope === "refunds" || scope === "payments") findings.push(F.noRefund());
  } else if (merchant === "m_sunita") findings.push(F.refundSunita());
  else if (merchant === "m_disputed") findings.push(F.dispute(world.playbooks.some((p) => p.issue_type === "chargeback_dispute")));
  const esc = findings.filter((f) => f.resolution === "escalate");
  let ticket: string | null = null;
  if (esc.length) {
    ticket = id("tkt");
    const dossier = { ticket_id: ticket, case_id, checkup_id: id("chk"), merchant_id: merchant, merchant_language: "hi", issue_types: [esc[0].issue_type], reason: `${esc[0].code} needs a specialist`, reason_code: esc[0].code, summary: `${esc[0].issue_type} for ${merchant}: needs a specialist.`, summary_source: "template", findings: esc.map((f) => ({ code: f.code, facts: f.facts })), conditions: { dispute_reason_category: "fraud_claim" }, evidence: esc.flatMap((f) => f.evidence), suggested_next_step: "Collect invoice and delivery proof from the merchant and respond before the deadline.", user_message: null, timeline: [] };
    world.escalations.unshift({ ticket_id: ticket, merchant_id: merchant, priority: "high", status: "open", eta: null, created_at: now(), case_id, checkup_id: dossier.checkup_id, dossier, resolved_by: null });
    emitFake("/ws/console", { type: "escalation_created", ts: now(), ticket: dossier }, 700);
    audit(case_id, "handoff_agent", "ESCALATED_TO_HUMAN", { ticket_id: ticket });
  }
  const status = ticket ? "escalated" : findings.some((f) => f.is_issue) ? "resolved" : "no_issue";
  world.checkups[status as "resolved"] += 1;
  const text: Record<string, string> = {
    settlement_gap_reconciled: "Ramesh ji, aaj ka settlement ₹1,800 kam aaya hai: ₹1,200 refund adjustment aur ₹600 fees. Aapko kuch karne ki zaroorat nahi.",
    device_low_battery: `Aapke Soundbox ki battery ${world.battery}% hai. Kripya charger lagaiye.`,
    device_offline: `Aapka Soundbox ${world.offlineMin} minute se offline hai. Kripya use band karke phir chalu kijiye aur network check kijiye.`,
    device_ok: `Aapka Soundbox theek chal raha hai. Battery ${world.battery}% hai.`,
    refund_overdue: `Aapka ₹1,450 ka refund (bank ref REF9876543210IN) aana tha, par abhi tak nahi aaya. Humne ise banking team ko bhej diya hai (ticket ${ticket}).`,
    refunds_none: "Aapka koi refund pending nahi hai.",
    dispute_open: `₹6,500 ka chargeback dispute khula hai. Yeh jokhim wala case hai, isliye specialist ise dekhenge (ticket ${ticket}).`,
  };
  const reply = findings.map((f) => (f.resolution === "playbook" ? "₹6,500 ke chargeback ke liye: kripya bill aur delivery ka saboot app mein upload kijiye. Pichhle aise case isi tarah suljhe the." : text[f.code])).join("\n");
  let offer = null;
  if (status === "resolved" && merchant === "m_ramesh" && !world.declined && !world.offered && channel !== "soundbox") {
    world.offered = true;
    offer = { type: "offer_card", product: "working_capital_loan", max_amount: money(100000), annual_rate_pct: 14, text: "Aapke collection record ke aadhar par aap ₹1,00,000 tak ke loan ke liye eligible hain. Kya aap jaankari chahenge?", actions: ["know_more", "decline"] };
  }
  trace(case_id, [
    ["captain", "captain_plan", { trigger: { channel, request_type: "checkup", subject_id: merchant, scope } }, { plan: ["context", "diagnostician", "guardian", "action|handoff", "offer?"] }],
    ["context", "fetch_context_bundle", { subject_id: merchant }, { found: true }],
    ["diagnostician", "run_checkup_diagnostics", { merchant_id: merchant, scope }, { findings: findings.map((f) => ({ code: f.code, resolution: f.resolution })) }, Math.min(...findings.map((f) => f.confidence))],
    ...(findings.some((f) => f.playbook) ? [["diagnostician", "match_playbook", { issue_type: "chargeback_dispute" }, { score: 1, usable: true }, 1] as any] : []),
    ["guardian", "evaluate_action_policy", { action_class: ticket ? "create_ticket" : "explain", confidence: findings[0]?.confidence ?? 1 }, { decision: ticket ? "escalate" : "allow", reason: ticket ? "Risky case: a specialist will handle it" : "Policy checks passed" }],
    ticket ? ["handoff", "package_escalation_dossier", {}, { ticket_id: ticket }] : ["action", "render_explanation", {}, { violations: [] }],
    ["captain", "finalize_response", { channel, request_type: "checkup" }, { status }],
  ]);
  return base(case_id, channel, lang ?? "hinglish", {
    status, reply_text: reply || "Sab theek hai, koi samasya nahi mili.", spoken_text: reply,
    checkup: { id: id("chk"), scope, status, cached: false, checked_at: now(), findings }, escalation: ticket ? { ticket_id: ticket, reused: false } : null, offer: offer as any,
  });
}

const FLIGHTS = [
  { label: "CHEAPEST", flight_id: "fl_demo_cheap", airline: "SpiceJet", dep_time: "17:05", arr_time: "22:20", duration_min: 315, stops: 1, price_inr: 3700, refundable: false, on_time_pct: 84 },
  { label: "FASTEST", flight_id: "fl_demo_fast", airline: "Air India", dep_time: "18:30", arr_time: "20:25", duration_min: 115, stops: 0, price_inr: 5600, refundable: true, on_time_pct: 90 },
  { label: "BEST_BALANCE", flight_id: "fl_demo_best", airline: "Vistara", dep_time: "19:00", arr_time: "21:05", duration_min: 125, stops: 0, price_inr: 4600, refundable: true, on_time_pct: 93 },
];

function travel(persona: PersonaId, text: string, lang: any, elder: boolean): TurnResult {
  const case_id = id("case");
  const t = text.toLowerCase();
  const st = world.pendingTravel[persona] ?? {};
  if (/delhi|dilli|दिल्ली/.test(t)) st.origin = "DEL";
  if (/mumbai|मुंबई/.test(t)) st.destination = "BOM";
  if (/kal|tomorrow|कल/.test(t)) st.date = new Date(Date.now() + 864e5).toISOString().slice(0, 10);
  if (/shaam|evening|शाम/.test(t)) st.window = "evening";
  if (!st.origin) st.origin = "DEL";
  const missing = !st.destination ? "destination" : !st.date ? "date" : null;
  world.pendingTravel[persona] = st;
  if (missing) {
    trace(case_id, [["planner", "generate_travel_roadmap", { slots: st }, { missing }, 0.7]]);
    return base(case_id, "chat", lang, { status: "needs_input", intent: "travel_flight_request", reply_text: missing === "destination" ? "Aapko kahan jaana hai?" : "Kis tareekh ko jaana hai?", missing_slot: missing as any, slots: { ...st } });
  }
  delete world.pendingTravel[persona];
  const date = st.date;
  const opts = (elder ? FLIGHTS.filter((f) => f.label === "BEST_BALANCE") : FLIGHTS).map((f) => ({
    ...f, from: "DEL", to: "BOM", date, price: money(f.price_inr), risk_flags: [!f.refundable && "non_refundable", f.stops > 0 && "has_stops"].filter(Boolean) as string[],
    score_breakdown: { price_score: f.label === "CHEAPEST" ? 0.3 : 0.16, duration_score: f.label === "CHEAPEST" ? 0 : 0.24, time_fit_score: 0.15, stops_score: f.stops ? 0.05 : 0.1, refundable_score: f.refundable ? 0.1 : 0, ontime_score: f.on_time_pct / 1000, total_score: f.label === "BEST_BALANCE" ? 0.79 : f.label === "FASTEST" ? 0.72 : 0.61 },
  }));
  const rec = opts.find((o) => o.label === "BEST_BALANCE")!;
  const reason = "Sujhav: Vistara, ₹4,600. Yeh sabse saste se ₹900 zyada hai par 190 minute jaldi pahunchata hai. Isme free cancellation bhi hai.";
  trace(case_id, [
    ["captain", "captain_plan", { trigger: { channel: "chat", request_type: "chat", subject_id: SUBJECT[persona] } }, { plan: ["listener", "planner", "search", "ranker", "guardian"] }],
    ["listener", "classify_intent_and_extract_slots", { message: text }, { intent: "travel_flight_request", tier: 0 }, 0.92],
    ["planner", "generate_travel_roadmap", { slots: st }, { missing: null }],
    ["search", "search_flight_inventories", { from: "DEL", to: "BOM", date }, { candidates: 14 }],
    ["guardian", "evaluate_action_policy", { action_class: "handoff_payment_link" }, { decision: "allow", reason: "Policy checks passed" }],
    ["ranker", "rank_and_package_human_handoff", {}, { recommended: rec.flight_id, score: 0.79 }],
    ["captain", "finalize_response", { channel: "chat", request_type: "chat" }, { status: "ready_for_review_and_pay" }],
  ]);
  return base(case_id, "chat", lang, {
    status: "ready_for_review_and_pay", intent: "travel_flight_request", reply_text: `${reason} Review aur payment aap khud 'Review and Pay' link par karenge. Saarthi kabhi payment ya booking confirm nahi karta.`,
    slots: { ...st, preference: "balanced" },
    roadmap: [`Aapki zaroorat samjhi: DEL se BOM, ${date}`, `${date} aur ek din aage-peeche ki flights dhoondhi`, "'evening' departure ko praathmikta", "Har vikalp ko daam, samay, timing, stop, refund aur on-time record par score kiya ('balanced')", "Jokhim check kiye (non-refundable fare, stop)", "CHEAPEST / FASTEST / BEST_BALANCE aur aapke liye Review & Pay link taiyaar"],
    top_options: opts as any, recommended: { ...rec, reason, reason_facts: { price: 4600, price_diff: 900, minutes_saved: 190 } } as any,
    booking_summary: { booking_draft_id: id("bk_draft"), status: "ready_for_human_review", passenger_name: persona === "meena" ? "Meena Devi" : "Arjun Sharma", flight: { flight_id: rec.flight_id, airline: rec.airline, from: "DEL", to: "BOM", date, dep_time: rec.dep_time, arr_time: rec.arr_time, duration_min: rec.duration_min, stops: 0, refundable: true }, fare: money(4600), convenience_fee: money(0), total_payable: money(4600), cancellation_policy: "refundable", risk_flags: [], order_id: id("ord"), payment_link: "mock://checkout", human_action_required: "Review and pay yourself." },
    handoff_ready: true,
  });
}

function chat(persona: PersonaId, body: any): TurnResult {
  const text: string = body.message ?? "";
  const t = text.toLowerCase();
  const lang = body.language ?? (/[ऀ-ॿ]/.test(text) ? "hi" : /\b(kya|hai|kyun|aaya|chahiye|mera|kal|se)\b/.test(t) ? "hinglish" : "en");
  const case_id = id("case");
  if (/\b(otp|pin|password|cvv)\b|ओटीपी|\d{6}.*code/.test(t)) {
    return base(case_id, "chat", lang, { status: "refused", intent: "unsafe_request", sensitive_data_blocked: true, reply_text: "Savdhaan: Paytm ya Saarthi kabhi bhi aapka UPI PIN, OTP ya password nahi maangta. Ise kisi ke saath share na karein." });
  }
  if (/pay (for me|kar do)|payment kar do|book it and pay/.test(t) && !/flight|delhi|mumbai/.test(t)) {
    return base(case_id, "chat", lang, { status: "refused", intent: "payment_request", reply_text: "Suraksha niyamon ke anusaar Saarthi kabhi khud payment nahi karta, na booking confirm karta hai." });
  }
  if (ROLE[persona] === "traveller") {
    if (/bk-/.test(t)) return base(case_id, "chat", lang, { intent: "travel_status", reply_text: `Booking BK-ARJ-1001: Air India AI-865 ${world.booking.status === "on_time" ? "samay par hai" : `${world.booking.delay} minute late hai`}.`, booking: { booking_ref: "BK-ARJ-1001", flight_no: "AI-865", airline: "Air India", from: "DEL", to: "BOM", date: new Date(Date.now() + 864e5).toISOString().slice(0, 10), dep_time: "19:00", status: world.booking.status as any, delay_minutes: world.booking.delay, gate: "32B" } });
    return travel(persona, text, lang, !!body.elder_mode);
  }
  if (/nahi chahiye|mat do|not interested|नहीं चाहिए/.test(t)) {
    world.declined = true;
    audit(case_id, persona, "OFFER_DECLINED_CONSENT_RESPECTED", {});
    return base(case_id, "chat", lang, { intent: "decline_offer", offer_declined: true, reply_text: "Theek hai, humne note kar liya. Hum dobara loan ka sujhav nahi denge." });
  }
  if (/loan|emi|लोन/.test(t)) {
    if (!/\d/.test(t)) return base(case_id, "chat", lang, { status: "needs_input", intent: "loan_emi_query", reply_text: "Aapko kitna loan chahiye?" });
    return base(case_id, "chat", lang, { intent: "loan_emi_query", reply_text: "₹50,000 ke liye 12 mahine ki EMI ₹4,489 mahina hogi (14% saalana byaaj). Aavedan ke liye 'apply' boliye; manzoori ek vyakti dega.", loan_quote: { principal: 50000, tenure_months: 12, rate_pct: 14, monthly_emi: 4489.36, total_payable: 53872.32, total_interest: 3872.32, daily_deduction: 149.65, monthly_emi_money: money(4489.36) } });
  }
  if (/settlement|सेटलमेंट|kam aaya|setlment/.test(t)) return { ...checkup(persona, "settlement", "chat", lang), intent: "settlement_short" };
  if (/soundbox|battery|साउंडबॉक्स|awaaz/.test(t)) return { ...checkup(persona, "device", "chat", lang), intent: "soundbox_offline" };
  if (/refund|fail|wapas|रिफंड/.test(t)) return { ...checkup(persona, "refunds", "chat", lang), intent: "refund_status" };
  if (/chargeback|dispute/.test(t)) return { ...checkup(persona, "payments", "chat", lang), intent: "chargeback_dispute" };
  if (/samajh gaya|dhanyavaad|thanks|namaste|hello/.test(t)) return base(case_id, "chat", lang, { intent: "greeting", reply_text: "Namaste! Main Saarthi hoon. Main aapka settlement, Soundbox, payment aur refund check kar sakta hoon." });
  return base(case_id, "chat", lang, { status: "needs_input", intent: "unknown", reply_text: "Kripya bataiye, aapko kis mein madad chahiye: settlement, Soundbox, payment/refund ya loan?" });
}

function metrics() {
  const c = world.checkups;
  const run = c.resolved + c.escalated + c.no_issue;
  const deflected = c.resolved + c.no_issue;
  return {
    checkups_run: run, checkup_cache_hits: 0, auto_resolved: c.resolved, no_issue_found: c.no_issue, escalated: c.escalated,
    escalation_rate_pct: run ? Math.round((1000 * c.escalated) / run) / 10 : 0, tickets_deflected: deflected, support_cost_saved_inr: deflected * 180,
    support_cost_per_ticket_inr: 180, avg_resolution_seconds: 0.03, loan_leads: world.loans.length, offers_shown_merchants: world.offered ? 1 : 0,
    offers_declined_merchants: world.declined ? 1 : 0, offer_conversion_pct: 0, requests_total: run, tier_mix: { tier0: { requests: run, pct: 100 } },
    llm_calls: 0, llm_cache_hits: 0, llm_calls_avoided: run, llm_tokens: 0, llm_cost_inr: 0, cost_per_resolution_inr: 0, travel_shortlist_avg_ms: 14,
    validator_violations_since_start: 0, disclaimer: "ALL FIGURES ARE MEASURED ON SIMULATED DATA (MOCK MODE)",
  };
}

const control = () => ({ kill_switch_active: world.kill, financial_impact_threshold_inr: 5000, auto_resolve_confidence_threshold: 0.85, clarify_confidence_threshold: 0.6, last_updated: now(), reason: null, updated_by: "mock" });

const STORE_KEY = "saarthi.mock.world";
function loadWorld() {
  try {
    const raw = localStorage.getItem(STORE_KEY);
    if (raw) Object.assign(world, JSON.parse(raw));
  } catch { /* ignore */ }
}
function saveWorld() {
  try { localStorage.setItem(STORE_KEY, JSON.stringify(world)); } catch { /* ignore */ }
}

/** Shared across tabs of the same browser via localStorage, like a real backend would be. */
export async function mockRequest<T>(persona: PersonaId | null, method: string, path: string, body: any, opts: { form?: FormData; raw?: boolean }): Promise<T> {
  await new Promise((r) => setTimeout(r, 150));
  loadWorld();
  try {
    return await handle<T>(persona, method, path, body, opts);
  } finally {
    saveWorld();
  }
}

async function handle<T>(persona: PersonaId | null, method: string, path: string, body: any, opts: { form?: FormData; raw?: boolean }): Promise<T> {
  const p = persona ?? "ops";
  const [route] = path.split("?");
  const r = (v: unknown) => v as T;
  if (route === "/health") return r({ status: "ok", app_name: "Saarthi (mock)", environment: "mock", demo_mode: true, database: "mock", timestamp: now() });
  if (route === "/chat") return r(chat(p, body));
  if (route === "/checkups") return r(checkup(p, body.scope, body.channel ?? "app", body.language));
  if (route === "/issues") return r(checkup(p, body.scope ?? "all", "app", body.language));
  if (route.startsWith("/soundbox/")) return r({ ...checkup(p, body.button ?? "settlement", "soundbox", body.language), device_id: route.split("/")[2] });
  if (route === "/voice/turn") {
    const name = (opts.form?.get("file") as File | null)?.name ?? "";
    if (!name.includes("settlement")) return r(base(id("case"), "voice", "hi", { status: "needs_input", transcript: "", transcript_unavailable: true, reply_text: "Maaf kijiye, theek se sunaai nahi diya. Kripya dobara boliye." }));
    return r({ ...chat(p, { message: "Aaj ka settlement kam kyun aaya?" }), transcript: "Aaj ka settlement kam kyun aaya?" });
  }
  if (route === "/voice/tts") return r(new Blob([]));
  if (route.startsWith("/devices/")) return r({ device_id: "soundbox_ramesh_01", merchant_id: "m_ramesh", model: "Soundbox v3 4G", battery: world.battery, network: "4G Airtel", last_seen: now(), firmware: "v2.4.1", is_offline: world.offlineMin > 120, minutes_since_seen: world.offlineMin, diagnosis: "", action_recommendation: "" });
  if (route.startsWith("/merchants/")) return r({ id: "m_ramesh", name: "Ramesh Kirana Store", city: "Delhi", state: "Delhi", language: "hi", business_type: "kirana", device_id: "soundbox_ramesh_01", joined_on: now(), risk_tier: "low", kyc_status: "verified" });
  if (route.startsWith("/pulse/")) return r({ merchant_id: "m_ramesh", language: "hinglish", text: `Shubh prabhat Ramesh ji! aaj ka settlement ₹22,700 aaya, jo ummeed se ₹1,800 kam hai. Pending refund: 0. Khule dispute: 0. Soundbox battery: ${world.battery}%.`, facts: { pending_refunds: 0, open_disputes: 0, battery: world.battery, settlement: { actual: 22700, gap: 1800 } }, tier: 0 });
  if (route.startsWith("/advice/")) return r({ merchant_id: "m_ramesh", language: "hinglish", topic: "all", text: `Diwali 5 din mein hai. Bheed badhegi: Soundbox poora charge rakhiye (abhi ${world.battery}%).`, facts: { festival: "Diwali", days_until: 5, battery: world.battery }, tier: 0 });
  if (route === "/loans/requests" && method === "POST") {
    const req = { request_id: id("loan_req"), merchant_id: body.merchant_id, amount: money(body.amount), tenure_months: body.tenure_months, rate_pct: 14, emi: money(4489.36), status: "awaiting_approval", approved_by: null };
    world.loans.unshift(req);
    emitFake("/ws/console", { type: "loan_request_updated", ts: now(), ...req }, 200);
    return r({ ...req, human_approval_required: true });
  }
  if (route === "/loans/requests") return r(world.loans.filter((l) => l.status === "awaiting_approval"));
  const loanMatch = route.match(/^\/loans\/requests\/(.+)\/(approve|reject)$/);
  if (loanMatch) {
    const l = world.loans.find((x) => x.request_id === loanMatch[1]);
    l.status = loanMatch[2] === "approve" ? "approved" : "rejected";
    l.approved_by = "ops_agent_1";
    emitFake("/ws/console", { type: "loan_request_updated", ts: now(), ...l });
    return r({ ...l });
  }
  if (route.startsWith("/travel/status/")) return r({ text: "Booking BK-ARJ-1001 samay par hai.", booking: { booking_ref: "BK-ARJ-1001", flight_no: "AI-865", airline: "Air India", from: "DEL", to: "BOM", date: now().slice(0, 10), dep_time: "19:00", status: world.booking.status, delay_minutes: world.booking.delay, gate: "32B" } });
  if (route.startsWith("/payments/mock-checkout/")) return r({ order_id: route.split("/").pop(), status: "simulated_checkout", notice: "SIMULATED (mock mode)." });
  if (route === "/metrics") return r(metrics());
  if (route === "/escalations") return r(world.escalations.filter((e) => e.status === "open"));
  const escMatch = route.match(/^\/escalations\/(.+)\/resolve$/);
  if (escMatch) {
    const e = world.escalations.find((x) => x.ticket_id === escMatch[1]);
    e.status = "resolved";
    let learned = null;
    if (body.save_as_playbook && e.dossier.issue_types.includes("chargeback_dispute")) {
      learned = { playbook_id: id("pb"), issue_type: "chargeback_dispute", root_cause: body.root_cause ?? "delivery_proof_verified", action: body.playbook_action ?? "request_evidence_upload", conditions_json: e.dossier.conditions, times_used: 0, created_from_case: e.case_id };
      world.playbooks.push(learned);
    }
    audit(e.ticket_id, "ops_agent_1", "ESCALATION_RESOLVED_BY_HUMAN", { resolution: body.resolution });
    emitFake("/ws/console", { type: "escalation_updated", ts: now(), ticket_id: e.ticket_id, status: "resolved", learned_playbook: learned });
    return r({ ticket_id: e.ticket_id, status: "resolved", resolved_by: "ops_agent_1", saved_as_playbook: !!learned, learned_playbook: learned });
  }
  if (route === "/playbooks") return r(world.playbooks);
  if (route === "/control/state") return r(control());
  if (route === "/control/kill-switch") {
    world.kill = body.active;
    audit("system_control", "admin", body.active ? "KILL_SWITCH_ENGAGED" : "KILL_SWITCH_DISENGAGED", { reason: body.reason });
    emitFake("/ws/console", { type: "killswitch_changed", ts: now(), ...control() });
    return r(control());
  }
  if (route === "/audit") return r(world.audit.slice(0, 60));
  if (route === "/audit/verify") return r({ chain_intact: true, total_records: world.audit.length, message: "mock" });
  if (route.startsWith("/demo/scenario/")) {
    const name = route.split("/").pop();
    if (name === "soundbox_offline") { world.offlineMin = 180; world.battery = 64; }
    if (name === "low_battery" || name === "festival_low_battery") { world.offlineMin = 15; world.battery = 12; }
    if (name === "flight_delay") world.booking = { status: "delayed", delay: 45 };
    return r({ scenario: name, mutated: { changed: name }, processing_started: false });
  }
  if (route.startsWith("/demo/trigger/")) {
    const name = route.split("/").pop()!;
    const ch = body?.channel ?? "app";
    if (name === "travel_search") return r(chat("arjun", { message: body?.message ?? "Delhi se Mumbai kal shaam ka flight" }));
    if (name === "festival_low_battery") return r({ status: "resolved", reply_text: `Diwali 5 din mein hai. Soundbox poora charge rakhiye (abhi ${world.battery}%).`, facts: {}, tier: 0 });
    const map: Record<string, [PersonaId, string]> = { settlement_short: ["ramesh", "settlement"], soundbox_offline: ["ramesh", "device"], low_battery: ["ramesh", "device"], payment_failed: ["ramesh", "payments"], refund_overdue: ["sunita", "refunds"], chargeback: ["gupta", "payments"] };
    const [hero, scope] = map[name] ?? ["ramesh", "all"];
    return r(checkup(hero, scope, ch, body?.language));
  }
  if (route === "/demo/reset") {
    Object.assign(world, { kill: false, battery: 12, offlineMin: 15, escalations: [], loans: [], declined: false, offered: false, checkups: { resolved: 0, escalated: 0, no_issue: 0 }, booking: { status: "on_time", delay: 0 } });
    world.playbooks = world.playbooks.filter((p) => p.created_from_case === "historical_resolution");
    return r({ status: "reset", cleared: {} });
  }
  throw new Error(`Mock has no handler for ${method} ${path}`);
}
