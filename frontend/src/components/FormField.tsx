import type { ReactNode } from "react";

type Props = {
  id: string;
  label: string;
  hint?: string;
  children: (describedBy: string | undefined) => ReactNode;
};

/** A labelled form control. The hint is announced with the control through aria-describedby. */
export function FormField({ id, label, hint, children }: Props) {
  const hintId = hint ? `${id}-hint` : undefined;
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      {children(hintId)}
      {hint && (
        <p id={hintId} className="text-sm text-slate-600">
          {hint}
        </p>
      )}
    </div>
  );
}

export const inputClass =
  "w-full rounded-xl border border-slate-300 bg-surface px-3.5 py-2.5 text-base shadow-sm placeholder:text-slate-400 focus:border-blue-700 focus:outline-2 focus:outline-offset-0 focus:outline-blue-200";
export const buttonClass =
  "inline-flex items-center justify-center gap-2 rounded-xl bg-brand px-5 py-2.5 font-semibold text-white shadow-sm transition hover:bg-brand-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700 disabled:cursor-not-allowed disabled:opacity-60";
export const secondaryButtonClass =
  "inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-surface px-5 py-2.5 font-semibold text-slate-800 shadow-sm transition hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700 disabled:cursor-not-allowed disabled:opacity-60";
