/**
 * Reconnecting WebSocket for the backend channels:
 *   /ws/trace?token=           (ops/admin)  agent_step events
 *   /ws/console?token=         (ops/admin)  escalation_*, loan_request_updated, killswitch_changed
 *   /ws/merchant/{id}?token=   (merchant)   soundbox_answer
 * Backoff 0.5 s -> 8 s. In mock mode the fake socket (BroadcastChannel) is used instead.
 */
import { config } from "./config";
import { getToken } from "./auth";
import type { PersonaId } from "@/types/contracts";

export type SocketStatus = "connecting" | "live" | "reconnecting" | "offline" | "mock";

export interface SocketHandle {
  close: () => void;
}

export function openSocket(opts: {
  path: string; // e.g. "/ws/trace"
  persona: PersonaId;
  onMessage: (data: any) => void;
  onStatus: (s: SocketStatus) => void;
}): SocketHandle {
  if (config.useMocks) {
    let stop = () => {};
    import("@/mocks/fakeSocket").then(({ subscribeFake }) => {
      stop = subscribeFake(opts.path, opts.onMessage);
      opts.onStatus("mock");
    });
    return { close: () => stop() };
  }

  let ws: WebSocket | null = null;
  let closed = false;
  let attempt = 0;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let ping: ReturnType<typeof setInterval> | undefined;

  const connect = async () => {
    if (closed) return;
    opts.onStatus(attempt === 0 ? "connecting" : "reconnecting");
    let token: string;
    try {
      token = await getToken(opts.persona, attempt > 2);
    } catch {
      if (!closed) schedule();
      return;
    }
    if (closed) return; // closed while waiting for the token (e.g. React StrictMode remount)
    ws = new WebSocket(`${config.wsUrl}${opts.path}?token=${encodeURIComponent(token)}`);
    ws.onopen = () => {
      attempt = 0;
      opts.onStatus("live");
      ping = setInterval(() => ws?.readyState === WebSocket.OPEN && ws.send("ping"), 25_000);
    };
    ws.onmessage = (ev) => {
      if (ev.data === "pong") return;
      try {
        opts.onMessage(JSON.parse(ev.data));
      } catch {
        /* ignore non-JSON */
      }
    };
    ws.onclose = () => {
      if (ping) clearInterval(ping);
      if (!closed) schedule();
    };
    ws.onerror = () => ws?.close();
  };

  const schedule = () => {
    attempt += 1;
    opts.onStatus(attempt > 4 ? "offline" : "reconnecting");
    const delay = Math.min(8000, 500 * 2 ** (attempt - 1));
    timer = setTimeout(connect, delay);
  };

  connect();
  return {
    close: () => {
      closed = true;
      if (timer) clearTimeout(timer);
      if (ping) clearInterval(ping);
      ws?.close();
    },
  };
}
