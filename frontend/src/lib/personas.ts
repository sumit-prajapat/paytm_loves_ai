import type { Lang, PersonaId, Role } from "@/types/contracts";

export interface Persona {
  id: PersonaId;
  label: string;
  role: Role;
  /** target_id for POST /auth/demo-token (merchant_id or customer_id). */
  targetId?: string;
  merchantId?: string;
  deviceId?: string;
  customerId?: string;
  defaultLang: Lang;
  elder?: boolean;
  note?: string;
}

export const PERSONAS: Record<PersonaId, Persona> = {
  ramesh: { id: "ramesh", label: "Ramesh (Kirana, Delhi)", role: "merchant", targetId: "m_ramesh", merchantId: "m_ramesh", deviceId: "soundbox_ramesh_01", defaultLang: "hi" },
  sunita: { id: "sunita", label: "Sunita (Tailor, Mumbai)", role: "merchant", targetId: "m_sunita", merchantId: "m_sunita", deviceId: "soundbox_sunita_01", defaultLang: "hinglish" },
  gupta: { id: "gupta", label: "Gupta Electronics (Lucknow)", role: "merchant", targetId: "m_disputed", merchantId: "m_disputed", deviceId: "soundbox_gupta_01", defaultLang: "hi" },
  arjun: { id: "arjun", label: "Arjun", role: "traveller", targetId: "c_arjun", customerId: "c_arjun", defaultLang: "hinglish" },
  meena: { id: "meena", label: "Meena Aunty", role: "traveller", targetId: "c_meena", customerId: "c_meena", defaultLang: "hi", elder: true },
  priya: {
    id: "priya", label: "Priya", role: "traveller", targetId: "c_arjun", customerId: "c_arjun", defaultLang: "en",
    note: "Backend has no Priya account; Priya uses the Arjun demo account with English replies.",
  },
  ops: { id: "ops", label: "Ops agent", role: "ops_agent", defaultLang: "en" },
  admin: { id: "admin", label: "Admin", role: "admin", defaultLang: "en" },
};

export const MERCHANT_PERSONAS: PersonaId[] = ["ramesh", "sunita", "gupta"];
export const TRAVEL_PERSONAS: PersonaId[] = ["arjun", "meena", "priya"];

export const MERCHANT_NAMES: Record<string, string> = {
  m_ramesh: "Ramesh Kirana Store",
  m_sunita: "Sunita Tailors",
  m_disputed: "Gupta Electronics",
};
