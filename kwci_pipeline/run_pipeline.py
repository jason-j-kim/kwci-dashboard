from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from kwci_pipeline import collectors, config, processor
else:
    from . import collectors, config, processor


def run(sample: bool = False) -> int:
    collectors.ensure_dirs()
    youtube_sample = sample or not config.YOUTUBE_API_KEY
    kf_sample = sample or not (config.KF_API_KEY and config.KF_API_URL)
    customs_sample = sample or not config.DATA_GO_KR_API_KEY

    if not config.YOUTUBE_API_KEY:
        print("[kwci] YOUTUBE_API_KEY missing: YouTube uses sample metrics.")
    if not (config.KF_API_KEY and config.KF_API_URL):
        print("[kwci] KF_API_KEY/KF_API_URL missing: KF uses sample metrics.")
    if not config.DATA_GO_KR_API_KEY:
        print("[kwci] DATA_GO_KR_API_KEY missing: 관세청 L1 수출 uses sample metrics.")

    survey = collectors.load_survey_baseline()
    youtube = collectors.collect_youtube_metrics(sample=youtube_sample)
    trends = collectors.collect_trends(sample=sample)
    kf = collectors.collect_kf_metrics(sample=kf_sample)
    customs = collectors.collect_customs_export(sample=customs_sample)
    kto = collectors.collect_kto_visitors(sample=customs_sample)
    tourism = collectors.collect_tourism_supply(sample=customs_sample)
    kosis = collectors.collect_kosis_industry(sample=sample or not config.KOSIS_API_KEY)
    l1_export = pd.concat([customs, kto], ignore_index=True)  # 관세청(식품·패션·뷰티)+KTO(관광)

    raw_paths = {
        "survey": collectors.save_raw(survey, "survey_baseline"),
        "youtube": collectors.save_raw(youtube, "youtube_metrics"),
        "trends": collectors.save_raw(trends, "trends_metrics"),
        "kf": collectors.save_raw(kf, "kf_metrics"),
        "customs": collectors.save_raw(customs, "customs_export"),
        "kto": collectors.save_raw(kto, "kto_visitors"),
        "tourism": collectors.save_raw(tourism, "tourism_supply"),
        "kosis": collectors.save_raw(kosis, "kosis_industry"),
    }
    panel = processor.build_panel(survey, youtube, trends, kf, l1_export)
    scored, country = processor.score_panel(panel)
    output_paths = processor.export_outputs(scored, country, extras={
        "tourism_supply": tourism.to_dict(orient="records"),
        "kosis_industry_export": kosis.to_dict(orient="records")})

    print("[kwci] raw files")
    for name, path in raw_paths.items():
        print(f"  - {name}: {path}")
    print("[kwci] outputs")
    for name, path in output_paths.items():
        print(f"  - {name}: {path}")
    g = processor.build_global(country)
    print("[kwci] global index")
    print(f"  - 글로벌 종합({g['method']}): {g['global_index']}  "
          f"(단순평균 {g['global_index_mean']} / 인구가중 {g['global_index_pop_weighted']})")
    print("[kwci] domain DSI (분야별)")
    print(processor.domain_summary(scored)[["genre", "genre_name", "dsi_mean", "domain_weight"]].to_string(index=False))
    print(f"[kwci] weight profiles (활성: {config.ACTIVE_WEIGHT_PROFILE})")
    for name, info in processor.profile_comparison(scored).items():
        print(f"  - {name:18} 글로벌평균 {info['global_mean']:5}  top3={info['top3']}")
    print("[kwci] top countries")
    print(country[["country", "country_name", "kwci", "youtube_views", "trends_interest"]].head(10).to_string(index=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect and compute the KWCI L2 country realtime module.")
    parser.add_argument("--sample", action="store_true", help="Force sample data without API calls.")
    args = parser.parse_args()
    return run(sample=args.sample)


if __name__ == "__main__":
    raise SystemExit(main())
