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
    from kwci_pipeline import config, processor
else:
    from . import config, processor

GROWTH = {"kpop": 0.08, "kvideo": 0.12, "kgame": 0.06, "kwebtoon": 0.20,
          "kfood": 0.09, "kbeauty": 0.11, "kfashion": 0.04, "ktourism": 0.10}
TOURISM_COVID = {
    (2020, 1): 0.85, (2020, 2): 0.05, (2020, 3): 0.04, (2020, 4): 0.04,
    (2021, 1): 0.05, (2021, 2): 0.06, (2021, 3): 0.08, (2021, 4): 0.12,
    (2022, 1): 0.18, (2022, 2): 0.30, (2022, 3): 0.45, (2022, 4): 0.60,
    (2023, 1): 0.72, (2023, 2): 0.82, (2023, 3): 0.90, (2023, 4): 0.93,
    (2024, 1): 0.95, (2024, 2): 0.98, (2024, 3): 1.00, (2024, 4): 1.00,
}


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
    kosis = None if sample else _kosis_annual()
    kto = None if sample else _kto_quarterly(qs)

    raw, sources = {}, {}
    for g in genres:
        series, src = None, "sample"
        if kosis and g in kosis and len(kosis[g]) >= 2:
            series, src = interp_annual_to_quarterly(kosis[g], qs), "kosis(real)"
        elif g == "ktourism" and kto:
            series, src = kto, "kto(real)"
        if series is None:
            series = {(y, q): _sample_domain_raw(g, y, q) for (y, q) in qs}
        raw[g], sources[g] = series, src

    idx = {}
    for g in genres:
        bv = [raw[g][(base, q)] for q in (1, 2, 3, 4) if (base, q) in raw[g]]
        avg = sum(bv) / len(bv) if bv else 1.0
        idx[g] = {qq: round(raw[g][qq] / avg * 100, 1) for qq in qs}
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
        "note": f"경제(L1) 백본 분기지수, 2018=100. 실데이터 {real_n}/8 분야, 나머지 추세 샘플.",
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
