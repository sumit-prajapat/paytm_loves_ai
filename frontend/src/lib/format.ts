/** Display-only formatting. Never computes money, prices, EMI, scores or dates. */
import type { Money } from "@/types/contracts";

const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 });

/** Prefer the backend's own formatted string; fall back to Indian grouping of a tool value. */
export function formatINR(v: Money | number | null | undefined): string {
  if (v == null) return "—";
  if (typeof v === "object") return v.formatted;
  return inr.format(v).replace(/\.00$/, "");
}

export function formatTime(iso?: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso.endsWith("Z") || /[+-]\d\d:\d\d$/.test(iso) ? iso : `${iso}Z`);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function formatDate(iso?: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso.length === 10 ? `${iso}T00:00:00` : iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

/** "125" (minutes, from the tool) -> "2h 05m". Pure unit display, no arithmetic on money. */
export function formatDuration(min?: number | null): string {
  if (min == null) return "—";
  const h = Math.floor(min / 60);
  const m = min % 60;
  return h ? `${h}h ${String(m).padStart(2, "0")}m` : `${m}m`;
}

export function pct(v?: number | null, digits = 0): string {
  if (v == null) return "—";
  return `${(v * 100).toFixed(digits)}%`;
}

export function maskId(id?: string | null): string {
  if (!id) return "—";
  return id.length > 6 ? `••••${id.slice(-4)}` : id;
}

export function ago(iso?: string | null): string {
  if (!iso) return "";
  const d = new Date(iso.endsWith("Z") || /[+-]\d\d:\d\d$/.test(iso) ? iso : `${iso}Z`).getTime();
  const s = Math.max(0, Math.round((Date.now() - d) / 1000));
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.round(s / 60)}m ago`;
  return `${Math.round(s / 3600)}h ago`;
}
