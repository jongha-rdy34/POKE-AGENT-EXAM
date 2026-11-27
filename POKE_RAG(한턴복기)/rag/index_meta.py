"""pokedex.sqlite → Chroma `pokemon_meta` 색인 (F2001·F2002). 청크 ID = form_key라 다시 실행해도 덮어쓰기만 일어난다.
  .venv/Scripts/python -m rag.index_meta
"""
import json
import sqlite3

from config import DATA_DIR, DB_PATH
from prep.review import current_season
from rag.store import collection

BATCH = 50
RULE_KO = {"single": "싱글", "double": "더블"}


TYPE_KO = {(d := json.loads(p.read_text(encoding="utf-8")))["name"]: d["names"].get("ko", d["name"])
           for p in (DATA_DIR / "raw" / "pokeapi" / "type").glob("*.json")}


def ko(db, table, key, fallback=None):
    row = db.execute(f"SELECT name_ko FROM {table} WHERE {'move_key' if table == 'move' else 'key'}=?", (key,)).fetchone()
    return (row[0] if row and row[0] else None) or fallback or key


def usage_text(db, form_key):
    """가장 최근 시즌의 룰별 채용률·도구. (텍스트, 최근 싱글 채용률)"""
    lines, single = [], 0.0
    season = current_season(db)
    for rule, teams, total, rate, items in db.execute(
            "SELECT rule, teams, total_teams, usage_rate, top_items FROM meta_usage WHERE form_key=? AND season=? ORDER BY rule DESC",
            (form_key, season)):
        top = ", ".join(f"{ko(db, 'item', k)}({n})" for k, n in json.loads(items)[:3])
        lines.append(f"{season} {RULE_KO[rule]} 상위 구축 {total}팀 중 {teams}팀({rate:.1%}) 채용, 주요 도구: {top}")
        single = rate if rule == "single" else single
    return "\n".join(lines) or f"{season} 상위 구축 데이터에 등장하지 않음", single


def build_docs(db):
    ids, texts, metas = [], [], []
    for r in db.execute("SELECT form_key, dex_no, name_ko, name_ja, name_en, type1, type2, hp, atk, def, spa, spd, spe, ability1, ability2, "
                        "hidden_ability, is_mega, genus_ko, flavor_ko FROM pokemon WHERE in_champions=1 ORDER BY dex_no, form_key"):
        k, dex, nko, nja, nen, t1, t2, hp, atk, df, spa, spd, spe, a1, a2, hid, mega, genus, flavor = r
        abil = ", ".join(ko(db, "ability", a) for a in (a1, a2) if a)
        moves = ", ".join(x[0] or x[1] for x in db.execute(
            "SELECT m.name_ko, m.move_key FROM learnset l JOIN move m USING(move_key) WHERE l.form_key=? AND m.power IS NOT NULL "
            "ORDER BY m.power DESC, m.move_key LIMIT 15", (k,))) or "확인된 습득기 없음"
        usage, rate = usage_text(db, k)
        text = (f"{nko} · {nja} · {nen} · 도감번호 {dex:04d} (form_key {k})\n타입: {TYPE_KO[t1]}{'/' + TYPE_KO[t2] if t2 else ''} ({t1}{'/' + t2 if t2 else ''})\n"
                f"종족값 H{hp} A{atk} B{df} C{spa} D{spd} S{spe} (합계 {hp + atk + df + spa + spd + spe})\n"
                f"특성: {abil}" + (f" / 숨겨진 특성: {ko(db, 'ability', hid)}" if hid else "") + f"\n분류: {genus or '-'}\n"
                f"도감 설명: {flavor or '-'}\n주요 습득기(위력순): {moves}\n{usage}")
        ids.append(k)
        texts.append(text)
        metas.append({"dex_no": dex, "form_key": k, "name_ko": nko or "", "type1": t1, "type2": t2 or "", "hp": hp, "atk": atk, "def": df,
                      "spa": spa, "spd": spd, "spe": spe, "is_mega": mega, "usage_rate": rate})
    return ids, texts, metas


def main():
    db = sqlite3.connect(DB_PATH)
    ids, texts, metas = build_docs(db)
    col = collection("pokemon_meta")
    for i in range(0, len(ids), BATCH):
        col.add_texts(texts[i:i + BATCH], metadatas=metas[i:i + BATCH], ids=ids[i:i + BATCH])  # 같은 ID면 덮어쓴다(upsert)
    print(f"색인 {len(ids)}건 시도 → 컬렉션 건수 {col._collection.count()}")


if __name__ == "__main__":
    main()
