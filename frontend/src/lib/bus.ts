/**
 * Cross-tab relay (same browser) via BroadcastChannel('saarthi-demo').
 * The backend returns a turn's reply to the tab that made the request; the relay lets the
 * /inject tablet tab, /stage, /merchant and /soundbox tabs show the same result.
 */
import type { LoanRequest, PersonaId, SoundboxAnswerEvent, TurnResult } from "@/types/contracts";

export type BusMessage =
  | { kind: "turn"; persona: PersonaId; result: TurnResult; userText?: string; origin: string; label?: string }
  | { kind: "loan"; request: LoanRequest }
  | { kind: "soundbox"; event: SoundboxAnswerEvent }
  | { kind: "reset" }
  | { kind: "mock-ws"; path: string; payload: any };

const channel: BroadcastChannel | null = typeof BroadcastChannel !== "undefined" ? new BroadcastChannel("saarthi-demo") : null;
const listeners = new Set<(m: BusMessage) => void>();
export const TAB_ID = Math.random().toString(36).slice(2, 10);

channel?.addEventListener("message", (ev) => listeners.forEach((l) => l(ev.data as BusMessage)));

/** Send to OTHER tabs (and optionally this tab too). */
export function broadcast(msg: BusMessage, includeSelf = false): void {
  channel?.postMessage(msg);
  if (includeSelf) listeners.forEach((l) => l(msg));
}

export function onBus(fn: (m: BusMessage) => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}
