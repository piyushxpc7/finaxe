# Prompt Changelog

## extraction/v1 — 2026-06-14
**Change:** Initial version. Migrated from Day 3 hardcoded string in `extraction/financial.py`.
**Why:** Prompts are versioned artifacts — every change is a deploy. Moving to registry enforces this.
**Model:** gpt-4o, temp 0
**Status:** Active

---

## summarize/v1 — 2026-06-14
**Change:** Initial version. 5-bullet analyst summary with section citation requirement.
**Why:** First structured summary prompt; cheaper model (gpt-4o-mini) — summarization doesn't need frontier.
**Model:** gpt-4o-mini, temp 0
**Status:** Active

---

## Changelog discipline
- Never edit an existing version file — create v2, v3, etc.
- Every new version requires an entry here with: what changed, why, model, date.
- The ledger records `prompt_version` per call — diffs are queryable.
