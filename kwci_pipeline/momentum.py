"""월간 모멘텀 서브지수 (nowcast) — 빠른 신호만으로 만든 선행지표.

전체 KWCI(분기)와 분리된 별도 층. 빠르게 갱신되는 두 가지만 결합:
  L1(경제) = 관세청 월수출 (kfood/kfashion/kbeauty)
  L3(수용자) = YouTube + Reddit (8분야)
연 단위(KOSIS·KOFICE)·인프라(KF·TourAPI)는 제외 — 월마다 안 변하므로 nowcast를 흐림.

momentum DSI(분야) = 수출 있는 분야: 0.5·수출_norm + 0.5·플랫폼_norm / 없는 분야: 플랫폼_norm
모멘텀(국가) = Σ(활성 도메인가중 × momentum DSI). 활성 가중치는 config.ACTIVE_WEIGHT_PROFILE.
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from kwci_pipeline import collectors, config, processor
else:
    from . import collectors, config, processor


def _last_month() -> str:
    lm = datetime.now(timezone(timedelta(hours=9))).replace(day=1) - timedelta(days=1)
    return lm.strftime("%Y-%m")


def build_momentum(sample: bool = False):
    customs = collectors.collect_customs_export(sample=sample or not config.DATA_GO_KR_API_KEY)
    yt = collectors.collect_youtube_metrics(sample=sample or not config.YOUTUBE_API_KEY)
    tr = collectors.collect_trends(sample=sample)

    df = yt[["country", "genre", "youtube_views"]].merge(
        tr[["country", "genre", "trends_interest"]], on=["country", "genre"], how="outer")
    df["youtube_views"] = df["youtube_views"].fillna(0)
    df["trends_interest"] = df["trends_interest"].fillna(0)
    df = df.merge(customs[["country", "genre", "export_usd"]], on=["country", "genre"], how="left")

    df["yt_norm"] = df.groupby("genre")["youtube_views"].transform(processor.minmax)
    df["tr_norm"] = df.groupby("genre")["trends_interest"].transform(processor.minmax)
    wy, wr = 0.6, 0.4
    df["wy"], df["wr"] = wy, wr
    rmask = df["country"].isin(config.TRENDS_RESTRICTED)
    df.loc[rmask, "wy"] = wy + wr
    df.loc[rmask, "wr"] = 0.0
    df["plat_norm"] = df["wy"] * df["yt_norm"] + df["wr"] * df["tr_norm"]
    df["exp_norm"] = df.groupby("genre")["export_usd"].transform(
        lambda x: processor.minmax(x) if x.notna().any() else x)

    def mdsi(r):
        if isinstance(r["exp_norm"], float) and math.isnan(r["exp_norm"]):
            return r["plat_norm"]
        return 0.5 * r["exp_norm"] + 0.5 * r["plat_norm"]

    df["mdsi"] = df.apply(mdsi, axis=1)
    weights = processor.active_weights()
    df["w"] = df["genre"].map(weights)
    df["wm"] = df["w"] * df["mdsi"]

    country = df.groupby("country", as_index=False).agg(momentum=("wm", "sum"))
    country["momentum"] = country["momentum"].clip(upper=100).round(2)
    country["country_name"] = country["country"].map(lambda c: config.TARGET_COUNTRIES[c]["name_ko"])
    country = country.sort_values("momentum", ascending=False)
    return df, country


def run(sample: bool = False) -> int:
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df, country = build_momentum(sample=sample)
    period = _last_month()
    out = {
        "period": period,
        "type": "monthly momentum subindex (nowcast)",
        "layers": "L1 관세청 월수출 + L3 YouTube·Google Trends (연단위·인프라 제외)",
        "weight_profile": config.ACTIVE_WEIGHT_PROFILE,
        "global_momentum": round(float(country["momentum"].mean()), 2),
        "countries": country.to_dict(orient="records"),
        "top": country.head(5).to_dict(orient="records"),
    }
    (config.ROOT_DIR / "data" / "momentum_latest.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    collectors.append_timeseries(country.assign(period=period), "momentum")
    print(f"[momentum] {period} · 프로파일 {config.ACTIVE_WEIGHT_PROFILE} · 글로벌 모멘텀 {out['global_momentum']}")
    print(country[["country", "country_name", "momentum"]].head(8).to_string(index=False))
    return 0


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="KWCI 월간 모멘텀 서브지수(nowcast).")
    ap.add_argument("--sample", action="store_true")
    args = ap.parse_args()
    return run(sample=args.sample)


if __name__ == "__main__":
    raise SystemExit(main())
