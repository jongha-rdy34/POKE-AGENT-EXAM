# OpenAI 판정: ChatGPT 데스크톱 앱 수동 실행 절차

API 판정(Gemini, Claude 하위 에이전트)과 **같은 프롬프트, 같은 패킷**을 쓴다. 다른 점은 아래 "API와 다른 조건"에 적고 보고서 한계에 그대로 옮긴다.

## 0. 준비 (한 번)
1. 설정 → 개인 맞춤 설정: **메모리 끄기**, **맞춤형 지침 비우기**(또는 끄기). 이전 대화 참조 기능도 끈다.
2. 모델 선택 메뉴에서 쓸 모델을 하나 정하고 12건 내내 바꾸지 않는다. 화면에 보이는 모델 이름을 그대로 적는다(예: `GPT-5.x Thinking`).
3. 패킷 파일은 `judge-eval/packets/chatgpt/`에 생긴다(Phase 4 뒤). 실행마다 업로드할 파일 목록이 `runs.csv`에 있다.

## 1. 실행 12건
| run_id | mode | 업로드 | 프롬프트 파일 |
|---|---|---|---|
| abs_X_r1~r3 | 절대 평가 X | X 패킷 | `packets/chatgpt/abs_X_r{n}.txt` |
| abs_Y_r1~r3 | 절대 평가 Y | Y 패킷 | `packets/chatgpt/abs_Y_r{n}.txt` |
| pw_XY_r1~r3 | 쌍비교 X→Y | X, Y 패킷 | `packets/chatgpt/pw_XY_r{n}.txt` |
| pw_YX_r1~r3 | 쌍비교 Y→X | Y, X 패킷 | `packets/chatgpt/pw_YX_r{n}.txt` |

`.txt` 프롬프트 파일에는 시스템 규칙 + 루브릭 + 패킷 텍스트가 이미 한 덩어리로 들어 있다. 이미지(캡처 묶음 PNG)만 따로 올린다.

## 2. 건마다
1. **새 임시 채팅**(Temporary Chat)을 연다. 이전 대화를 이어 쓰지 않는다.
2. 해당 이미지 파일을 첨부하고, 프롬프트 `.txt` 내용을 전부 붙여 넣어 보낸다.
3. 응답 JSON을 그대로 복사해 `judges/raw/chatgpt/{run_id}.json`으로 저장한다. 고치지 않는다.
4. 응답이 JSON이 아니거나 형식이 틀리면 같은 채팅에서 아래 문장을 보낸다(최대 2회). 그래도 틀리면 받은 그대로 저장한다(실패로 집계).
   > 출력 형식을 어겼습니다. 지정한 JSON 하나만, 다른 글자 없이 다시 출력하세요.
5. `judges/raw/chatgpt/log.csv`에 한 줄 추가: `run_id,날짜시각,화면의 모델 이름,재요청 횟수`

## 3. 가져오기
```bash
python judges/import_manual.py judges/raw/chatgpt
```
스키마를 검사하고 `judges/raw/chatgpt.jsonl`로 합친다. 형식 위반은 `"status":"schema_fail"`로 남는다.

## API와 다른 조건 (보고서 한계에 기록)
- temperature를 정할 수 없다(앱 기본값). Claude 하위 에이전트도 같다. Gemini만 0.2로 고정된다.
- 모델 ID는 API ID가 아니라 화면 이름이다. 앱이 내부적으로 쓰는 버전은 알 수 없다.
- 앱의 시스템 프롬프트가 붙는다. 메모리와 맞춤형 지침을 껐어도 완전히 같은 조건은 아니다.
- 사람이 복사·붙여넣기를 하므로 순서·파일을 잘못 고를 수 있다. `log.csv`와 run_id로 점검한다.
