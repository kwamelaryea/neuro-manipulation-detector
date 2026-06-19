# Neuro Manipulation Detector — API Contract

This contract is **frozen** across Phase 1 (LLM scorer) and Phase 2 (TRIBE v2).
The Chrome extension depends only on this shape and never changes between phases.

## POST /analyze

### Request

```json
{
  "text": "string (required, min length 1) — visible page text",
  "url": "string (optional) — source URL, metadata only, not scored"
}
```

### Response — `200 OK`

```json
{
  "limbic_score": 0.0,          // float 0.0–1.0 — emotional arousal signal
  "pfc_score": 0.0,             // float 0.0–1.0 — cognitive engagement / suppression
  "manipulation_index": 0.0,    // float 0.0–10.0 — composite ratio (limbic / (pfc + ε))
  "dominant_technique": "fear", // one of: fear | urgency | tribal_identity | reward_loop | neutral
  "confidence": "high"          // one of: low | medium | high
}
```

### Errors

| Status | Meaning |
|---|---|
| 422 | Request validation failed (e.g. empty `text`) |
| 500 | Scorer error (LLM call failed, inference failed) |

## GET /health

Returns `{ "status": "ok" }`. Used for liveness checks.

## Scoring semantics

- **limbic_score** — strength of limbic/salience engagement (amygdala, insula, hippocampus).
- **pfc_score** — strength of prefrontal/executive engagement (dlPFC, ACC). Manipulative content suppresses this.
- **manipulation_index** — `clamp(10 * limbic / (pfc + 0.1), 0, 10)`. High limbic + low PFC ⇒ high index.
- **dominant_technique** — single strongest persuasion technique.
- **confidence** — scorer's certainty given text length and signal clarity.
