import { useState } from "react";
import { useRealtime } from "@/app/realtime";
import { TravelChat } from "@/components/panels/TravelChat";
import type { PersonaId } from "@/types/contracts";

export default function Travel() {
  const [persona, setPersona] = useState<PersonaId>("arjun");
  useRealtime({ trace: true });
  return (
    <div className="flex min-h-full items-start justify-center sm:items-center sm:p-4">
      <TravelChat persona={persona} onPersona={setPersona} />
    </div>
  );
}
