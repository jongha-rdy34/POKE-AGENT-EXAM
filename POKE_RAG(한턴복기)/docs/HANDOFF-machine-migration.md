# 인계장: 노트북으로 작업 환경 이전 (2026-10-22 작성, 2026-10-23 GitHub 방식으로 갱신)

## ★ 2026-10-23 갱신: GitHub 저장소 + 백업 압축본 방식 (이 절이 아래 내용보다 우선)

옮기는 경로는 둘이다. 코드와 문서는 **사용자의 비공개 GitHub 저장소**로 옮긴다. git에 넣지 않는 데이터는 **백업 압축본** `C:\Users\SSAFY\Desktop\AIpjt-backup-20261023.zip`(약 53MB)으로 옮긴다. `.env`는 어느 쪽에도 넣지 않는다.

### A. 이 PC에서 (사용자가 직접. 커밋은 사용자가 한다)

1. GitHub에서 **비공개(Private)** 저장소를 만든다. README·.gitignore는 추가하지 않고 빈 저장소로 만든다.
2. 저장소 폴더에서:
   ```
   git config user.name "<이름>"
   git config user.email "<GitHub 이메일>"
   git checkout -b main
   git add -A
   git status            # .env, .venv/, chroma_db/, data/raw/pokedb/, data/logs/ 가 목록에 없어야 한다
   git commit -m "Initial import: loss review coach (server, web, prep, rag, docs)"
   git remote add origin https://github.com/<계정>/<저장소>.git
   git push -u origin main
   ```
   - 커밋 대상은 약 5,270개 파일, 24MB다. 대부분 `data/raw/pokeapi`이고, 가장 큰 파일은 `data/processed/pokedex.sqlite`(7.9MB)다.
   - 2026-10-23에 비밀값 검사를 했다. 걸린 것은 문서·테스트의 예시값(`이름표:비밀값`, `s3cret`)과 기술 이름 문자열(`sk-galar…`)뿐이었다.
   - `prep/.agents/skills/`(agent-skills 25개 사본)가 커밋 대상에 들어간다. 플러그인과 중복이다. 넣을지 사용자가 정한다. 빼려면 `.gitignore`에 `prep/.agents/`를 추가한다.
3. 백업 압축본을 USB나 개인 클라우드로 옮긴다. 압축본 안의 `data/logs/`에는 친구 테스트 원문이 들어 있다. 친구 동의 범위가 "다른 사람에게 보내지 않는다"이므로 공유 폴더에는 두지 않는다.
4. `.env` 값 중 노트북에서 다시 쓸 것은 `INVITE_TOKENS`(friend1~3)뿐이다. GMS 키는 만료된다. 메신저로 보내지 말고, 노트북에서 새로 쓰거나 직접 옮겨 적는다.

### B. 노트북에서

1. `git clone https://github.com/<계정>/<저장소>.git AIpjt`
2. 백업 압축본을 푼다. `README.txt`대로 옮긴다.
   - `repo-ignored/*` → 저장소 루트(`data/raw/pokedb`, `chroma_db`, `data/logs`)
   - `gstack/AIpjt/` → `~/.gstack/projects/AIpjt/` (gstack 설치 뒤)
   - `claude-memory/*` → `~/.claude/projects/<새 경로 이름>/memory/`. 새 경로 이름은 노트북에서 Claude Code를 한 번 실행해 확인한다. 저장소의 `docs/agent-memory/`도 같은 내용이다.
3. Python 3.12로 `python -m venv .venv` 후 `.venv\Scripts\pip install -r requirements.txt`
4. `.env.example`을 `.env`로 복사한다. 새 OpenAI API 키를 넣고, `OPENAI_BASE_URL`은 비우고, `INVITE_TOKENS`를 넣는다.
5. 아래 "노트북에서 확인할 것" 2~3을 한다. 테스트는 2026-10-23 기준 **86개 통과**다. 그다음 임베딩 호환을 확인한다.
6. 서버: `.venv\Scripts\python -m uvicorn server.app:app --port 8000 --no-access-log`
   - 친구에게 링크를 줄 때는 `cloudflared tunnel --url http://127.0.0.1:8000`을 쓴다(`winget install Cloudflare.cloudflared`).
   - SSAFY 망은 cloudflared(7844)를 막지만 집 망은 보통 열려 있다. 막히면 `--protocol http2`를 붙인다. 그래도 안 되면 Pinggy(`ssh -p 443 -R0:127.0.0.1:8000 a.pinggy.io`, 무료 60분)를 쓴다.

### C. 설치할 스킬·플러그인 (Claude Code)

이 프로젝트의 설계·리뷰 문서는 아래 스킬로 만들었다. 다음 agent도 같은 도구를 쓰면 문서 형식(D·R·C 번호, 리뷰 보고서)이 이어진다.

| 무엇 | 출처 | 설치 | 이 프로젝트에서 쓴 곳 |
|---|---|---|---|
| **gstack** (필수) | github.com/garrytan/gstack (이 PC는 v1.91.176.0) | 저장소 README의 설치 절차대로 `~/.claude/skills/gstack`에 받고 `./setup` | /office-hours(설계 2건), /plan-ceo-review, /plan-eng-review(#1~#3), /plan-design-review, /design-consultation(DESIGN.md) |
| superpowers | 마켓플레이스 `anthropics/claude-plugins-official` | `/plugin`에서 `superpowers@claude-plugins-official` | 브레인스토밍·계획·TDD 흐름 |
| agent-skills | 마켓플레이스 `addyosmani/agent-skills` | `/plugin marketplace add addyosmani/agent-skills` 후 `agent-skills@addy-agent-skills` | spec·plan·test·review |
| ponytail | 마켓플레이스 `DietrichGebert/ponytail` | `/plugin marketplace add DietrichGebert/ponytail` 후 `ponytail@ponytail` | 최소 변경 원칙(세션 시작 시 자동) |
| figma | `figma@claude-plugins-official` | `/plugin`에서 설치 | 선택. 이 프로젝트에서 쓴 기록 없음 |
| design-taste-frontend | github.com/Leonxlnx/taste-skill | 저장소의 `.agents/skills/`와 `skills-lock.json`에 이미 들어 있다(따로 설치 불필요) | DESIGN.md 검수(0 FAIL·0 WARN) |

gstack 관련 함정(이 PC 기준):
- 이 Windows 환경에서는 `/office-hours` 같은 하위 스킬이 슬래시 명령으로 등록되지 않았다. `/gstack` 라우터를 쓰거나, `~/.claude/skills/gstack/<이름>/SKILL.md`를 직접 읽어 실행한다.
- 헬퍼가 `bun.exe: No such file`로 깨지면 `npm i -g bun`을 다시 실행한다(2026-10-23에 두 번 겪음).
- `jq`가 없어 일부 로그 단계를 건너뛰었다. 노트북에는 설치해 둔다.
- Codex 외부 리뷰를 쓰려면 `npm i -g @openai/codex`와 `gstack-config set codex_reviews enabled`가 필요하다.

---

사용자는 2026-10-23 이후 이 PC(SSAFY 교육장, `C:\Users\SSAFY\Desktop\AIpjt`)를 계속 쓸 수 없다. 이후 작업은 개인 노트북에서 한다. 파일 백업은 2026-10-23에 사용자가 직접 한다. 이 문서는 무엇을 옮기고 무엇을 새로 만들지 정리한다.

## 먼저 알아 둘 것

- **커밋이 0개다.** 모든 파일이 untracked 상태라 git 기록으로 복구할 수 없다. 옮기기 전에 첫 커밋을 만들거나, 폴더 전체를 압축해서 옮긴다. 커밋할 때 `.env`가 빠졌는지 확인한다(`.gitignore`에 있음).
- **GMS API 키가 2026-10-23에 만료된다.** 노트북에서는 새 키가 필요하다.
  - ChatGPT Plus 구독은 API를 포함하지 않는다. platform.openai.com에서 결제 수단을 등록하고(최소 $5 선불) 키를 따로 발급한다.
  - `.env`에서 `OPENAI_API_KEY`를 새 키로 바꾸고, `OPENAI_BASE_URL`을 비운다(GMS 주소 제거).
- **Remote Control(`claude rc`)은 이 PC에서 실행된다.** 이 PC를 끄면 폰에서도 이어 갈 수 없다. 노트북에서는 노트북에서 새로 실행한다.
- 다른 세션 두 개가 같은 폴더에서 작업 중이었다(엔지니어링+헤드, aipjt-8d). 백업 전에 두 세션의 작업이 끝났는지 확인한다. 특히 계산기 구현(`prep/calculator.py`)이 진행 중이었다.

## 옮길 것

| 무엇 | 위치(이 PC) | 크기 | 비고 |
|---|---|---|---|
| 프로젝트 전체 | `C:\Users\SSAFY\Desktop\AIpjt` | 약 867MB (`.venv` 788MB 포함) | `.venv`는 빼고 옮긴다(아래 "새로 만들 것") |
| 원본 데이터 | `data/raw/` (pokedb·pokeapi·bulbapedia·bulbapedia_rules·champions_data) | 24MB | `data/raw/pokedb/`는 `.gitignore`에 있어 **커밋하면 빠진다.** 압축본에 꼭 포함하거나, 다운로드 스크립트로 다시 받는다 |
| 가공 데이터 | `data/processed/pokedex.sqlite` 등 | 3.9MB | D24로 도구 전체 분포 재빌드 완료본 |
| 평가셋 | `data/eval/` | 56KB | `community_cases.jsonl` 51건 |
| 벡터 색인 | `chroma_db/` | 48MB | `.gitignore`에 있다. 옮기면 재색인(임베딩 비용)이 필요 없다 |
| 비밀값 | `.env` | — | **커밋·메신저로 보내지 않는다.** GMS 키는 어차피 만료되므로 새 키로 새로 쓴다 |
| 설계·리뷰 문서 | `docs/designs/` | 작음 | 설계 v1.2, 디자인·CEO 리뷰 보고서, 인계장들, 프로토타입 |
| gstack 상태 | `C:\Users\SSAFY\.gstack\` | 367KB | `projects/AIpjt/`(설계 원본·테스트 계획·결정·학습·리뷰 로그), `config.yaml` |
| Claude 메모리 | `C:\Users\SSAFY\.claude\projects\c--Users-SSAFY-Desktop-AIpjt\memory\` | 21KB | 노트북의 프로젝트 경로가 달라지면 폴더 이름도 바뀐다. 노트북에서 한 번 실행해 새 폴더(`~/.claude/projects/<새 경로 이름>/memory/`)를 확인한 뒤, 그 안에 파일을 복사한다 |

## 새로 만들 것 (옮기지 않음)

- **Python 가상환경:** 이 PC는 Python 3.12.10이다. 노트북에서 다음을 실행한다.
  ```
  python -m venv .venv
  .venv\Scripts\pip install -r requirements.txt
  ```
- **gstack 스킬:** `~/.claude/skills/gstack`(100MB)은 옮기지 말고 노트북에서 다시 설치한다. 이 Windows 환경에서는 하위 스킬이 등록되지 않아, `~/.claude/skills/gstack/<이름>/SKILL.md`를 직접 읽어 실행했다.
- **Codex 외부 리뷰용 도구:** `npm i -g @openai/codex`, `npm i -g bun`, `gstack-config set codex_reviews enabled`. 그리고 `jq`도 설치한다(없어서 task JSONL을 건너뛰었다).
- **`__pycache__/`:** 옮기지 않는다.

## 노트북에서 확인할 것 (순서대로)

1. `.env`에 새 OpenAI 키를 넣고 `OPENAI_BASE_URL`을 비운다.
2. `.venv\Scripts\python -m unittest discover -s tests -t .`가 통과하는지 본다(기존 계산기 테스트 15개 + 이후 추가분).
3. **임베딩 호환 확인.** Chroma에 저장된 청크 몇 개의 원문을 새 키(`text-embedding-3-small`)로 다시 임베딩해서, 저장된 벡터와 코사인 유사도를 비교한다. 약 1.0이면 재색인하지 않는다. 다르면 전체를 재색인한다(336 + 2,364건).
4. 메모리 파일이 새 경로에서 읽히는지 본다. 새 세션의 시작 컨텍스트에 `MEMORY.md` 목록이 보이면 된다.
5. 이어서 할 일은 `docs/designs/loss-review-coach.ceo-review.md`(CEO 리뷰, 범위 축소 모드)와 `HANDOFF-design-implementation.md`부터 읽는다.

## 갱신 (2026-10-23, 엔지니어링 세션)

- **GMS 키:** 2026-10-23 확인 시점에는 임베딩 호출이 성공했다(만료 시각 미확인). 노트북에서는 위 1번대로 새 키를 쓴다.
- **추가된 데이터·코드:**
  - `data/raw/bulbapedia_rules/`(규칙 문서 45개, T10), `data/raw/smogon/2026-09_gen9championsbssregmc-1500.json`(3.7MB, Smogon 월간 통계).
  - `prep/bulbapedia_rules.py`, `prep/smogon.py`, `rag/index_rules.py`, `prep/review.py`(현재 `current_season`만), `data/eval/community_cases_verification.json`.
  - `pokedex.sqlite`에 `smogon_usage` 테이블(323종).
- **색인 건수 변경:** `pokemon_docs`는 2,364 → **2,731**(규칙 문서 367청크). 3번 임베딩 호환 확인에서 재색인하게 되면 `pokemon_meta` 336 + `pokemon_docs` 2,731이다(`rag.index_meta`, `rag.index_docs`, `rag.index_bulbapedia`, `rag.index_rules` 순).
- **테스트:** 2번 확인 기준은 이제 **27개**(계산기 22 + 시즌 3 + Smogon 2).
- `data/raw/smogon/`은 `.gitignore`에 없다. 커밋해도 되지만 3.7MB이므로 압축본에 포함하거나 `python -m prep.smogon`으로 다시 받는다.
