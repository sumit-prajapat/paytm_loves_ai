/**
 * Data contracts — mirror the EXISTING Saarthi backend (/api/v1, FastAPI).
 * Where the frontend spec proposed different shapes, the backend wins; the UI adapts.
 * Money always arrives as { amount_paise, formatted } or raw numbers from tools — the
 * frontend only displays them.
 */

export type Lang = "hi" | "hinglish" | "en" | "mr";
export type Role = "merchant" | "traveller" | "ops_agent" | "admin";
export type PersonaId = "ramesh" | "sunita" | "gupta" | "arjun" | "meena" | "priya" | "ops" | "admin";

export type AgentName =
  | "captain" | "listener" | "context" | "diagnostician" | "action" | "planner" | "search"
  | "ranker" | "offer" | "guardian" | "handoff" | "learner";

export interface Money {
  amount_paise: number;
  formatted: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  role: Role;
  user_id: string;
  username: string;
  merchant_id: string | null;
  customer_id: string | null;
}

// ---------------------------------------------------------------- check-ups
export type Scope = "settlement" | "device" | "payments" | "refunds" | "all";
export type Channel = "app" | "chat" | "voice" | "soundbox";

export interface Finding {
  scope: string;
  code:
    | "settlement_gap_reconciled" | "settlement_gap_unreconciled" | "settlement_ok" | "settlement_none"
    | "device_low_battery" | "device_offline" | "device_ok" | "device_none"
    | "refund_pending" | "refund_overdue" | "refunds_none"
    | "payments_failed" | "payments_none" | "dispute_open";
  issue_type: string | null;
  resolution: "explain" | "guide" | "escalate" | "info" | "playbook";
  is_issue: boolean;
  confidence: number;
  evidence: string[];
  facts: Record<string, any>;
  playbook?: { id: string; action: string; score: number; root_cause: string } | null;
}

export interface CheckupInfo {
  id: string;
  scope: string;
  status: string;
  cached: boolean;
  checked_at: string;
  minutes_ago?: number;
  recheck_available_in_seconds?: number;
  findings: Finding[];
}

export interface OfferCard {
  type: "offer_card";
  product: string;
  max_amount: Money;
  annual_rate_pct: number;
  text: string;
  actions: string[];
}

export interface LoanQuote {
  principal: number;
  tenure_months: number;
  rate_pct: number;
  monthly_emi: number;
  total_payable: number;
  total_interest: number;
  daily_deduction: number;
  monthly_emi_money?: Money;
}

export interface LoanRequest {
  request_id: string;
  merchant_id?: string;
  amount: Money;
  tenure_months: number;
  rate_pct: number;
  emi: Money;
  status: "awaiting_approval" | "approved" | "rejected";
  approved_by?: string | null;
}

export interface AudioMeta {
  audio_id: string;
  audio_url: string;
  content_type: string;
  expires_at: number;
  bytes: number;
  tts_provider: string;
  tts_fallback: boolean;
  slow: boolean;
}

export interface ScoreBreakdown {
  price_score: number;
  duration_score: number;
  time_fit_score: number;
  stops_score: number;
  refundable_score: number;
  ontime_score: number;
  total_score: number;
}

export interface FlightOption {
  label?: "CHEAPEST" | "FASTEST" | "BEST_BALANCE";
  flight_id: string;
  airline: string;
  from: string;
  to: string;
  date: string;
  dep_time: string;
  arr_time: string;
  duration_min: number;
  stops: number;
  price_inr: number;
  price: Money;
  refundable: boolean;
  on_time_pct: number;
  score_breakdown: ScoreBreakdown;
  risk_flags?: string[];
}

export interface BookingSummary {
  booking_draft_id: string;
  status: "ready_for_human_review";
  passenger_name: string;
  flight: Pick<FlightOption, "flight_id" | "airline" | "from" | "to" | "date" | "dep_time" | "arr_time" | "duration_min" | "stops" | "refundable">;
  fare: Money;
  convenience_fee: Money;
  total_payable: Money;
  cancellation_policy: "refundable" | "non_refundable";
  risk_flags: string[];
  order_id: string;
  payment_link: string;
  human_action_required: string;
}

export interface TravelSlots {
  origin?: string;
  destination?: string;
  date?: string;
  window?: string;
  preference?: string;
}

export interface TurnResult {
  case_id: string;
  channel: Channel;
  status: string; // resolved | no_issue | escalated | needs_input | refused | ready_for_review_and_pay | awaiting_human_approval | quota_exceeded | no_results
  intent?: string;
  language: Lang;
  reply_text: string;
  spoken_text?: string;
  checkup?: CheckupInfo;
  escalation?: { ticket_id: string; reused: boolean } | null;
  offer?: OfferCard | null;
  offer_declined?: boolean;
  loan_quote?: LoanQuote | null;
  loan_request?: LoanRequest;
  roadmap?: string[];
  slots?: TravelSlots;
  missing_slot?: "origin" | "destination" | "date";
  top_options?: FlightOption[];
  recommended?: FlightOption & { reason: string; reason_facts: Record<string, any> };
  booking_summary?: BookingSummary | null;
  handoff_ready?: boolean;
  booking?: TravelBooking | null;
  sensitive_data_blocked?: boolean;
  prompt_injection_blocked?: boolean;
  degraded: boolean;
  degrade_reasons: string[];
  cost: { tier: number; llm_calls: number; tokens: number; cost_inr: number; tool_calls: number; duration_ms: number };
  audio?: AudioMeta;
  // voice turn extras
  transcript?: string;
  transcript_unavailable?: boolean;
  stt_provider?: string;
  device_id?: string;
}

export interface TravelBooking {
  booking_ref: string;
  flight_no: string;
  airline: string;
  from: string;
  to: string;
  date: string;
  dep_time: string;
  status: "on_time" | "delayed" | "cancelled";
  delay_minutes: number;
  terminal?: string | null;
  gate?: string | null;
}

// ---------------------------------------------------------------- console
export interface Dossier {
  ticket_id: string;
  case_id: string;
  checkup_id: string | null;
  merchant_id: string;
  merchant_language: string;
  issue_types: string[];
  reason: string;
  reason_code: string;
  summary: string;
  summary_source: string;
  findings: { code: string; facts: Record<string, any> }[];
  conditions: Record<string, any>;
  evidence: string[];
  suggested_next_step: string;
  user_message: string | null;
  timeline: { ts: string; event: string }[];
}

export interface Escalation {
  ticket_id: string;
  merchant_id: string;
  priority: string;
  status: string;
  eta: string | null;
  created_at: string;
  case_id: string | null;
  checkup_id: string | null;
  dossier: Dossier | null;
  resolved_by: string | null;
}

export interface Playbook {
  playbook_id: string;
  issue_type: string;
  root_cause: string;
  action: string;
  conditions_json: Record<string, any> | null;
  times_used: number;
  created_from_case: string | null;
}

export interface Metrics {
  checkups_run: number;
  checkup_cache_hits: number;
  auto_resolved: number;
  no_issue_found: number;
  escalated: number;
  escalation_rate_pct: number;
  tickets_deflected: number;
  support_cost_saved_inr: number;
  support_cost_per_ticket_inr: number;
  avg_resolution_seconds: number;
  loan_leads: number;
  offers_shown_merchants: number;
  offers_declined_merchants: number;
  offer_conversion_pct: number;
  requests_total: number;
  tier_mix: Record<string, { requests: number; pct: number }>;
  llm_calls: number;
  llm_cache_hits: number;
  llm_calls_avoided: number;
  llm_tokens: number;
  llm_cost_inr: number;
  cost_per_resolution_inr: number;
  travel_shortlist_avg_ms: number;
  validator_violations_since_start: number;
  disclaimer: string;
}

export interface ControlState {
  kill_switch_active: boolean;
  financial_impact_threshold_inr: number;
  auto_resolve_confidence_threshold: number;
  clarify_confidence_threshold: number;
  last_updated: string;
  reason: string | null;
  updated_by: string | null;
}

export interface AuditEntry {
  id: number;
  case_id: string;
  actor: string;
  action: string;
  detail: any;
  previous_hash: string;
  hash: string;
  ip_address: string | null;
  correlation_id: string | null;
  timestamp: string;
}

export interface DeviceStatus {
  device_id: string;
  merchant_id: string;
  model: string;
  battery: number;
  network: string;
  last_seen: string;
  firmware: string;
  is_offline: boolean;
  minutes_since_seen: number;
  diagnosis: string;
  action_recommendation: string;
}

export interface Merchant {
  id: string;
  name: string;
  city: string;
  state: string;
  language: string;
  business_type: string;
  device_id: string | null;
  joined_on: string;
  risk_tier: string;
  kyc_status: string;
}

export interface PulseResponse {
  merchant_id: string;
  language: Lang;
  text: string;
  facts: Record<string, any>;
  tier: number;
  audio?: AudioMeta;
}

export interface Health {
  status: string;
  app_name: string;
  environment: string;
  demo_mode: boolean;
  database: string;
  timestamp: string;
}

// ---------------------------------------------------------------- realtime
/** /ws/trace message (one agent step). */
export interface TraceStep {
  type: "agent_step";
  run_id: string;
  case_id: string;
  agent: string; // backend agent name (may be llm_gateway / pulse)
  tool: string | null;
  input: any;
  output: any;
  confidence: number;
  cost_tier: number;
  tokens: number;
  cost_inr: number;
  latency_ms: number;
  ts: string;
}

export type ConsoleEvent =
  | { type: "escalation_created"; ts: string; ticket: Dossier }
  | { type: "escalation_updated"; ts: string; ticket_id: string; status: string; learned_playbook: any }
  | ({ type: "loan_request_updated"; ts: string } & LoanRequest)
  | ({ type: "killswitch_changed"; ts: string } & ControlState);

export interface SoundboxAnswerEvent {
  type: "soundbox_answer";
  ts: string;
  merchant_id: string;
  device_id: string;
  case_id: string;
  text: string;
  audio_url: string;
  language: Lang;
}

// ---------------------------------------------------------------- eval
export interface EvalRow {
  id: string;
  scenario: string;
  language: string;
  input?: string;
  expected: string;
  actual: string;
  passed: boolean;
  tier: number;
  violations: number;
  reply: string;
  latency_ms?: number;
}
export interface EvalResults {
  generated_at: string;
  summary: {
    cases: number;
    hinglish_pct: number;
    accuracy: number;
    deflection_pct: number;
    escalation_precision: number;
    escalation_recall: number;
    validator_violations: number;
    tier_mix: Record<string, number>;
    llm_calls: number;
    cost_inr_total: number;
    cost_per_resolution_inr: number;
    avg_latency_ms: number;
    travel_consistency: string;
  };
  verdict: Record<string, boolean>;
  rows: EvalRow[];
}
