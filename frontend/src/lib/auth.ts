/**
 * Demo authentication against the backend's existing POST /api/v1/auth/demo-token
 * (enabled when the backend runs with DEMO_MODE=true). Tokens are cached per persona in
 * sessionStorage and refreshed when they expire or the backend answers 401.
 */
import { config } from "./config";
import { PERSONAS } from "./personas";
import type { PersonaId, TokenResponse } from "@/types/contracts";

interface Cached {
  token: string;
  exp: number;
  info: TokenResponse;
}

const memory = new Map<PersonaId, Cached>();
const inflight = new Map<PersonaId, Promise<Cached>>();

function decodeExp(token: string): number {
  try {
    const payload = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
    return (payload.exp as number) * 1000;
  } catch {
    return Date.now() + 30 * 60 * 1000;
  }
}

function load(persona: PersonaId): Cached | undefined {
  const m = memory.get(persona);
  if (m) return m;
  try {
    const raw = sessionStorage.getItem(`saarthi.token.${persona}`);
    if (raw) {
      const c = JSON.parse(raw) as Cached;
      memory.set(persona, c);
      return c;
    }
  } catch {
    /* storage unavailable */
  }
  return undefined;
}

async function fetchToken(persona: PersonaId): Promise<Cached> {
  const p = PERSONAS[persona];
  const role = p.role;
  if (config.useMocks) {
    const { mockToken } = await import("@/mocks/mockApi");
    const info = mockToken(persona);
    return { token: info.access_token, exp: Date.now() + 3600_000, info };
  }
  const res = await fetch(`${config.apiUrl}${config.apiPrefix}/auth/demo-token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role, target_id: p.targetId ?? null }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.message || `Login failed for ${p.label} (HTTP ${res.status})`);
  }
  const info = (await res.json()) as TokenResponse;
  return { token: info.access_token, exp: decodeExp(info.access_token), info };
}

export async function getToken(persona: PersonaId, force = false): Promise<string> {
  const cached = force ? undefined : load(persona);
  if (cached && cached.exp - Date.now() > 60_000) return cached.token;
  if (!inflight.has(persona)) {
    inflight.set(
      persona,
      fetchToken(persona)
        .then((c) => {
          memory.set(persona, c);
          try {
            sessionStorage.setItem(`saarthi.token.${persona}`, JSON.stringify(c));
          } catch {
            /* ignore */
          }
          return c;
        })
        .finally(() => inflight.delete(persona)),
    );
  }
  return (await inflight.get(persona)!).token;
}

export function clearTokens(): void {
  memory.clear();
  try {
    Object.keys(sessionStorage)
      .filter((k) => k.startsWith("saarthi.token."))
      .forEach((k) => sessionStorage.removeItem(k));
  } catch {
    /* ignore */
  }
}
