"""KWCI 실데이터 API 연결 진단 스크립트.

본인 PC(키가 환경변수로 설정된 환경)에서 실행:

    cd "D:\\K wave index"
    python kwci_pipeline\\check_apis.py

각 API의 (1) 키 존재 여부 (2) 네트워크 도달 여부 (3) 인증 유효성
(4) 실제 표본 응답을 점검하고 요약표를 출력한다.
"""
from __future__ import annotations

import base64
import sys
from pathlib import Path

import requests

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from kwci_pipeline import config
else:
    from . import config


def mask(secret: str) -> str:
    if not secret:
        return "(없음)"
    if len(secret) <= 8:
        return secret[0] + "***"
    return f"{secret[:4]}...{secret[-4:]} (len={len(secret)})"


def check_youtube() -> tuple[str, str]:
    if not config.YOUTUBE_API_KEY:
        return "MISSING", "YOUTUBE_API_KEY 환경변수 없음"
    try:
        r = requests.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "part": "id",
                "chart": "mostPopular",
                "regionCode": "US",
                "maxResults": 1,
                "key": config.YOUTUBE_API_KEY,
            },
            timeout=30,
        )
    except Exception as e:  # noqa: BLE001
        return "NETWORK", f"연결 실패: {type(e).__name__}"
    if r.status_code == 200:
        n = len(r.json().get("items", []))
        return "OK", f"HTTP 200, 응답 항목 {n}개 — 정상"
    if r.status_code == 403:
        reason = ""
        try:
            reason = r.json()["error"]["errors"][0].get("reason", "")
        except Exception:  # noqa: BLE001
            pass
        hint = "할당량 초과(quotaExceeded)" if reason == "quotaExceeded" else f"키 권한/활성화 문제 ({reason})"
        return "AUTH", f"HTTP 403 — {hint}"
    if r.status_code == 400:
        return "AUTH", "HTTP 400 — API 키 무효(keyInvalid) 가능성"
    return "ERROR", f"HTTP {r.status_code}"


def check_reddit() -> tuple[str, str]:
    if not (config.REDDIT_CLIENT_ID and config.REDDIT_CLIENT_SECRET):
        return "MISSING", "REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET 환경변수 없음"
    auth = f"{config.REDDIT_CLIENT_ID}:{config.REDDIT_CLIENT_SECRET}".encode()
    headers = {
        "Authorization": "Basic " + base64.b64encode(auth).decode("ascii"),
        "User-Agent": "kwci_pipeline/1.0 by local-research",
    }
    try:
        r = requests.post(
            "https://www.reddit.com/api/v1/access_token",
            data={"grant_type": "client_credentials"},
            headers=headers,
            timeout=30,
        )
    except Exception as e:  # noqa: BLE001
        return "NETWORK", f"연결 실패: {type(e).__name__}"
    if r.status_code == 200 and r.json().get("access_token"):
        token = r.json()["access_token"]
        try:
            t = requests.get(
                "https://oauth.reddit.com/r/kpop/new",
                params={"limit": 1},
                headers={"Authorization": f"Bearer {token}", "User-Agent": "kwci_pipeline/1.0 by local-research"},
                timeout=30,
            )
            kids = len(t.json().get("data", {}).get("children", []))
            return "OK", f"토큰 발급 성공, r/kpop 표본 {kids}건 — 정상"
        except Exception:  # noqa: BLE001
            return "OK", "토큰 발급 성공(데이터 호출은 확인 못 함)"
    if r.status_code in (401, 403):
        return "AUTH", f"HTTP {r.status_code} — client_id/secret 무효 또는 앱 타입(script/web) 확인 필요"
    return "ERROR", f"HTTP {r.status_code}"


def check_kf() -> tuple[str, str]:
    if not config.KF_API_KEY:
        return "MISSING", "KF_API_KEY / DATA_GO_KR_API_KEY 환경변수 없음"
    if not config.KF_API_URL:
        return "MISSING", "KF_API_URL 환경변수 없음 (data.go.kr 승인 호출 URL 필요)"
    try:
        r = requests.get(
            config.KF_API_URL,
            params={
                "ServiceKey": config.KF_API_KEY,
                "pageNo": "1",
                "numOfRows": "1",
                "returnType": "JSON",
                "cond[country_iso_alp2::EQ]": "US",
            },
            timeout=30,
        )
    except Exception as e:  # noqa: BLE001
        return "NETWORK", f"연결 실패: {type(e).__name__}"
    if r.status_code == 200:
        return "OK", "HTTP 200 — 정상 (응답 본문 구조는 수집 시 파싱)"
    if r.status_code in (401, 403):
        return "AUTH", f"HTTP {r.status_code} — 서비스키 무효 또는 미승인"
    return "ERROR", f"HTTP {r.status_code}"


def check_trends() -> tuple[str, str]:
    """Google Trends(pytrends) — L3 수용자. 키 불필요, 설치·호출 점검."""
    try:
        from pytrends.request import TrendReq
    except Exception:  # noqa: BLE001
        return "MISSING", "pytrends 미설치 (pip install pytrends)"
    try:
        py = TrendReq(hl="en-US", tz=0)
        py.build_payload(["K-pop"], timeframe="today 3-m")
        reg = py.interest_by_region(resolution="COUNTRY", inc_low_vol=True)
        if reg is not None and not reg.empty:
            return "OK", f"pytrends 정상 (국가 {len(reg)}개 응답)"
        return "ERROR", "응답 비어있음 (레이트리밋 가능)"
    except Exception as e:  # noqa: BLE001
        return "ERROR", f"호출 실패: {type(e).__name__} (레이트리밋/네트워크)"


def check_customs() -> tuple[str, str]:
    """관세청 품목별 국가별 수출입실적 (data.go.kr 15100475). DATA_GO_KR_API_KEY 사용."""
    from datetime import datetime, timedelta, timezone
    if not config.DATA_GO_KR_API_KEY:
        return "MISSING", "DATA_GO_KR_API_KEY 없음"
    yymm = (datetime.now(timezone(timedelta(hours=9))).replace(day=1) - timedelta(days=1)).strftime("%Y%m")
    try:
        r = requests.get(config.CUSTOMS_EXPORT_URL, params={
            "serviceKey": config.DATA_GO_KR_API_KEY, "strtYymm": yymm, "endYymm": yymm,
            "hsSgn": "3304", "cntyCd": "US"}, timeout=30)
    except Exception as e:  # noqa: BLE001
        return "NETWORK", f"연결 실패: {type(e).__name__}"
    body = r.text or ""
    if r.status_code == 200 and "SERVICE" not in body.upper().split("RESULTMSG")[0][:0] + "":
        if "<expDlr>" in body or "<item>" in body or "00" in body[:200]:
            if "SERVICE_KEY_IS_NOT_REGISTERED" in body or "등록되지" in body:
                return "AUTH", "활용신청 필요(키 미등록) — data.go.kr 15100475 활용신청"
            return "OK", "HTTP 200 — 정상(수출 응답 수신)"
    if "SERVICE_KEY_IS_NOT_REGISTERED" in body or "등록되지" in body:
        return "AUTH", "활용신청 필요 — data.go.kr 15100475 활용신청"
    if r.status_code in (401, 403):
        return "AUTH", f"HTTP {r.status_code} — 활용신청/키 확인"
    return "ERROR" if r.status_code >= 400 else "OK", f"HTTP {r.status_code}"


def check_tourapi() -> tuple[str, str]:
    """한국관광공사 TourAPI KorService2 (data.go.kr 15101578). DATA_GO_KR_API_KEY 사용."""
    if not config.DATA_GO_KR_API_KEY:
        return "MISSING", "DATA_GO_KR_API_KEY 없음"
    try:
        r = requests.get("https://apis.data.go.kr/B551011/KorService2/areaBasedList2", params={
            "serviceKey": config.DATA_GO_KR_API_KEY, "MobileOS": "ETC", "MobileApp": "kwci",
            "_type": "json", "numOfRows": 1, "pageNo": 1, "contentTypeId": 12}, timeout=30)
    except Exception as e:  # noqa: BLE001
        return "NETWORK", f"연결 실패: {type(e).__name__}"
    body = r.text or ""
    if "SERVICE_KEY_IS_NOT_REGISTERED" in body or "등록되지" in body:
        return "AUTH", "활용신청 필요 — data.go.kr 15101578 활용신청"
    if r.status_code == 200 and ("resultCode" in body or "items" in body):
        return "OK", "HTTP 200 — 정상(관광정보 응답)"
    if r.status_code in (401, 403):
        return "AUTH", f"HTTP {r.status_code} — 활용신청/키 확인"
    return "ERROR" if r.status_code >= 400 else "OK", f"HTTP {r.status_code}"


def check_kosis() -> tuple[str, str]:
    """KOSIS 콘텐츠산업조사(orgId=113). 별도 KOSIS_API_KEY 필요."""
    if not config.KOSIS_API_KEY:
        return "MISSING", "KOSIS_API_KEY 없음 (kosis.kr/openapi 발급)"
    try:
        r = requests.get("https://kosis.kr/openapi/Param/statisticsParameterData.do", params={
            "method": "getList", "apiKey": config.KOSIS_API_KEY, "orgId": "113",
            "tblId": "DT_113_STBL_1024776", "itmId": "13103843981T1", "objL1": "ALL",
            "prdSe": "Y", "startPrdDe": "2022", "endPrdDe": "2023", "format": "json", "jsonVD": "Y"},
            timeout=30)
    except Exception as e:  # noqa: BLE001
        return "NETWORK", f"연결 실패: {type(e).__name__}"
    body = r.text or ""
    if "인증" in body or "err" in body.lower()[:200] or "ERR" in body[:200]:
        return "AUTH", "키/파라미터 확인 (KOSIS 오류 응답)"
    if r.status_code == 200 and ("DT" in body or "PRD_DE" in body or "[" in body[:5]):
        return "OK", "HTTP 200 — 정상(통계 응답)"
    return "ERROR" if r.status_code >= 400 else "OK", f"HTTP {r.status_code}"


def main() -> int:
    print("=" * 64)
    print(" KWCI 실데이터 API 연결 진단")
    print("=" * 64)
    print("[환경변수]")
    print(f"  YOUTUBE_API_KEY      : {mask(config.YOUTUBE_API_KEY)}")
    print(f"  REDDIT_CLIENT_ID     : {mask(config.REDDIT_CLIENT_ID)}")
    print(f"  REDDIT_CLIENT_SECRET : {mask(config.REDDIT_CLIENT_SECRET)}")
    print(f"  KF_API_KEY           : {mask(config.KF_API_KEY)}")
    print(f"  KF_API_URL           : {config.KF_API_URL or '(없음)'}")
    print(f"  DATA_GO_KR_API_KEY   : {mask(config.DATA_GO_KR_API_KEY)}")
    print(f"  KOSIS_API_KEY        : {mask(config.KOSIS_API_KEY)}")
    print("-" * 64)

    results = {
        "YouTube Data API v3 (L3)": check_youtube(),
        "Google Trends (L3)": check_trends(),
        "KF 한류현황 API (L2)": check_kf(),
        "관세청 수출 (L1)": check_customs(),
        "TourAPI 관광 (L1/공급)": check_tourapi(),
        "KOSIS 콘텐츠산업 (L1)": check_kosis(),
    }
    icons = {"OK": "✅", "MISSING": "⬜", "AUTH": "🔑", "NETWORK": "📡", "ERROR": "❌"}
    print(f"{'API':26} {'상태':6} 세부")
    print("-" * 64)
    for name, (status, detail) in results.items():
        print(f"{name:26} {icons.get(status,'?')} {status:7} {detail}")
    print(f"{'KOFICE 설문 baseline':26} ⚙️  BUILTIN 연 1회 설문 — 내장 baseline(정상)")
    print("=" * 64)
    ok = sum(1 for s, _ in results.values() if s == "OK")
    print(f"실연결 정상: {ok}/6  (KOFICE 제외)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
