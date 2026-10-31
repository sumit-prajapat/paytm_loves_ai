import { useState } from "react";
import { useRealtime } from "@/app/realtime";
import { MerchantChat } from "@/components/panels/MerchantChat";
import type { PersonaId } from "@/types/contracts";

export default function MerchantPhone() {
  const [persona, setPersona] = useState<PersonaId>("ramesh");
  useRealtime({ trace: true, merchant: persona });
  return (
    <div className="flex min-h-full items-start justify-center sm:items-center sm:p-4">
      <MerchantChat persona={persona} onPersona={setPersona} />
    </div>
  );
}
