---
name: gms-key-expiry
description: SSAFY GMS API key expires 2026-10-23; replacement must be a paid OpenAI API key (ChatGPT Plus does not cover API)
metadata:
  node_type: memory
  type: project
  originSessionId: 7161a63b-d20d-4a52-998b-182fd95d4f63
  modified: 2026-10-22T08:15:57.714Z
---

SSAFY GMS API key expires 2026-10-23 (user, 2026-10-22). After that the user must issue a new key. User has ChatGPT Plus, which does NOT include API credits — API is billed separately on platform.openai.com (prepaid, min ~$5).

**Why:** All chat (`gpt-4o-mini`) and embeddings (`text-embedding-3-small`) go through `config.OPENAI_BASE_URL` (GMS). Losing the key stops RAG answers; D16 degraded mode keeps calculator output alive.

**How to apply:** Switching = change `OPENAI_API_KEY`, clear `OPENAI_BASE_URL` in `.env`. Before assuming reindex is needed, re-embed a few stored Chroma chunks with the new key and compare to stored vectors (cos ≈ 1.0 → no reindex). Related: [[ai-core-project-2]].
