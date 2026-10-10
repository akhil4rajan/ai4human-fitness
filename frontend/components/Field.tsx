import { type ReactNode } from "react";

export function Field({ id, label, hint, children }: { id: string; label: string; hint?: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      {children}
      {hint && <p className="text-xs text-muted">{hint}</p>}
    </div>
  );
}

export const inputClass = "rounded-lg border border-border bg-surface px-3 py-2 w-full";
export const buttonClass =
  "rounded-lg bg-accent px-4 py-2 font-medium text-accent-contrast disabled:opacity-50";
