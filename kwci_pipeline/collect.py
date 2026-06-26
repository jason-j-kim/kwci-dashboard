"""소스별 수집 CLI — 수집 주기와 지수 산출 주기를 분리한다.

각 소스를 고유 주기로 수집해 시계열(data/timeseries/)에 누적하고, 날짜별 raw도 저장한다.
지수 산출(run_pipeline.py)은 분기 단위로 별도 실행한다.

사용:
    python kwci_pipeline/collect.py platform   # 주 단위 (YouTube + Reddit)
    python kwci_pipeline/collect.py customs    # 월 단위 (관세청 수출)
    python kwci_pipeline/collect.py tourism    # 월 단위 (TourAPI 공급 스냅샷)
    python kwci_pipeline/collect.py kosis      # 연 단위 (KOSIS 콘텐츠산업)
    python kwci_pipeline/collect.py kf         # 연/분기 (KF 한류현황)
    python kwci_pipeline/collect.py all
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from kwci_pipeline import collectors, config
else:
    from . import collectors, config


def _store(df, name: str) -> None:
    collectors.save_raw(df, name)
    collectors.append_timeseries(df, name)


def collect(source: str, force_sample: bool | None = None) -> None:
    def smp(missing: bool) -> bool:
        return missing if force_sample is None else force_sample

    did = []
    if source in ("platform", "all"):
        yt = collectors.collect_youtube_metrics(sample=smp(not config.YOUTUBE_API_KEY))
        tr = collectors.collect_trends(sample=False if force_sample is None else force_sample)
        _store(yt, "youtube_metrics"); _store(tr, "trends_metrics"); did += ["youtube", "trends"]
    if source in ("customs", "all"):
        _store(collectors.collect_customs_export(sample=smp(not config.DATA_GO_KR_API_KEY)), "customs_export")
        did.append("customs")
    if source in ("tourism", "all"):
        _store(collectors.collect_tourism_supply(sample=smp(not config.DATA_GO_KR_API_KEY)), "tourism_supply")
        did.append("tourism")
    if source in ("kosis", "all"):
        _store(collectors.collect_kosis_industry(sample=smp(not config.KOSIS_API_KEY)), "kosis_industry")
        did.append("kosis")
    if source in ("kf", "all"):
        _store(collectors.collect_kf_metrics(sample=smp(not (config.KF_API_KEY and config.KF_API_URL))), "kf_metrics")
        did.append("kf")
    if source in ("survey", "all"):
        _store(collectors.load_survey_baseline(), "survey_baseline"); did.append("survey")
    print(f"[collect] {source}: {', '.join(did)} → raw + data/timeseries 누적")


def main() -> int:
    ap = argparse.ArgumentParser(description="KWCI 소스별 수집 (시계열 누적).")
    ap.add_argument("source", choices=["platform", "customs", "tourism", "kosis", "kf", "survey", "all"])
    ap.add_argument("--sample", action="store_true", help="강제 샘플 수집")
    args = ap.parse_args()
    collect(args.source, force_sample=True if args.sample else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
