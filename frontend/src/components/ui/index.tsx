import clsx from "clsx";
import { Loader2, X } from "lucide-react";
import { useEffect, type ButtonHTMLAttributes, type ReactNode } from "react";
import { useToasts } from "@/lib/toast";

type Variant = "primary" | "sky" | "secondary" | "danger" | "ghost" | "ok";

export function Button({
  variant = "secondary", size = "md", loading, className, children, ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: "sm" | "md" | "lg"; loading?: boolean }) {
  return (
    <button
      {...rest}
      disabled={rest.disabled || loading}
      className={clsx(
        "inline-flex select-none items-center justify-center gap-1.5 rounded-btn border font-semibold transition",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 focus-visible:ring-offset-1",
        "disabled:cursor-not-allowed disabled:opacity-50",
        size === "sm" && "min-h-[36px] px-2.5 text-xs",
        size === "md" && "min-h-[44px] px-3.5 text-sm",
        size === "lg" && "min-h-[56px] px-5 text-base",
        variant === "primary" && "border-navy-700 bg-navy-700 text-white hover:bg-navy-900",
        variant === "sky" && "border-sky-500 bg-sky-500 text-navy-900 hover:brightness-95",
        variant === "secondary" && "border-line bg-card text-ink font-bold hover:bg-slate-100 dark:hover:bg-slate-800",
        variant === "danger" && "border-risk bg-risk text-white hover:brightness-95",
        variant === "ok" && "border-ok bg-ok text-white hover:brightness-95",
        variant === "ghost" && "border-transparent bg-transparent text-ink hover:bg-slate-100 dark:hover:bg-slate-800",
        className,
      )}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
      {children}
    </button>
  );
}

export function Badge({ tone = "sky", children, className }: { tone?: "ok" | "warn" | "risk" | "sky" | "sim" | "muted"; children: ReactNode; className?: string }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-bold",
        tone === "ok" && "bg-ok-bg text-ok",
        tone === "warn" && "bg-warn-bg text-warn",
        tone === "risk" && "bg-risk-bg text-risk",
        tone === "sky" && "bg-sky-100 text-sky-800",
        tone === "sim" && "border border-amber-300 bg-amber-100 text-amber-800",
        tone === "muted" && "bg-slate-100 text-slate-600",
        className,
      )}
    >
      {children}
    </span>
  );
}

export function SimulatedBadge({ label = "SIMULATED DATA" }: { label?: string }) {
  return <Badge tone="sim">⚠ {label}</Badge>;
}

export function Card({ className, children, ...rest }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div {...rest} className={clsx("rounded-card border border-line bg-card p-4 shadow-card", className)}>
      {children}
    </div>
  );
}

export function Switch({ checked, onChange, label, danger }: { checked: boolean; onChange: (v: boolean) => void; label: string; danger?: boolean }) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={clsx(
        "relative h-7 w-12 shrink-0 rounded-full transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500",
        checked ? (danger ? "bg-risk" : "bg-ok") : "bg-slate-400",
      )}
    >
      <span className={clsx("absolute top-1 h-5 w-5 rounded-full bg-white shadow transition-all", checked ? "left-6" : "left-1")} />
    </button>
  );
}

export function Dialog({ open, onClose, title, children, footer }: { open: boolean; onClose: () => void; title: string; children: ReactNode; footer?: ReactNode }) {
  useEffect(() => {
    if (!open) return;
    const k = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-slate-900/40 p-4" onClick={onClose}>
      <div role="dialog" aria-modal aria-label={title} className="w-full max-w-lg animate-rise rounded-card bg-white p-5 shadow-card" onClick={(e) => e.stopPropagation()}>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-bold">{title}</h2>
          <button aria-label="Close" onClick={onClose} className="rounded-full p-1 hover:bg-slate-100"><X className="h-5 w-5" /></button>
        </div>
        <div className="max-h-[70vh] overflow-auto scrollbar-thin">{children}</div>
        {footer && <div className="mt-4 flex flex-wrap justify-end gap-2">{footer}</div>}
      </div>
    </div>
  );
}

export function Sheet({ open, onClose, title, children, side = "right" }: { open: boolean; onClose: () => void; title: string; children: ReactNode; side?: "right" | "bottom" }) {
  useEffect(() => {
    if (!open) return;
    const k = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-40 bg-slate-900/40" onClick={onClose}>
      <aside
        role="dialog"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
        className={clsx(
          "absolute flex flex-col bg-white shadow-2xl",
          side === "right" ? "right-0 top-0 h-full w-full max-w-md animate-rise" : "bottom-0 left-0 right-0 max-h-[85vh] rounded-t-3xl animate-rise",
        )}
      >
        <div className="flex items-center justify-between border-b border-line px-4 py-3">
          <h2 className="font-bold">{title}</h2>
          <button aria-label="Close" onClick={onClose} className="rounded-full p-1 hover:bg-slate-100"><X className="h-5 w-5" /></button>
        </div>
        <div className="flex-1 overflow-auto p-4 scrollbar-thin">{children}</div>
      </aside>
    </div>
  );
}

export function Tabs<T extends string>({ tabs, value, onChange }: { tabs: { id: T; label: string }[]; value: T; onChange: (v: T) => void }) {
  return (
    <div role="tablist" className="flex flex-wrap gap-1">
      {tabs.map((t) => (
        <button
          key={t.id}
          role="tab"
          aria-selected={value === t.id}
          onClick={() => onChange(t.id)}
          className={clsx("min-h-[36px] rounded-lg px-3 text-xs font-semibold", value === t.id ? "bg-sky-100 text-sky-800" : "text-muted hover:bg-slate-100")}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

export function Toaster() {
  const { toasts, dismiss } = useToasts();
  return (
    <div aria-live="polite" className="pointer-events-none fixed bottom-4 right-4 z-[60] flex w-[min(360px,calc(100vw-2rem))] flex-col gap-2">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={clsx(
            "pointer-events-auto animate-rise rounded-xl border bg-white p-3 shadow-card",
            t.tone === "risk" && "border-l-4 border-l-risk",
            t.tone === "ok" && "border-l-4 border-l-ok",
            t.tone === "warn" && "border-l-4 border-l-warn",
            t.tone === "info" && "border-l-4 border-l-sky-500",
          )}
        >
          <div className="flex items-start justify-between gap-2">
            <b className="text-sm">{t.title}</b>
            <button aria-label="Dismiss" onClick={() => dismiss(t.id)} className="text-muted"><X className="h-4 w-4" /></button>
          </div>
          {t.body && <p className="mt-0.5 text-xs text-muted">{t.body}</p>}
        </div>
      ))}
    </div>
  );
}

export function Empty({ icon, title, sub }: { icon?: ReactNode; title: string; sub?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-1 py-6 text-center text-muted">
      {icon}
      <b className="text-sm text-ink">{title}</b>
      {sub && <p className="text-xs">{sub}</p>}
    </div>
  );
}

export function SaarthiMark({ size = 32 }: { size?: number }) {
  return (
    <img
      src="/assets/paytm_ai_logo.png"
      alt="Paytm loves AI"
      className="inline-block rounded bg-white p-0.5 object-contain shadow-sm"
      style={{ height: size, width: "auto", maxHeight: 40 }}
      onError={(e) => {
        (e.target as HTMLElement).style.display = "none";
      }}
    />
  );
}
