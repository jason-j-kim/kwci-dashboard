# 외부 검토 요청 (REVIEW_REQUEST) — for Codex / 객관적 평가

> 이 저장소(KWCI)의 1차 완성본에 대한 **객관적 평가**를 요청합니다.
> 먼저 AGENTS.md(구조)와 DECISIONS.md(결정 근거)를 읽고, 아래 항목을 비판적으로 검토해 주세요.
> 산출물은 (1) 항목별 평가 + 근거, (2) 발견한 오류/버그 목록, (3) 우선순위가 매겨진 개선 제안으로 정리해 주세요.

## A. 방법론 타당성
1. 레이어 가중(L1 0.5 / L2 0.3 / L3 0.2)과 결측 재정규화 규칙이 합리적인가? 민감도는?
2. 도메인 가중 프로파일(industry/equal/economic α0.6/cultural α0.4)의 설계와 활성 선택(문화중심)이 타당한가?
3. DSI→KWCI 합성에서 누락/이중계산/단위 불일치는 없는가?

## B. 정규화
4. 시계열 2018=100 vs 횡단 0~100 **이중 체제**가 개념적으로 건전한가? 사용자 혼동 위험과 표기 방식은 충분한가?
5. Min-Max 단일창 정규화의 극단값 취약성 — 백분위/Z-score 대안의 필요성?

## C. 데이터 신뢰성·소스 적합성
6. 소스 매핑이 측정 목적에 맞는가?
   - KOSIS 콘텐츠산업조사(orgId=113) → kpop/kvideo/kgame/kwebtoon
   - 관세청 HS → kfood(가공식품)/kfashion(의류)/kbeauty(화장품)
   - KOSIS 국적별 입국자(orgId=111, DT_091_111_2009_S005A) → ktourism
   - KOFICE/YouTube/Google Trends → L3, KF → L2
7. 콘텐츠 4분야의 **국가별 L1 부재**(전국 단위만)가 횡단 국가 비교를 왜곡하지 않는가? 보완책?
8. 플랫폼 편향(중국·러시아 YouTube/Trends 차단)에 대한 보정이 충분한가?
9. 저(低)베이스 효과(특히 K웹툰 2018) 처리와 '만화 수출' 정의의 적절성?
10. verified-fixed 폴백이 결과의 신뢰성·재현성에 주는 영향?

## D. 다변화 지수
11. ENM=1/HHI 산식과 해석(관광 source-market, 수용 audience)이 올바른가?
12. 수용 다변화의 KOFICE 1차 기준 채택이 YouTube 단면 왜곡을 적절히 회피하는가? 표본·연 1회 한계는?
13. 다변화를 종합지수에 **편입하지 않고 별도 항목**으로 둔 선택이 타당한가, 아니면 가중 편입이 나은가?

## E. 재현성·엔지니어링
14. 파이프라인(run_pipeline/history/momentum)이 키만 있으면 결정론적으로 재현되는가?
15. 코드 품질·구조·버그·예외처리·테스트 부재 점검.
16. GitHub Actions 자동화(on:push/cron/폴백)의 견고성.

## F. 종합
17. 학술/정책 인용 가능 수준인가? 가장 시급한 보완 3가지는?
18. 지수 설계 전반에 대한 대안적 접근(있다면).

## 참고 산출물
- 라이브 대시보드: https://jason-j-kim.github.io/kwci-dashboard/
- 데이터: data/history.json(2018=100 시계열), data/kwci_latest.json(횡단), data/momentum_latest.json
- 학술 보고서·해설서 .docx는 별도 보관(요청 시 공유).
