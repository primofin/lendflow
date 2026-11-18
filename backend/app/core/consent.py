"""Consent text (BR-21). Bump CONSENT_VERSION whenever wording or purposes change."""

CONSENT_VERSION = "2026-11-v1"

PURPOSES: list[dict[str, str]] = [
    {
        "code": "credit_scoring",
        "label": "Credit scoring and assessment of your loan application",
    },
    {
        "code": "ai_document_processing",
        "label": "AI-assisted document processing (reading and summarising your documents; "
        "a human always makes the decision)",
    },
    {
        "code": "application_processing",
        "label": "Processing and tracking your application, including contact about its status",
    },
]

STATEMENT = (
    "LendFlow will process the personal data you provide only for the purposes listed. "
    "You can view, correct, export or request deletion of your data at any time."
)
