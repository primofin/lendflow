"use client";

import { useRef, useState } from "react";
import type { FormEvent } from "react";

import { apiRequest } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import { docTypeLabel } from "@/lib/api/types";
import type { UploadedDocument, UploadNotice } from "@/lib/api/types";
import { checkFile } from "@/lib/loan/fileCheck";

import { buttonClass, inputClass } from "./FormField";

type Props = {
  applicationId: string;
  label: string; // what is being uploaded, for the accessible names
  docTypes: string[]; // any of these satisfies it; more than one shows a choice
  notice: UploadNotice;
  knownIds: string[]; // documents already stored, to recognise a repeat of the same file
  onDone: () => void;
};

/** LF-005: one upload form. Used per missing item and for extra documents. */
export function UploadControl({ applicationId, label, docTypes, notice, knownIds, onDone }: Props) {
  const [docType, setDocType] = useState(docTypes[0]);
  const [message, setMessage] = useState<{ kind: "error" | "ok"; text: string } | null>(null);
  const [sending, setSending] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    const file = input.current?.files?.[0];
    if (!file) {
      setMessage({ kind: "error", text: "Choose a file first." });
      return;
    }
    const problem = checkFile(file, notice);
    if (problem) {
      setMessage({ kind: "error", text: problem });
      return;
    }
    const form = new FormData();
    form.set("doc_type", docType);
    form.set("file", file);
    setSending(true);
    try {
      const stored = await apiRequest<UploadedDocument>(
        `/api/applications/${applicationId}/documents`,
        { method: "POST", form },
      );
      setMessage({
        kind: "ok",
        text: knownIds.includes(stored.id)
          ? "This file was already uploaded, so nothing was added."
          : "Uploaded.",
      });
      if (input.current) input.current.value = "";
      onDone();
    } catch (failure) {
      setMessage({
        kind: "error",
        text:
          failure instanceof ApiError
            ? failure.message
            : "The upload did not finish. Check your connection and try again; sending the same file again will not create a duplicate.",
      });
    } finally {
      setSending(false);
    }
  }

  return (
    <form onSubmit={submit} className="mt-2 flex flex-wrap items-center gap-2" noValidate>
      {docTypes.length > 1 && (
        <select
          aria-label={`Document type for ${label}`}
          value={docType}
          onChange={(e) => setDocType(e.target.value)}
          className={inputClass}
        >
          {docTypes.map((type) => (
            <option key={type} value={type}>
              {docTypeLabel(type)}
            </option>
          ))}
        </select>
      )}
      <input
        ref={input}
        type="file"
        accept={notice.allowed_types.join(",")}
        aria-label={`File for ${label}`}
        className="max-w-full text-sm"
      />
      <button
        type="submit"
        disabled={sending}
        aria-label={`Upload ${label}`}
        className={buttonClass}
      >
        {sending ? "Uploading…" : "Upload"}
      </button>
      {message && (
        <p
          role={message.kind === "error" ? "alert" : "status"}
          className={`basis-full text-sm ${message.kind === "error" ? "text-red-700" : "text-green-800"}`}
        >
          {message.text}
        </p>
      )}
    </form>
  );
}
