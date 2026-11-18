"use client";

import { useEffect, useState } from "react";

import { apiRequest } from "@/lib/api/client";
import type { LoanTerms } from "@/lib/api/types";

/** The configured limits (LF-003/LF-004), read from the API so they never drift from the backend. */
export function useLoanTerms(): { terms: LoanTerms | null; failed: boolean } {
  const [terms, setTerms] = useState<LoanTerms | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let live = true;
    apiRequest<LoanTerms>("/api/loan-terms")
      .then((value) => live && setTerms(value))
      .catch(() => live && setFailed(true));
    return () => {
      live = false;
    };
  }, []);
  return { terms, failed };
}
