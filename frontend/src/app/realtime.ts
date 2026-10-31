import { useEffect } from "react";
import { api } from "@/lib/api";
import { crewAgentFor } from "@/lib/agents";
import { onBus, TAB_ID } from "@/lib/bus";
import { PERSONAS } from "@/lib/personas";
import { toast } from "@/lib/toast";
import { openSocket } from "@/lib/ws";
import { applyTurn, refreshConsole } from "@/services/actions";
import { uid, useStore } from "@/store";
import type { ConsoleEvent, PersonaId, SoundboxAnswerEvent, TraceStep } from "@/types/contracts";

const st = () => useStore.getState();

/** case_id -> persona, learned from the captain_plan step, to drive "which agent is working". */
const caseOwner = new Map<string, PersonaId>();
const SUBJECT_TO_PERSONA: Record<string, PersonaId> = {
  m_ramesh: "ramesh", m_sunita: "sunita", m_disputed: "gupta", c_arjun: "arjun", c_meena: "meena",
};

let metricsTimer: ReturnType<typeof setTimeout> | undefined;
let consoleSubscribers = 0;

function onTrace(step: TraceStep) {
  if (step.type !== "agent_step") return;
  st().addStep(step);
  const subj = step.input?.trigger?.subject_id;
  if (subj && SUBJECT_TO_PERSONA[subj]) caseOwner.set(step.case_id, SUBJECT_TO_PERSONA[subj]);
  const owner = caseOwner.get(step.case_id);
  if (owner) {
    if (step.tool === "finalize_response" && step.agent === "captain") st().setTyping(owner, null);
    else if (st().typing[owner]) st().setTyping(owner, crewAgentFor(step));
  }
  if (step.tool === "finalize_response" && consoleSubscribers > 0) {
    if (metricsTimer) clearTimeout(metricsTimer);
    metricsTimer = setTimeout(() => refreshConsole(["metrics"]), 1500);
  }
}

function onConsole(ev: ConsoleEvent) {
  switch (ev.type) {
    case "escalation_created":
      toast({ title: "New escalation", body: `${ev.ticket.ticket_id} · ${ev.ticket.issue_types.join(", ")} · ${ev.ticket.merchant_id}`, tone: "risk" });
      refreshConsole(["esc", "metrics"]);
      break;
    case "escalation_updated":
      refreshConsole(["esc", "pb", "metrics"]);
      break;
    case "loan_request_updated": {
      const { type: _t, ts: _ts, ...req } = ev;
      st().upsertLoan(req);
      refreshConsole(["loans", "metrics"]);
      break;
    }
    case "killswitch_changed": {
      const { type: _t, ts: _ts, ...control } = ev;
      st().set({ control });
      break;
    }
  }
}

function onSoundbox(ev: SoundboxAnswerEvent) {
  if (ev.type !== "soundbox_answer") return;
  st().enqueueSoundbox({
    id: `sb_${ev.case_id}`, text: ev.text, lang: ev.language, audio_url: ev.audio_url, device_id: ev.device_id, ts: Date.now(),
  });
}

/** Open the backend WebSockets a page needs. */
export function useRealtime(opts: { trace?: boolean; console?: boolean; merchant?: PersonaId | null }) {
  const { trace, console: consoleWs, merchant } = opts;
  useEffect(() => {
    if (!trace) return;
    const h = openSocket({ path: "/ws/trace", persona: "ops", onMessage: onTrace, onStatus: (s) => st().setSocket("trace", s) });
    return () => h.close();
  }, [trace]);
  useEffect(() => {
    if (!consoleWs) return;
    consoleSubscribers += 1;
    refreshConsole();
    const h = openSocket({ path: "/ws/console", persona: "ops", onMessage: onConsole, onStatus: (s) => st().setSocket("console", s) });
    const poll = setInterval(() => refreshConsole(["metrics"]), 15_000);
    return () => {
      consoleSubscribers -= 1;
      clearInterval(poll);
      h.close();
    };
  }, [consoleWs]);
  useEffect(() => {
    const p = merchant ? PERSONAS[merchant] : null;
    if (!p?.merchantId) return;
    const h = openSocket({
      path: `/ws/merchant/${p.merchantId}`, persona: p.id, onMessage: onSoundbox, onStatus: (s) => st().setSocket("merchant", s),
    });
    return () => h.close();
  }, [merchant]);
}

/** Global: cross-tab relay + backend health. Mounted once in <App/>. */
export function useGlobalSync() {
  useEffect(() => {
    const off = onBus((m) => {
      switch (m.kind) {
        case "turn":
          if (m.origin === TAB_ID) return;
          if (m.userText) {
            const thread = st().threads[m.persona] ?? [];
            const last = thread[thread.length - 1];
            if (!(last && last.role === "user" && last.text === m.userText)) {
              st().pushMessage(m.persona, { id: uid("u"), role: "user", ts: Date.now(), text: m.userText });
            }
          }
          applyTurn(m.persona, m.result, { tag: m.label });
          break;
        case "loan":
          st().upsertLoan(m.request);
          break;
        case "reset":
          st().resetDemoState();
          break;
        case "soundbox":
          onSoundbox(m.event);
          break;
      }
    });
    const check = () =>
      api.health().then(
        () => st().set({ apiStatus: "ok" }),
        () => st().set({ apiStatus: "down" }),
      );
    check();
    const t = setInterval(check, 15_000);
    return () => {
      off();
      clearInterval(t);
    };
  }, []);
}
