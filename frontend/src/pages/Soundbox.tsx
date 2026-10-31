import { useState } from "react";
import { useRealtime } from "@/app/realtime";
import { ConnectionPill, TopBar } from "@/components/layout";
import { SoundboxPanel } from "@/components/panels/SoundboxPanel";
import { MERCHANT_PERSONAS, PERSONAS } from "@/lib/personas";
import type { PersonaId } from "@/types/contracts";

export default function SoundboxPage() {
  const [persona, setPersona] = useState<PersonaId>("ramesh");
  useRealtime({ merchant: persona });
  return (
    <div className="min-h-full">
      <TopBar title="Soundbox simulator">
        <ConnectionPill />
        <label className="flex items-center gap-1.5 text-xs">
          <span className="opacity-80">Device of</span>
          <select value={persona} onChange={(e) => setPersona(e.target.value as PersonaId)} className="rounded-md bg-white/10 px-2 py-1 text-white">
            {MERCHANT_PERSONAS.map((id) => <option key={id} value={id} className="text-ink">{PERSONAS[id].label}</option>)}
          </select>
        </label>
      </TopBar>
      <main className="flex justify-center px-4 py-6">
        <SoundboxPanel persona={persona} />
      </main>
    </div>
  );
}
