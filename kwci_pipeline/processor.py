from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from . import config


def minmax(series: pd.Series) -> pd.Series:
    mn, mx = series.min(), series.max()
    if pd.isna(mn) or pd.isna(mx) or mx == mn:
        return pd.Series([50.0] * len(series), index=series.index)
    return (series - mn) / (mx - mn) * 100


def build_panel(survey, youtube, trends, kf, export=None):
    survey = survey.rename(columns={"source": "survey_source"})
    youtube = youtube.rename(columns={"source": "youtube_source"})
    trends = trends.rename(columns={"source": "trends_source"})
    kf = kf.rename(columns={"source": "kf_source"})
    panel = survey.merge(youtube, on=["country", "genre"], how="left")
    panel = panel.merge(trends, on=["country", "genre"], how="left")
    panel = panel.merge(kf, on="country", how="left")
    panel["youtube_views"] = panel["youtube_views"].fillna(0)
    panel["trends_interest"] = panel["trends_interest"].fillna(0)
    panel["kf_count"] = panel["kf_count"].fillna(panel["kf_score"])
    # L1 경제: 관세청 수출액 (해당 분야만; 나머지 분야는 NaN → L1 결측)
    if export is not None and len(export):
        export = export.rename(columns={"source": "customs_source"})
        panel = panel.merge(export[["country", "genre", "export_usd", "customs_source"]],
                            on=["country", "genre"], how="left")
    else:
        panel["export_usd"] = float("nan")
    return panel


def compute_domain_weights(alpha: float | None = None) -> dict:
    """프레임워크 2축 가중치: w_i = α·(수출_i/Σ수출) + (1-α)·(영향력_i/Σ영향력).

    영향력 프록시는 현 GENRE_WEIGHTS(산업규모안)를 사용한다(글로벌 SNS·미디어
    영향력 지표 미구현). 참고용 산출이며, 활성 가중치는 GENRE_WEIGHTS이다.
    """
    alpha = config.WEIGHT_ALPHA if alpha is None else alpha
    exp = config.DOMAIN_EXPORT_REF
    infl = config.GENRE_WEIGHTS
    etot, itot = sum(exp.values()), sum(infl.values())
    w = {g: alpha * (exp[g] / etot) + (1 - alpha) * (infl[g] / itot) for g in exp}
    s = sum(w.values())
    return {g: round(w[g] / s, 4) for g in w}


def weight_profiles() -> dict:
    """선택 가능한 가중치 프로파일 전체."""
    base = dict(config.GENRE_WEIGHTS)
    genres = list(base)
    equal = {g: round(1.0 / len(genres), 4) for g in genres}
    return {
        "industry": base,
        "equal": equal,
        "two_axis_economic": compute_domain_weights(0.6),
        "two_axis_cultural": compute_domain_weights(0.4),
    }


def active_weights() -> dict:
    return weight_profiles().get(config.ACTIVE_WEIGHT_PROFILE, dict(config.GENRE_WEIGHTS))


def profile_comparison(scored: pd.DataFrame) -> dict:
    """모든 프로파일에서의 글로벌 평균·상위국 비교 (DSI는 가중치와 무관하므로 재가중만)."""
    piv = scored.pivot_table(index="country", columns="genre", values="dsi", aggfunc="first")
    out = {}
    for name, w in weight_profiles().items():
        kwci_c = sum(piv[g] * w.get(g, 0) for g in piv.columns).clip(upper=100)
        ranked = kwci_c.sort_values(ascending=False)
        out[name] = {
            "weights": {g: round(w[g], 4) for g in w},
            "global_mean": round(float(kwci_c.mean()), 2),
            "top3": list(ranked.head(3).index),
        }
    return out


def score_panel(panel):
    """프레임워크 L1/L2/L3 → DSI → KWCI 산출.

    현재 신호 매핑: L2=KF 한류인프라, L3=KOFICE 설문·YouTube·Reddit.
    L1(경제)은 수집기 미구현 → 도메인 층위가중을 L2·L3로 재정규화(프레임워크 결측규칙).
    """
    s = panel.copy()
    # L3 내부 신호 정규화 (장르별 Min-Max)
    s["survey_norm"] = s.groupby("genre")["survey_score"].transform(minmax)
    s["youtube_norm"] = s.groupby("genre")["youtube_views"].transform(minmax)
    s["trends_norm"] = s.groupby("genre")["trends_interest"].transform(minmax)

    # L2 (영향력): KF 한류현황 — 국가 단위
    kf = s[["country", "kf_count"]].drop_duplicates().copy()
    kf["L2_norm"] = minmax(kf["kf_count"])
    s = s.merge(kf[["country", "L2_norm"]], on="country", how="left")

    # L3 결합 (Google 차단/제한국 → trends 가중을 youtube로 이전)
    a = config.L3_SUBWEIGHTS["survey"]; b = config.L3_SUBWEIGHTS["youtube"]; g = config.L3_SUBWEIGHTS["trends"]
    s["wa"], s["wb"], s["wg"] = a, b, g
    rmask = s["country"].isin(config.TRENDS_RESTRICTED)
    s.loc[rmask, "wb"] = b + g
    s.loc[rmask, "wg"] = 0.0
    s["L3_norm"] = s["wa"] * s["survey_norm"] + s["wb"] * s["youtube_norm"] + s["wg"] * s["trends_norm"]

    # L1 (경제): 관세청 수출액 → 분야별 Min-Max. 수출 데이터 없는 분야는 NaN(결측).
    if "export_usd" in s.columns:
        s["L1_norm"] = s.groupby("genre")["export_usd"].transform(
            lambda x: minmax(x) if x.notna().any() else x)
    else:
        s["L1_norm"] = math.nan

    # DSI: 존재하는 층위만으로 층위가중 재정규화
    lw = config.LAYER_WEIGHTS

    def dsi_row(r):
        present = {}
        if not (isinstance(r["L1_norm"], float) and math.isnan(r["L1_norm"])):
            present["L1"] = r["L1_norm"]
        present["L2"] = r["L2_norm"]
        present["L3"] = r["L3_norm"]
        tot = sum(lw[k] for k in present) or 1.0
        return sum(lw[k] / tot * present[k] for k in present)

    s["dsi"] = s.apply(dsi_row, axis=1)
    s["genre_weight"] = s["genre"].map(active_weights())
    s["weighted_dsi"] = s["genre_weight"] * s["dsi"]

    country = s.groupby("country", as_index=False).agg(
        kwci=("weighted_dsi", "sum"),
        L2_norm=("L2_norm", "first"),
        youtube_views=("youtube_views", "sum"),
        trends_interest=("trends_interest", "mean"),
    )
    country["trends_interest"] = country["trends_interest"].round(1)
    country["kwci"] = country["kwci"].clip(upper=100).round(2)
    country["country_name"] = country["country"].map(lambda c: config.TARGET_COUNTRIES[c]["name_ko"])
    country = country.sort_values("kwci", ascending=False)
    return s, country


def domain_summary(scored: pd.DataFrame) -> pd.DataFrame:
    """도메인(분야)별 DSI 평균 — 어떤 분야가 전 세계적으로 강한지."""
    d = scored.groupby("genre", as_index=False).agg(dsi_mean=("dsi", "mean"))
    d["genre_name"] = d["genre"].map(config.GENRE_NAMES_KO)
    d["domain_weight"] = d["genre"].map(config.GENRE_WEIGHTS)
    d["dsi_mean"] = d["dsi_mean"].round(2)
    return d.sort_values("dsi_mean", ascending=False)


def build_global(country: pd.DataFrame) -> dict:
    vals = country.set_index("country")["kwci"]
    mean_idx = round(float(vals.mean()), 2)
    pop = {c: config.COUNTRY_POPULATION.get(c, 0) for c in vals.index}
    pop_total = sum(pop.values()) or 1
    pop_weighted = round(float(sum(vals[c] * pop[c] for c in vals.index) / pop_total), 2)
    headline = pop_weighted if config.GLOBAL_INDEX_METHOD == "pop_weighted" else mean_idx
    return {
        "global_index": headline, "method": config.GLOBAL_INDEX_METHOD,
        "global_index_mean": mean_idx, "global_index_pop_weighted": pop_weighted,
        "countries_count": int(vals.shape[0]),
        "max_country": {"country": vals.idxmax(), "value": round(float(vals.max()), 2)},
        "min_country": {"country": vals.idxmin(), "value": round(float(vals.min()), 2)},
    }


def _enm_of(series: pd.Series) -> dict | None:
    """국가별 값 시리즈 → 유효시장수 ENM=1/HHI + 상위국."""
    v = series.astype(float)
    tot = float(v.sum())
    if tot <= 0 or len(v) == 0:
        return None
    p = v / tot
    hhi = float((p ** 2).sum())
    enm = (1.0 / hhi) if hhi > 0 else 0.0
    return {
        "enm": round(enm, 2),
        "enm_pct": round(enm / max(len(v), 1) * 100, 1),
        "hhi": round(hhi, 4),
        "top_country": v.idxmax(),
        "top_share_pct": round(float(p.max()) * 100, 1),
    }


def audience_diversification(scored: pd.DataFrame) -> dict:
    """수용 시장 다변화(audience): 분야별 국가 구성비의 유효시장수 ENM=1/HHI. 값↑=쏠림↓.

    1차 기준 = KOFICE 해외한류실태조사(survey_score): 국가별 '실제 관심/소비'를 연 1회
    측정한 안정 지표 → 단면 노이즈 없음(YouTube API의 '지역노출×글로벌조회수' 왜곡 회피).
    youtube_* = 참고용 보조(현재 단면, 노이즈 큼). basis로 출처 명시.
    """
    out = {}
    for g, grp in scored.groupby("genre"):
        survey = _enm_of(grp.groupby("country")["survey_score"].mean())
        yt = _enm_of(grp.groupby("country")["youtube_views"].sum())
        if survey:
            rec = dict(survey)
            rec["basis"] = "kofice_survey"
            if yt:
                rec["youtube_enm"] = yt["enm"]
                rec["youtube_top"] = f"{yt['top_country']} {yt['top_share_pct']}%"
            out[g] = rec
        elif yt:
            rec = dict(yt)
            rec["basis"] = "youtube_snapshot"
            out[g] = rec
        else:
            out[g] = {"enm": None, "basis": "no_data"}
    return out


def export_outputs(scored: pd.DataFrame, country: pd.DataFrame, extras: dict | None = None) -> dict[str, Path]:
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    date_label = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d")
    panel_path = config.OUTPUT_DIR / f"{date_label}_kwci_panel.csv"
    country_path = config.OUTPUT_DIR / f"{date_label}_kwci_country.csv"
    domain_path = config.OUTPUT_DIR / f"{date_label}_kwci_domain.csv"
    global_path = config.OUTPUT_DIR / f"{date_label}_kwci_global.csv"
    latest_json_path = config.ROOT_DIR / "data" / "kwci_latest.json"

    scored.to_csv(panel_path, index=False, encoding="utf-8-sig")
    country.to_csv(country_path, index=False, encoding="utf-8-sig")
    dom = domain_summary(scored)
    dom.to_csv(domain_path, index=False, encoding="utf-8-sig")
    gsum = build_global(country)
    pd.DataFrame([{"date": date_label,
                   **{k: v for k, v in gsum.items() if k not in ("max_country", "min_country")},
                   "max_country": gsum["max_country"]["country"],
                   "min_country": gsum["min_country"]["country"]}]).to_csv(
        global_path, index=False, encoding="utf-8-sig")

    latest = {
        "date": date_label,
        "framework": "KWCI L1/L2/L3 DSI model",
        "cadence": config.REFRESH_CADENCE,
        "base_year": config.BASE_YEAR,
        "base_year_indexed": False,
        "note": "횡단 0~100 원지수(국가 간 상대비교). L1은 국가별 수집분(관세청 푸드·패션·뷰티, KTO 관광)이 DSI에 실제 반영됨. 2018=100 시계열 지수는 history.json에서 별도 제공.",
        "layer_structure": "L1 경제(0.5)/L2 영향력(0.3)/L3 수용자(0.2). L1=관세청(푸드·패션·뷰티)+KTO(관광) 국가별 실측 연결. KOSIS(K-pop·K영상·게임·웹툰)는 전국 단위라 횡단 DSI엔 미반영→2018=100 history에 반영. 데이터 없는 층위는 재정규화.",
        "l1_coverage": {
            "per_country_real": ["kfood", "kfashion", "kbeauty", "ktourism"],
            "national_only_in_history": ["kpop", "kvideo", "kgame", "kwebtoon"],
        },
        "layer_weights": config.LAYER_WEIGHTS,
        "active_weight_profile": config.ACTIVE_WEIGHT_PROFILE,
        "domain_weights": active_weights(),
        "weight_profiles": profile_comparison(scored),
        "formula": "DSI_i=Σ(wL·L_norm); KWCI=Σ(w_i·DSI_i); KWCI_index=KWCI/KWCI_2018×100",
        "global": gsum,
        "domains": dom.to_dict(orient="records"),
        "countries": country.to_dict(orient="records"),
        "top": country.head(5).to_dict(orient="records"),
        "audience_diversification": audience_diversification(scored),
        "audience_diversification_note": "분야별 국가 구성비의 유효시장수 ENM=1/HHI(값↑=쏠림↓). 1차 기준=KOFICE 해외한류실태조사 국가별 관심(연 1회·안정, 단면 노이즈 없음). youtube_*는 참고용 보조(현재 단면, YouTube API 한계로 노이즈 큼). basis 필드로 출처 표시.",
    }
    if extras:
        latest.update(extras)
    latest_json_path.write_text(json.dumps(latest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"panel": panel_path, "country": country_path, "domain": domain_path,
            "global": global_path, "json": latest_json_path}
