/**
 * Typed client for the EXISTING backend (/api/v1). All endpoints and payloads below exist in
 * the backend; nothing is invented. With VITE_USE_MOCKS=true the same calls are served by the
 * offline mock adapter (src/mocks), which returns backend-shaped data.
 */
import { config } from "./config";
import { getToken } from "./auth";
import type {
  AuditEntry, Channel, ControlState, DeviceStatus, Escalation, Health, LoanRequest, Merchant, Metrics,
  PersonaId, Playbook, PulseResponse, Scope, TravelBooking, TurnResult,
} from "@/types/contracts";

export class ApiError extends Error {
  constructor(public status: number, message: string, public correlationId?: string, public code?: string) {
    super(message);
  }
}

type Method = "GET" | "POST";

async function parseError(res: Response): Promise<ApiError> {
  const body = await res.json().catch(() => null);
  // Backend formats: {error: true, code, message, correlation_id} or {error: {code, message, correlation_id}}
  const e = body && typeof body.error === "object" ? body.error : body;
  return new ApiError(res.status, e?.message || res.statusText || "Request failed", e?.correlation_id, e?.code);
}

async function request<T>(
  persona: PersonaId | null,
  method: Method,
  path: string,
  body?: unknown,
  opts: { form?: FormData; raw?: boolean } = {},
): Promise<T> {
  if (config.useMocks) {
    const { mockRequest } = await import("@/mocks/mockApi");
    return mockRequest<T>(persona, method, path, body, opts);
  }
  const doFetch = async (force: boolean) => {
    const headers: Record<string, string> = {};
    if (persona) headers.Authorization = `Bearer ${await getToken(persona, force)}`;
    if (body !== undefined && !opts.form) headers["Content-Type"] = "application/json";
    return fetch(`${config.apiUrl}${path.startsWith("/health") ? "" : config.apiPrefix}${path}`, {
      method,
      headers,
      body: opts.form ?? (body !== undefined ? JSON.stringify(body) : undefined),
    });
  };
  let res: Response;
  try {
    res = await doFetch(false);
    if (res.status === 401 && persona) res = await doFetch(true); // expired/rotated secret
  } catch {
    throw new ApiError(0, "Backend not reachable. Is it running on " + config.apiUrl + "?");
  }
  if (!res.ok) throw await parseError(res);
  if (opts.raw) return (await res.blob()) as T;
  return (await res.json()) as T;
}

export const api = {
  health: () => request<Health>(null, "GET", "/health"),

  // ---- conversation & on-demand triggers
  chat: (p: PersonaId, b: { message: string; language?: string | null; session_id?: string; elder_mode?: boolean }) =>
    request<TurnResult>(p, "POST", "/chat", b),
  checkup: (p: PersonaId, b: { scope: Scope; channel?: Channel; language?: string | null; force_refresh?: boolean; include_audio?: boolean; session_id?: string }) =>
    request<TurnResult>(p, "POST", "/checkups", b),
  raiseIssue: (p: PersonaId, b: { scope?: Scope; description?: string; insist?: boolean; language?: string | null }) =>
    request<TurnResult & { ticket_created?: boolean; can_insist?: boolean }>(p, "POST", "/issues", b),
  soundboxAsk: (p: PersonaId, deviceId: string, b: { button?: Scope; command_text?: string; language?: string | null; force_refresh?: boolean }) =>
    request<TurnResult>(p, "POST", `/soundbox/${encodeURIComponent(deviceId)}/ask`, b),
  voiceTurn: (p: PersonaId, audio: Blob, b: { language?: string | null; slow?: boolean; session_id?: string; filename?: string }) => {
    const form = new FormData();
    form.append("file", audio, b.filename ?? "voice.webm");
    if (b.language) form.append("language", b.language);
    form.append("slow", String(Boolean(b.slow)));
    if (b.session_id) form.append("session_id", b.session_id);
    return request<TurnResult>(p, "POST", "/voice/turn", undefined, { form });
  },
  tts: (p: PersonaId, text: string, language: string, slow = false) =>
    request<Blob>(p, "POST", "/voice/tts", { text, language, slow }, { raw: true }),

  // ---- merchant reads (on request)
  merchant: (p: PersonaId, id: string) => request<Merchant>(p, "GET", `/merchants/${id}`),
  device: (p: PersonaId, id: string) => request<DeviceStatus>(p, "GET", `/devices/${id}/status`),
  pulse: (p: PersonaId, merchantId: string, q: { audio?: boolean; language?: string | null } = {}) =>
    request<PulseResponse>(p, "GET", `/pulse/${merchantId}?audio=${Boolean(q.audio)}${q.language ? `&language=${q.language}` : ""}`),
  advice: (p: PersonaId, merchantId: string, topic: "festival" | "battery" | "all" = "all", language?: string | null) =>
    request<PulseResponse & { topic: string }>(p, "GET", `/advice/${merchantId}?topic=${topic}${language ? `&language=${language}` : ""}`),
  loanApply: (p: PersonaId, b: { merchant_id: string; amount: number; tenure_months: number }) =>
    request<LoanRequest & { human_approval_required: boolean }>(p, "POST", "/loans/requests", b),

  // ---- travel
  travelStatus: (p: PersonaId, ref: string, language?: string | null) =>
    request<{ text: string; booking: TravelBooking }>(p, "GET", `/travel/status/${encodeURIComponent(ref)}${language ? `?language=${language}` : ""}`),
  mockCheckout: (orderId: string) =>
    request<{ order_id: string; status: string; notice: string }>(null, "GET", `/payments/mock-checkout/${orderId}`),

  // ---- ops console (ops_agent / admin)
  metrics: () => request<Metrics>("ops", "GET", "/metrics"),
  escalations: (status = "open") => request<Escalation[]>("ops", "GET", `/escalations?status_filter=${status}`),
  resolveEscalation: (ticketId: string, b: { resolution: string; save_as_playbook: boolean; playbook_action?: string | null; root_cause?: string }) =>
    request<{ ticket_id: string; status: string; saved_as_playbook: boolean; learned_playbook: any }>("ops", "POST", `/escalations/${ticketId}/resolve`, b),
  playbooks: () => request<Playbook[]>("ops", "GET", "/playbooks"),
  loanRequests: (status = "awaiting_approval") => request<LoanRequest[]>("ops", "GET", `/loans/requests?status_filter=${status}`),
  decideLoan: (id: string, approve: boolean, notes?: string) =>
    request<LoanRequest>("ops", "POST", `/loans/requests/${id}/${approve ? "approve" : "reject"}`, { confirm: approve, notes }),
  controlState: () => request<ControlState>("ops", "GET", "/control/state"),
  setKillSwitch: (active: boolean, reason: string) =>
    request<ControlState>("admin", "POST", "/control/kill-switch", { active, reason, actor: "console" }),
  audit: (caseId?: string, limit = 60) =>
    request<AuditEntry[]>("admin", "GET", `/audit?limit=${limit}${caseId ? `&case_id=${encodeURIComponent(caseId)}` : ""}`),
  auditVerify: () => request<{ chain_intact: boolean; total_records?: number; message?: string }>("admin", "GET", "/audit/verify"),

  // ---- demo support (backend DEMO_MODE)
  demoScenario: (name: string) => request<{ scenario: string; mutated: any; processing_started: boolean }>("ops", "POST", `/demo/scenario/${name}`),
  demoTrigger: (name: string, b: { channel?: Channel; language?: string | null; message?: string } = {}) =>
    request<TurnResult>("ops", "POST", `/demo/trigger/${name}`, b),
  demoReset: () => request<{ status: string; cleared: Record<string, number> }>("ops", "POST", "/demo/reset"),
};

export function errorText(e: unknown): string {
  if (e instanceof ApiError) return e.status ? `${e.message} (HTTP ${e.status})` : e.message;
  return e instanceof Error ? e.message : String(e);
}
