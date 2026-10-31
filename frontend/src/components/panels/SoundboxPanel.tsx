import { useEffect, useState } from "react";
import { AnnouncementList, DeviceStatusRow, EnableAudioOverlay, LiveWave, SoundboxControls, SoundboxDevice, useSoundboxPlayer } from "@/components/soundbox";
import { Card } from "@/components/ui";
import { api } from "@/lib/api";
import { PERSONAS } from "@/lib/personas";
import { soundboxPress } from "@/services/actions";
import { useStore } from "@/store";
import type { DeviceStatus, PersonaId } from "@/types/contracts";

export function SoundboxPanel({ persona = "ramesh", compact }: { persona?: PersonaId; compact?: boolean }) {
  const p = PERSONAS[persona];
  const { level, phase } = useSoundboxPlayer(true);
  const nowPlaying = useStore((s) => s.nowPlaying);
  const history = useStore((s) => s.history);
  const [device, setDevice] = useState<DeviceStatus | null>(null);
  const [pressing, setPressing] = useState<string | null>(null);

  useEffect(() => {
    if (!p.deviceId) return;
    api.device(persona, p.deviceId).then(setDevice, () => setDevice(null));
  }, [persona, p.deviceId, history.length]);

  const press = async (button: "settlement" | "device" | "all") => {
    setPressing(button);
    await soundboxPress(persona, button);
    setPressing(null);
  };

  const speaking = nowPlaying?.text;
  return (
    <div className="relative flex w-full max-w-[340px] flex-col items-center gap-3">
      <EnableAudioOverlay />
      <SoundboxDevice phase={phase} level={level} device={device} size={compact ? 200 : 230} />
      <LiveWave level={level} active={phase === "speaking"} />
      <div className="grid w-full grid-cols-3 gap-2" aria-label="Soundbox buttons">
        <button
          type="button"
          disabled={pressing !== null}
          onClick={() => press("settlement")}
          className="flex min-h-[40px] items-center justify-center rounded-btn border border-line bg-card px-2 py-1.5 text-xs font-bold text-ink shadow-sm hover:border-sky-500 hover:bg-sky-50 dark:hover:bg-sky-950 transition"
        >
          {pressing === "settlement" ? "…" : "💰 Settlement"}
        </button>
        <button
          type="button"
          disabled={pressing !== null}
          onClick={() => press("device")}
          className="flex min-h-[40px] items-center justify-center rounded-btn border border-line bg-card px-2 py-1.5 text-xs font-bold text-ink shadow-sm hover:border-sky-500 hover:bg-sky-50 dark:hover:bg-sky-950 transition"
        >
          {pressing === "device" ? "…" : "🔋 Device"}
        </button>
        <button
          type="button"
          disabled={pressing !== null}
          onClick={() => press("all")}
          className="flex min-h-[40px] items-center justify-center rounded-btn border border-line bg-card px-2 py-1.5 text-xs font-bold text-ink shadow-sm hover:border-sky-500 hover:bg-sky-50 dark:hover:bg-sky-950 transition"
        >
          {pressing === "all" ? "…" : "✅ Sab"}
        </button>
      </div>
      <Card className="w-full !p-3">
        <small className="text-muted">Abhi bol raha hai</small>
        <p className="mt-0.5 min-h-[48px] text-[17px] font-semibold leading-snug" lang="hi">
          {speaking ? `“${speaking}”` : <span className="text-sm font-normal text-muted">Button dabaiye ya “Saarthi, mera settlement check karo” boliye.</span>}
        </p>
      </Card>
      <DeviceStatusRow d={device} />
      {!compact && (
        <>
          <SoundboxControls />
          <Card className="w-full !p-3">
            <small className="text-muted">Pichhle announcements</small>
            <AnnouncementList />
          </Card>
        </>
      )}
    </div>
  );
}
