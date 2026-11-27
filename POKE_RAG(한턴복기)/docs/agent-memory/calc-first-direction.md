---
name: calc-first-direction
description: "Review coach must show damage calc per opponent build first (Smart Nuo parity), stats layered on top; Champions items first"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 4355691c-3097-4b2c-a44a-ab030cc27187
  modified: 2026-10-23T01:30:05.825Z
---

The loss-review coach must lead with plain damage calculation: for each opponent build [SP | nature | ability | item], show whether the actual result reproduces ("16번 중 k번 (6.3%)"), even for builds absent from usage stats. Usage stats (pokedb/Smogon item and ability rates) are annotations on those rows, not a filter. Items currently in Pokémon Champions come first (official list: champion_item table from Bulbapedia + Showdown Reg M-C, 85 held items, built by prep/champions_items.py — not usage data); out-of-Champions items (choice band/specs, assault vest) are still shown but after and labeled.

**Why:** Friend case 1 (2026-10-23): Pawmot Iron Fist ice punch KO'd H2 C32 S32 Modest Mega Garchomp Z; the stats-only model said "no reason found", while Smart Nuo (the calculator the user and friends use) showed Life Orb 6.3% / Choice Band 75.0%. The user's words: if it can't do this, people will just use existing calculators.

**How to apply:** validate new mechanics against Smart Nuo/Showdown numbers before trusting stats-based output; never let missing usage data hide a calc-possible build. Roll % in the calc table is OK (calc fact); keep cause-probability % hidden. Community SP shorthand "CS" means H2 C32 S32. See [[data-source-priority]], [[ai-core-project-2]].
