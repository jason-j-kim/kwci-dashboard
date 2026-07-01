// KWCI 대시보드 — 8개 산업 분야 × L1/L2/L3 DSI 모델 (프레임워크 기준)
// 도메인 정의는 정적, 수치(DSI·KWCI·국가순위·가중치 프로파일)는 data/kwci_latest.json에서 읽어 덮어쓴다.

const domains = [
  {
    id: "kpop", name: "K-pop", weight: 0.20, dsi: 43, color: "#1d5fd1",
    summary: "음반 수출과 글로벌 차트·스트리밍, YouTube/SNS 반응을 결합한 대표 한류 분야.",
    sources: ["관세청 HS8523", "KOCCA·DART", "Billboard/Luminate", "Spotify Charts", "YouTube Data API", "Google Trends"],
    indicators: {
      "L1 경제": ["음반 수출액(HS 8523)", "해외 스트리밍·엔터 매출(KOCCA·DART)"],
      "L2 영향력": ["Billboard Hot100·Global200 성과", "Spotify Global Top200 스트림"],
      "L3 수용자": ["KOFICE 설문 기준선", "YouTube 한국음악 글로벌 조회수", "Google Trends 검색 관심도"]
    }
  },
  {
    id: "kvideo", name: "K영상", weight: 0.18, dsi: 43, color: "#d8426b",
    summary: "드라마·영화 통합. 방송/영화 수출, OTT 랭킹, 글로벌 평점과 반응을 추적.",
    sources: ["KOCCA", "KOFIC", "Netflix Top10 CSV", "IMDb TSV", "Google Trends", "X API"],
    indicators: {
      "L1 경제": ["방송콘텐츠 수출액(KOCCA)", "영화 완성작·서비스 수출(KOFIC)", "OTT 라이선싱 계약액"],
      "L2 영향력": ["Netflix 글로벌 Top10 체류주수", "IMDb 8.0+ 한국작 평점·투표"],
      "L3 수용자": ["YouTube 예고편 글로벌 조회수", "Google Trends·X 해시태그"]
    }
  },
  {
    id: "kgame", name: "K게임", weight: 0.16, dsi: 43, color: "#7a3ff2",
    summary: "게임 수출·산업 매출과 Steam 이용지표, 수상·검색 반응을 결합.",
    sources: ["KOCCA 게임백서", "KOSIS", "Steam Web API", "The Game Awards", "Google Trends"],
    indicators: {
      "L1 경제": ["게임 수출액(KOCCA)", "게임산업 매출(KOSIS)"],
      "L2 영향력": ["Steam 동시접속·리뷰(한국 게임)", "The Game Awards 노미·수상"],
      "L3 수용자": ["KOFICE 설문 기준선", "YouTube 게임 영상 조회수", "Google Trends 한국 게임명"]
    }
  },
  {
    id: "kwebtoon", name: "K웹툰", weight: 0.10, dsi: 42, color: "#e07b1a",
    summary: "만화·웹툰 수출과 글로벌 플랫폼 확산, 영상화 IP, 커뮤니티 담론.",
    sources: ["KOCCA 만화백서", "KOSIS", "WEBTOON/Tapas", "공공데이터포털", "Google Trends"],
    indicators: {
      "L1 경제": ["만화·웹툰 수출액(KOCCA)", "산업 매출(KOSIS)"],
      "L2 영향력": ["글로벌 플랫폼 MAU·영상화 IP", "공공저작물 웹툰 목록"],
      "L3 수용자": ["Google Trends webtoon/manhwa", "r/webtoons 등 커뮤니티"]
    }
  },
  {
    id: "kfood", name: "K푸드", weight: 0.10, dsi: 43, color: "#3b8b4f",
    summary: "식품 수출과 해외 레스토랑·미디어·커뮤니티 반응으로 식문화 파급을 측정.",
    sources: ["관세청 HS", "KOFICE", "KF API", "YouTube Data API", "Google Trends"],
    indicators: {
      "L1 경제": ["농수산식품 수출액(aT)", "품목별 수출(라면·김치·소스·김, 관세청 HS)"],
      "L2 영향력": ["Michelin 선정·미디어 기사", "Yelp/Google 한식당 도시별 신규등록"],
      "L3 수용자": ["YouTube 먹방·TikTok #kfood", "Google Trends·r/KoreanFood"]
    }
  },
  {
    id: "kfashion", name: "K패션", weight: 0.08, dsi: 43, color: "#c0398a",
    summary: "의류·섬유 수출과 글로벌 런웨이·플랫폼 노출, SNS 확산을 추적.",
    sources: ["관세청 HS61·62", "KOSIS·섬산련", "패션위크", "무신사", "TikTok", "Google Trends"],
    indicators: {
      "L1 경제": ["의류·섬유 수출액(관세청 HS61/62)", "패션·섬유산업 매출"],
      "L2 영향력": ["글로벌 패션위크 한국 디자이너·패션지", "무신사 글로벌 등 플랫폼 지표"],
      "L3 수용자": ["TikTok #koreanfashion 재생수", "Google Trends Korean fashion"]
    }
  },
  {
    id: "kbeauty", name: "K뷰티", weight: 0.10, dsi: 43, color: "#008c88",
    summary: "화장품 수출과 글로벌 유통·미디어, K-beauty 담론 확산을 생활문화 지표로.",
    sources: ["관세청 HS33", "Sephora/Amazon", "글로벌 뷰티지", "TikTok/YouTube", "Google Trends"],
    indicators: {
      "L1 경제": ["화장품 수출액(HS 33류)", "국가별 수출 점유율"],
      "L2 영향력": ["Sephora/Ulta/Amazon K-beauty SKU·순위", "Allure/Vogue 특집 기사"],
      "L3 수용자": ["TikTok #kbeauty·YouTube 튜토리얼", "Google Trends Korean skincare"]
    }
  },
  {
    id: "ktourism", name: "K관광", weight: 0.08, dsi: 43, color: "#2aa6c4",
    summary: "방한 관광 수요와 인지도·인프라, 검색 반응으로 한류 관광을 측정.",
    sources: ["한국관광공사 KTO", "data.go.kr", "TripAdvisor/UNWTO", "TourAPI", "Google Trends"],
    indicators: {
      "L1 경제": ["방한 외래관광객 수(KTO)", "한류동기 방문객 비율"],
      "L2 영향력": ["TripAdvisor 순위·UNWTO TTDI", "관광지·숙박 인프라(TourAPI)"],
      "L3 수용자": ["Google Trends visit Korea·Seoul", "Booking/Airbnb 검색지수"]
    }
  }
];

const sourceGroups = [
  { title: "공공 API", items: ["관세청 UNI-PASS·품목별국가별 수출입실적", "KOSIS 콘텐츠산업조사", "한국관광공사 TourAPI / KTO 관광통계", "KF 한류현황 API"] },
  { title: "상업·플랫폼 API", items: ["YouTube Data API v3", "Google Trends(pytrends)", "확장 후보: Billboard·Spotify·Netflix·Steam"] },
  { title: "비공식·수동 수집", items: ["pytrends (Google Trends)", "TikTok Research / Amazon PA API", "시상식·영화제·패션위크 결과", "미디어 모니터링 아카이브"] }
];

const PROFILE_LABELS = {
  industry: "산업규모안",
  equal: "동일배분",
  two_axis_economic: "경제중심(α=0.6)",
  two_axis_cultural: "문화중심(α=0.4)"
};

const tabs = document.querySelector(".tabs");
const detail = document.querySelector(".domain-detail");
const weightList = document.querySelector(".weight-list");
const sourceGrid = document.querySelector(".source-grid");
const weightProfileSelect = document.querySelector("#weightProfileSelect");
const kwciValue = document.querySelector("#kwciValue");
const canvas = document.querySelector("#barChart");
const ctx = canvas.getContext("2d");
const l2Latest = document.querySelector("#l2Latest");

let selected = domains[0].id;
let latest = null; // kwci_latest.json payload
let historyData = null; // history.json payload (2018=100)

function getWeight(domain) {
  const profile = selectedWeightProfile();
  const profileWeights = latest?.weight_profiles?.[profile]?.weights;
  const directWeights = profile === latest?.active_weight_profile ? latest?.domain_weights : null;
  return Number(profileWeights?.[domain.id] ?? directWeights?.[domain.id] ?? domain.weight);
}

function activeWeightProfile() {
  return latest?.active_weight_profile || "industry";
}

function selectedWeightProfile() {
  const value = weightProfileSelect?.value || "active";
  return value === "active" ? activeWeightProfile() : value;
}

function renderTabs() {
  tabs.innerHTML = domains.map((domain) => `
    <button type="button" role="tab" aria-selected="${domain.id === selected}" data-id="${domain.id}">
      ${domain.name}
    </button>
  `).join("");
}

function renderDetail() {
  const domain = domains.find((item) => item.id === selected);
  const selectedProfile = selectedWeightProfile();
  detail.innerHTML = `
    <div class="domain-kicker">
      <span class="pill">${PROFILE_LABELS[selectedProfile] || selectedProfile} ${(getWeight(domain) * 100).toFixed(1)}%</span>
      <span class="pill">현재 지수 ${domain.dsi} (2018=100)</span>
      <span class="pill">분기 패널</span>
    </div>
    <h3>${domain.name}</h3>
    <p>${domain.summary}</p>
    <p><b>핵심 소스:</b> ${domain.sources.join(" · ")}</p>
    <div class="indicator-grid">
      ${Object.entries(domain.indicators).map(([layer, items]) => `
        <article>
          <h4>${layer}</h4>
          <ul>${items.map((item) => `<li>${item}</li>`).join("")}</ul>
        </article>
      `).join("")}
    </div>
  `;
}

function renderWeights() {
  const total = domains.reduce((sum, domain) => sum + getWeight(domain), 0);
  const profile = selectedWeightProfile();
  const active = activeWeightProfile();
  const label = PROFILE_LABELS[profile] || profile;
  const activeLabel = PROFILE_LABELS[active] || active;
  const mode = profile === active ? "활성" : "비교";
  weightList.innerHTML = `<p class="muted-line">${mode} 프로파일: <b>${label}</b>${profile !== active ? ` · 활성 ${activeLabel}` : ""}</p>` + domains.map((domain) => {
    const adjusted = getWeight(domain) / total;
    const industry = Number(domain.industryWeight ?? domain.weight);
    const industryText = profile !== "industry" ? `<small>산업기본 ${(industry * 100).toFixed(1)}%</small>` : "";
    return `
      <div class="weight-row">
        <header><span>${domain.name}</span><span>${(adjusted * 100).toFixed(1)}%</span></header>
        <div class="bar"><span style="width:${adjusted * 100}%; background:${domain.color}"></span></div>
        ${industryText}
      </div>
    `;
  }).join("");
}

function renderSources() {
  sourceGrid.innerHTML = sourceGroups.map((group) => `
    <article>
      <h3>${group.title}</h3>
      <ul>${group.items.map((item) => `<li>${item}</li>`).join("")}</ul>
    </article>
  `).join("");
}

function computeKwci() {
  const total = domains.reduce((sum, domain) => sum + getWeight(domain), 0);
  return domains.reduce((sum, domain) => sum + domain.dsi * (getWeight(domain) / total), 0);
}

function headlineKwci() {
  if (historyData && historyData.composite && historyData.composite.length) {
    return historyData.composite[historyData.composite.length - 1];
  }
  if (latest && latest.global && typeof latest.global.global_index === "number") {
    return latest.global.global_index;
  }
  return computeKwci();
}

function drawChart() {
  const ratio = window.devicePixelRatio || 1;
  const box = canvas.getBoundingClientRect();
  canvas.width = box.width * ratio;
  canvas.height = Math.max(box.height, 280) * ratio;
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);

  const width = box.width;
  const height = Math.max(box.height, 280);
  ctx.clearRect(0, 0, width, height);

  const padding = { top: 30, right: 24, bottom: 72, left: 46 };
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;
  const barW = chartW / domains.length * 0.58;

  ctx.strokeStyle = "#d9e0e8";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(padding.left, padding.top);
  ctx.lineTo(padding.left, padding.top + chartH);
  ctx.lineTo(padding.left + chartW, padding.top + chartH);
  ctx.stroke();

  const yMax = Math.max(100, Math.ceil(Math.max(...domains.map((d) => d.dsi)) / 100) * 100);
  ctx.fillStyle = "#657080";
  ctx.font = "12px Segoe UI, sans-serif";
  [0, 0.25, 0.5, 0.75, 1].map((f) => Math.round(yMax * f)).forEach((tick) => {
    const y = padding.top + chartH - chartH * tick / yMax;
    ctx.fillText(String(tick), 10, y + 4);
    ctx.strokeStyle = tick === 0 ? "#d9e0e8" : "#eef2f6";
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(padding.left + chartW, y);
    ctx.stroke();
  });

  domains.forEach((domain, index) => {
    const x = padding.left + index * (chartW / domains.length) + (chartW / domains.length - barW) / 2;
    const barH = chartH * domain.dsi / yMax;
    const y = padding.top + chartH - barH;
    ctx.fillStyle = domain.color;
    ctx.fillRect(x, y, barW, barH);

    ctx.fillStyle = "#17202a";
    ctx.font = "700 12px Segoe UI, sans-serif";
    ctx.fillText(domain.dsi, x + barW / 2 - 8, y - 8);

    ctx.save();
    ctx.translate(x + barW / 2, padding.top + chartH + 16);
    ctx.rotate(-Math.PI / 5);
    ctx.fillStyle = "#405064";
    ctx.font = "12px Segoe UI, sans-serif";
    ctx.fillText(domain.name, -4, 0);
    ctx.restore();
  });
}

function renderDashboard() {
  const v = headlineKwci().toFixed(1);
  kwciValue.textContent = v;
  const hero = document.querySelector("#heroKwci");
  if (hero) hero.textContent = v;
  drawChart();
}

function applyLatest(payload) {
  latest = payload;
  const active = payload.domain_weights || {};
  const industryRows = {};
  (payload.domains || []).forEach((row) => {
    industryRows[row.genre] = row.industry_weight ?? row.domain_weight;
  });
  domains.forEach((domain) => {
    if (active[domain.id] != null) domain.weight = Number(active[domain.id]);
    if (industryRows[domain.id] != null) domain.industryWeight = Number(industryRows[domain.id]);
  });
  if (weightProfileSelect) {
    const activeOption = weightProfileSelect.querySelector('option[value="active"]');
    const activeLabel = PROFILE_LABELS[activeWeightProfile()] || activeWeightProfile();
    if (activeOption) activeOption.textContent = `활성: ${activeLabel}`;
    weightProfileSelect.value = "active";
  }
  // 막대·헤드라인은 history(2018=100)에서 채운다. 여기선 국가 패널과 가중치 프로파일을 사용.
}

function renderLatestPanel() {
  if (!l2Latest) return;
  if (!latest) {
    l2Latest.textContent = "파이프라인 실행 후 data/kwci_latest.json을 읽어 국가별 KWCI·분야 DSI·가중치 프로파일을 표시합니다.";
    return;
  }
  const rows = (latest.countries || latest.top || []).slice(0, 8);
  const g = latest.global || {};
  const profiles = latest.weight_profiles || {};
  const profLine = Object.entries(profiles).map(([k, v]) =>
    `${PROFILE_LABELS[k] || k} ${v.global_mean}`).join(" · ");
  l2Latest.innerHTML = `
    <div class="latest-headline">
      <span>국가 간 평균 (상대 0~100)</span>
      <strong>${g.global_index ?? "-"}</strong>
      <span class="muted-line">단순평균 ${g.global_index_mean ?? "-"} · 인구가중 ${g.global_index_pop_weighted ?? "-"} · 현재 단면</span>
    </div>
    <div class="latest-table">
      <div class="latest-row">
        <span>국가</span><span>KWCI</span><span>점수</span><span>YouTube</span><span>Trends</span>
      </div>
      ${rows.map((row) => `
        <div class="latest-row">
          <span>${row.country_name || row.country}</span>
          <span class="latest-score" style="--v:${Math.min(row.kwci, 100)}%"></span>
          <span>${Number(row.kwci).toFixed(2)}</span>
          <span>${Number(row.youtube_views || 0).toLocaleString()}</span>
          <span>${Number(row.trends_interest || 0).toFixed(1)}</span>
        </div>
      `).join("")}
    </div>
    ${profLine ? `<p class="muted-line">가중치 프로파일별 글로벌 평균 — ${profLine}</p>` : ""}
    <p class="muted-line">${latest.date} · ${latest.layer_structure || latest.framework || ""} · 활성 ${PROFILE_LABELS[latest.active_weight_profile] || latest.active_weight_profile || ""}</p>
  `;
}

function renderAll() {
  renderTabs();
  renderDetail();
  renderWeights();
  renderSources();
  renderDashboard();
}

async function loadLatest() {
  try {
    const response = await fetch("kwci_latest.json", { cache: "no-store" });
    if (!response.ok) throw new Error("missing latest file");
    applyLatest(await response.json());
    renderAll();
  } catch (error) {
    // 실데이터 없으면 정적 샘플 유지
  }
  renderLatestPanel();
}

tabs.addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  selected = button.dataset.id;
  renderAll();
});

weightProfileSelect?.addEventListener("change", renderAll);
window.addEventListener("resize", drawChart);

function drawLineChart(canvas, labels, series) {
  const ratio = window.devicePixelRatio || 1;
  const box = canvas.getBoundingClientRect();
  const W = box.width || 620, H = Math.max(box.height, 320);
  canvas.width = W * ratio; canvas.height = H * ratio;
  const c = canvas.getContext("2d"); c.setTransform(ratio, 0, 0, ratio, 0, 0);
  c.clearRect(0, 0, W, H);
  const pad = { t: 16, r: 14, b: 48, l: 44 };
  const cw = W - pad.l - pad.r, ch = H - pad.t - pad.b;
  let mx = 0; series.forEach(s => s.data.forEach(v => { if (v > mx) mx = v; }));
  mx = Math.ceil(mx / 50) * 50 || 100;
  const n = labels.length;
  c.font = "11px Segoe UI, sans-serif";
  const tick = Math.max(50, Math.round(mx / 4 / 50) * 50);
  for (let t = 0; t <= mx; t += tick) {
    const y = pad.t + ch - ch * t / mx;
    c.strokeStyle = t === 0 ? "#d9e0e8" : "#eef2f6";
    c.beginPath(); c.moveTo(pad.l, y); c.lineTo(pad.l + cw, y); c.stroke();
    c.fillStyle = "#657080"; c.fillText(String(t), 8, y + 4);
  }
  const step = Math.ceil(n / 8);
  c.fillStyle = "#405064";
  labels.forEach((lb, i) => {
    if (i % step === 0 || i === n - 1) {
      const x = pad.l + cw * (i / (n - 1 || 1));
      c.save(); c.translate(x, pad.t + ch + 14); c.rotate(-Math.PI / 6); c.fillText(lb, -12, 0); c.restore();
    }
  });
  series.forEach(s => {
    c.strokeStyle = s.color; c.lineWidth = s.width || 1.4; c.beginPath();
    s.data.forEach((v, i) => {
      const x = pad.l + cw * (i / (n - 1 || 1)); const y = pad.t + ch - ch * v / mx;
      i ? c.lineTo(x, y) : c.moveTo(x, y);
    });
    c.stroke();
  });
}

async function loadHistory() {
  try {
    const res = await fetch("history.json", { cache: "no-store" });
    if (!res.ok) throw new Error();
    const h = await res.json();
    historyData = h;
    const last = h.quarters.length - 1;
    domains.forEach((d) => { if (h.domains[d.id]) d.dsi = h.domains[d.id][last]; });
    renderDashboard();
    renderDetail();
    const cv = document.querySelector("#historyChart");
    if (cv) {
      const colorOf = id => (domains.find(d => d.id === id) || {}).color || "#888";
      const series = [{ name: "종합", color: "#17202a", width: 3, data: h.composite }];
      Object.keys(h.domains).forEach(g => series.push({ name: h.domain_names[g], color: colorOf(g), width: 1.3, data: h.domains[g] }));
      drawLineChart(cv, h.quarters, series);
      document.querySelector("#historyLegend").innerHTML = series.map(s =>
        `<span class="lg"><i style="background:${s.color}"></i>${s.name}</span>`).join("");
      document.querySelector("#historyNote").textContent = `${h.note} · 활성 ${h.weight_profile}`;
    }
  } catch (e) {
    const n = document.querySelector("#historyNote");
    if (n) n.textContent = "history.json 생성 후 표시됩니다 (python kwci_pipeline/history.py).";
  }
}

async function loadMomentum() {
  const el = document.querySelector("#momentumPanel"); if (!el) return;
  try {
    const res = await fetch("momentum_latest.json", { cache: "no-store" });
    if (!res.ok) throw new Error();
    const m = await res.json();
    const rows = (m.countries || m.top || []).slice(0, 8);
    el.innerHTML = `<div class="latest-headline"><span>${m.period} 글로벌 모멘텀</span>` +
      `<strong>${m.global_momentum}</strong><span class="muted-line">${m.layers}</span></div>` +
      `<div class="latest-table">${rows.map(r =>
        `<div class="latest-row mom"><span>${r.country_name || r.country}</span>` +
        `<span class="latest-score" style="--v:${Math.min(r.momentum, 100)}%"></span>` +
        `<span>${Number(r.momentum).toFixed(1)}</span></div>`).join("")}</div>`;
  } catch (e) {
    el.textContent = "data/momentum_latest.json 생성 후 표시됩니다 (python kwci_pipeline/momentum.py).";
  }
}

renderAll();
loadLatest();
loadHistory();
loadMomentum();
