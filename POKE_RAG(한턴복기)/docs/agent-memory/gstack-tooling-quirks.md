---
name: gstack-tooling-quirks
description: "gstack helpers on this machine — bun.exe missing breaks codex probe, review-log, plan-reality; sub-skills read directly"
metadata:
  node_type: memory
  type: reference
  originSessionId: 4355691c-3097-4b2c-a44a-ab030cc27187
  modified: 2026-10-22T17:56:16.083Z
---

On this SSAFY desktop (as of 2026-10-23):
- `bun` was missing (bun.exe) until 2026-10-23; reinstalled with `npm i -g bun` (1.4.4). If gstack helpers fail with "bun.exe: No such file", reinstall the same way.
- gstack sub-skills are not registered as skills; read `~/.claude/skills/gstack/<name>/SKILL.md` directly.
- jq is not installed.

**How to apply:** on helper failure, check `bun --version` first. See [[ai-core-project-2]].
