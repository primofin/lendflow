/** LF-011 / BR-13: the checks a decision form can make before sending. The server still decides;
 * these only save a round trip and say what is missing. */

import type { DecisionOutcome, DecisionSubmit } from "@/lib/api/types";

/** Mirrors the API's minimum (EXPLANATION_MIN in app/schemas/decision.py). */
export const EXPLANATION_MIN = 20;

export type DecisionValues = {
  outcome: DecisionOutcome | "";
  reasonCode: string;
  explanation: string;
  conditions: string;
};

export type DecisionErrors = Partial<Record<keyof DecisionValues, string>>;

export function validateDecision(values: DecisionValues): DecisionErrors {
  const errors: DecisionErrors = {};
  const explanation = values.explanation.trim();
  if (!values.outcome) {
    errors.outcome = "Choose a decision.";
    return errors;
  }
  if (values.outcome === "reject") {
    if (!values.reasonCode) errors.reasonCode = "Choose a reason code for the rejection.";
    if (explanation.length < EXPLANATION_MIN) {
      errors.explanation = `Explain the rejection in plain language the borrower can understand (at least ${EXPLANATION_MIN} characters).`;
    }
    if (!values.conditions.trim()) {
      errors.conditions =
        "Say which documents or conditions could change the outcome.";
    }
  }
  if (values.outcome === "request_info" && explanation.length < EXPLANATION_MIN) {
    errors.explanation = `Say which information the borrower must add (at least ${EXPLANATION_MIN} characters).`;
  }
  return errors;
}

/** Only the fields the outcome carries are sent: the API refuses extras. */
export function toDecisionPayload(
  values: DecisionValues,
  supersedesId: string | null,
): DecisionSubmit {
  const outcome = values.outcome as DecisionOutcome;
  const payload: DecisionSubmit = { outcome };
  if (outcome === "reject") {
    payload.reason_code = values.reasonCode;
    payload.explanation = values.explanation.trim();
    payload.conditions = values.conditions.trim();
  } else if (outcome === "request_info") {
    payload.explanation = values.explanation.trim();
  }
  if (supersedesId) payload.supersedes_id = supersedesId;
  return payload;
}

export const CONFIRMATION: Record<DecisionOutcome, string> = {
  approve:
    "You are approving this application. The borrower will be told it is approved.",
  reject:
    "You are rejecting this application. The borrower will see the reason, your explanation and the conditions.",
  request_info:
    "You are asking the borrower for more information. They will see your message.",
  refer: "You are referring this file to a supervisor. The borrower is not told.",
};
