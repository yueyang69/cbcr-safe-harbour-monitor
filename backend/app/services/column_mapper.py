"""Deterministic CSV column → CbCR standard field mapping (Stage 3).

Maps raw CSV headers to the standard financial_data fields using the shared
ALIASES dictionary plus difflib fuzzy matching. No LLM involved — this is the
deterministic mapping layer for the batch upload flow. AI never touches the
Safe Harbour engine; neither does this module.
"""
from __future__ import annotations

from difflib import SequenceMatcher

from .ai_service import ALIASES

# The standard fields a CSV column may map to (mirrors the financial_data model).
STANDARD_FIELDS = [
    "jurisdiction",
    "fiscal_year",
    "currency",
    "revenue",
    "pbt",
    "covered_taxes",
    "payroll",
    "tangible_assets",
]

EXACT_CONFIDENCE = 1.0
ALIAS_CONFIDENCE = 0.9
FUZZY_THRESHOLD = 0.6


def map_columns(
    csv_headers: list[str],
    sample_values: dict[str, list[str]] | None = None,
) -> list[dict]:
    """Map each CSV header to a standard field (three-tier matching).

    1. Exact match against ALIASES (case/whitespace-insensitive) → keeps the
       alias's stored confidence (1.0 for canonical English, 0.80-0.99 for
       Chinese / looser aliases).
    2. Fuzzy match (difflib ratio > FUZZY_THRESHOLD) against every ALIASES key
       → highest score wins, capped at ALIAS_CONFIDENCE.
    3. No match → mapped_field=None, confidence=0 (frontend must pick manually).

    Returns a list of
    [{"csv_name", "mapped_field", "confidence", "sample_values"}] where
    sample_values is a small preview of actual cell values per column (kept as
    reference for the human reviewer, not used for scoring).
    """
    samples = sample_values or {}
    results: list[dict] = []

    for header in csv_headers:
        lookup_key = header.strip().lower()
        match = ALIASES.get(lookup_key)

        if match is not None:
            target, confidence = match
            results.append({
                "csv_name": header,
                "mapped_field": target,
                "confidence": EXACT_CONFIDENCE if lookup_key == target else confidence,
                "sample_values": samples.get(header, []),
            })
            continue

        # Fuzzy pass: highest-scoring alias key above threshold.
        best_field: str | None = None
        best_score = 0.0
        for alias, (target, _) in ALIASES.items():
            score = SequenceMatcher(None, lookup_key, alias.strip().lower()).ratio()
            if score > FUZZY_THRESHOLD and score > best_score:
                best_score = score
                best_field = target

        if best_field is not None:
            results.append({
                "csv_name": header,
                "mapped_field": best_field,
                "confidence": min(ALIAS_CONFIDENCE, best_score),
                "sample_values": samples.get(header, []),
            })
            continue

        results.append({
            "csv_name": header,
            "mapped_field": None,
            "confidence": 0,
            "sample_values": samples.get(header, []),
        })

    return results
