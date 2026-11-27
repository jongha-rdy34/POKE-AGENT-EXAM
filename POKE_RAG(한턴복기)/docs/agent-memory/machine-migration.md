---
name: machine-migration
description: After 2026-10-23 the user moves AIpjt off the SSAFY PC to a personal laptop; handoff at docs/HANDOFF-machine-migration.md
metadata:
  node_type: memory
  type: project
  originSessionId: 7161a63b-d20d-4a52-998b-182fd95d4f63
  modified: 2026-10-22T08:23:34.608Z
---

From 2026-10-24 the user works on a personal laptop, not the SSAFY PC (C:\Users\SSAFY\Desktop\AIpjt). User backs up files on 2026-10-23.

**Why:** The SSAFY PC is not available long-term. Repo has zero commits; data/raw/pokedb and chroma_db are gitignored, so a commit alone loses them.

**How to apply:** On a new machine, read docs/HANDOFF-machine-migration.md first. Memory folder name changes with the project path — copy these memory files into the new ~/.claude/projects/<slug>/memory/. Related: [[gms-key-expiry]], [[ai-core-project-2]].

**2026-10-23 update:** Migration path is the user's private GitHub repo (user commits/pushes) + backup zip `C:\Users\SSAFY\Desktop\AIpjt-backup-20261023.zip` (pokedb, chroma_db, data/logs, ~/.gstack/projects/AIpjt, memory; no .env). Steps and required skills: "★" section at top of docs/HANDOFF-machine-migration.md. Friend-test feedback: docs/HANDOFF-friend-test-1.md.
