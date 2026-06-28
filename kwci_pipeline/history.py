"""분기 시계열 엔진 — 2018Q1~현재, 기준연도 2018=100. (실데이터 역사 백필)

경제(L1) 백본 지수의 분기별 추이. 백필 가능한 소스는 실데이터로, 나머지는 추세 샘플로 채운다.
도메인별 데이터 출처를 sources에 표기(real vs sample)해 정직하게 구분한다.

실 백필:
  - KOSIS 콘텐츠산업 수출(orgId=113): 연간 2018~최신 → 분기 선형보간. 음악·방송·영화·게임·만화.
    (한 번 호출로 다년치 수신. KOSIS_API_KEY 필요.)
  - KTO 출입국관광통계(15000297): 월별 방한객 → 분기 합산. ktourism.
    (월별 루프 호출. DATA_GO_KR_API_KEY + 15000297 활용신청 필요.)
샘플 폴백:
  - 관세청(kfood·kfashion·kbeauty)은 월별×HS×국가 호출량이 커서 기본 샘플 추세. 실 백필은
    별도(HISTORY_BACKFILL_CUSTOMS) — 운영계정·대량호출 시 확장.
"""
from __future__ import annotations

import json
import math
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from kwci_pipeline import config, processor, collectors
else:
    from . import config, processor, collectors

GROWTH = {"kpop": 0.08, "kvideo": 0.12, "kgame": 0.06, "kwebtoon": 0.20,
          "kfood": 0.09, "kbeauty": 0.11, "kfashion": 0.04, "ktourism": 0.10}
TOURISM_COVID = {
    (2020, 1): 0.85, (2020, 2): 0.05, (2020, 3): 0.04, (2020, 4): 0.04,
    (2021, 1): 0.05, (2021, 2): 0.06, (2021, 3): 0.08, (2021, 4): 0.12,
    (2022, 1): 0.18, (2022, 2): 0.30, (2022, 3): 0.45, (2022, 4): 0.60,
    (2023, 1): 0.72, (2023, 2): 0.82, (2023, 3): 0.90, (2023, 4): 0.93,
    (2024, 1): 0.95, (2024, 2): 0.98, (2024, 3): 1.00, (2024, 4): 1.00,
}

# ── 실측 연간 지수(2018=100) ───────────────────────────────────
# 각 도메인 L1 경제지표(수출/매출)의 검증 통계 기반 연간 지수. 엔드포인트(2018·2024)는
# 공식 통계로 검증, 중간연도는 실측/근사. 출처: 콘텐츠산업조사(음악·방송·게임), KOCCA
# 웹툰 실태조사(매출), 농식품부(농식품 수출), 식약처(화장품 수출), 한국관광공사(외래객).
#   음악 5.64→18.0억$ / 방송 4.78→12.52억$ / 게임 64.1→85.0억$ / 웹툰매출 4663→22856억원
#   농식품 64.8→99.8억$ / 화장품 62.8→102억$ / 의류 보합 / 외래객 1535→1637만명
REAL_ANNUAL_INDEX = {
    "kpop":     {2018: 100, 2019: 135, 2020: 121, 2021: 154, 2022: 160, 2023: 230, 2024: 319},
    "kvideo":   {2018: 100, 2019: 99,  2020: 145, 2021: 147, 2022: 167, 2023: 188, 2024: 262},
    "kgame":    {2018: 100, 2019: 104, 2020: 128, 2021: 135, 2022: 139, 2023: 117, 2024: 133},
    "kwebtoon": {2018: 100, 2019: 137, 2020: 226, 2021: 336, 2022: 392, 2023: 469, 2024: 490},
    "kfood":    {2018: 100, 2019: 108, 2020: 117, 2021: 132, 2022: 136, 2023: 139, 2024: 154},
    "kbeauty":  {2018: 100, 2019: 104, 2020: 121, 2021: 146, 2022: 127, 2023: 135, 2024: 162},
    "kfashion": {2018: 100, 2019: 98,  2020: 87,  2021: 100, 2022: 108, 2023: 104, 2024: 105},
    "ktourism": {2018: 100, 2019: 114, 2020: 16,  2021: 6,   2022: 21,  2023: 72,  2024: 107},
}
REAL_LAST_YEAR = 2024  # 이후 연도는 최신 확정치 유지(보수적)


def _real_idx_q(genre: str, year: int, q: int) -> float:
    """실측 연간지수 → 분기지수. 연간값을 분기 중앙에 배치해 선형보간, 확정연도 이후는 유지."""
    a = REAL_ANNUAL_INDEX[genre]

    def av(yr):
        return a[yr] if yr <= REAL_LAST_YEAR else a[REAL_LAST_YEAR]

    lo = av(year)
    hi = av(year + 1)
    return round(lo + (hi - lo) * (q - 0.5) / 4.0, 1)


def _idx_q_from_annual(aidx: dict, year: int, q: int) -> float:
    """이미 2018=100으로 지수화된 연간 dict(aidx)를 분기로 보간. 최신연도 이후는 유지."""
    last, first = max(aidx), min(aidx)

    def av(yr):
        if yr in aidx:
            return aidx[yr]
        if yr >= last:
            return aidx[last]
        if yr <= first:
            return aidx[first]
        lo_y = max(y for y in aidx if y < yr)
        hi_y = min(y for y in aidx if y > yr)
        return aidx[lo_y] + (aidx[hi_y] - aidx[lo_y]) * (yr - lo_y) / (hi_y - lo_y)

    lo = av(year)
    hi = av(year + 1)
    return round(lo + (hi - lo) * (q - 0.5) / 4.0, 1)


def _current_quarter():
    now = datetime.now(timezone(timedelta(hours=9)))
    return now.year, (now.month - 1) // 3 + 1


def quarters(base_year: int):
    ey, eq = _current_quarter()
    out, y, q = [], base_year, 1
    while (y, q) <= (ey, eq):
        out.append((y, q))
        q += 1
        if q > 4:
            y, q = y + 1, 1
    return out


# ── 샘플 추세 (폴백) ──────────────────────────────────────────
def _sample_domain_raw(genre: str, year: int, q: int) -> float:
    base = (1 + GROWTH[genre]) ** ((year - 2018) + (q - 1) / 4.0)
    if genre == "ktourism":
        base *= TOURISM_COVID.get((year, q), 1.0)
    seasonal = 1 + 0.03 * math.sin((q / 4.0) * 2 * math.pi)
    noise = 1 + ((hash((genre, year, q)) % 7) - 3) / 120.0
    return max(base * seasonal * noise, 0.001)


# ── 실 백필: KOSIS 연간 (한 번 호출로 다년치) ──────────────────
def _kosis_annual():
    if not config.KOSIS_API_KEY:
        return None
    try:
        r = requests.get(config.KOSIS_URL, params={
            "method": "getList", "apiKey": config.KOSIS_API_KEY, "orgId": config.KOSIS_ORG_ID,
            "tblId": config.KOSIS_EXPORT_TBL, "itmId": config.KOSIS_EXPORT_ITM, "objL1": "ALL",
            "prdSe": "Y", "startPrdDe": str(config.HISTORY_BASE_YEAR),
            "endPrdDe": str(_current_quarter()[0]), "format": "json", "jsonVD": "Y"}, timeout=40)
        data = r.json()
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(data, list) or not data:
        return None
    out = {}
    for rec in data:
        g = config.KOSIS_INDUSTRY_MAP.get((rec.get("C1_NM") or "").strip())
        if not g:
            continue
        try:
            y = int(rec.get("PRD_DE")); v = float(rec.get("DT") or 0)
        except (TypeError, ValueError):
            continue
        out.setdefault(g, {})
        out[g][y] = out[g].get(y, 0.0) + v
    return out or None


def _customs_annual(hs_codes):
    """관세청 무역통계 → 분야별 전국 연간 수출액(2018~). HS 코드 합, 연 단위.

    뷰티(화장품 HS)·패션(의류 HS)·푸드(K-food 가공식품 HS)의 공식 무역통계 기반.
    키 없거나 응답 결측이면 None(→ 검증고정 폴백).
    """
    if not config.DATA_GO_KR_API_KEY or not hs_codes:
        return None
    # 진행 중인 올해는 부분 연도(예: 5개월치)라 1년치와 비교 불가 → 직전 완성연도까지만 사용.
    # (이후 분기는 _idx_q_from_annual이 최신 완성연도 값으로 유지)
    end_year = _current_quarter()[0] - 1
    out, got = {}, False
    for y in range(config.HISTORY_BASE_YEAR, end_year + 1):
        tot = 0.0
        for hs in hs_codes:
            try:
                r = requests.get(config.CUSTOMS_EXPORT_URL, params={
                    "serviceKey": config.DATA_GO_KR_API_KEY,
                    "strtYymm": f"{y}01", "endYymm": f"{y}12", "hsSgn": hs}, timeout=40)
                tot += collectors._parse_customs_expdlr(r.text)
            except Exception:  # noqa: BLE001
                continue
        if tot > 0:
            out[y] = tot
            got = True
    return out if got else None


def interp_annual_to_quarterly(annual: dict, qs: list) -> dict:
    """연간값 → 분기값. 연도 내 다음 연도로 선형 램프, 데이터 밖은 CAGR 외삽."""
    yrs = sorted(annual)
    res = {}
    last = yrs[-1]
    cagr = 1.0
    if len(yrs) >= 2 and annual[yrs[-2]] > 0:
        cagr = (annual[last] / annual[yrs[-2]]) ** (1.0 / (last - yrs[-2]))
    for (y, q) in qs:
        if y in annual and (y + 1) in annual:
            v = annual[y] + (annual[y + 1] - annual[y]) * (q - 1) / 4.0
        elif y in annual:
            slope = (annual[y] - annual[y - 1]) if (y - 1) in annual else 0.0
            v = annual[y] + slope * (q - 1) / 4.0
        elif y > last:
            v = annual[last] * (cagr ** ((y - last) + (q - 1) / 4.0))
        else:
            v = annual[yrs[0]]
        res[(y, q)] = max(v, 0.001)
    return res


# ── 실 백필: KTO 월별 → 분기 ──────────────────────────────────
def _kto_quarterly(qs: list):
    if not config.DATA_GO_KR_API_KEY:
        return None
    monthly = {}
    got = False
    for (y, q) in qs:
        for mo in range((q - 1) * 3 + 1, (q - 1) * 3 + 4):
            ym = f"{y}{mo:02d}"
            try:
                r = requests.get(config.KTO_VISITORS_URL, params={
                    "ServiceKey": config.DATA_GO_KR_API_KEY, "YM": ym, "ED_CD": "E",
                    "numOfRows": 600, "pageNo": 1}, timeout=30)
                tot = sum(int(x) for x in re.findall(r"<num>(\d+)</num>", r.text))
            except Exception:  # noqa: BLE001
                tot = 0
            if tot:
                got = True
            monthly[(y, q)] = monthly.get((y, q), 0) + tot
    if not got:
        return None
    return {k: max(v, 0.001) for k, v in monthly.items()}


def build_history(sample: bool = False):
    base = config.HISTORY_BASE_YEAR
    qs = quarters(base)
    genres = list(config.GENRE_WEIGHTS)

    # 콘텐츠 4분야(K-pop·K영상·게임·웹툰)는 KOSIS 콘텐츠산업조사 연간 수출(2018~)을
    # 라이브로 받아 2018=100 지수화한다(API 자동화). 나머지 4분야(푸드·패션·뷰티·관광)는
    # 장기 백필이 API로 깔끔하지 않아 검증 통계 고정값(REAL_ANNUAL_INDEX)을 사용한다.
    # KOSIS 키 없거나 응답 결측이면 해당 분야도 검증고정값으로 폴백(결정론적).
    KOSIS_GENRES = {"kpop", "kvideo", "kgame", "kwebtoon"}
    kosis = None if sample else _kosis_annual()  # {genre: {year: 전국 수출액}}
    idx, sources = {}, {}
    for g in genres:
        ann = kosis.get(g) if (kosis and g in KOSIS_GENRES) else None
        yrs = sorted(y for y in (ann or {}) if y >= config.HISTORY_BASE_YEAR)
        if ann and len(yrs) >= 2 and ann.get(config.HISTORY_BASE_YEAR):
            base_v = ann[config.HISTORY_BASE_YEAR]
            aidx = {y: ann[y] / base_v * 100 for y in ann if ann[y] is not None}
            idx[g] = {qq: _idx_q_from_annual(aidx, qq[0], qq[1]) for qq in qs}
            sources[g] = "kosis(real)"
        else:
            idx[g] = {qq: _real_idx_q(g, qq[0], qq[1]) for qq in qs}
            sources[g] = "stat(verified-fixed)"
    # 관광은 KTO 출입국관광통계(월별 방한 외래객, 2018~)로 2018=100 지수화 — API 자동화.
    # KTO 키 없거나 2018 베이스 결측이면 검증고정값 유지(폴백).
    if not sample:
        kto = _kto_quarterly(qs)
        if kto:
            bvals = [kto[(base, q)] for q in (1, 2, 3, 4) if (base, q) in kto and kto[(base, q)] > 0.01]
            bavg = (sum(bvals) / len(bvals)) if bvals else 0.0
            if bavg > 0:
                idx["ktourism"] = {qq: round(kto.get(qq, 0.0) / bavg * 100, 1) for qq in qs}
                sources["ktourism"] = "kto(real)"

    # 푸드·패션·뷰티는 관세청 무역통계(전국 연간 수출)로 2018=100 지수화 — API 자동화.
    # 푸드=가공식품(라면·김치 등) HS, 패션=의류 HS, 뷰티=화장품 HS. 실패 시 검증고정 유지.
    if not sample:
        for g in ("kfood", "kfashion", "kbeauty"):
            ann = _customs_annual(config.CUSTOMS_HS_CODES.get(g))
            yrs = sorted(y for y in (ann or {}) if y >= config.HISTORY_BASE_YEAR)
            if ann and len(yrs) >= 2 and ann.get(config.HISTORY_BASE_YEAR):
                base_v = ann[config.HISTORY_BASE_YEAR]
                aidx = {y: ann[y] / base_v * 100 for y in ann if ann[y]}
                idx[g] = {qq: _idx_q_from_annual(aidx, qq[0], qq[1]) for qq in qs}
                sources[g] = "customs(real)"

    weights = processor.active_weights()
    composite = {qq: round(sum(weights[g] * idx[g][qq] for g in genres), 1) for qq in qs}

    def label(yq):
        return f"{yq[0]}Q{yq[1]}"

    disp = [yq for yq in qs if label(yq) >= config.HISTORY_DISPLAY_START]
    real_n = sum(1 for s in sources.values() if "real" in s)
    return {
        "base_year": base,
        "display_start": config.HISTORY_DISPLAY_START,
        "weight_profile": config.ACTIVE_WEIGHT_PROFILE,
        "sources": sources,
        "real_domains": real_n,
        "note": f"2018=100 분기지수. 전 8분야 공공 API 실측 우선: 콘텐츠 4분야(K-pop·K영상·게임·웹툰)=KOSIS 콘텐츠산업조사 수출 {sum(1 for s in sources.values() if s == 'kosis(real)')}/4, 관광=KTO 출입국통계, 푸드·패션·뷰티=관세청 무역통계(가공식품·의류·화장품 HS). API 결측 분야는 검증 통계로 폴백. 분기 선형보간, 최신 확정연도 이후 유지.",
        "notes": {
            "kwebtoon": "K웹툰 L1은 KOSIS '만화 수출' 기준. 콘텐츠산업조사의 만화산업은 출판만화+온라인만화(웹툰)를 포함하며, 2020년부터 웹툰이 매출의 과반·수출을 주도(종이 만화 아님). 2018년 수출 베이스가 작아 증가 배수가 크게 보이는 저(低)베이스 효과 유의. 웹툰 '산업 매출'(2024년 2.29조원, 4.9배)은 내수 포함이라 별도 지표로 해석.",
            "kfood": "K푸드 L1은 관세청 가공식품(라면·김치·소스·조미김 등) 수출 기준. 농식품 총수출(곡물·축산 등 포함)이 아니라 한류 식품 신호에 맞춘 가공식품 위주이므로 총수출보다 증가율이 높을 수 있음.",
            "ktourism": "K관광 L1은 KTO 출입국관광통계(방한 외래객). 2020–21 코로나 급감·이후 회복 반영.",
            "vintage": "최신 확정 연간은 2024년(2025년 통계 미발표). 2025년은 2024 확정치로 보수적 유지(참고: 2025 상반기 만화·웹툰 수출 전년동기비 약 -15%).",
        },
        "quarters": [label(q) for q in disp],
        "composite": [composite[q] for q in disp],
        "domains": {g: [idx[g][q] for q in disp] for g in genres},
        "domain_names": {g: config.GENRE_NAMES_KO[g] for g in genres},
    }


def run(sample: bool = False) -> int:
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    hist = build_history(sample=sample)
    (config.ROOT_DIR / "data" / "history.json").write_text(
        json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[history] {hist['quarters'][0]}~{hist['quarters'][-1]} · 2018=100 · "
          f"실데이터 {hist['real_domains']}/8 · composite {hist['composite'][0]}→{hist['composite'][-1]}")
    for g, s in hist["sources"].items():
        print(f"   {config.GENRE_NAMES_KO[g]:4} {s}")
    return 0


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", action="store_true", help="강제 샘플(실 백필 생략)")
    return run(sample=ap.parse_args().sample)


if __name__ == "__main__":
    raise SystemExit(main())
