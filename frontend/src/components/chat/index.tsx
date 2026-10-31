import clsx from "clsx";
import { Loader2, Mic, Pause, Play, Send, Square } from "lucide-react";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Button } from "@/components/ui";
import { AGENT_BY_NAME, AGENT_VERB } from "@/lib/agents";
import { playReply, startRecording, unlockAudio, type PlayHandle, type Recording } from "@/lib/audio";
import { t } from "@/lib/i18n";
import { toast } from "@/lib/toast";
import { useStore, type UiMessage } from "@/store";
import type { AgentName, Lang, PersonaId } from "@/types/contracts";

const TAGS: Record<string, string> = {
  demo: "🔘 Demo: user trigger simulated",
  soundbox: "🔊 Soundbox se poocha",
  button: "",
};

function Bars({ n = 22, seed = 1 }: { n?: number; seed?: number }) {
  const bars = useMemo(() => Array.from({ length: n }, (_, i) => 4 + Math.round(((Math.sin((i + seed) * 1.7) + Math.sin((i + seed) * 0.6) + 2.2) / 4.4) * 14)), [n, seed]);
  return (
    <span className="anim flex h-5 flex-1 items-center gap-[2px]" aria-hidden>
      {bars.map((h, i) => <i key={i} className="block w-[3px] rounded bg-current opacity-70" style={{ height: h }} />)}
    </span>
  );
}

export function AudioButton({ url, bytes, text, lang, dark, slow }: { url?: string | null; bytes?: number; text: string; lang: string; dark?: boolean; slow?: boolean }) {
  const [playing, setPlaying] = useState(false);
  const handle = useRef<PlayHandle | null>(null);
  return (
    <button
      aria-label={playing ? "Pause" : "Play audio"}
      onClick={async () => {
        if (playing) {
          handle.current?.stop();
          setPlaying(false);
          return;
        }
        await unlockAudio();
        setPlaying(true);
        handle.current = playReply({ url, bytes, text, lang, slow, volume: useStore.getState().volume });
        const how = await handle.current.done;
        if (how === "none") toast({ title: t("audio.unavailable", lang as Lang), tone: "warn" });
        setPlaying(false);
      }}
      className={clsx("grid h-8 w-8 shrink-0 place-items-center rounded-full", dark ? "bg-white text-navy-700" : "bg-navy-700 text-white")}
    >
      {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
    </button>
  );
}

export function Bubble({ m, children }: { m: UiMessage; children?: ReactNode }) {
  const lowData = useStore((s) => s.lowBandwidth);
  const mine = m.role === "user";
  if (m.role === "system") {
    return (
      <div role={m.error ? "alert" : undefined} className={clsx("self-center rounded-lg px-3 py-1.5 text-center text-xs", m.error ? "bg-risk-bg text-risk" : "bg-slate-100 text-muted")}>
        {m.text}
      </div>
    );
  }
  const tag = m.tag ? TAGS[m.tag] : "";
  return (
    <div className={clsx("flex max-w-[88%] flex-col gap-2", mine ? "self-end items-end" : "self-start items-start w-full")}>
      {(m.text || m.voice) && (
        <div className={clsx("phone-text animate-rise rounded-2xl px-3.5 py-2.5 shadow-sm", mine ? "rounded-br-sm bg-navy-700 text-white" : "rounded-bl-sm bg-sky-100 text-navy-950 border border-sky-200")}>
          {tag && <div className={clsx("mb-1 text-[11px] font-bold", mine ? "text-sky-200" : "text-sky-800")}>{tag}</div>}
          {m.voice ? (
            <>
              <div className="flex items-center gap-2">
                {m.voice.pending ? <Loader2 className="h-5 w-5 animate-spin" /> : <span className="grid h-7 w-7 place-items-center rounded-full bg-white/90 text-navy-700"><Mic className="h-4 w-4" /></span>}
                {!lowData ? <Bars seed={m.text.length} /> : <span className="text-xs">▶</span>}
                <small className="tabular-nums">0:{String(Math.max(1, Math.round(m.voice.seconds))).padStart(2, "0")}</small>
              </div>
              <div className="mt-1 text-[13px] italic opacity-90">
                {m.voice.pending ? t("stt.listening", null) : m.voice.failed ? t("stt.fail", null) : `“${m.text}”`}
              </div>
            </>
          ) : (
            <>
              {!mine && (
                <div className="mb-1.5 flex items-center justify-between gap-2 border-b border-sky-200 pb-1.5">
                  <div className="flex items-center gap-2">
                    <AudioButton url={m.audio?.audio_url} bytes={m.audio?.bytes} text={m.text} lang={m.lang ?? "hi"} slow={m.audio?.slow} />
                    <span className="text-[12px] font-extrabold text-sky-900">🔊 सुनिए (Tap to Listen)</span>
                  </div>
                  {!lowData && m.audio && <Bars seed={m.text.length} />}
                </div>
              )}
              <div className="whitespace-pre-line text-[14.5px] font-medium leading-relaxed">{m.text}</div>
            </>
          )}
        </div>
      )}
      {children}
    </div>
  );
}

export function TypingIndicator({ agent }: { agent: string | null | undefined }) {
  if (!agent) return null;
  const meta = AGENT_BY_NAME[agent as AgentName];
  return (
    <div className="flex items-center gap-2 self-start text-xs text-muted" aria-live="polite">
      <span className="h-2 w-2 animate-pulse rounded-full" style={{ background: meta?.color ?? "var(--sky-500)" }} />
      {meta ? `${meta.label} Agent ${AGENT_VERB[meta.name] ?? "kaam kar raha hai"}…` : t("typing", null)}
    </div>
  );
}

export function QuickReplies({ items }: { items: { label: string; onClick: () => void }[] }) {
  if (!items.length) return null;
  return (
    <div className="flex gap-1.5 overflow-x-auto border-t border-line bg-card px-3 py-2 scrollbar-thin">
      {items.map((q) => (
        <button key={q.label} onClick={q.onClick} className="min-h-[36px] whitespace-nowrap rounded-full border border-line bg-card text-ink font-semibold px-3 text-[12.5px] hover:border-sky-500 hover:bg-sky-50 dark:hover:bg-sky-950">
          {q.label}
        </button>
      ))}
    </div>
  );
}

export function ChatThread({ persona, render }: { persona: PersonaId; render: (m: UiMessage) => ReactNode }) {
  const messages = useStore((s) => s.threads[persona]) ?? [];
  const typing = useStore((s) => s.typing[persona]);
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => {
    // Braces matter: newer browsers return a Promise from scrollIntoView, which React would treat as a cleanup.
    end.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, typing]);
  return (
    <div className="flex flex-1 flex-col gap-2.5 overflow-y-auto bg-slate-50 dark:bg-slate-900/40 p-3 scrollbar-thin text-ink" aria-live="polite">
      {messages.map((m) => <div key={m.id} className="contents">{render(m)}</div>)}
      <TypingIndicator agent={typing} />
      <div ref={end} />
    </div>
  );
}

/** Push-and-hold to talk; tap toggles as a fallback. Sends audio to POST /voice/turn. */
export function MicButton({ onAudio, lang, size = 72, disabled }: { onAudio: (blob: Blob, seconds: number) => void; lang?: Lang | null; size?: number; disabled?: boolean }) {
  const [rec, setRec] = useState<Recording | null>(null);
  const [secs, setSecs] = useState(0);
  const [cancelArmed, setCancelArmed] = useState(false);
  const downAt = useRef(0);
  const startX = useRef(0);
  useEffect(() => {
    if (!rec) return;
    const started = Date.now();
    const iv = setInterval(() => setSecs((Date.now() - started) / 1000), 200);
    return () => clearInterval(iv);
  }, [rec]);

  const begin = async () => {
    if (rec || disabled) return;
    try {
      await unlockAudio();
      const r = await startRecording();
      setSecs(0);
      setRec(r);
    } catch {
      toast({ title: "Microphone", body: "Mic permission nahi mili. Likh kar bhejiye.", tone: "warn" });
    }
  };
  const finish = async (cancel: boolean) => {
    if (!rec) return;
    const r = rec;
    setRec(null);
    setCancelArmed(false);
    if (cancel) {
      r.cancel();
      return;
    }
    const { blob, seconds } = await r.stop();
    if (seconds < 0.6) return;
    onAudio(blob, seconds);
  };

  return (
    <div className="flex flex-col items-center">
      <button
        aria-label={rec ? "Stop and send" : t("mic.hold", lang)}
        aria-pressed={!!rec}
        disabled={disabled}
        onPointerDown={(e) => {
          downAt.current = Date.now();
          startX.current = e.clientX;
          (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
          begin();
        }}
        onPointerMove={(e) => rec && setCancelArmed(startX.current - e.clientX > 60)}
        onPointerUp={() => {
          const held = Date.now() - downAt.current;
          if (held > 400) finish(cancelArmed); // hold-to-talk release
        }}
        onClick={() => {
          // tap-to-toggle fallback: a quick tap while recording stops and sends
          if (rec && Date.now() - downAt.current < 400 && secs > 0.8) finish(false);
        }}
        style={{ width: size, height: size }}
        className={clsx(
          "grid touch-none place-items-center rounded-full bg-sky-500 text-navy-900 shadow-[0_0_0_6px_rgba(0,180,230,.18)] transition",
          rec && "scale-110 animate-pulsering",
          cancelArmed && "bg-risk text-white",
          disabled && "opacity-50",
        )}
      >
        {rec ? <Square className="h-7 w-7" /> : <Mic className="h-8 w-8" />}
      </button>
      <span className="mt-1 text-[10.5px] text-muted">
        {rec ? (cancelArmed ? "✕ cancel" : `${t("mic.release", lang)} · 0:${String(Math.floor(secs)).padStart(2, "0")}`) : t("mic.hold", lang)}
      </span>
    </div>
  );
}

export function Composer({ onSend, onAudio, lang, placeholder, disabled, busy }: {
  onSend: (text: string) => void; onAudio: (b: Blob, s: number) => void; lang?: Lang | null; placeholder?: string; disabled?: boolean; busy?: boolean;
}) {
  const [text, setText] = useState("");
  return (
    <form
      className="flex items-center gap-2 border-t border-line bg-card px-3 pb-3 pt-2"
      onSubmit={(e) => {
        e.preventDefault();
        if (!text.trim() || disabled) return;
        onSend(text);
        setText("");
      }}
    >
      <label className="sr-only" htmlFor="composer">Message</label>
      <input
        id="composer"
        value={text}
        maxLength={2000}
        onChange={(e) => setText(e.target.value)}
        placeholder={placeholder ?? t("type.here", lang)}
        className="min-h-[44px] min-w-0 flex-1 rounded-full border border-line bg-bg text-ink placeholder:text-muted px-4 text-[15px] focus:border-sky-500 focus:outline-none"
      />
      {text.trim() ? (
        <Button type="submit" variant="primary" aria-label={t("send", lang)} loading={busy} className="h-12 w-12 rounded-full !px-0">
          <Send className="h-5 w-5" />
        </Button>
      ) : (
        <MicButton onAudio={onAudio} lang={lang} size={60} disabled={disabled} />
      )}
    </form>
  );
}

export const PHRASE_BANK = [
  "Aaj ka settlement kam kyun aaya?",
  "Soundbox band ho gaya, awaaz nahi aa rahi",
  "Mera payment fail ho gaya, paisa kab aayega?",
  "Mujhe 50000 ka loan chahiye, EMI kitna?",
  "Nahi chahiye loan, mat do",
  "आज मेरा सेटलमेंट कम क्यों आया?",
  "Why is my settlement short today?",
  "Delhi se Mumbai kal shaam ka flight, sasta aur jaldi",
];
