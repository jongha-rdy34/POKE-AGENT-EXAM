---
name: ai-core-project-2
description: "SSAFY AI core project round 2 (RAG domain knowledge service) in this folder; domain = Pokémon, planning stage as of 2026-10-21"
metadata:
  node_type: memory
  type: project
  originSessionId: a15b3ff2-c5d2-4265-977d-9ad37633eab2
  modified: 2026-10-22T01:40:14.383Z
---

c:\Users\SSAFY\Desktop\AIpjt holds SSAFY "AI 코어 프로젝트 2회차 — RAG 기반 도메인 지식 서비스". User chose the Pokémon domain (2026-10-21). Spec requires F2001–F2012 mandatory (two Chroma collections, 3 prompts: query extraction / candidate selection / answer generation, LangGraph retrieve+generate, citation display, Streamlit UI), F2013–F2016 optional, pinned library versions (LangChain 1.3.14, LangGraph 1.2.10, ChromaDB 1.5.9, Streamlit 1.62.0, etc.).

Data-source rules checked 2026-10-21: OP.GG terms (last updated 2026-09-14) forbid automated scripts/scraping/data mining and copying content without written consent → don't crawl op.gg. champs.pokedb.tokyo terms forbid bulk/continuous access and heavy load, but /guide/opendata publishes top-team CSV/JSON (`/opendata/s{n}_{single|double}_ranked_teams.{csv|json}`) and allows programmatic download if done gently and re-hosted locally; no explicit license.

PokeAPI checked 2026-10-21: has version-group/pokedex `champions` (231 species) and learnsets tagged `champions`; base stats, types, move power/type/class, nature +/- stats, names in ko/ja/ja-hrkt/ja-roma. Lacks stat formula, Champions stat-point system, damage/決定力 formulas, STAB rule → those must come from documents. Korean text is flavor text only (effect_entries are en/fr/de).

pokedb↔PokeAPI mapping (checked on S6 single, 2026-10-21): pokedb `id` = "DDDD-FF" (national dex + form index). Dex part = PokeAPI species id (114/114 matched, ja names identical). Form index usually = index in species.varieties, but not always (Floette 0670-05 = floette-eternal, variety idx 1, because cosmetic flower forms take indices) → keep an explicit form override table; match by pokemon-form `form_names` ja as fallback (Tauros Paldea name text differs). User wants dex-number-based mapping for maintenance.

Plan lives in agent.md at project root (2026-10-21): scope = Pokémon Champions; prefetch all Champions-scope data (PokeAPI + pokedb + champions-data GitHub CC BY 4.0), lazy-fetch+cache outside scope; calculations done in code inside the retrieve node. Fandom ko wiki: CC-BY-SA content but Fandom ToS bans automated access → only usable via XML dump (unverified) or permission.

Bulbapedia (checked 2026-10-21): API open, CC BY-NC-SA 2.5, robots Crawl-delay 5, no anti-bot policy found; has up-to-date Champions-era data (Mega Garchomp Z, Ogerpon) → chosen as main external doc source.

2026-10-22: user lifted the spec's tech-stack constraints (pinned versions, Streamlit, library whitelist) — free to build; recorded in agent.md 1.1 only, other sections not yet rewritten. Functional/non-functional requirements still apply.

2026-10-22 /office-hours: product wedge changed to "한 턴 복기 코치" — newcomer post-loss diagnosis (why did I lose → opponent item → how to beat), v1 singles one-turn, code back-calculates causes from pokedb item usage × SP spreads × natures. Approved design doc: docs/designs/loss-review-coach.md (+ ~/.gstack/projects/AIpjt/). User wants no paid subscription; ads only, later, IP risk acknowledged. User worries SSAFY GMS key will expire; OpenAI free accounts have no free credits → recommended moving embeddings local before GMS expires (pending user decision, needs new package).

**Why:** User wants a plan first; on 2026-10-21 they said not to write code yet.
**How to apply:** Don't start implementation until the user approves the plan. Related: [[user-domain-interests]].
