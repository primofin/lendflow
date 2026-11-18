"use client";

import { useEffect, useRef } from "react";

import { buttonClass } from "./FormField";

type Props = {
  open: boolean;
  title: string;
  children: React.ReactNode;
  confirmLabel: string;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
};

/** A modal confirmation on the native <dialog>: focus is trapped inside while open and returns
 * to the control that opened it when closed. Escape cancels. */
export function ConfirmDialog({
  open,
  title,
  children,
  confirmLabel,
  busy = false,
  onConfirm,
  onCancel,
}: Props) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      if (typeof dialog.showModal === "function") dialog.showModal();
      else dialog.setAttribute("open", "");
    } else if (!open && dialog.open) {
      if (typeof dialog.close === "function") dialog.close();
      else dialog.removeAttribute("open");
    }
  }, [open]);

  return (
    <dialog
      ref={ref}
      aria-labelledby="confirm-title"
      onCancel={(event) => {
        event.preventDefault(); // Escape: let our state close it so focus handling stays ours
        if (!busy) onCancel();
      }}
      className="m-auto max-w-md rounded border border-slate-400 p-6 backdrop:bg-black/40"
    >
      <h2 id="confirm-title" className="text-lg font-semibold">
        {title}
      </h2>
      <div className="mt-3">{children}</div>
      <div className="mt-5 flex gap-3">
        <button type="button" onClick={onConfirm} disabled={busy} className={buttonClass}>
          {busy ? "Saving…" : confirmLabel}
        </button>
        <button
          type="button"
          onClick={onCancel}
          disabled={busy}
          className="rounded border border-slate-400 px-4 py-2 font-medium"
        >
          Cancel
        </button>
      </div>
    </dialog>
  );
}
