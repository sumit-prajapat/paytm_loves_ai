import clsx from "clsx";
import { BatteryMedium, Clock, Cpu, Signal, Volume2, VolumeX } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Button, Card } from "@/components/ui";
import { playChime, playReply, unlockAudio } from "@/lib/audio";
import { formatTime } from "@/lib/format";
import { useStore } from "@/store";
import type { DeviceStatus } from "@/types/contracts";

/** Consumes the Soundbox queue: chime -> 300 ms -> TTS. Announcements never overlap. */
export function useSoundboxPlayer(enabled: boolean): { level: number; phase: "idle" | "chime" | "speaking" } {
  const nowPlaying = useStore((s) => s.nowPlaying);
  const queueLen = useStore((s) => s.queue.length);
  const unlocked = useStore((s) => s.audioUnlocked);
  const [phase, setPhase] = useState<"idle" | "chime" | "speaking">("idle");
  const [level, setLevel] = useState(0);
  const busy = useRef(false);

  useEffect(() => {
    if (!enabled || !unlocked || busy.current || nowPlaying || !queueLen) return;
    const item = useStore.getState().nextSoundbox();
    if (!item) return;
    busy.current = true;
    (async () => {
      const { soundEnabled, volume, slowSpeech } = useStore.getState();
      try {
        if (soundEnabled) {
          setPhase("chime");
          await playChime(volume);
          await new Promise((r) => setTimeout(r, 300));
          setPhase("speaking");
          const h = playReply({ url: item.audio_url, bytes: item.bytes, text: item.text, lang: item.lang, volume, slow: slowSpeech });
          let raf = 0;
          if (h.analyser) {
            const buf = new Uint8Array(h.analyser.frequencyBinCount);
            const tick = () => {
              h.analyser!.getByteFrequencyData(buf);
              setLevel(buf.reduce((a, b) => a + b, 0) / (buf.length * 255));
              raf = requestAnimationFrame(tick);
            };
            tick();
          } else {
            const iv = setInterval(() => setLevel(0.3 + Math.random() * 0.5), 120);
            raf = -Number(iv);
          }
          await h.done;
          if (raf > 0) cancelAnimationFrame(raf);
          else clearInterval(-raf);
        } else {
          setPhase("speaking");
          await new Promise((r) => setTimeout(r, 2500));
        }
      } finally {
        setLevel(0);
        setPhase("idle");
        useStore.getState().finishSoundbox();
        busy.current = false;
      }
    })();
  }, [enabled, unlocked, nowPlaying, queueLen]);

  return { level, phase };
}

export function SoundboxDevice({ phase, level, device, size = 230 }: { phase: "idle" | "chime" | "speaking"; level: number; device?: DeviceStatus | null; size?: number }) {
  const offline = device?.is_offline;
  const lowBattery = (device?.battery ?? 100) <= 20;
  const led = offline ? "#475569" : phase === "chime" ? "#FFFFFF" : lowBattery && phase === "idle" ? "#F59E0B" : "var(--sky-500)";
  return (
    <div
      className={clsx("relative grid place-items-center rounded-[44px] bg-gradient-to-br from-slate-800 to-[#0B1020] shadow-[0_20px_40px_rgba(0,0,0,.25)]", offline && "grayscale")}
      style={{ width: size, height: size }}
      role="img"
      aria-label={`Soundbox ${offline ? "offline" : phase}`}
    >
      <div
        className="absolute left-1/2 top-4 h-2 w-[120px] -translate-x-1/2 rounded-md transition-all"
        style={{
          background: led,
          opacity: phase === "idle" && !offline ? 0.45 : 1,
          boxShadow: offline ? "none" : `0 0 ${8 + level * 40}px ${led}`,
        }}
      />
      <div className="grid grid-cols-9 gap-2" aria-hidden>
        {Array.from({ length: 63 }, (_, i) => (
          <i key={i} className="block h-2.5 w-2.5 rounded-full bg-slate-700" style={phase === "speaking" ? { opacity: 0.5 + ((i * 7) % 5) * level * 0.25 } : undefined} />
        ))}
      </div>
      <div className={clsx("mono absolute bottom-4 rounded-md border border-slate-600 bg-slate-900 px-2.5 py-0.5 text-[11px]", offline ? "text-red-400" : "text-cyan-300")}>
        {offline ? `OFFLINE · ${device?.minutes_since_seen} min` : phase === "speaking" ? "SPEAKING…" : phase === "chime" ? "♪" : lowBattery ? "LOW BATTERY" : "READY"}
      </div>
    </div>
  );
}

export function LiveWave({ level, active }: { level: number; active: boolean }) {
  const bars = 34;
  return (
    <div className="anim flex h-11 items-center gap-[3px] text-sky-500" aria-hidden>
      {Array.from({ length: bars }, (_, i) => {
        const base = (Math.sin(i * 1.7) + Math.sin(i * 0.6) + 2.2) / 4.4;
        const h = active ? 4 + base * 36 * (0.4 + level * 1.6) : 4;
        return <i key={i} className="block w-1 rounded bg-current transition-all duration-100" style={{ height: Math.min(44, h) }} />;
      })}
    </div>
  );
}

export function DeviceStatusRow({ d }: { d?: DeviceStatus | null }) {
  if (!d) return null;
  return (
    <Card className="flex flex-wrap justify-around gap-2 !p-3 text-[13px]">
      <span className="flex items-center gap-1"><BatteryMedium className="h-4 w-4" /> <b className="num">{d.battery}%</b></span>
      <span className="flex items-center gap-1"><Signal className="h-4 w-4" /> {d.network}</span>
      <span className="flex items-center gap-1"><Clock className="h-4 w-4" /> {d.minutes_since_seen} min ago</span>
      <span className="mono flex items-center gap-1"><Cpu className="h-4 w-4" /> fw {d.firmware}</span>
    </Card>
  );
}

export function EnableAudioOverlay() {
  const unlocked = useStore((s) => s.audioUnlocked);
  const set = useStore((s) => s.set);
  if (unlocked) return null;
  return (
    <div className="absolute inset-0 z-20 grid place-items-center rounded-2xl bg-white/85 p-4 backdrop-blur-sm">
      <Card className="max-w-xs text-center">
        <Volume2 className="mx-auto h-9 w-9 text-sky-500" />
        <b className="mt-1 block text-base">Audio chalu karein</b>
        <p className="mb-3 mt-1 text-xs text-muted">Browser ko ek click chahiye (autoplay rule). Demo se pehle ek baar dabaiye.</p>
        <Button variant="sky" className="w-full" onClick={async () => { await unlockAudio(); set({ audioUnlocked: true }); }}>Enable audio</Button>
      </Card>
    </div>
  );
}

export function SoundboxControls() {
  const { volume, soundEnabled, slowSpeech, set } = useStore();
  return (
    <div className="flex w-full flex-wrap items-center gap-2">
      <label className="flex flex-1 items-center gap-2 text-xs">
        <Volume2 className="h-4 w-4" />
        <span className="sr-only">Volume</span>
        <input type="range" min={0} max={1} step={0.05} value={volume} onChange={(e) => set({ volume: Number(e.target.value) })} className="flex-1 accent-sky-500" />
      </label>
      <Button size="sm" onClick={() => set({ soundEnabled: !soundEnabled })} aria-pressed={!soundEnabled}>
        {soundEnabled ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />} {soundEnabled ? "Mute" : "Unmute"}
      </Button>
      <Button size="sm" onClick={() => set({ slowSpeech: !slowSpeech })} aria-pressed={slowSpeech}>🐢 {slowSpeech ? "Normal speed" : "Dheere bolo"}</Button>
    </div>
  );
}

export function AnnouncementList() {
  const history = useStore((s) => s.history);
  const enqueue = useStore((s) => s.enqueueSoundbox);
  if (!history.length) return <p className="text-xs text-muted">Abhi tak koi announcement nahi.</p>;
  return (
    <ul className="divide-y divide-line text-[13px]">
      {history.map((h) => (
        <li key={h.id} className="flex items-center gap-2 py-1.5">
          <button aria-label="Replay" className="rounded-full bg-navy-700 px-2 text-white" onClick={() => enqueue({ ...h, id: `${h.id}_r${Date.now()}` })}>▶</button>
          <span className="line-clamp-1 flex-1">{h.text}</span>
          <small className="text-muted">{formatTime(new Date(h.ts).toISOString())}</small>
        </li>
      ))}
    </ul>
  );
}
