import { create } from "zustand";
import { crewAgentFor } from "@/lib/agents";
import type {
  AgentName, AudioMeta, ControlState, Escalation, Lang, LoanRequest, Metrics, PersonaId, Playbook, TraceStep, TurnResult,
} from "@/types/contracts";
import type { SocketStatus } from "@/lib/ws";

// ------------------------------------------------------------------ types
export interface UiMessage {
  id: string;
  role: "user" | "saarthi" | "system";
  ts: number;
  lang?: Lang;
  text: string;
  voice?: { seconds: number; pending?: boolean; failed?: boolean };
  audio?: AudioMeta;
  result?: TurnResult;
  tag?: string;
  error?: boolean;
}

export type AgentState = "idle" | "working" | "done" | "blocked";

export interface CaseRow {
  case_id: string;
  first: string;
  last: string;
  title: string;
  status?: string;
  channel?: string;
  request_type?: string;
  steps: number;
  tier?: number;
}

export interface SoundboxItem {
  id: string;
  text: string;
  lang: string;
  audio_url?: string | null;
  bytes?: number;
  device_id?: string;
  ts: number;
}

export interface InjectEntry {
  id: string;
  ts: number;
  scenario: string;
  label: string;
  status: "running" | "done" | "error";
  outcome?: string;
  case_id?: string;
  detail?: string;
}

export interface SeriesPoint {
  run: number;
  rate: number;
  status: string;
  playbook?: boolean;
}

interface State {
  // settings
  lang: Lang | null; // null = auto (backend decides from message/profile)
  lowBandwidth: boolean;
  elderMode: boolean;
  soundEnabled: boolean;
  volume: number;
  slowSpeech: boolean;
  audioUnlocked: boolean;
  stagePhone: "ramesh" | "arjun";
  theme: "light" | "dark";
  // connections
  apiStatus: "unknown" | "ok" | "down";
  sockets: Record<string, SocketStatus>;
  // chat
  threads: Partial<Record<PersonaId, UiMessage[]>>;
  typing: Partial<Record<PersonaId, string | null>>;
  // trace
  steps: TraceStep[];
  agentStates: Record<AgentName, AgentState>;
  cases: Record<string, CaseRow>;
  selectedCase: string | null;
  // console
  escalations: Escalation[];
  loans: LoanRequest[];
  loanStatus: Record<string, LoanRequest>;
  playbooks: Playbook[];
  metrics: Metrics | null;
  control: ControlState | null;
  series: SeriesPoint[];
  // soundbox
  queue: SoundboxItem[];
  history: SoundboxItem[];
  nowPlaying: SoundboxItem | null;
  // inject
  injectLog: InjectEntry[];
}

interface Actions {
  set: (p: Partial<State>) => void;
  setSocket: (name: string, s: SocketStatus) => void;
  pushMessage: (persona: PersonaId, m: UiMessage) => void;
  patchMessage: (persona: PersonaId, id: string, p: Partial<UiMessage>) => void;
  clearThread: (persona: PersonaId) => void;
  setTyping: (persona: PersonaId, text: string | null) => void;
  addStep: (s: TraceStep) => void;
  settleAgent: (a: AgentName) => void;
  enqueueSoundbox: (i: SoundboxItem) => void;
  nextSoundbox: () => SoundboxItem | null;
  finishSoundbox: () => void;
  upsertInject: (e: InjectEntry) => void;
  addSeriesPoint: (status: string) => void;
  markPlaybookPoint: () => void;
  upsertLoan: (r: LoanRequest) => void;
  resetDemoState: () => void;
}

const idleAgents = (): Record<AgentName, AgentState> => ({
  captain: "idle", listener: "idle", context: "idle", diagnostician: "idle", action: "idle", planner: "idle",
  search: "idle", ranker: "idle", offer: "idle", guardian: "idle", handoff: "idle", learner: "idle",
});

function loadPref<T>(key: string, fallback: T): T {
  try {
    const v = localStorage.getItem(`saarthi.pref.${key}`);
    return v === null ? fallback : (JSON.parse(v) as T);
  } catch {
    return fallback;
  }
}
export function savePref(key: string, v: unknown): void {
  try {
    localStorage.setItem(`saarthi.pref.${key}`, JSON.stringify(v));
  } catch {
    /* ignore */
  }
}

const settleTimers = new Map<AgentName, ReturnType<typeof setTimeout>>();

function caseTitle(s: TraceStep): string | undefined {
  const i = s.input || {};
  if (s.tool === "captain_plan" && i.trigger) {
    const t = i.trigger;
    return `${t.request_type}${t.scope ? ` · ${t.scope}` : ""} · ${t.subject_id}`;
  }
  return undefined;
}

export const useStore = create<State & Actions>((set, get) => ({
  lang: loadPref<Lang | null>("lang", null),
  lowBandwidth: loadPref("lowBandwidth", false),
  elderMode: loadPref("elderMode", false),
  soundEnabled: loadPref("soundEnabled", true),
  volume: loadPref("volume", 0.9),
  slowSpeech: loadPref("slowSpeech", false),
  audioUnlocked: false,
  stagePhone: "ramesh",
  theme: "light",
  apiStatus: "unknown",
  sockets: {},
  threads: {},
  typing: {},
  steps: [],
  agentStates: idleAgents(),
  cases: {},
  selectedCase: null,
  escalations: [],
  loans: [],
  loanStatus: {},
  playbooks: [],
  metrics: null,
  control: null,
  series: [],
  queue: [],
  history: [],
  nowPlaying: null,
  injectLog: [],

  set: (p) => set(p),
  setSocket: (name, s) => set((st) => ({ sockets: { ...st.sockets, [name]: s } })),
  pushMessage: (persona, m) =>
    set((st) => ({ threads: { ...st.threads, [persona]: [...(st.threads[persona] ?? []), m].slice(-200) } })),
  patchMessage: (persona, id, p) =>
    set((st) => ({
      threads: { ...st.threads, [persona]: (st.threads[persona] ?? []).map((m) => (m.id === id ? { ...m, ...p } : m)) },
    })),
  clearThread: (persona) => set((st) => ({ threads: { ...st.threads, [persona]: [] } })),
  setTyping: (persona, text) => set((st) => ({ typing: { ...st.typing, [persona]: text } })),

  addStep: (s) => {
    if (get().steps.some((x) => x.run_id === s.run_id)) return; // de-duplicate (multiple sockets/tabs)
    const agent = crewAgentFor(s);
    const blocked = s.agent === "guardian" && ["block", "escalate"].includes(s.output?.decision);
    set((st) => {
      const prev = st.cases[s.case_id];
      const row: CaseRow = prev
        ? { ...prev, last: s.ts, steps: prev.steps + 1 }
        : { case_id: s.case_id, first: s.ts, last: s.ts, title: "", steps: 1 };
      const title = caseTitle(s);
      if (title) {
        row.title = title;
        row.channel = s.input?.trigger?.channel;
        row.request_type = s.input?.trigger?.request_type;
      }
      if (s.tool === "finalize_response" && s.agent === "captain") {
        if (s.output?.status) row.status = s.output.status;
        row.tier = s.cost_tier;
        if (!row.title && s.input?.cache) row.title = "cached check-up";
      }
      return {
        steps: [...st.steps, s].slice(-600),
        cases: { ...st.cases, [s.case_id]: row },
        selectedCase: st.selectedCase ?? s.case_id,
        agentStates: { ...st.agentStates, [agent]: blocked ? "blocked" : "working" },
      };
    });
    const old = settleTimers.get(agent);
    if (old) clearTimeout(old);
    settleTimers.set(agent, setTimeout(() => get().settleAgent(agent), 900));
  },
  settleAgent: (a) => {
    set((st) => ({ agentStates: { ...st.agentStates, [a]: st.agentStates[a] === "blocked" ? "blocked" : "done" } }));
    settleTimers.set(a, setTimeout(() => set((st) => ({ agentStates: { ...st.agentStates, [a]: "idle" } })), 2500));
  },

  enqueueSoundbox: (i) =>
    set((st) => (st.queue.some((q) => q.id === i.id) || st.history.some((h) => h.id === i.id) || st.nowPlaying?.id === i.id
      ? st
      : { queue: [...st.queue, i] })),
  nextSoundbox: () => {
    const { queue, nowPlaying } = get();
    if (nowPlaying || !queue.length) return null;
    const [head, ...rest] = queue;
    set({ queue: rest, nowPlaying: head });
    return head;
  },
  finishSoundbox: () =>
    set((st) => ({ history: st.nowPlaying ? [st.nowPlaying, ...st.history].slice(0, 5) : st.history, nowPlaying: null })),

  upsertInject: (e) =>
    set((st) => {
      const exists = st.injectLog.some((x) => x.id === e.id);
      const log = exists ? st.injectLog.map((x) => (x.id === e.id ? { ...x, ...e } : x)) : [e, ...st.injectLog];
      return { injectLog: log.slice(0, 10) };
    }),
  addSeriesPoint: (status) =>
    set((st) => ({
      series: [...st.series, { run: st.series.length + 1, rate: status === "escalated" ? 100 : 0, status }],
    })),
  markPlaybookPoint: () =>
    set((st) => {
      if (!st.series.length) return st;
      const s = [...st.series];
      s[s.length - 1] = { ...s[s.length - 1], playbook: true };
      return { series: s };
    }),
  upsertLoan: (r) => set((st) => ({ loanStatus: { ...st.loanStatus, [r.request_id]: r } })),
  resetDemoState: () =>
    set({
      threads: {}, typing: {}, steps: [], cases: {}, selectedCase: null, agentStates: idleAgents(), series: [],
      queue: [], history: [], nowPlaying: null, injectLog: [], loanStatus: {},
    }),
}));

export function uid(prefix = "m"): string {
  return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`;
}
