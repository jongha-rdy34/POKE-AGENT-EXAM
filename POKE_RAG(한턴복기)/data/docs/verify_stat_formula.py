"""stat_damage_formulas.md의 §2 검증: Champions 공식 = 본가 Gen III+ 공식(Lv50, IV31, EV=8·SP-4)과 같은가.
Gen III+ 공식: Bulbapedia 'Stat' 문서 §Formula / Champions 공식: 'Stat point' 문서 §Calculation."""
from math import floor

def gen3_hp(b, iv, ev, lv): return (2 * b + iv + ev // 4) * lv // 100 + lv + 10
def gen3_other(b, iv, ev, lv, nat_pct): return ((2 * b + iv + ev // 4) * lv // 100 + 5) * nat_pct // 100
def champ_hp(b, sp): return b + sp + 75
def champ_other(b, sp, nat_pct): return (b + sp + 20) * nat_pct // 100  # 1.1/1.0/0.9를 정수 %로 계산해 부동소수 오차 회피

def ev_of(sp): return 0 if sp == 0 else 8 * sp - 4  # Stat point 문서: 첫 포인트 4 EV, 이후 포인트당 8 EV

for b in range(1, 256):
    for sp in range(33):
        assert champ_hp(b, sp) == gen3_hp(b, 31, ev_of(sp), 50), (b, sp)
        for pct in (90, 100, 110):
            assert champ_other(b, sp, pct) == gen3_other(b, 31, ev_of(sp), 50, pct), (b, sp, pct)

# 예시: 한카리아스(종족값 H108 A130 B95 C80 D85 S102), 종족값은 PokeAPI data/raw/pokeapi/pokemon/garchomp.json
a_neutral = champ_other(130, 32, 100); a_adamant = champ_other(130, 32, 110)
assert (a_neutral, a_adamant) == (182, 200)
assert champ_hp(108, 2) == 185 and champ_other(95, 32, 100) == 147
print("OK: 공식 일치 (b=1..255, sp=0..32, 성격 3종), 예시 A", a_neutral, a_adamant)
