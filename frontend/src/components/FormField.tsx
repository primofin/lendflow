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
  "rounded border border-slate-400 px-3 py-2 text-base focus:outline-2 focus:outline-offset-2 focus:outline-blue-700";
export const buttonClass =
  "rounded bg-blue-800 px-4 py-2 font-medium text-white hover:bg-blue-900 focus:outline-2 focus:outline-offset-2 focus:outline-blue-700 disabled:cursor-not-allowed disabled:opacity-60";
