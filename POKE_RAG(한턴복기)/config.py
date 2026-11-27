"""프로젝트 설정 1곳. 모든 모듈은 .env를 직접 읽지 말고 여기서 import한다. (F2005·F2006·F2014, NF2003)"""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent
ENV_PATH = ROOT / ".env"  # collect.py 등 어디서 실행해도 같은 파일을 읽는다
load_dotenv(ENV_PATH)

# 비밀·환경 값 (.env)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL") or None  # SSAFY GMS 사용 시 base_url만 바꾼다
CONTACT = os.getenv("CONTACT", "")  # 출처가 User-Agent 연락처를 요구할 때만 사용
USER_AGENT = "ssafy-edu-rag/0.1" + (f" ({CONTACT})" if CONTACT else "")

# 모델 (GMS에서 제공하는 이름에 맞춰 .env로 덮어쓴다)
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini")
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")

# 청킹 (F2005)
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# 검색 (F2006·F2014)
TOP_K = 6
SEARCH_TYPE = "similarity"  # "similarity" | "mmr"
MMR_FETCH_K = 20
MMR_LAMBDA = 0.5

# 현재 시즌. 비우면 meta_usage의 최신 시즌을 쓴다(prep.review.current_season). 시연 중 고정할 때만 "M-6"처럼 넣는다
CURRENT_SEASON = os.getenv("CURRENT_SEASON") or None

# Smogon 월간 통계(성격·SP·특성 보충, agent.md 1.3절 4). 새 달이 공개되면 MONTH만 바꾸고 python -m prep.smogon → build_db
SMOGON_MONTH = "2026-09"
SMOGON_FORMAT = "gen9championsbssregmc"  # Champions 싱글, 레귤레이션 M-C
SMOGON_CUTOFF = 1500

# 한 턴 복기 (docs/designs/loss-review-coach.md). 평가셋(CEO-T4)으로 조정한다
REVIEW_MIN_SPREAD = 0.2       # D25: 도구 그룹 일치 비율 차이가 이보다 작으면 "도구로 구분 불가"
DIFF_REVIEW_PROB = 0.2        # D31: pokedb·Smogon 기준 1순위 원인의 확률 차이가 이 이상이면 두 결과를 함께 표시
REVIEW_INTIMIDATE_PRIOR = 0.2  # D19: "공격 −1(위협 등)" 후보의 사전 비중. 실제 위협 빈도 데이터가 없어 정한 값
SMOGON_TOP_SPREADS = 20       # Smogon 기준 상대 배분 후보 수(가중치 큰 순)

# 초대 토큰과 사용 한도 (CEO C3-1, eng #3 R3). .env INVITE_TOKENS=이름표:비밀값,이름표:비밀값 — 기록에는 이름표만 남는다
INVITE_TOKENS = {secret.strip(): label.strip() for label, secret in  # 비밀값 → 이름표
                 (p.split(":", 1) for p in os.getenv("INVITE_TOKENS", "").split(",") if ":" in p) if secret.strip()}
DAILY_REVIEWS_PER_TOKEN = 50   # 토큰당 하루 복기(POST /api/feature/review) 횟수, 한국 시간 자정에 초기화
DAILY_EXTRACTS_PER_TOKEN = 100  # 토큰당 하루 문장 읽기 횟수(다시 쓰기 여유를 둔다)
DAILY_LLM_CALLS = 400          # 서버 전체 하루 LLM 호출 상한. GMS에는 결제 한도 설정이 없어 코드가 막는다
# 복기 요약(summary)을 LLM이 다듬을지. 화면은 결론(headline, 코드)과 계산표만 보여 summary를 쓰지 않아 기본 끔(디자인 W1, 2026-10-23).
# 켜면 복기마다 GMS를 한 번 더 부르고 서버 전체 하루 LLM 상한에 들어간다
REVIEW_SUMMARY_LLM = os.getenv("REVIEW_SUMMARY_LLM", "") == "1"
EXTRACTION_TTL = 30 * 60       # 추출 결과 보관 시간(초): 확인 화면에서 고쳤는지 비교용(R8)

# 외부 요청 간격(초) (NF2006). Bulbapedia는 robots.txt Crawl-delay: 5
REQUEST_INTERVAL = 0.15
BULBAPEDIA_INTERVAL = 5

# 저장 경로
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "processed" / "pokedex.sqlite"  # 구조화 저장소. 모든 모듈은 이 값만 쓴다
CHROMA_DIR = ROOT / "chroma_db"
REVIEW_LOG = DATA_DIR / "logs" / "reviews.jsonl"  # CEO C8-1. .gitignore 대상(개인 문장 포함)
