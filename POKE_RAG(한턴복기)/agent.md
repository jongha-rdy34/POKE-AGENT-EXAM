# 포켓몬 챔피언스 RAG 에이전트 — 작업 계획

> SSAFY AI 코어 프로젝트 2회차 "RAG 기반 도메인 지식 서비스" 계획 문서.
> 상태: **구현 초기 (선수집 진행 중)** · 최종 갱신: 2026-10-21
>
> **이 문서를 읽는 에이전트에게**
> 1. 먼저 1.1 **기술 스택 제한**과 1.2 **UI 결정(HTML/CSS/JS로 처음부터)**을 읽는다. 이 두 절은 모든 작업에 우선한다.
> 2. 작업은 9절 **체크리스트**를 위에서부터 진행한다. 끝낸 항목은 `- [x]`로 바꾸고, 산출물 경로와 완료 날짜를 같은 줄 끝에 적는다.
> 3. 각 작업이 어떤 명세 요구사항을 충족하는지는 8절 표를 본다. 필수 요구사항(F2001–F2012)은 수정·생략할 수 없다.
> 4. **데이터 충돌이 나면 1.3 데이터 우선순위(PokeAPI > pokedb)를 따른다.** 챔피언스 등장 여부로 계산·조회를 막지 않는다.

---

## 1. 목표

자연어 질의를 받아 **포켓몬 챔피언스(Pokémon Champions)** 랭크배틀 관점의 답을 근거와 함께 제시한다.

- 수치 질의: "AS 한카리아스의 지진 결정력 알려줘" → 실수치·결정력 계산 + 공식 문서 인용
- 메타 질의: "이번 시즌 한카리아스는 주로 뭘 들고 누구랑 같이 나와?" → pokedb 시즌 데이터 인용
- 지식 질의: "까칠한피부는 어떤 특성이야?" → 위키 문서 인용
- 예상 밖 질의도 들어온다는 전제로, **데이터는 넓게 미리 확보하고 계산은 코드가 한다.**

도메인 위험도: 게임 도메인이므로 면책 안내 불필요(F2012의 진행 상태·오류 안내는 구현).

### 1.1 기술 스택 제한 (명세 1.2절 4)·5) — 반드시 지킬 것)

> **지침 변경 (2026-10-22, 사용자 지시): 이 절의 제약은 해제됐다.**
> - 라이브러리 **버전 고정**, 명세 목록 외 라이브러리 금지, **Streamlit** 등 명세의 기술 스택 제약을 더는 따르지 않아도 된다. 시스템은 자유롭게 빌드할 수 있다.
> - 지금은 **기록만** 해 둔 상태다. 이 절의 표·`requirements.txt`와 1.2절 이하 내용은 아직 고치지 않았다. 스택을 실제로 바꿀 때 해당 절을 함께 수정하고 이 안내를 갱신한다.
> - 명세의 **기능·비기능 요구사항(8절)은 그대로 유효**하다. 해제된 것은 기술 스택 제약뿐이다.

명세가 개발 언어·도구와 라이브러리 **버전까지 고정**했다. 아래 목록에 없는 라이브러리는 추가하지 않는다. 표준 라이브러리(`json`, `sqlite3`, `urllib`, `re` 등)는 자유롭게 쓴다. 꼭 필요한 외부 패키지가 생기면 추가하기 전에 사용자에게 확인받는다.

| 구분 | 허용 범위 |
|---|---|
| 언어 | Python 3.10+ |
| UI | HTML5 / CSS3 / JavaScript (프레임워크·빌드 도구 없이 순수 HTML/CSS/JS) — 1.2절 참고 |
| 서버 | FastAPI + Uvicorn + Pydantic (명세의 "심화 선택 시" 목록) |
| Vector DB | ChromaDB (`langchain-chroma` 경유) |
| RAG 파이프라인 | LangChain / LangGraph (retrieve·generate 두 노드) |
| LLM·임베딩 | OpenAI API (`langchain-openai`, SSAFY GMS 사용 시 `base_url`만 변경) |
| 도구 | VS Code / Git |
| 참고(설치 목록 외) | PDF 출처를 쓰게 되면 `pypdf`가 명세 참고자료에 있어 사용해도 된다. |

**`requirements.txt` (명세 버전 그대로, 프로젝트 루트에 이 내용으로 만든다)**

```text
# 필수 (명세 1.2절 5)
langchain==1.3.14
langgraph==1.2.10
langsmith==0.10.17
langchain-core==1.6.0
langchain-openai==1.4.3
langchain-community==0.4.2
langchain-chroma==1.1.0
langchain-text-splitters==1.1.2
chromadb==1.5.9
openai==2.54.0
streamlit==1.62.0
requests==2.34.2
python-dotenv==1.2.3
typing-extensions==4.16.0

# 심화 (명세상 "심화 선택 시" — 이 프로젝트는 1.2절 결정에 따라 처음부터 사용)
fastapi==0.141.1
uvicorn[standard]==0.52.4
pydantic==2.13.5
```

`streamlit`은 명세 필수 목록이라 그대로 둔다. 다만 사용자 화면은 1.2절에 따라 HTML/CSS/JS로 만들고, Streamlit은 쓰지 않는다(필요하면 개발용 디버그 화면에만 사용).

### 1.2 UI 결정: 첫 작업부터 HTML/CSS/JS + FastAPI로 구성한다

**배경.** 명세에서 "HTML·CSS·JavaScript로 화면 직접 구현(F2013)"은 **심화** 요구사항이고, 필수 화면(F2009 항목 선택·대화, F2011 조건 탐색, F2012 진행 상태·오류 안내)은 Streamlit 예시로 설명돼 있다.

**결정.** F2013은 심화지만, 나중에 Streamlit 화면을 HTML/CSS/JS로 갈아엎으면 화면·서버 구조를 처음부터 다시 짜야 한다. 그래서 **처음부터 HTML/CSS/JS 화면 + FastAPI 서버로 구상하고, 필수 화면 요구사항(F2009·F2011·F2012)도 이 화면에서 구현한다.** Streamlit 단계는 거치지 않는다.

**다른 에이전트가 지켜야 할 것**

- 화면 코드는 `web/`(정적 파일), 서버는 `server/`(FastAPI)에 두고 **화면과 서버를 분리**한다(F2013).
- 화면은 서버의 JSON API만 호출한다. RAG·계산 로직을 화면 JS에 넣지 않는다.
- API 키, 프롬프트 전문, 오류 추적(traceback)은 응답에 넣지 않는다(NF2004). 오류는 코드와 사용자용 안내 문구만 보낸다.
- 화면 디자인 작업 시 `.agents/skills/design-taste-frontend` 스킬을 참고할 수 있다(외부 프레임워크는 쓰지 않는다).

**요청·응답 형식 초안 (F2013 "요청·응답 형식 정의")**

| 메서드·경로 | 요청 | 응답 | 관련 요구사항 |
|---|---|---|---|
| `GET /api/status` | — | `{meta_count, docs_count, api_key_ok, index_ok}` | F2002 색인 건수 표시, F2012 색인 없음·키 누락 안내 |
| `GET /api/pokemon?q=` | 검색어(선택) | `[{form_key, dex_no, name_ko, name_ja, types}]` | F2009 항목 선택 |
| `POST /api/chat` | `{form_key, session_id, message, review_id?}` (`review_id`: 복기 결과 아래 채팅이면 그 턴을 맥락으로, 디자인 DR15) | SSE 스트림: `status` 이벤트(`collecting` / `retrieving` / `generating`, 수집된 문서 제목) → 마지막 `answer` 이벤트 `{answer, citations:[{n, title, url, source_type}], no_citation}` | F2003–F2008, F2012 진행 상태 |
| `GET /api/history?form_key=&session_id=` | — | 해당 포켓몬의 대화 기록 | F2009 항목별 대화 분리 |
| `POST /api/search` | `{query}` | `[{form_key, name_ko, reason}]` (조건에 맞는 항목만) | F2011 조건 탐색 |
| `POST /api/feature/{name}` | `{form_key, ...}` | `{result, citations}` | F2010 특화 기능 |
| `POST /api/feature/review/extract` | `{text}` — 자연어 한 줄(CEO C0). LLM은 한글 이름·공격 측·결과만, 코드가 alias·learnset으로 검증, SP는 코드만(D22) | `{type: review\|rule\|fail, fields, missing, extraction_id}` | eng #3 R1·R2 |
| `POST /api/feature/review` | `{session_id, extraction_id?, ...확인된 구조화 칸}` — 확인 단계("이렇게 이해했어요") 뒤 호출 | SSE `status` → `answer` `{summary, causes(순위·대표 조건의 k/16, % 없음), unsupported, assumptions, sources(pokedb·Smogon), review_id, degraded?}`. 요약 숫자는 계산 결과와 대조(R7) | 설계 v1.3·CEO 리뷰·eng #3 |
| `POST /api/feature/review/{review_id}/feedback` · `POST /api/feature/review/delete` · `GET /api/quota` | 패인 질문 답 / 토큰 이름표 기준 삭제 / — | `{ok}` / `{deleted}` / `{remaining}` | eng #3 R1·R8 |
| `GET /api/moves?form_key=` / `?q=` | 공격 측 폼 | `[{move_key, name_ko, type, category, power}]`(물리·특수만) | 디자인 DR14 |
| (공통) 초대 토큰 | 첫 접속 `?t=` → HttpOnly 쿠키로 바꾸고 깨끗한 주소로 이동, `Referrer-Policy: no-referrer` | 없으면 403, 토큰당 하루 50회·서버 전체 하루 LLM 상한 초과 429 + 안내 | CEO C3-1·eng #3 R3 |

### 1.3 데이터 우선순위 (사용자 지시 — 모든 작업에 적용)

1. **PokeAPI > pokedb.** 값(종족값·타입·특성·기술·도구 효과·이름)은 PokeAPI가 정한다. 충돌하면 PokeAPI를 채택한다.
2. **pokedb는 PokeAPI의 부분집합으로 본다.** 챔피언스 랭크배틀에서 실제로 쓰인 사용 통계(채용률·도구·동반 포켓몬)만 담당하고, 값은 PokeAPI에서 가져온다. ID 매핑·검증도 PokeAPI 기준이다.
3. **포켓몬 챔피언스는 분기된 게임이므로 챔피언스를 기준으로 삼지 않는다.** 챔피언스에서 확인되지 않은 도구(구애머리띠·구애안경 등)·기술·포켓몬도 PokeAPI에 있으면 계산과 답변에서 취급한다. `in_champions`는 필터·안내용 표지일 뿐 계산·조회의 제한 조건이 아니다.
4. **사용 통계는 pokedb + Smogon (2026-10-22 사용자 결정).** **Smogon(지난달)은 사실상 최신 시즌 데이터로 간주한다.** 답변은 pokedb M-6 기준과 Smogon 기준으로 각각 계산하고, 차이가 유의미하면 양쪽을 함께 보여 주며 Smogon에는 "Pokémon Showdown(시뮬레이터) 환경에서 수집된 데이터"를 명시한다(설계 v1.3, D31·D32). 도구·채용률·동반 포켓몬은 **pokedb(실제 게임 상위 구축, 현재 M-6)**가 우선한다. pokedb에 없는 **성격·SP 배분·특성 분포**는 **Smogon 월간 통계 `gen9championsbssregmc`(Pokémon Showdown 래더, 레귤레이션 M-C, 레이팅 1500 이상)**로 채운다. 두 출처 모두 답변에 출처와 시점(시즌/월)을 표기한다. Smogon은 시뮬레이터 모집단이고 한 달 늦다는 점을 근거에 밝힌다. 값(종족값·위력 등)은 여전히 PokeAPI. championsbattledata는 이용 조건(개인·교육 한정)과 원천 미공개로 채택하지 않음.
4. **champions-data는 구버전(2026-04-16)이다.** 우선순위 밖의 참고 자료로, PokeAPI에 값이 없는 공백만 보충하고 출처를 `cd`로 표시한다. 차이는 `data/processed/crosscheck_report.md`에만 기록하고 코드는 PokeAPI 값을 쓴다.
5. Bulbapedia는 값이 아니라 **서술 근거 문서**와 공식 출처다. PokeAPI 값과 어긋나면 어긋남을 밝히고 PokeAPI 값을 쓴다.

---

## 2. 데이터 출처와 이용 조건 (NF2006 · NF2007)

| 출처 | 용도 | 이용 조건 (확인일 2026-10-21) | 판정 |
|---|---|---|---|
| **PokeAPI** (pokeapi.co) | 종족값·타입·특성·기술·성격·도구·다국어 이름, `champions` 도감(231종)·습득기술 | 무료, 로컬 캐시 요청(fair use) | ✅ 사용 — 일괄 수집 후 캐시 |
| **Smogon 월간 통계** (smogon.com/stats, `chaos/gen9championsbssregmc-1500.json`) | Champions 싱글(레귤레이션 M-C) Showdown 래더의 성격·SP 배분·특성·도구·기술·동반 분포 | 공식 약관 없음. pkmn/smogon README는 집계 통계를 퍼블릭 도메인으로 봄(제3자 해석), 공식 API 없음, 월 1회 공개 | ✅ 성격·SP·특성 보충 전용(1.3절 4), 월 1회 다운로드, 출처·월 표기. 수익화 전 Smogon에 이용 확인 |
| **챔피언스 도구 목록** (Bulbapedia "List of items by index number in Pokémon Champions"·"Shop (Champions)" + Showdown `data/mods/champions/items.ts`) | 게임에서 쓸 수 있는 지닌 도구 85종·메가스톤 81종 | Bulbapedia CC BY-NC-SA 2.5(5초 간격 API), Showdown MIT | ✅ `prep/champions_items.py`가 두 출처를 대조해 `champion_item` 표로 적재. 업데이트로 도구가 늘면 `download` 다시 실행 |
| **pokedb 오픈데이터** (champs.pokedb.tokyo/guide/opendata) | 시즌별 상위 팀 CSV/JSON (순위·레이트·포켓몬·폼·도구·테라) | 프로그램 다운로드 허용, 과부하 금지, 자체 서버에 사본 보관 권장. 페이지 크롤링은 약관 제3조(대량·연속 취득) 위반. 재배포 라이선스 명시 없음 | ✅ 오픈데이터 파일만 사용, 시즌당 1회 다운로드. 제출물엔 원본 대신 다운로드 스크립트 |
| **pokemon-champions-data** (github.com/otterlyclueless/pokemon-champions-data) | 챔피언스 전용 데이터(258종, 기술 900, 도구 583) + `mechanics/` 문서 | CC BY 4.0. 최종 갱신 2026-04-16(구버전) | △ **1.3절에 따라 PokeAPI 공백 보충 전용**(출처 `cd` 표시). 값 충돌 시 사용하지 않음. 색인하지 않음 |
| **Bulbapedia** (영문, `bulbapedia.bulbagarden.net/w/api.php`) | **외부 문서 주 출처**: 포켓몬별 문서(폼·메가·종족값·특성), 도구, 메커니즘(Stat point 공식) | CC BY-NC-SA 2.5. robots.txt가 `/wiki/` 허용, **`Crawl-delay: 5`**. API 정상 응답. 자동 접근 금지 조항은 찾지 못함(전용 정책 페이지 없음) | ✅ 사용 — 단일 스레드, 요청 간격 5초, 캐시 필수 |
| **포켓몬 위키** (pokemon.fandom.com/ko) | 한국어 포켓몬·기술·특성 문서, `/Champions 기술` 하위 문서 | 콘텐츠 CC-BY-SA. **Fandom 이용약관은 서면 허가 없는 로봇·스크래핑·자동 접근을 금지**(검색 결과로 확인, 약관 원문은 Cloudflare 차단으로 직접 열람 못 함). 웹페이지는 Cloudflare 봇 차단, `api.php`는 응답함 | ⚠️ 실시간 API 수집 불가. **XML 덤프**가 제공되면 F2004의 "제공된 문서 묶음" 경로로 사용 |
| 한국어 위키백과 | 일반 배경 문서 | CC BY-SA 4.0, User-Agent에 연락처 필수 | △ 보조 (개별 포켓몬 문서 부족) |
| OP.GG | — | 약관이 자동 스크립트 수집·스크래핑·데이터마이닝 금지 | ❌ 제외 |

포켓몬 IP: © Nintendo/Creatures/GAME FREAK — 교육 목적 비상업 사용임을 README에 명시.

### 2.1 포켓몬 위키(Fandom ko) 확인 결과

- MediaWiki 1.43, 문서 16,184개, 라이선스 CC-BY-SA.
- 내용: `한카리아스 (포켓몬)`은 2026-08 갱신, 정보상자에 한칭·일칭·영칭·전국도감번호(0445) 포함 → 도감번호 매핑 가능. `자속보정`, `성격`, `개체값`, `노력치`, `데미지` 문서 있음. `<포켓몬>/Champions 기술` 하위 문서 존재(챔피언스 PP 등 반영).
- 한계: 메커니즘 문서가 오래됨(`능력치` 2020, `데미지` 2017). **챔피언스 능력 포인트(SP) 체계와 결정력 문서는 없음.** `지진 (기술)`, `명랑` 같은 표제어는 없고 `지진`처럼 다른 제목을 씀.
- 결론: 내용은 한국어 위키백과보다 적합하나, **약관상 실시간 자동 수집은 불가**.
  - 1안: 위키의 `특수:통계`에서 XML 덤프 제공 여부를 브라우저로 확인 → 있으면 덤프를 로컬 코퍼스로 쓰고 F2004 수집 단계를 로컬 검색으로 대체(명세 F2004가 허용하는 방식).
  - 2안: 덤프가 없으면 Fandom 운영진에 서면 허가 요청, 그동안은 Bulbapedia + champions-data 문서로 진행.

---

## 3. 핵심 결정: 메타데이터를 미리 받을 것인가, 질의마다 받을 것인가

### 결정: **챔피언스 범위는 전량 선수집, 범위 밖은 요청 시 수집 후 캐시 (하이브리드)**

"번호·이름 매핑만 미리 두고 나머지는 질의 때 요청"하는 방식은 채택하지 않는다.

| 근거 | 설명 |
|---|---|
| F2011 조건 탐색이 불가능해짐 | "스피드 100 이상 땅 타입" 같은 조건은 전체 포켓몬의 속성이 이미 색인돼 있어야 검색된다. |
| F2001·F2002 요구 | 항목 1건을 "하나의 색인 텍스트"로 구성해 임베딩해야 하므로 속성이 먼저 있어야 한다. |
| 응답 시간 (NF2001) | 결정력 질의 하나에 pokemon·move·nature·item·ability 호출이 3~5회 필요. 매번 외부 호출하면 느리고 실패 지점이 늘어난다. |
| 외부 API 예절 (NF2002·NF2006) | PokeAPI는 캐시를 요청하고, pokedb는 자체 사본 보관을 요구한다. |
| 규모가 작음 | 챔피언스 231종(폼 포함 약 260) + 기술 수백 개 + 도구·특성 수백 개. 0.15초 간격으로 수집해도 수 분 내 끝나는 1회성 작업. |
| 계산 정확도 | 숫자를 코드가 계산하려면 종족값·위력·성격 보정이 구조화된 값으로 손에 있어야 한다. |

범위 밖(챔피언스에 없는 포켓몬·기술)을 물으면 그때 PokeAPI에서 받아 같은 캐시에 저장(write-through)하고, 화면에 "챔피언스 미등장" 안내를 붙인다.

### 3.1 미리 받을 데이터 목록

| 데이터 | 출처 | 범위 | 갱신 주기 |
|---|---|---|---|
| 포켓몬 종·폼: 종족값, 타입, 특성/숨겨진 특성, 키·무게, 진화 계통, 분류, 도감 설명(ko) | PokeAPI `/pokemon`, `/pokemon-species`, `/pokemon-form` | `pokedex/champions` 231종 + 폼·메가 | 게임 업데이트 시 |
| 다국어 이름 (ko / ja → 없으면 ja-hrkt / en) | PokeAPI 각 리소스 `names`, `form_names` | 포켓몬·폼·기술·특성·도구·성격·타입 | 동일 |
| 챔피언스 습득 기술 | PokeAPI `moves[].version_group_details` 중 `champions` | 231종 | 동일 |
| 기술: 위력, 명중, PP, 타입, 분류(물리/특수), 대상, 우선도, 효과 | PokeAPI `/move` + champions-data `moves.json`(교차검증) | 챔피언스 습득 기술 합집합 | 동일 |
| 성격 25종 (+/− 스탯) | PokeAPI `/nature` | 전체 | 고정 |
| 타입 상성표 18×18 | PokeAPI `/type` (champions-data `type-chart`로 검증) | 전체 | 고정 |
| 특성·도구: 이름, 효과(배틀 보정 배율 포함) | PokeAPI `/ability`, `/item` + champions-data | 챔피언스 등장분 | 업데이트 시 |
| 메가스톤 → 메가 폼 매핑 | PokeAPI 메가 varieties + 도구 이름 | 챔피언스 메가 | 업데이트 시 |
| 시즌 메타: 채용률, 도구 분포, 동반 포켓몬, 테라 타입 | pokedb 오픈데이터 (싱글/더블 × 시즌) | M-1 ~ 현재 시즌 | 시즌마다 1회 |
| ID 매핑표 `pokedb_id ↔ dex_no ↔ pokeapi_name` | pokedb + PokeAPI | 오픈데이터 등장분 전부 | 시즌마다 검증 |
| 별칭 사전: "한카", "갸라도스=갸라", "AS", "HB" 등 | 수작업 + 생성 | 자주 쓰는 표기 | 수시 |
| 메커니즘 문서: SP 체계, 실수치 공식, 성격 보정, 자속, 결정력, 데미지 공식 | champions-data `mechanics/`, Bulbapedia, 위키(덤프) | 고정 목록 | 업데이트 시 |

### 3.2 질의 시점에 수집하는 것 (F2003~F2005 파이프라인)

- 위키 계열 서술형 문서(특성·기술 설명, 포켓몬 상세, 배경 지식)는 **질의 → 검색어 추출(프롬프트 1) → 후보 선별(프롬프트 2) → 본문 수집 → 청킹·색인** 순서로 가져오고, 수집한 검색어는 캐시해 재수집하지 않는다.
- 출처는 2절 판정에 따라 Bulbapedia / (덤프가 있으면) 포켓몬 위키 로컬 코퍼스 / 한국어 위키백과.

---

## 4. 식별자 규칙 (도감번호 중심)

pokedb ID 형식은 `"DDDD-FF"` (전국도감번호 4자리 + 폼 번호).

- **종 키 `dex_no`** = `int(DDDD)` = PokeAPI species id. (M-6 싱글 114종 전부 일치, 일본어 이름까지 동일)
- **폼 키 `form_key`** = PokeAPI pokemon 이름 (예: `ninetales-alola`, `floette-eternal`).
  - 기본 규칙: `species.varieties[FF]`
  - 예외는 보정표로 관리: `0670-05 → floette-eternal` (꽃 색 외형 폼이 번호를 차지해서 어긋남)
  - 검증: PokeAPI `pokemon-form.form_names`의 일본어 폼명과 pokedb `form` 대조, 불일치 시 로그 후 보정표에 추가
- **메가진화**는 pokedb ID로 구분되지 않음(`0006-00` + 도구 `リザードナイトＹ`) → 도구 기준으로 메가 폼 매핑.
- 모든 저장소(구조화 DB, `pokemon_meta`, `pokemon_docs`, 메타 통계)는 `dex_no` + `form_key`를 공통 키로 쓴다.

---

## 5. 저장 구조

### 5.1 구조화 저장소 (SQLite 또는 JSON, 계산·필터용)

`pokemon(dex_no, form_key, name_ko, name_ja, name_en, type1, type2, hp, atk, def, spa, spd, spe, abilities, hidden_ability, is_mega, ...)`
`move(move_key, name_ko, name_ja, type, category, power, accuracy, pp, priority, target, effect_ko)`
`learnset(form_key, move_key)` · `nature(key, name_ko, name_ja, plus, minus)` · `item(...)` · `ability(...)` · `type_chart(atk_type, def_type, mult)`
`id_map(pokedb_id, dex_no, form_key)` · `alias(alias, kind, target_key)`
`meta_usage(season, rule, form_key, usage_rate, top_items, top_teammates, top_tera)`

### 5.2 Vector DB (Chroma) 컬렉션 2개

- **`pokemon_meta`** — 항목 1건 = 청크 1개, 청크 ID = `form_key`(다시 색인해도 덮어쓰기만 일어남).
  색인 텍스트: `한국어명 · 일본어명 · 영문명 · 도감번호 · 타입 · 종족값(H/A/B/C/D/S) · 특성/숨겨진 특성 · 분류 · 도감 설명 · 주요 습득기 · 최근 시즌 채용률·주요 도구`
  메타데이터 필드: `dex_no, form_key, type1, type2, spe, atk, ..., is_mega, usage_rate` → F2011 `where` 필터에 사용.
- **`pokemon_docs`** — 외부 문서 청크, 청크 ID = `form_key:doc_id:seq`.
  메타데이터 필드: `title, url, doc_id, dex_no, form_key, related_name, query, collected_at, source_type`(fandom_ko / bulbapedia / wikipedia_ko / champions_data / pokedb).
  메커니즘 문서는 `form_key = "_global"`로 넣어 모든 질의에서 검색 대상이 되게 한다.

---

## 6. 질의 처리 흐름 (LangGraph)

명세는 **retrieve / generate 두 노드**를 요구하므로 계산은 retrieve 노드 안에서 처리한다.

```
[retrieve]
  1. 의도·개체 추출 (LLM, JSON 출력)
     예: {"intent":"decisive_power","pokemon":"한카리아스","move":"지진",
          "nature":["명랑","고집"],"item":null}
     - SP는 LLM이 뽑지 않는다. 원문을 코드(정규식 "A20 S32" + 별칭 사전 "AS")가 파싱하고 check_sp로 검증한다(docs/designs/loss-review-coach.md D22).
     - 별칭 사전으로 정규화 (한카→garchomp, AS→A32·S32)
     - 정보가 부족하면 기본값을 명시적으로 가정하고 답변에 표기
       (예: 성격 미지정 → 공격 보정 성격 2종 모두 계산)
  2. 구조화 조회: 종족값·타입·기술 위력·성격 보정·도구/특성 배율
  3. 계산기 실행 (코드): 실수치 = floor((종족값 + SP + 20) × 성격보정), HP는 종족값 + SP + 75
     결정력 = 실수치 × 위력 × 자속(1.5) × 도구·특성 보정
  4. 근거 수집: pokemon_meta(선택 항목 고정 포함) + pokemon_docs(메커니즘 공식, 의미 검색) + 메타 통계
     → 병합·중복 제거·번호 부여, 계산 결과도 "계산 근거" 블록으로 첨부
[generate]
  5. 답변 생성 (프롬프트 3): 근거 블록과 계산 결과만 사용, 주장마다 [근거 n], 없으면 "확인되지 않음"
  6. 본문에서 실제 인용된 근거만 화면에 표시 (F2008)
```

검증 예시 (한카리아스 A130, 지진 위력 100, 땅 자속):
- 명랑: 실수치 (130+32+20)×1.0 = 182 → 결정력 182×100×1.5 = **27,300**
- 고집: floor(182×1.1) = 200 → 결정력 200×100×1.5 = **30,000**

공식의 출처와 한계는 `data/docs/stat_damage_formulas.md`를 따른다.

### 프롬프트 3종

1. **검색어 추출**: 포켓몬 배틀 분석가 역할. 출력은 JSON 배열(항목명 항상 포함, 외부 문서가 영문이므로 영문 검색어).
2. **후보 선별**: 제목·요약만 보고 색인할 문서 ID를 JSON으로 반환.
3. **답변 생성**: 근거·계산 결과만 사용, 근거 번호 표기, 근거 없으면 확인되지 않는다고 답변. 답변은 한국어.

의도·개체 추출 프롬프트는 retrieve 노드의 전처리로 별도 관리한다(3종 프롬프트와 구분해 설계문서에 기술).

---

## 7. 서비스 기능 (화면은 모두 HTML/CSS/JS — 1.2절)

- **F2009** 포켓몬 선택 + 포켓몬별 대화 기록.
- **F2010 도메인 특화 기능**
  - 결정력·실수치 계산기: 자연어 → 계산 + 공식 근거
  - 시즌 메타 리포트: 선택 포켓몬의 채용률·도구·동반 포켓몬 (pokedb 근거)
  - (선택) 스피드 라인 비교: "AS 한카리아스보다 빠른 상위 포켓몬"
- **F2011 조건 탐색**: 자연어 → 구조 조건 추출 → `where` 필터 + 벡터 검색 → LLM 선별 → 카드 → 클릭 시 대화로 이동.
- **F2012**: 수집·생성 진행 상태, 색인 0건 / API 키 누락 / 검색 결과 없음 안내.

---

## 8. 요구사항 대응

"요구사항 내용"은 명세 2.7절 표의 문구 그대로다. 도메인에 맞게 표현만 바꿀 수 있고, 필수 항목은 수정할 수 없다.

### 8.1 기능 요구사항

| 요구사항 번호 | 요구사항 내용 (명세) | 프로젝트의 대응 |
|---|---|---|
| F2001 (필수) | 선택한 도메인의 항목 목록을 로드하고 항목 1건을 하나의 색인 텍스트로 구성한다. | 챔피언스 도감 231종(+폼·메가)을 PokeAPI에서 선수집하고, 5.2절 색인 텍스트(이름·타입·종족값·특성·도감 설명·채용률)로 구성 |
| F2002 (필수) | 항목 텍스트를 임베딩하여 Vector DB 컬렉션에 색인한다. | `pokemon_meta` 컬렉션, 청크 ID = `form_key`로 고정해 재색인 시 덮어쓰기만 발생. 색인 건수는 `GET /api/status`로 화면에 표시 |
| F2003 (필수) | 도메인 전문가 역할 프롬프트로 항목과 질문에서 외부 문서 검색어를 추출한다. | 프롬프트 1: 포켓몬 배틀 분석가 역할, JSON 배열 출력, 선택 포켓몬 문서명은 항상 포함, 영문 검색어 |
| F2004 (필수) | 외부 문서 출처에서 검색하고, 선별 프롬프트로 후보 중 색인할 문서를 선별하여 본문과 원문 출처를 수집한다. | Bulbapedia API 검색 → 프롬프트 2가 제목·요약만 보고 선별 → 본문·URL 수집. 선택 포켓몬 자체 문서는 선별과 무관하게 항상 수집. 검색어 캐시로 재수집 방지 |
| F2005 (필수) | 수집한 문서를 청킹하여 별도의 컬렉션에 색인한다. 청크 크기와 중복 길이는 설정으로 조정할 수 있어야 한다. | `pokemon_docs` 컬렉션, 청크 ID = `form_key:doc_id:seq`. 청크 크기·중복은 설정 파일(`config`)에서 조정 |
| F2006 (필수) | 두 컬렉션을 검색하여 병합하고 중복 청크를 제거한다. 검색할 근거 수(Top-k)는 설정으로 조정할 수 있어야 한다. | 선택 포켓몬 메타 청크는 항상 포함 + 문서 의미 검색(`form_key` 필터) + 메커니즘 문서(`_global`) + 메타 통계 병합, 청크 ID로 중복 제거. Top-k는 설정 파일 |
| F2007 (필수) | 답변 생성 프롬프트로, 검색된 문서만을 근거로 답하고, 근거가 없으면 확인되지 않는다고 답한다. | LangGraph retrieve·generate 두 노드(6절). 프롬프트 3이 근거·계산 결과만 사용. 근거마다 출처 유형(구조화 데이터/Bulbapedia/pokedb/계산) 표시 |
| F2008 (필수) | 답변에 사용한 근거 문서의 제목과 원문 출처를 표시한다. 답변에 인용된 근거가 없으면 그 사실을 안내한다. | 답변 본문의 `[근거 n]`을 파싱해 실제 인용된 근거만 `citations`로 반환, 화면에 제목·URL 표시. 인용 0건이면 `no_citation: true`로 안내 |
| F2009 (필수) | 항목을 선택하고 채팅으로 질문과 답변을 주고받는다. | HTML/CSS/JS 화면에서 포켓몬 선택(`GET /api/pokemon`) + 채팅(`POST /api/chat`), 대화 기록은 `form_key`별로 분리 |
| F2010 (필수) | 도메인 특성에 맞는 기능을 1개 이상 설계하고, 근거와 함께 제공한다. | 결정력·실수치 계산기, 시즌 메타 리포트(7절). 결과에 공식 문서·pokedb 근거 첨부 |
| F2011 (필수) | 사용자의 자연어 조건으로 항목을 검색하여 맞는 항목만 제시한다. | `POST /api/search`: 조건 추출 → Chroma `where` 필터 + 벡터 검색 → LLM 선별 → 카드 표시, 카드 클릭 시 해당 포켓몬 대화로 이동 |
| F2012 (필수) | 처리 중 상태와 오류 안내, 위험 도메인의 면책 안내를 표시한다. | SSE `status` 이벤트로 수집·검색·생성 단계와 수집된 문서 제목 표시. 색인 0건·API 키 누락·검색 결과 없음 안내. 게임 도메인이라 면책 안내는 해당 없음 |
| F2013 (심화) | HTML, CSS, JavaScript로 사용자 화면을 구현한다. | **처음부터 채택**(1.2절). `web/` 정적 화면 + `server/` FastAPI, 요청·응답 형식은 1.2절 표 |
| F2014 (심화) | 유사도 검색 대신 MMR을 적용하여 근거의 다양성을 확보한다. | 설정으로 `similarity` / `mmr` 전환(`fetch_k`, `k`). 같은 질문의 두 결과를 비교해 기록 |
| F2015 (심화) | RAG 사용 전후의 답변을 비교하여 차이를 정리한다. | "AS 한카리아스 지진 결정력" 등 수치·메타 질의 5개 이상을 RAG 없이/있이 답하게 하고 사실 정확성·근거 제시·모름 인정 기준으로 비교 문서 작성 |
| F2016 (심화) | 종류가 다른 문서 출처를 함께 색인하고 근거에 출처 종류를 구분한다. | Bulbapedia 문서 + champions-data 메커니즘 문서 + pokedb 통계를 함께 색인, `source_type`으로 구분 표시 |

### 8.2 비기능 요구사항

| 요구사항 번호 | 요구사항 내용 (명세) | 프로젝트의 대응 |
|---|---|---|
| NF2001 | 대표 질문에 대한 전체 처리 시간이 사용에 지장이 없어야 한다. | 구조화 데이터·포켓몬 문서 선수집으로 질의 시점 외부 호출 최소화. Bulbapedia 5초 제한 때문에 질의 시점 수집은 필요한 문서만 |
| NF2002 | 이미 수집 · 색인한 검색어는 다시 수집하지 않아야 한다. | 선수집 파일 캐시(`collect.py`는 기존 파일 건너뜀) + 검색어 수집 캐시 |
| NF2003 | API 키는 환경변수로 관리하고 소스코드에 포함하지 않아야 한다. | `.env` + `python-dotenv`, `.env`는 `.gitignore`에 추가, `.env.example`만 제출 |
| NF2004 | 화면에 API 키, 전체 프롬프트, 오류 추적 정보를 노출하지 않아야 한다. | 서버가 오류를 코드·안내 문구로만 변환해 응답, 프롬프트 전문은 응답에 포함하지 않음 |
| NF2005 | 수집, 색인, 검색, 생성, UI의 책임을 분리하고, 도메인에 묶인 부분은 데이터 준비 영역에 모아야 한다. | 모듈 분리: 수집 / 색인 / 검색 / 생성 / 서버 / 화면(`web/`). 포켓몬 전용 코드(PokeAPI·pokedb 파싱, 별칭, 계산기)는 데이터 준비 영역에 모음 |
| NF2006 | 재시도와 호출 간격 규칙을 지키고, 출처가 요구하는 식별 정보(예: 위키백과 User-Agent 연락처)를 포함해야 한다. | PokeAPI·pokedb 0.15초 이상, Bulbapedia 5초 간격, 지수 백오프 재시도, User-Agent에 프로젝트 식별 정보 |
| NF2007 | 수집한 데이터와 문서의 출처와 이용 조건을 기록하고 지켜야 한다. | README에 2절 출처·라이선스 표, pokedb 원본은 제출물에서 제외하고 다운로드 스크립트로 대체 |

---

## 9. 작업 순서 (체크리스트)

진행 규칙: 위에서부터 순서대로 진행한다. 완료하면 `- [x]`로 바꾸고 줄 끝에 `→ 산출물 경로 (완료 날짜)`를 적는다. 막히면 체크하지 말고 아래에 `- 막힘: 이유`를 한 줄 추가한다.

**폴더 구조** (2026-10-21 정리)

```
config.py            설정·.env 로더(모든 모듈이 여기서 import)
prep/                데이터 준비 코드: collect · idmap · crosscheck · build_db · alias · llm_check, id_overrides.json(보정표)
data/raw/            원본: pokeapi/ · pokedb/ · champions_data/(구버전, 보충 전용)
data/processed/      가공 결과: pokedex.sqlite · id_map.json · crosscheck.json · *_report.md
data/docs/           메커니즘 문서(출처 표시) + 검증 스크립트
```
실행은 프로젝트 루트에서 `.venv/Scripts/python -m prep.<모듈>`. 순서: collect → idmap → crosscheck → build_db.

### 0단계 — 환경

- [x] 1.1절 내용으로 `requirements.txt` 작성, 가상환경에 설치 (F2013 대비 FastAPI·Uvicorn·Pydantic 포함) → `requirements.txt`, `.venv/` (`pip check` 통과) (2026-10-21)
- [x] `.env`(`OPENAI_API_KEY`, `OPENAI_BASE_URL`), `.gitignore`(`.env`, `data/pokedb/`, Chroma 저장소), `git init` (NF2003) → `.env`(키는 비어 있음), `.env.example`, `.gitignore`, `.git/` (2026-10-21)
- [x] 설정 파일 1개에 청크 크기·중복·Top-k·검색 방식(similarity/mmr)·요청 간격 정의 (F2005·F2006·F2014) → `config.py` (`.env`를 `ROOT/.env`로 고정해 읽음. 모든 모듈은 여기서 import) (2026-10-21)
- [x] LLM 경로 결정(SSAFY GMS / 개인 키) 후 연결 확인 → SSAFY GMS, 채팅 `gpt-4o-mini`·임베딩 `text-embedding-3-small`(1536차원) 호출 성공, `llm_check.py` (2026-10-21)

### 1단계 — 데이터 선수집 (데이터 준비 영역)

- [x] `collect.py`로 PokeAPI 챔피언스 범위 + pokedb 전 시즌 수집 완료 → `data/pokeapi/`(종 1025·포켓몬/폼 400·기술 496·특성 216·도구 2222·성격 25·타입 18), `data/pokedb/`(M-1~M-6 싱글·더블 12개). 도구 목록 2223개 중 1개는 404로 저장되지 않음 (2026-10-21)
- [x] `id_map`(pokedb_id ↔ dex_no ↔ form_key) 생성, 전 시즌 검증, 보정표 작성 (4절) → `prep/idmap.py`, `prep/id_overrides.json`, `data/processed/id_map.json`(ID 205/205 통과, 메가스톤 74개), `data/processed/id_map_report.md`. pokedb 원본 입력 오류 의심 2건(ヘラクロス+ライチュウナイトＸ, ヒヤッキー+ゴルーグナイト)은 매핑 제외 (2026-10-21)
- [x] champions-data 내려받기, PokeAPI와 기술 위력·PP 교차검증 → 차이 목록 작성 → `data/raw/champions_data/`(커밋 고정), `prep/crosscheck.py`, `data/processed/crosscheck_report.md`. **우선순위: PokeAPI·pokedb 무조건 우선, champions-data는 구버전이라 공백 보충만(사용자 지시)**. 종족값 차이 0건, PP 395개 기술 차이(PokeAPI=본가 값 의심), 챔피언스 추가 포켓몬 20종은 두 출처 모두 습득기 없음 (2026-10-21)
- [x] 구조화 저장소(5.1절) 구축 → `prep/build_db.py`, `data/processed/pokedex.sqlite`(포켓몬/폼 400·기술 496·습득기 19,850·도구 2,222·특성 216·성격 25·타입상성 324·id_map 205·mega_map 77·meta_usage 1,240). PokeAPI·pokedb 기준, champions-data는 습득기가 빈 `floette`만 `source='cd'`로 보충 (2026-10-21)
- [x] 별칭 사전 1차본 ("한카", "AS", "HB" 등) → `prep/alias.py`(build_db가 호출), `pokedex.sqlite`의 `alias` 테이블(이름 ko/ja/en, 앞 두 글자 줄임말, SP 배분 30종 등 13,000여 건). 동일 종족값 폼의 이름 충돌 4건은 후보 여러 개로 남김 (2026-10-21)
- [x] 메커니즘 문서 작성·출처 검증 → `data/docs/stat_damage_formulas.md`, `data/docs/verify_stat_formula.py` (2026-10-21)

### 2단계 — 색인 (RAG 1·2)

- [x] 계산기 모듈 + 단위 테스트 (182 / 200 / 27,300 / 30,000 예시 포함) → `prep/calculator.py`, `tests/test_calculator.py`(14개 통과, `.venv/Scripts/python -m unittest discover -s tests -t .`). 도구 보정은 PokeAPI 효과 문구 기준으로 구애머리띠·구애안경·힘의머리띠·박식안경·생명의구슬·달인의띠·전용 도구·타입 강화 도구 39개를 지원(챔피언스 등장 여부 무관, 1.3절). 계산식 없는 도구·특성은 오류로 거절 (2026-10-22)
- [x] `pokemon_meta` 색인, 두 번 실행해도 건수 불변 확인 (F2001·F2002) → `rag/index_meta.py`, `rag/store.py`, `chroma_db/`(챔피언스 336폼, 재실행 후에도 336건) (2026-10-22)
- [x] 메커니즘 문서 → `pokemon_docs` 색인 (`form_key = "_global"`) → `rag/index_docs.py`, `rag/docs.py`(87청크, 요약 문서 + Bulbapedia 원문 3곳 관련 절, 재실행 후에도 87건) (2026-10-22)
- [x] 챔피언스 231종 Bulbapedia 문서 선수집·색인 (5초 간격, 약 20분) → `prep/bulbapedia.py`, `data/raw/bulbapedia/`(231종, 누락 0), `rag/index_bulbapedia.py`(2,276청크, `pokemon_docs` 전체 2,364건, 재실행 후에도 동일). 소개+Biology만 수집, 표·습득기는 PokeAPI 담당 (2026-10-22)

- [x] 한 턴 복기 계산 기반(설계 `docs/designs/loss-review-coach.md` T1·T2·T6) → `prep/build_db.py` 도구 전체 분포(D24), `prep/review.py` `current_season`(D13), `prep/calculator.py` `damage_rolls`·`speed`·`item_kind`(@smogon/calc 0.10.0 대조 9사례 일치), `tests/` 25개 통과. 복기 로직(T3·T8·T9)·서버·화면은 CEO 리뷰 후 (2026-10-22)
- [x] 복기 계산 핵심(T3·T8·T9 CEO 범위·T13) → `prep/review.py` `review`(두 기준·차이 판정·가정/미지원 표기), CLI `python -m prep.review '<json>'`, tests 38개 통과. 서버는 eng 재리뷰 #3(C1-1·C3-1·C8-1) 후 (2026-10-23)
- [x] eng 재리뷰 #3 과제 E1~E3 → SP 파서·계산 캐시(E1), `server/extract.py`·추출 정답셋 35건(E2, 사용자 확인 전), `server/access.py`·`server/logs.py`(E3). tests 64개. 남은 것 E4(FastAPI 라우트·SSE·요약 숫자 대조) (2026-10-23)
- [x] E4 복기 서버 → `server/app.py`·`server/summary.py`·`server/llm.py`, 실행 `.venv/Scripts/python -m uvicorn server.app:app --port 8000 --no-access-log`, `.env`에 `INVITE_TOKENS=이름표:비밀값`. tests 72개. 다음: 4단계 화면(`web/`, 시안 `docs/designs/prototype/review-tab.html`) (2026-10-23)

- [x] 평가셋 규칙 문서 선수집·색인·라벨 대조(설계 T10, D23) → `prep/bulbapedia_rules.py`, `rag/index_rules.py`(Bulbapedia 45문서 367청크, `pokemon_docs` 2,731건), `data/eval/community_cases_verification.json`(51건 중 verified 47) (2026-10-22)
- [x] Smogon 월간 통계 적재(1.3절 4, 성격·SP·특성 보충) → `prep/smogon.py`, `config.SMOGON_*`, `data/raw/smogon/2026-09_gen9championsbssregmc-1500.json`, `pokedex.sqlite`의 `smogon_usage`(323종, 대응 실패 0, 챔피언스 336폼 중 308폼), `tests/test_smogon.py`. 도구·특성·기술 키는 PokeAPI 키로 변환해 저장(T12, 도구·특성 대응 실패 0건, 기술 15종은 move 테이블 밖이라 `showdown:<id>`로 보존) (2026-10-22)
### 3단계 — 서버와 RAG 파이프라인

- [ ] FastAPI 골격 + `GET /api/status`, `GET /api/pokemon` (1.2절 표)
- [ ] 프롬프트 1·2 + 질의 시점 수집 파이프라인, 검색어 캐시 (F2003–F2005, NF2002)
- [ ] 검색 병합·중복 제거 (F2006)
- [ ] LangGraph retrieve·generate 두 노드, 프롬프트 3, 인용 파싱 (F2007·F2008)
- [ ] `POST /api/chat` SSE 스트림 + 대화 기록 (F2009·F2012)
- [ ] 오류 응답에서 키·프롬프트·traceback 제거 확인 (NF2004)

### 4단계 — 화면 (HTML/CSS/JS, 처음부터)

- [x] `web/index.html`·`app.js` 골격, 서버 정적 파일 제공 → 복기 탭(시안을 실제 API에 연결: 문장 읽기 → 확인(`ask`·`notes`) → SSE 복기 → 두 기준 표·피드백·삭제·남은 횟수, 403 초대 안내). CSS는 시안처럼 index.html 안에 둔다. 채팅·규칙 답변은 `/api/chat`이 없어 "준비 중". 브라우저 실사용 확인은 아직 (2026-10-23)
- [x] 계산 우선 개정 v1.4(친구 사례 1) → 철주먹 계산, `calc_table`(통계 밖 도구도 계산, 챔피언스 도구 우선), 메가 줄임말·성격 코드 읽기·별칭 H2, 요약 표기 검사, 화면 계산표. 스마트누오 기대값(6.3%·75.0%) 재현. tests 79개 (2026-10-23)
- [x] 챔피언스 도구 목록 → `prep/champions_items.py`·`champion_item` 표(Bulbapedia 색인+상점 = Showdown Reg M-C, 일반 도구 85종 일치). 계산표의 "챔피언스에 없는 도구" 판정을 실전 통계 등장 여부 대신 이 표로. tests 82개 (2026-10-23)
- [x] 디자인 확정안 web/ 이식 → 시안 마크업·CSS·화면 코드 그대로 + 실제 API(문장 읽기·SSE·쿠키 토큰·남은 횟수·피드백·삭제). jsdom으로 친구 사례 전체 흐름 확인. 남은 것: /design-review 시각 검수, learnset 빈 14개 폼 보충 결정 (2026-10-23)
- [x] 디자인 병렬 작업 반영 → `docs/designs/HANDOFF-design-parallel.md` "디자인 결과" 절을 읽고 `web/`으로 옮긴다
- [ ] 포켓몬 선택 + 포켓몬별 채팅, 색인 건수 표시 (F2009·F2002)
- [ ] 진행 상태(수집 문서 제목 포함), 색인 0건·키 누락·결과 없음 안내 (F2012)
- [ ] 근거 목록 표시(제목·원문 링크·출처 종류), 인용 0건 안내 (F2008·F2016)
- [ ] 조건 탐색 화면: 카드 → 클릭 시 해당 포켓몬 대화로 이동 (F2011)
- [ ] 특화 기능 화면: 결정력 계산기, 시즌 메타 리포트 (F2010)

### 5단계 — 심화와 검증

- [ ] MMR 전환과 유사도 검색 결과 비교 기록 (F2014)
- [ ] RAG 전후 비교 문서 — 대표 질문 5개 이상 (F2015)
- [ ] 명세 4장 검증 항목별 실행·캡처, 요구사항 대조표·테스트 결과표·셀프/상호 체크리스트
- [ ] 소스코드·제출물에 API 키 없음 확인 (NF2003)

### 6단계 — 제출

- [ ] README.md: 개요·실행 방법, 필수/심화 기능, 데이터 준비·색인 절차, 출처·이용 조건(2절), 심화 요약
- [ ] 요구사항 정의서, RAG 파이프라인 설계문서
- [ ] `AI코어프로젝트2_[주제명]_지역_반_성명.zip`으로 압축 (pokedb 원본 제외, 다운로드 스크립트 포함)

---

## 10. 미결 사항과 위험

- [ ] **포켓몬 위키 XML 덤프 제공 여부** — 브라우저로 `pokemon.fandom.com/ko/wiki/특수:통계` 확인 (봇 접근은 Cloudflare 차단)
- [ ] **Fandom 이용약관 원문** 직접 확인 (자동 접근 조항, API 사용 허용 여부)
- [x] Bulbapedia API 접근 확인 (2026-10-21): 메가한카리아스Z(종족값 108/130/85/141/85/151, 드래곤 단일, 특성 부유, 챔피언스 프런티어 숍 2,000VP), 오거폰(가면 4종 타입·특성, 오모테나시 특성, 종족값) 모두 최신 정보 확인. 한국어명은 각 문서의 "In other languages"에 있음
- [ ] Bulbapedia는 5초 간격 제한이 있어 질의 시점 수집이 느림 → 챔피언스 231종 문서는 선수집(약 20분), 질의 시점 수집은 메커니즘·도구·특성 문서 위주
- [ ] 영문 문서 대응: 프롬프트 1이 영문 검색어를 출력하도록 설계, 임베딩은 다국어 모델 사용, 답변은 한국어로 생성
- [ ] champions-data의 최신성 (2026-04 이후 Ver.1.1.0 / 1.2.0 밸런스 변경 반영 여부)
- [ ] PokeAPI 기술 데이터가 챔피언스 전용 변경(PP 등)을 반영하는지 — 위키 `/Champions 기술` 문서에서 PP가 본가와 다른 사례 확인됨
- [ ] pokedb 다른 시즌·더블 룰의 추가 폼 (우라오스, 오거폰 등) → 보정표 확장
- [x] LLM 경로: SSAFY GMS 사용 (토큰 제한이 있어 소형 모델 `gpt-4o-mini` 유지, 2026-10-21)
- [ ] **최신 시즌(M-7) 사용률 통계 출처 확보** (2026-10-22 사용자 요청, 설계 문서 `docs/designs/loss-review-coach.md`의 "현재 시즌" 전제)
  - 확인된 사실(2026-10-22): pokedb 오픈데이터 안내 페이지는 M-1~M-6만 나열, `opendata/s7_single_ranked_teams.json`은 404. `s6_single_ranked_teams.json`의 `last-modified`가 2026-10-22 02:00 GMT라 M-6 파일이 아직 갱신 중이거나 pokedb가 진행 중 시즌을 M-6으로 부를 가능성 → **pokedb의 시즌 번호와 게임 내 현재 시즌의 대응부터 확인**.
  - 게임 내 랭크배틀 통계는 존재하지만 공개 공식 API는 검색에서 찾지 못함. 게임 클라이언트 내부 API 역분석 호출은 이용약관 위험이 커서 하지 않는다(약관 원문 확인 전까지 금지).
  - 제3자 후보(이용 조건·라이선스·데이터 원천·갱신 주기 모두 미확인, NF2006·NF2007에 따라 확인 후 2절 표에 추가): championsbattledata.com API(`/api/battle/:format/:name`, 일별 스냅샷·CSV, https://championsbattledata.com/api_guide), github.com/Gheist23/pokemonbattledata(오픈소스, 시즌 아카이브), Smogon 월간 Champions 통계(약 1개월 지연).
  - 채택 시 1.3절 우선순위상 pokedb와 같은 자리(사용 통계 전용, 값은 PokeAPI)로 두고, `meta_usage`에 `source` 열을 추가해 출처를 구분한다.
  - **2026-10-22 조사 결과:**
    - 현재 시즌: **M-7, 2026-10-07 ~ 11-04 10:59(JST), 레귤레이션 M-C**(Pokémon HOME 공식 뉴스 news.pokemon-home.com/ja/page/845.html). pokedb 시즌 번호는 게임 시즌과 같다(사이트 화면에 "シーズンM-7 開催中").
    - pokedb: 사이트 화면에는 M-7 사용률이 나오지만 오픈데이터는 M-1~M-6만 공개(s7 = 404). 공개 시점(시즌 종료 후인지)은 안내 페이지에 없음. 화면 크롤링은 약관 위반이라 쓰지 않는다. → 시즌 종료(11-04) 후 s7 공개 여부 확인, 또는 운영자(@pokedb_tokyo)에게 문의.
    - championsbattledata.com / github.com/Gheist23/pokemonbattledata: **M-7 일별 스냅샷이 2026-10-22까지 있음**(`data/meta/M7/<날짜>/Singles.json`). 포켓몬별 기술·도구·성격(`stat_alignment`)·동반 포켓몬 비율(전체 래더 기준으로 보임, pokedb의 상위 구축과 모집단이 다름). README상 배틀 CSV에 SP 배분 열(hp_points…speed_points)도 있음. 이용 조건(license.html): "personal, educational, and competitive analysis use", 공유·사용 시 "credit Pokemon Champions Battle Data and link to https://championsbattledata.com/". 데이터 원천은 명시 없음. GitHub 라이선스 표기 NOASSERTION, 저장소에 유료 앱(Companion Pro) 결제 코드 포함. → 과제(교육) 용도는 조건상 가능, 광고 수익화는 조건 밖.
    - Smogon/Pokémon Showdown 월간 통계(smogon.com/stats): 시뮬레이터 래더 기준이라 게임 랭크배틀과 모집단이 다르고 월 1회(최신 2026-09, 10-01 공개). 포맷 `gen9championsbssregmc`(Champions 싱글, 레귤레이션 M-C = 현재 M-7과 같은 레귤레이션), 9월 69,462판(레이팅 0/1500/1630/1760 기준별). `chaos/*.json`에 특성·도구·기술·동반·**성격+SP 배분**(`"Adamant:1/32/0/0/1/32"`, SP 단위). 공식 약관 없음, pkmn/smogon README는 "aggregated stats information is freely available in the public domain"(제3자 해석), 공식 API 없음. 이용 범위 제한 조항은 찾지 못함(수익화 전 Smogon 확인 권장). Showdown 이름 → form_key 대응 필요.
  - **2026-10-22 사용자 결정:** M-7 데이터를 확보하기 전까지 답변 기준 시즌은 pokedb의 M-6이다. 설계 T7(색인 본문 시즌 통계 제거)은 M-7 확보 가능성을 파악한 뒤 다시 검토한다(T10 먼저).
- [ ] 결정력 계산에 넣을 보정 범위 — 도구는 PokeAPI 기준으로 지원 완료(`stat_damage_formulas.md` §3). **남은 것: 특성 보정(테크니션·천하장사 등), 날씨·랭크, 메트로놈 등 상태 의존 도구.** 값은 PokeAPI 특성 효과 문구와 Bulbapedia로 확인 필요
