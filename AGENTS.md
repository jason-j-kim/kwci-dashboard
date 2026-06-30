# KWCI (K-Wave Composite Index) — Agent Handoff / Context

> Codex/AI 에이전트가 이 저장소를 자동 이해하도록 돕는 컨텍스트 문서.
> 결정 근거는 DECISIONS.md, 외부 검토 요청 항목은 REVIEW_REQUEST.md 참조.

## 1. 개요
KWCI는 한류(K-wave)를 8개 산업 도메인 × 3개 자료 레이어로 측정해 분기 단위로 합산하는 종합 지수다.
- 라이브 대시보드: https://jason-j-kim.github.io/kwci-dashboard/
- 자동화: GitHub Actions(.github/workflows/update.yml) — on:push(kwci_pipeline/**) + 월 1회 cron + 수동(workflow_dispatch).

## 2. 측정 구조
- 8 도메인: kpop, kvideo, kgame, kwebtoon, kfood, kbeauty, kfashion, ktourism
- 3 레이어(가중): L1 경제 0.5 / L2 영향력 0.3 / L3 수용자 0.2 (결측 레이어는 남은 층으로 재정규화)
- L3 하위가중: KOFICE 설문 0.40 / YouTube 0.35 / Google Trends 0.25
- 산식:
  - DSI_i = Sum(w_L · L_norm) = 0.5·L1 + 0.3·L2 + 0.2·L3
  - KWCI   = Sum(w_i · DSI_i)
  - KWCI_index = (KWCI_t / KWCI_2018) × 100
- 도메인 가중 프로파일: industry / equal / two_axis_economic(alpha=0.6) / two_axis_cultural(alpha=0.4, 활성)

## 3. 정규화 두 체제 (중요)
- 시계열(history.json): 2018=100 기준연도 지수화 — "2018 대비 성장".
- 횡단(kwci_latest.json): 0~100 단면 정규화(base_year_indexed=false) — "같은 시점 국가 간 상대비교".
- 두 수치를 직접 비교하지 말 것.

## 4. 데이터 소스
- L1 경제:
  - 콘텐츠 4분야(kpop·kvideo·kgame·kwebtoon) = KOSIS 콘텐츠산업조사 수출 (orgId=113, tbl DT_113_STBL_1024776). 전국 단위 → 2018=100 history에만 반영(횡단 DSI 미반영).
  - kfood·kfashion·kbeauty = 관세청 무역통계(getNitemtradeList) HS코드 수출(가공식품·의류·화장품).
  - ktourism = KOSIS 국적·지역별 외국인 입국자 (orgId=111, tbl DT_091_111_2009_S005A, itm 13103870964T1) 2018–2024 실측 + 2025 공표연간.
- L2 영향력: KF 한류현황 API (확장 여지: Billboard/Spotify/Netflix/Steam).
- L3 수용자: KOFICE 해외한류실태조사(설문 baseline) · YouTube Data API v3 · Google Trends(pytrends). [Reddit 폐지]
- 시장 다변화(별도 항목, 종합지수 미편입): ENM = 1/HHI, HHI = Sum(share^2).
  - 관광 source-market: 국적 구성, 2018=100 시계열(history.json: tourism_diversification, tourism_shares).
  - 수용 audience: 분야별 국가 구성, KOFICE 설문 1차 기준(kwci_latest.json: audience_diversification).

## 5. 파일 지도
- kwci_pipeline/config.py — 도메인·가중치·국가(15)·HS·KOSIS 매핑·키 로딩
- kwci_pipeline/collectors.py — 소스별 수집기(youtube/trends/kf/customs/kosis/kto)
- kwci_pipeline/processor.py — DSI·KWCI·프로파일·audience 다변화·kwci_latest.json 출력
- kwci_pipeline/history.py — 2018=100 분기 시계열·관광(orgId=111)·관광 다변화·history.json 출력
- kwci_pipeline/momentum.py — 월간 나우캐스트(momentum_latest.json)
- kwci_pipeline/run_pipeline.py — 수집→산출 엔트리
- kwci_pipeline/check_apis.py — API 연결 진단
- index.html / script.js / styles.css — 대시보드(차트는 의존성 없는 커스텀 canvas)
- data/*.json — 산출물(대시보드가 읽음)
- .github/workflows/update.yml — 자동 실행/커밋

## 6. 실행
```
pip install pandas requests pytrends
python kwci_pipeline/run_pipeline.py
python kwci_pipeline/history.py
python kwci_pipeline/momentum.py
```
- 환경변수(Secrets): KOSIS_API_KEY, DATA_GO_KR_API_KEY, KF_API_URL, YOUTUBE_API_KEY.
- 키 결측/네트워크 실패 시 검증된 고정값(verified-fixed)으로 결정론적 폴백(sources 라벨로 정직하게 표기).

## 7. 저장소 외 산출물
- 학술 보고서·대시보드 해설서(.docx)는 로컬 작업폴더에만 있음(저장소 미포함). 필요 시 별도 공유.

## 8. 규약·주의
- 수치는 프로토타입. 절대값보다 구조·순위·추세로 해석.
- kwci_pipeline/** 커밋은 on:push로 자동 재배포됨(index.html 커밋은 GitHub Pages만 갱신).
- 알려진 한계: DECISIONS.md "Known limitations" 참조.
