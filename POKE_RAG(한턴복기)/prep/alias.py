"""별칭 사전 1차본 → alias 테이블. build_db가 마지막에 호출한다. (agent.md 5.1절·6절)
  종류: pokemon / move / ability / item / nature = 이름(ko·ja·en) 및 줄임말 → 키,  spread = "AS" 같은 SP 배분 표기 → "atk:32,spe:32"
  .venv/Scripts/python -m prep.alias   # 단독 재생성
"""
import re
import sqlite3
from collections import defaultdict
from itertools import permutations

from config import DB_PATH

STAT = {"H": "hp", "A": "atk", "B": "def", "C": "spa", "D": "spd", "S": "spe"}


def build(db):
    rows = set()

    def add(alias, kind, target, note):
        if alias and alias.strip():
            rows.add((alias.strip(), kind, target, note))

    # 이름 별칭: 챔피언스 포켓몬은 기본 폼 이름이 종 이름을 대표하고, 폼 이름은 그 폼을 가리킨다
    for kind, table, key, where in (("pokemon", "pokemon", "form_key", "WHERE in_champions=1"), ("move", "move", "move_key", ""),
                                    ("ability", "ability", "key", ""), ("item", "item", "key", ""), ("nature", "nature", "key", "")):
        for k, *names in db.execute(f"SELECT {key}, name_ko, name_ja, name_en FROM {table} {where}"):
            for n in names:
                add(n, kind, k, "name")
            add(k, kind, k, "key")
    # 한 종 이름("한카리아스")은 폼 이름과 겹치면 기본 폼으로 되돌린다
    for sp, k in db.execute("SELECT species, form_key FROM pokemon WHERE is_default=1 AND in_champions=1"):
        for lang in ("name_ko", "name_ja", "name_en"):
            (n,) = db.execute(f"SELECT {lang} FROM pokemon WHERE form_key=?", (k,)).fetchone()
            rows.difference_update({r for r in rows if r[0] == n and r[1] == "pokemon" and r[2] != k and r[3] == "name" and "(" not in r[0]})
            add(n, "pokemon", k, "name")

    # 한글 폼 이름이 "킬가르도 (실드폼)"·"로토무의 모습"·"갑주무사 (Mega Golisopod)" 꼴이라 사람이 쓰는 이름이 없다(eng #3 R2 추출)
    taken = {r[0] for r in rows if r[1] == "pokemon"}
    for k, name, is_default, is_mega in db.execute("SELECT form_key, name_ko, is_default, is_mega FROM pokemon WHERE in_champions=1"):
        base = re.sub(r"의 모습$", "", re.sub(r"\s*\(.*\)$", "", name or ""))
        if not base or base == name:
            continue
        if is_mega and "(" in name:
            suffix = re.search(r" ([XYZ])\)$", name)  # "한카리아스 (Mega Garchomp Z)" → 메가한카리아스Z (server.app.display_name과 같은 표기)
            add("메가" + base + (suffix.group(1) if suffix else ""), "pokemon", k, "메가 + 종 이름")
        elif is_default and base not in taken:
            add(base, "pokemon", k, "폼 표기를 뗀 기본 폼 이름")

    # 줄임말: 종 한글 이름 앞 두 글자(한카·갸라 등). 다른 종과 겹치거나 이미 있는 이름이면 만들지 않는다
    prefix = defaultdict(set)
    for sp, name in db.execute("SELECT species, name_ko FROM pokemon WHERE is_default=1 AND in_champions=1"):
        if name and len(name) > 2:
            prefix[name[:2]].add(sp)
    taken = {r[0] for r in rows}
    for p, sps in prefix.items():
        if len(sps) == 1 and p not in taken:
            (k,) = db.execute("SELECT form_key FROM pokemon WHERE species=? AND is_default=1", (next(iter(sps)),)).fetchone()
            add(p, "pokemon", k, "auto-prefix(한글 앞 두 글자)")

    # SP 배분 표기: 두 능력에 최대치 32씩, 남는 2는 H에 둔다("CS" = H2 C32 S32, 스마트누오 등 계산기 관례·사용자 지시 2026-10-23).
    # H가 들어간 배분("HA")은 남는 2를 어디 둘지 관례가 없어 비워 둔다
    for a, b in permutations(STAT, 2):
        rest, note = ("", "두 능력 32씩, 나머지 2는 미지정") if "H" in (a, b) else (",hp:2", "두 능력 32씩, 나머지 2는 H")
        add(a + b, "spread", f"{STAT[a]}:32,{STAT[b]}:32{rest}", note)

    db.execute("DELETE FROM alias")
    db.executemany("INSERT OR IGNORE INTO alias VALUES(?,?,?,?)", sorted(rows))
    db.commit()
    return db.execute("SELECT kind, COUNT(*) FROM alias GROUP BY kind").fetchall()


if __name__ == "__main__":
    print(build(sqlite3.connect(DB_PATH)))
