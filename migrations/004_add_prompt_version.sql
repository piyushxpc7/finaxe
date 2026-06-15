-- Migration 004: add prompt_version column to llm_calls
-- Tracks which prompt version was used for each LLM call.
-- NULL for calls made before Day 4 (backward-compatible).

ALTER TABLE llm_calls
    ADD COLUMN IF NOT EXISTS prompt_version TEXT;
