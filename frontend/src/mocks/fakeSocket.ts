/**
 * Fake WebSocket for VITE_USE_MOCKS=true. Events are shared across tabs of the same browser
 * via BroadcastChannel so /stage, /soundbox, /console and /inject stay in sync offline.
 */
import { broadcast, onBus } from "@/lib/bus";

type Handler = (data: any) => void;
const subs = new Map<string, Set<Handler>>();

function deliver(path: string, payload: any) {
  subs.get(path)?.forEach((h) => h(payload));
}

onBus((m) => {
  if (m.kind === "mock-ws") deliver(m.path, m.payload);
});

export function emitFake(path: string, payload: any, delayMs = 0): void {
  setTimeout(() => {
    deliver(path, payload);
    broadcast({ kind: "mock-ws", path, payload });
  }, delayMs);
}

export function subscribeFake(path: string, handler: Handler): () => void {
  if (!subs.has(path)) subs.set(path, new Set());
  subs.get(path)!.add(handler);
  return () => subs.get(path)?.delete(handler);
}
