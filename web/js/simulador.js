/**
 * Simulador Imobiliário DV — paridade completa com Streamlit (app.py).
 */
import { apiGet, apiPost, apiPatch, apiPut, apiDelete } from "./api.js";
import { ensureChartLibs, ensureLeaflet } from "./lib/asset-loaders.js";
import { scheduleIdle } from "./lib/idle.js";
import { renderStepper, showStepSection, shouldHideStepper, STEPS } from "./stepper.js";

const $ = (id) => document.getElementById(id);
const fmtBR = (v) => {
  const n = Number(v);
  if (isNaN(n)) return "0,00";
  return n.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

function showMsg(el, text, ok = true) {
  if (!el) return;
  el.textContent = text;
  el.style.color = ok ? "var(--cor-azul-esc)" : "var(--cor-vermelho)";
}

/* ---------- Rendas dinâmicas ---------- */
function renderRendasInputs(n, values) {
  const host = $("rendas-extra");
  if (!host) return;
  host.innerHTML = "";
  const q = Math.min(4, Math.max(1, parseInt(n, 10) || 1));
  for (let i = 0; i < q; i++) {
    const lab = document.createElement("label");
    lab.textContent = `Renda Part. ${i + 1} (R$)`;
    const inp = document.createElement("input");
    inp.type = "number";
    inp.name = `renda_${i}`;
    inp.className = "input-field";
    inp.step = "100";
    inp.min = "0";
    inp.placeholder = "0,00";
    const def = values && values[i] != null ? values[i] : (i === 0 ? 3500 : 0);
    inp.value = def || "";
    lab.appendChild(inp);
    host.appendChild(lab);
  }
}

/* ---------- CPF mask + validation ---------- */
function maskCpfInput(ev) {
  const v = ev.target.value.replace(/\D/g, "").slice(0, 11);
  let out = "";
  if (v.length > 0) out += v.slice(0, 3);
  if (v.length > 3) out += "." + v.slice(3, 6);
  if (v.length > 6) out += "." + v.slice(6, 9);
  if (v.length > 9) out += "-" + v.slice(9, 11);
  ev.target.value = out;
}
$("input-cpf")?.addEventListener("input", maskCpfInput);

function validarCPF(cpf) {
  const nums = cpf.replace(/\D/g, "");
  if (nums.length !== 11) return false;
  if (/^(\d)\1{10}$/.test(nums)) return false;
  let soma = 0;
  for (let i = 0; i < 9; i++) soma += parseInt(nums[i]) * (10 - i);
  let d1 = 11 - (soma % 11);
  if (d1 >= 10) d1 = 0;
  if (parseInt(nums[9]) !== d1) return false;
  soma = 0;
  for (let i = 0; i < 10; i++) soma += parseInt(nums[i]) * (11 - i);
  let d2 = 11 - (soma % 11);
  if (d2 >= 10) d2 = 0;
  return parseInt(nums[10]) === d2;
}

/* ================================================================
   SPA NAVIGATION
   ================================================================ */
let _currentPage = "home";

/** Evita recarregar dados pesados do mesmo passo após refreshUI repetido sem sair do wizard */
let _lastHeavyPassoLoaded = null;

const NAV_DEBOUNCE_MS = 360;
let _navBusy = false;
let _lastNavAt = 0;

/** Cache de listas para abrir detalhe por id; ADM edita a partir destes objetos */
const _conteudoListCache = { campanhas: [], treinamentos: [] };
let _conteudoDetalheTipo = "campanhas";
let _conteudoDetalheItem = null;

/**
 * Única função que altera visibilidade das vistas principais (home, wizard, campanhas, etc.).
 * Ao esconder o wizard, liberta mapas/iframes da galeria.
 */
function setAppView(page) {
  _currentPage = page;
  const homeEl = $("home-section");
  const wizardEl = $("wizard-wrap");
  const campEl = $("campanhas-section");
  const treinEl = $("treinamentos-section");
  const detEl = $("conteudo-detalhe-section");
  const navbar = $("navbar");
  if (!homeEl || !wizardEl) return;

  const hideWizard =
    page === "home" || page === "campanhas" || page === "treinamentos" || page === "conteudo_detalhe";
  if (hideWizard) {
    destroyGalleryResources();
    _lastHeavyPassoLoaded = null;
  }

  if (navbar) {
    if (page === "home") navbar.classList.add("navbar-home");
    else navbar.classList.remove("navbar-home");
  }

  homeEl.classList.toggle("home-active", page === "home");
  homeEl.style.display = page === "home" ? "" : "none";
  wizardEl.classList.toggle("hidden", hideWizard);
  if (campEl) campEl.style.display = page === "campanhas" ? "" : "none";
  if (treinEl) treinEl.style.display = page === "treinamentos" ? "" : "none";
  if (detEl) detEl.style.display = page === "conteudo_detalhe" ? "" : "none";

  if (page === "campanhas") loadCampanhas();
  if (page === "treinamentos") loadTreinamentos();
  if (page === "conteudo_detalhe") renderConteudoDetalhe();

  updateNavHighlight(page);
}

function loadPage(page) {
  setAppView(page);
}

async function withTopNavGuard(fn) {
  const now = Date.now();
  if (_navBusy || now - _lastNavAt < NAV_DEBOUNCE_MS) return;
  _lastNavAt = now;
  _navBusy = true;
  try {
    await fn();
  } catch (e) {
    console.warn("[nav]", e);
  } finally {
    _navBusy = false;
  }
}

/** Simulador na navbar: se estava em galeria ou analytics, volta ao passo `input`. */
async function navigateToSimuladorFromNav() {
  await withTopNavGuard(async () => {
    let st;
    try {
      st = await apiGet("/api/session");
    } catch {
      return;
    }
    const p = st.passo_simulacao;
    if (p === "gallery" || p === "client_analytics") {
      await apiPatch("/api/session", { passo_simulacao: "input" });
    }
    setAppView("simulador");
    await refreshUI();
  });
}

function updateNavHighlight(page) {
  const sim = $("nav-simulador");
  const gal = $("nav-galeria");
  const camp = $("nav-campanhas");
  const trein = $("nav-treinamentos");

  [sim, gal, camp, trein].forEach((el) => el?.classList.remove("active"));

  if (page === "gallery" || page === "galeria") gal?.classList.add("active");
  else if (page === "campanhas") camp?.classList.add("active");
  else if (page === "treinamentos") trein?.classList.add("active");
  else if (page === "conteudo_detalhe") {
    if (_conteudoDetalheTipo === "treinamentos") trein?.classList.add("active");
    else camp?.classList.add("active");
  } else if (page !== "home") sim?.classList.add("active");

  updateNavIndicator();
}

function updateNavIndicator() {
  const indicator = $("navActiveIndicator");
  const wrapper = document.querySelector(".nav-links-wrapper");
  if (!indicator || !wrapper) return;

  const activeLink = wrapper.querySelector(".nav-link-item.active");
  if (!activeLink) {
    indicator.style.width = "0px";
    return;
  }
  const wrapperRect = wrapper.getBoundingClientRect();
  const linkRect = activeLink.getBoundingClientRect();
  indicator.style.left = (linkRect.left - wrapperRect.left) + "px";
  indicator.style.width = linkRect.width + "px";
}

/* ================================================================
   PROFILE DROPDOWN
   ================================================================ */
function initProfileDropdown() {
  const trigger = $("profileTrigger");
  const dropdown = $("profileDropdown");
  if (!trigger || !dropdown) return;

  trigger.addEventListener("click", (ev) => {
    ev.stopPropagation();
    dropdown.classList.toggle("active");
  });

  document.addEventListener("click", (ev) => {
    if (!dropdown.contains(ev.target) && ev.target !== trigger) {
      dropdown.classList.remove("active");
    }
  });

  $("dd-config")?.addEventListener("click", () => {
    dropdown.classList.remove("active");
    openConfigModal();
  });

  $("dd-historico")?.addEventListener("click", () => {
    dropdown.classList.remove("active");
    openHistoricoModal();
  });

  $("dd-logout")?.addEventListener("click", () => {
    dropdown.classList.remove("active");
    doLogout();
  });
}

function setProfileInfo(estado) {
  const name = estado.user_name || estado.email || "Corretor";
  const cargo = estado.user_cargo || "Consultor";
  const imob = estado.user_imobiliaria || "";

  const initEl = $("navInitial");
  if (initEl) initEl.textContent = (name[0] || "C").toUpperCase();

  const nameEl = $("userNameDisplay");
  if (nameEl) nameEl.textContent = name;

  const roleEl = $("userRoleDisplay");
  if (roleEl) roleEl.textContent = cargo;

  const imobEl = $("userImobDisplay");
  if (imobEl) {
    imobEl.textContent = imob;
    imobEl.style.display = imob ? "" : "none";
  }
}

/* ================================================================
   BANNER CAROUSEL
   ================================================================ */
const DEFAULT_HOME_BANNER_URLS = [
  "https://images.unsplash.com/photo-1560518883-ce09059eeffa?ixlib=rb-4.0.3&auto=format&fit=crop&w=1920&q=80",
  "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?ixlib=rb-4.0.3&auto=format&fit=crop&w=1920&q=80",
  "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?ixlib=rb-4.0.3&auto=format&fit=crop&w=1920&q=80",
];

function escapeCssUrl(url) {
  return String(url).replace(/\\/g, "\\\\").replace(/'/g, "\\'");
}

let _bannerInterval = null;
let _bannerIdx = 0;
let _bannerAbort = null;
/** Evita GET /api/home/banners em cada refreshUI quando não está na home. */
let _homeBannersFetchedAt = 0;
const HOME_BANNERS_CLIENT_TTL_MS = 10 * 60 * 1000;

/**
 * Reconstrói slides e dots; volta a ligar listeners (cancela os anteriores via AbortController).
 */
function applyHomeBannerUrls(urls) {
  const host = $("homeBanner");
  if (!host) return;
  const list = urls && urls.length ? urls : [...DEFAULT_HOME_BANNER_URLS];
  const overlay = host.querySelector(".banner-overlay");
  host.querySelectorAll(".banner-slide").forEach((el) => el.remove());
  const ref = overlay || host.firstChild;
  list.forEach((url, i) => {
    const d = document.createElement("div");
    d.className = "banner-slide" + (i === 0 ? " active" : "");
    d.style.backgroundImage = `url('${escapeCssUrl(url)}')`;
    if (ref) host.insertBefore(d, ref);
    else host.appendChild(d);
  });
  const dotsHost = $("banner-dots");
  if (dotsHost) {
    dotsHost.innerHTML = list
      .map((_, i) => `<div class="b-dot${i === 0 ? " active" : ""}" role="presentation"></div>`)
      .join("");
  }
  _bannerIdx = 0;
  initBannerCarousel();
}

async function loadHomeBanners(options = {}) {
  const force = options.force === true;
  if (!force) {
    if (_currentPage !== "home") return;
    if (_homeBannersFetchedAt && Date.now() - _homeBannersFetchedAt < HOME_BANNERS_CLIENT_TTL_MS) return;
  }
  try {
    const data = await apiGet("/api/home/banners");
    _homeBannersFetchedAt = Date.now();
    const imgs = Array.isArray(data.imagens) ? data.imagens : [];
    applyHomeBannerUrls(imgs);
    const bar = $("home-banners-admin-bar");
    if (bar) bar.style.display = data.is_admin === true ? "" : "none";
  } catch (e) {
    console.warn("[home/banners]", e);
  }
}

function initBannerCarousel() {
  const host = $("homeBanner");
  if (!host) return;
  if (_bannerAbort) _bannerAbort.abort();
  _bannerAbort = new AbortController();
  const sig = { signal: _bannerAbort.signal };

  function allSlides() {
    return [...host.querySelectorAll(".banner-slide")];
  }
  function allDots() {
    return [...document.querySelectorAll("#banner-dots .b-dot")];
  }

  function goSlide(idx) {
    const slides = allSlides();
    const dots = allDots();
    if (!slides.length) return;
    _bannerIdx = ((idx % slides.length) + slides.length) % slides.length;
    slides.forEach((s, i) => s.classList.toggle("active", i === _bannerIdx));
    dots.forEach((d, i) => d.classList.toggle("active", i === _bannerIdx));
  }

  $("banner-prev-btn")?.addEventListener(
    "click",
    () => {
      goSlide(_bannerIdx - 1);
      resetBannerAuto();
    },
    sig,
  );
  $("banner-next-btn")?.addEventListener(
    "click",
    () => {
      goSlide(_bannerIdx + 1);
      resetBannerAuto();
    },
    sig,
  );
  $("banner-dots")?.addEventListener(
    "click",
    (ev) => {
      const t = ev.target.closest(".b-dot");
      if (!t || !t.parentElement) return;
      const dots = [...t.parentElement.querySelectorAll(".b-dot")];
      const i = dots.indexOf(t);
      if (i >= 0) {
        goSlide(i);
        resetBannerAuto();
      }
    },
    sig,
  );

  function resetBannerAuto() {
    if (_bannerInterval) clearInterval(_bannerInterval);
    _bannerInterval = setInterval(() => goSlide(_bannerIdx + 1), 6000);
  }
  resetBannerAuto();
}

/* ================================================================
   CONFIG MODAL
   ================================================================ */
function openConfigModal() {
  const overlay = $("config-overlay");
  if (!overlay) return;
  overlay.classList.remove("hidden");

  if (_estadoCache) {
    const s = _estadoCache;
    const setVal = (id, v) => { const el = $(id); if (el) el.value = v || ""; };
    setVal("conf-nome", s.user_name || s.email || "");
    setVal("conf-email", s.email || "");
    setVal("conf-cargo", s.user_cargo || "");
    setVal("conf-imob", s.user_imobiliaria || "");
    const senhaEl = $("conf-senha");
    if (senhaEl) senhaEl.value = "";
  }
  $("config-msg").textContent = "";
}

$("btn-close-config")?.addEventListener("click", () => $("config-overlay")?.classList.add("hidden"));

$("btn-save-config")?.addEventListener("click", async () => {
  const msg = $("config-msg");
  const nome = $("conf-nome")?.value?.trim();
  const email = $("conf-email")?.value?.trim();
  const senha = $("conf-senha")?.value;
  const body = {};
  if (nome) body.user_name = nome;
  if (email) body.email = email;
  if (senha) body.password = senha;
  try {
    await apiPatch("/api/session", body);
    showMsg(msg, "Configurações salvas com sucesso!", true);
    _estadoCache = await apiGet("/api/session");
    setProfileInfo(_estadoCache);
  } catch (e) {
    showMsg(msg, e.message || "Erro ao salvar.", false);
  }
});

/* ================================================================
   HISTORICO MODAL
   ================================================================ */
function openHistoricoModal() {
  const overlay = $("historico-overlay");
  if (!overlay) return;
  overlay.classList.remove("hidden");
  $("historico-search-input")?.focus();
  const ul = $("historico-modal-results");
  if (ul && !ul.children.length) loadHistoricoModalResults("");
}

$("btn-close-historico")?.addEventListener("click", () => $("historico-overlay")?.classList.add("hidden"));

$("btn-historico-search")?.addEventListener("click", () => {
  const q = $("historico-search-input")?.value || "";
  loadHistoricoModalResults(q);
});

async function loadHistoricoModalResults(q) {
  const ul = $("historico-modal-results");
  if (!ul) return;
  ul.innerHTML = "<li class='muted'>A pesquisar…</li>";
  try {
    const data = await apiGet(`/api/cadastros/buscar-simulacoes?q=${encodeURIComponent(q)}&limite=20`);
    const itens = data.itens || [];
    ul.innerHTML = "";
    itens.forEach((row) => {
      const li = document.createElement("li");
      const nome = row.Nome || row.nome || "—";
      const emp = row["Empreendimento Final"] || "—";
      const dataStr = row["Data/Horário"] || row["Data"] || "";
      let label = `${nome} | ${emp}`;
      if (dataStr) label += ` | ${dataStr}`;
      li.innerHTML = `<div class="historico-btn" style="display:flex;justify-content:space-between;align-items:center;gap:.5rem;flex-wrap:wrap;">
        <span style="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;">${label}</span>
        <div style="display:flex;gap:.35rem;flex-shrink:0;">
          <button type="button" class="btn btn-primary btn-sm hist-load">Carregar</button>
          <button type="button" class="btn btn-secondary btn-sm hist-panel">Ver Painel</button>
        </div>
      </div>`;
      li.querySelector(".hist-load")?.addEventListener("click", async () => {
        try {
          await apiPost("/api/cliente/importar-historico", { row });
          $("historico-overlay")?.classList.add("hidden");
          loadPage("simulador");
          await goStep("fechamento_aprovado");
        } catch (e) { alert(e.message); }
      });
      li.querySelector(".hist-panel")?.addEventListener("click", async () => {
        try {
          await apiPost("/api/cliente/importar-historico", { row });
          $("historico-overlay")?.classList.add("hidden");
          loadPage("simulador");
          await goStep("client_analytics");
        } catch (e) { alert(e.message); }
      });
      ul.appendChild(li);
    });
    if (!itens.length) ul.innerHTML = "<li class='muted'>Nenhum resultado.</li>";
  } catch (e) {
    ul.innerHTML = `<li class='muted'>Erro: ${e.message}</li>`;
  }
}

/* ---------- State cache ---------- */
let _estadoCache = null;

/* ================================================================
   STEP-SPECIFIC LOADERS
   ================================================================ */

/** Alinha fechamento (finan/subsídio) ao modo número após setVal — paridade com pagamento. */
function syncFechCurrencyFromDc(dc) {
  const d = dc || {};
  ["fech-finan", "fech-sub"].forEach((id, i) => {
    const el = $(id);
    if (!el) return;
    el.type = "number";
    el.step = "any";
    const key = i === 0 ? "finan_usado" : "fgts_sub_usado";
    const v = d[key];
    const n = v != null && v !== "" ? Number(v) : 0;
    el.value = Number.isFinite(n) && n !== 0 ? String(n) : n === 0 ? "0" : "";
  });
}

async function loadFechamentoContexto() {
  try {
    const ctx = await apiGet("/api/fechamento/contexto");
    const dc = ctx.dados_cliente || {};
    const comp = ctx.comparativo || {};

    const setVal = (id, v) => { const el = $(id); if (el) el.value = v ?? ""; };
    setVal("fech-finan", dc.finan_usado);
    setVal("fech-sub", dc.fgts_sub_usado);
    setVal("fech-prazo", dc.prazo_financiamento ?? 360);
    syncFechCurrencyFromDc(dc);
    const selSist = $("fech-sistema");
    if (selSist && dc.sistema_amortizacao) selSist.value = dc.sistema_amortizacao;

    const refFin = $("fech-finan-ref");
    if (refFin) refFin.textContent = `Financiamento Máximo (curva): R$ ${fmtBR(ctx.finan_f_ref ?? 0)}`;
    const refSub = $("fech-sub-ref");
    if (refSub) refSub.textContent = `Subsídio Máximo (curva): R$ ${fmtBR(ctx.sub_f_ref ?? 0)}`;

    renderComparativo(comp);
  } catch (e) {
    console.error("[SIMULADOR] loadFechamentoContexto:", e);
    showMsg($("fechamento-msg"), "Erro ao carregar contexto do fechamento.", false);
  }
}

let _lastComparativo = null;

function renderComparativo(comp) {
  const el = $("fech-comparativo");
  if (!el) return;
  if (comp) _lastComparativo = comp;
  const c = _lastComparativo;
  if (!c) return;

  const sistema = $("fech-sistema")?.value || "SAC";
  const finan = parseFloat($("fech-finan")?.value) || 0;

  if (sistema === "SAC") {
    const montante = finan + (c.sac_juros ?? 0);
    el.innerHTML = `<b>SAC</b><br/>
      Parcela inicial: <b>R$ ${fmtBR(c.sac_primeira ?? 0)}</b><br/>
      Parcela final: <b>R$ ${fmtBR(c.sac_ultima ?? 0)}</b><br/>
      Montante total: <b>R$ ${fmtBR(montante)}</b>`;
  } else {
    const montante = finan + (c.price_juros ?? 0);
    el.innerHTML = `<b>PRICE</b><br/>
      Parcela fixa: <b>R$ ${fmtBR(c.price_parcela ?? 0)}</b><br/>
      Montante total: <b>R$ ${fmtBR(montante)}</b>`;
  }
}

async function loadGuideData() {
  const cardsEl = $("guide-viaveis-cards");
  const recEl = $("guide-recomendacoes");
  const filterEl = $("guide-emp-filter");
  if (cardsEl) cardsEl.innerHTML = '<div class="skeleton skeleton-card"></div>';
  try {
    const [data, metaEstoque] = await Promise.all([
      apiPost("/api/simulacao/recomendacoes", {}),
      apiGet("/api/estoque/filtros-meta"),
    ]);
    await populateEstoqueFiltersFromMeta(metaEstoque);
    const empList = data.empreendimentos_viaveis || [];
    if (cardsEl) {
      if (!empList.length) {
        cardsEl.innerHTML = "<p class='muted'>Sem empreendimentos viáveis para este perfil.</p>";
      } else {
        let html = "";
        for (const item of empList) {
          const emp = item.empreendimento || item;
          const qtd = item.unidades_viaveis || 0;
          html += `<div class="viavel-card"><p class="viavel-card-emp">${emp}</p><p class="viavel-card-qtd">${qtd} unidades viáveis</p></div>`;
        }
        cardsEl.innerHTML = html;
      }
    }
    if (filterEl) {
      const empNames = empList.map((e) => e.empreendimento || e);
      filterEl.innerHTML = '<option value="Todos">Todos</option>';
      empNames.forEach((e) => {
        filterEl.innerHTML += `<option value="${e}">${e}</option>`;
      });
    }
    renderRecomendacoes(data);
    _guideData = data;
  } catch (e) {
    if (cardsEl) cardsEl.innerHTML = `<p class='muted'>Erro: ${e.message}</p>`;
  }
}

let _guideData = null;

function renderRecomendacoes(data) {
  const el = $("guide-recomendacoes");
  if (!el) return;
  const groups = [
    { key: "ideal", label: "IDEAL", css: "badge-ideal" },
    { key: "seguro", label: "SEGURO", css: "badge-seguro" },
    { key: "facilitado", label: "FACILITADO", css: "badge-facilitado" },
  ];
  let html = '<div class="scrolling-wrapper">';
  let total = 0;
  for (const g of groups) {
    const list = data[g.key] || [];
    for (const item of list) {
      total++;
      const row = item.row || item;
      html += `<div class="card-item">
        <div class="recommendation-card">
          <span class="rec-perfil-label">PERFIL</span>
          <div class="rec-badge-wrap"><span class="${g.css}">${g.label}</span></div>
          <b class="rec-emp-name">${row.Empreendimento || row.empreendimento || "—"}</b>
          <div class="rec-unid-line">Unidade: ${row.Identificador || row.identificador || "—"}</div>
          <div class="rec-prices">
            <div><span class="small muted">Avaliação</span><br/><b>R$ ${fmtBR(row["Valor de Avaliação Bancária"] || row.avaliacao || 0)}</b></div>
            <div><span class="small muted">Venda</span><br/><span class="price-tag">R$ ${fmtBR(row["Valor de Venda"] || row.venda || 0)}</span></div>
          </div>
        </div>
      </div>`;
    }
  }
  html += "</div>";
  if (!total) html = "<p class='muted'>Nenhuma unidade encontrada.</p>";
  el.innerHTML = html;
}

async function applyEstoqueFilters() {
  try {
    const selB = $("est-bairro");
    const selE = $("est-emp");
    const params = [];
    if (selB?.value) params.push(`bairro=${encodeURIComponent(selB.value)}`);
    if (selE?.value) params.push(`empreendimento=${encodeURIComponent(selE.value)}`);
    const cobMin = parseInt($("est-cob")?.value || "0", 10);
    if (cobMin > 0) params.push(`cobertura_min_pct=${cobMin}`);
    const ordem = $("est-ordem")?.value === "desc" ? "maior_preco" : "menor_preco";
    params.push(`ordem=${ordem}`);
    const pmaxRaw = $("est-pmax")?.value;
    const pmax = pmaxRaw != null && String(pmaxRaw).trim() !== "" ? parseFloat(String(pmaxRaw).replace(/[R$\s.]/g, "").replace(",", ".")) : NaN;
    if (!Number.isNaN(pmax) && pmax > 0) params.push(`preco_max=${pmax}`);
    const q = params.length ? `?${params.join("&")}` : "";
    const data = await apiGet(`/api/estoque${q}`);
    renderEstoqueRows(data.itens || []);
  } catch (e) {
    console.error("[SIMULADOR] applyEstoqueFilters:", e);
  }
}

/** Preenche selects do estoque a partir de GET /api/estoque/filtros-meta (1 round-trip). */
async function populateEstoqueFiltersFromMeta(meta) {
  try {
    const emps = meta?.empreendimentos || [];
    const selE = $("est-emp");
    if (selE) {
      selE.innerHTML = '<option value="">Todos</option>';
      emps.forEach((e) => { selE.innerHTML += `<option value="${e}">${e}</option>`; });
    }
    const bairros = meta?.bairros || [];
    const selB = $("est-bairro");
    if (selB) {
      selB.innerHTML = '<option value="">Todos</option>';
      bairros.forEach((b) => { selB.innerHTML += `<option value="${b}">${b}</option>`; });
    }
    await applyEstoqueFilters();
  } catch (e) { console.error("[SIMULADOR] populateEstoqueFiltersFromMeta:", e); }
}

async function populateEstoqueFilters() {
  try {
    const meta = await apiGet("/api/estoque/filtros-meta");
    await populateEstoqueFiltersFromMeta(meta);
  } catch (e) { console.error("[SIMULADOR] populateEstoqueFilters:", e); }
}

function renderEstoqueRows(rows) {
  const wrap = $("estoque-table-wrap");
  if (!wrap) return;
  if (!rows.length) { wrap.innerHTML = "<p class='muted'>Sem dados.</p>"; return; }
  let html = `<table class="estoque-table"><thead><tr>
    <th>Unidade</th><th>Bairro</th><th>Empreendimento</th><th>Avaliação (R$)</th><th>Venda (R$)</th><th>Poder Real (R$)</th><th>Cobertura</th>
  </tr></thead><tbody>`;
  for (const r of rows) {
    const cob = Number(r.Cobertura || r.cobertura || 0);
    html += `<tr>
      <td>${r.Identificador || r.identificador || ""}</td>
      <td>${r.Bairro || r.bairro || ""}</td>
      <td>${r.Empreendimento || r.empreendimento || ""}</td>
      <td>R$ ${fmtBR(r["Valor de Avaliação Bancária"] || r.avaliacao || 0)}</td>
      <td>R$ ${fmtBR(r["Valor de Venda"] || r.venda || 0)}</td>
      <td>R$ ${fmtBR(r.Poder_Compra || r.poder_compra || 0)}</td>
      <td>${cob.toFixed(1)}%</td>
    </tr>`;
  }
  html += "</tbody></table>";
  wrap.innerHTML = html;
}

async function loadSelectionEmpreendimentos() {
  const sel = $("sel-empreendimento");
  if (!sel) return;
  sel.innerHTML = '<option value="">—</option>';
  const selU = $("sel-unidade");
  if (selU) { selU.innerHTML = '<option value="">—</option>'; selU.disabled = true; }
  try {
    const data = await apiGet("/api/estoque/empreendimentos");
    const dc = _estadoCache?.dados_cliente || {};
    const empAtual = dc.empreendimento_nome || "";
    (data.empreendimentos || []).forEach((e) => {
      const o = document.createElement("option");
      o.value = e; o.textContent = e;
      if (e === empAtual) o.selected = true;
      sel.appendChild(o);
    });
    if (empAtual) await loadSelectionUnidades(empAtual);
  } catch (e) { console.error("[SIMULADOR] loadSelectionEmpreendimentos:", e); }
}

async function loadSelectionUnidades(emp) {
  const selU = $("sel-unidade");
  if (!selU || !emp) return;
  selU.innerHTML = '<option value="">—</option>';
  selU.disabled = true;
  try {
    const data = await apiGet(`/api/estoque/unidades?empreendimento=${encodeURIComponent(emp)}`);
    const dc = _estadoCache?.dados_cliente || {};
    const uidAtual = dc.unidade_id || "";
    (data.unidades || []).forEach((u) => {
      const o = document.createElement("option");
      o.value = u.identificador;
      o.textContent = u.label || u.identificador;
      o.dataset.valorVenda = String(u.valor_venda ?? "");
      o.dataset.valorAvaliacao = String(u.valor_avaliacao ?? "");
      if (u.identificador === uidAtual) o.selected = true;
      selU.appendChild(o);
    });
    selU.disabled = false;
    if (selU.value) await loadTermometro();
  } catch (e) {
    console.error("[SIMULADOR] loadSelectionUnidades:", e);
    showMsg($("unidade-msg"), "Erro ao carregar unidades.", false);
  }
}

async function loadTermometro() {
  const emp = $("sel-empreendimento")?.value;
  const uid = $("sel-unidade")?.value;
  const wrap = $("termometro-wrap");
  if (!emp || !uid) { if (wrap) wrap.classList.add("hidden"); return; }
  const vf = $("valor-final-unidade")?.value;
  let q = `/api/selection/termometro?empreendimento=${encodeURIComponent(emp)}&identificador=${encodeURIComponent(uid)}`;
  if (vf && parseFloat(vf) > 0) q += `&valor_final=${encodeURIComponent(vf)}`;
  try {
    const data = await apiGet(q);
    if (wrap) wrap.classList.remove("hidden");
    const selUEl = $("sel-unidade");
    const selOpt = selUEl?.selectedOptions?.[0];
    const vAval = selOpt?.dataset?.valorAvaliacao || data.valor_avaliacao || 0;
    $("termo-avaliacao").textContent = `R$ ${fmtBR(vAval)}`;
    $("termo-venda").textContent = `R$ ${fmtBR(data.valor_para_termometro || data.valor_venda_tabela || 0)}`;
    const pct = Math.min(100, Math.max(0, Number(data.percentual_cobertura || 0)));
    const fill = $("termo-fill");
    if (fill) fill.style.width = `${pct}%`;
    $("termo-pct").textContent = `${pct.toFixed(1)}% Coberto`;
    const vfInput = $("valor-final-unidade");
    if (vfInput && !vfInput.value) vfInput.value = data.valor_venda_tabela || "";
  } catch (e) { console.error("[SIMULADOR] loadTermometro:", e); }
}

/** Alinha inputs monetários do pagamento ao modo número (evita conflito com máscara R$ após setVal). */
function syncPayCurrencyInputsFromDc(dc) {
  const d = dc || {};
  const ids = ["pay-ato1", "pay-ato2", "pay-ato3", "pay-ato4", "pay-ps", "pay-vc"];
  const keys = ["ato_final", "ato_30", "ato_60", "ato_90", "ps_usado", "volta_caixa_input"];
  ids.forEach((id, i) => {
    const el = $(id);
    if (!el) return;
    el.type = "number";
    el.step = "any";
    const v = d[keys[i]];
    const n = v != null && v !== "" ? Number(v) : 0;
    el.value = Number.isFinite(n) && n !== 0 ? String(n) : n === 0 ? "0" : "";
  });
  const parc = $("pay-ps-parc");
  if (parc) {
    parc.type = "number";
    parc.value = String(d.ps_parcelas || 60);
  }
}

function politicaIsEmcash(pol) {
  return String(pol || "").toLowerCase().includes("emcash");
}

/** Saldo a parcelar em 30/60/90 após ato imediato (só para mensagem ao distribuir). */
function restanteParaAtosParcelados(dc) {
  const d = dc || {};
  const u = Number(d.imovel_valor) || 0;
  const f = Number(d.finan_usado) || 0;
  const fg = Number(d.fgts_sub_usado) || 0;
  const ps = Number(d.ps_usado) || 0;
  const a1 = Number(d.ato_final) || 0;
  return Math.max(0, u - f - fg - ps - a1);
}

async function loadPaymentContexto() {
  try {
    if (!_estadoCache) _estadoCache = await apiGet("/api/session");
    const ctx = await apiGet("/api/pagamento/contexto");
    const ru = ctx.resumo_unidade || {};
    const dc = _estadoCache?.dados_cliente || {};
    const banner = $("payment-banner");
    if (banner) {
      banner.innerHTML = `<div class="payment-banner-inner">
        <div class="payment-banner-title">${ru.empreendimento || "N/A"} - ${ru.unidade || "N/A"}</div>
        <div>Valor Final da Unidade: <b>R$ ${fmtBR(ru.valor_final || 0)}</b></div>
        <div>Financiamento: R$ ${fmtBR(ru.financiamento || 0)} | Subsídio: R$ ${fmtBR(ru.fgts_sub || 0)} | Prazo: ${ru.prazo_fin || 360}x | ${ru.sistema || "SAC"}</div>
      </div>`;
    }

    const setVal = (id, v) => { const el = $(id); if (el) el.value = v ?? ""; };
    setVal("pay-ato1", dc.ato_final || 0);
    setVal("pay-ato2", dc.ato_30 || 0);
    setVal("pay-ato3", dc.ato_60 || 0);
    setVal("pay-ato4", dc.ato_90 || 0);
    setVal("pay-ps", dc.ps_usado || 0);
    setVal("pay-ps-parc", dc.ps_parcelas || 60);
    setVal("pay-vc", dc.volta_caixa_input || 0);
    syncPayCurrencyInputsFromDc(dc);

    const isEmcash = politicaIsEmcash(dc.politica);
    const ato4El = $("pay-ato4");
    if (ato4El) ato4El.disabled = isEmcash;
    const btn3 = $("btn-dist-3");
    if (btn3) btn3.disabled = isEmcash;

    const psRef = $("pay-ps-ref");
    if (psRef) psRef.textContent = `Limite máximo de Pro Soluto: R$ ${fmtBR(ctx.ps_limite_ui || 0)}`;

    const mps = ctx.metricas_ps || {};
    const psParc = $("pay-ps-parcela-info");
    if (psParc) psParc.textContent = `Parcela máxima (C43/G14): R$ ${fmtBR(mps.parcela_max_g14 || 0)}`;

    const psPrazo = $("pay-ps-prazo-ref");
    if (psPrazo) {
      psPrazo.textContent = `Prazo máx. parcelas: ${ctx.parc_max_ui || 84} meses (política ${ctx.pol_prazo || 0} × app ${ctx.prazo_cap_app || 84})`;
      const parcInput = $("pay-ps-parc");
      if (parcInput) parcInput.max = ctx.parc_max_ui || 84;
    }
    const vcRef = $("pay-vc-ref");
    if (vcRef) vcRef.textContent = `Folga Volta ao Caixa: R$ ${fmtBR(ctx.volta_caixa_ref || 0)}`;

    const mensal = $("pay-mensalidade");
    if (mensal) {
      const parc = dc.ps_parcelas || 60;
      mensal.innerHTML = `Mensalidade PS (PMT×(1+E1)): <b>R$ ${fmtBR(ctx.mensalidade_ps || 0)}</b> (${parc}x)`;
    }

    await refreshPaymentGap();
  } catch (e) {
    console.error("[SIMULADOR] loadPaymentContexto:", e);
    const el = $("gap-status");
    if (el) { el.className = "gap-status gap-erro"; el.textContent = "Erro ao carregar dados do pagamento."; }
  }
}

async function refreshPaymentGap() {
  const el = $("gap-status");
  const btn = $("btn-next-payment_flow");
  try {
    const g = await apiGet("/api/pagamento/gap");
    const ok = g.pode_avancar_resumo === true;
    const gap = Number(g.gap_final || 0);
    if (el) {
      if (Math.abs(gap) <= 1.0) {
        el.className = "gap-status gap-ok";
        el.textContent = "Valores fechados — pode avançar ao resumo.";
      } else if (gap > 0) {
        el.className = "gap-status gap-erro";
        el.textContent = `Atenção: Falta cobrir R$ ${fmtBR(Math.abs(gap))}.`;
      } else {
        el.className = "gap-status gap-erro";
        el.textContent = `Atenção: Valor excedente de R$ ${fmtBR(Math.abs(gap))}.`;
      }
    }
    if (btn) btn.disabled = !ok;
  } catch (e) {
    if (el) { el.className = "gap-status gap-erro"; el.textContent = "Erro ao ler gap: " + e.message; }
    if (btn) btn.disabled = true;
  }
}

async function patchPaymentAndRefresh() {
  const body = {};
  const num = (id) => {
    let v = $(id)?.value;
    if (v == null || v === "") return undefined;
    v = String(v).replace(/[R$\s.]/g, "").replace(",", ".");
    const n = parseFloat(v);
    return isNaN(n) ? undefined : n;
  };
  const pu = num("pay-ps"); if (pu !== undefined) body.ps_usado = pu;
  const pp = $("pay-ps-parc")?.value; if (pp) body.ps_parcelas = parseInt(pp, 10);
  const af = num("pay-ato1"); if (af !== undefined) body.ato_final = af;
  const a30 = num("pay-ato2"); if (a30 !== undefined) body.ato_30 = a30;
  const a60 = num("pay-ato3"); if (a60 !== undefined) body.ato_60 = a60;
  const a90 = num("pay-ato4"); if (a90 !== undefined) body.ato_90 = a90;
  const vc = num("pay-vc"); if (vc !== undefined) body.volta_caixa = vc;
  try {
    await apiPatch("/api/pagamento/estado", body);
    await loadPaymentContexto();
  } catch (e) { console.error("[SIMULADOR] patchPaymentAndRefresh:", e); }
}

async function loadResumoBlocos() {
  const host = $("resumo-blocos-html");
  if (!host) return;
  try {
    const data = await apiGet("/api/resumo/blocos-html");
    let html = `<h3 class="resumo-titulo-principal">${data.titulo || ""}</h3>`;
    (data.secoes || []).forEach((s) => {
      html += `<div class="summary-header">${s.titulo}</div><div class="summary-body">${s.html}</div>`;
    });
    host.innerHTML = html;
  } catch (e) {
    host.textContent = "Erro: " + e.message;
  }
}

/* ================================================================
   GALLERY
   ================================================================ */
let _galleryMaps = new Map();
let _galleryActiveProductName = null;

/** Liberta mapas Leaflet e estado ao sair do wizard ou recarregar a galeria */
function destroyGalleryResources() {
  _galleryMaps.forEach((m) => {
    try {
      m.remove();
    } catch {
      /* noop */
    }
  });
  _galleryMaps.clear();
  _galleryActiveProductName = null;
}

function youtubeEmbed(url) {
  if (!url || typeof url !== "string") return "";
  const u = url.trim();
  let m = u.match(/[?&]v=([^&]+)/);
  if (m) return `https://www.youtube.com/embed/${m[1]}`;
  m = u.match(/youtu\.be\/([^/?]+)/);
  if (m) return `https://www.youtube.com/embed/${m[1]}`;
  if (u.includes("youtube.com/embed/")) return u.split("?")[0];
  return "";
}

/** ID de ficheiro/pasta a partir de URL do Google Drive */
function driveFileIdFromUrl(url) {
  if (!url || typeof url !== "string") return "";
  const u = url.trim();
  let m = u.match(/\/file\/d\/([^/]+)/);
  if (m) return m[1];
  m = u.match(/[?&]id=([^&]+)/);
  if (m && u.includes("drive.google.com")) return m[1];
  return "";
}

function driveThumbnailUrl(url) {
  const id = driveFileIdFromUrl(url);
  if (!id) return url;
  return `https://drive.google.com/thumbnail?id=${id}&sz=w800`;
}

/** iframe src para vídeo ou PDF alojado no Drive */
function drivePreviewEmbedUrl(url) {
  const id = driveFileIdFromUrl(url);
  if (!id) return "";
  return `https://drive.google.com/file/d/${id}/preview`;
}

/** URL para abrir ficheiro Drive num separador (fallback) */
function driveOpenUrl(url) {
  const id = driveFileIdFromUrl(url);
  if (id) return `https://drive.google.com/file/d/${id}/view`;
  return url;
}

let _galeriaEditNomeAtual = null;
/** @type {"edit"|"create"} */
let _galeriaEditModo = "edit";

function addGaleriaEditImagemRow(nome = "", link = "") {
  const list = $("galeria-edit-imagens-list");
  if (!list) return;
  const wrap = document.createElement("div");
  wrap.className = "galeria-edit-img-row";
  const inN = document.createElement("input");
  inN.className = "input-field";
  inN.placeholder = "Nome (ex.: Fachada)";
  inN.value = nome;
  const inL = document.createElement("input");
  inL.className = "input-field";
  inL.placeholder = "URL (imagem ou Drive)";
  inL.value = link;
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "btn btn-secondary btn-sm";
  btn.textContent = "Remover";
  btn.addEventListener("click", () => wrap.remove());
  wrap.append(inN, inL, btn);
  list.appendChild(wrap);
}

function openGaleriaEditModal(nome, meta) {
  _galeriaEditModo = "edit";
  _galeriaEditNomeAtual = nome;
  const title = $("galeria-edit-title");
  if (title) title.textContent = `Editar galeria — ${nome}`;
  const nomeEl = $("galeria-edit-nome");
  const nomeWrap = $("galeria-edit-nome-wrap");
  if (nomeEl) {
    nomeEl.value = nome;
    nomeEl.disabled = true;
  }
  if (nomeWrap) nomeWrap.style.display = "";
  const vidEl = $("galeria-edit-video");
  if (vidEl) vidEl.value = meta.video || "";
  const latEl = $("galeria-edit-lat");
  const lonEl = $("galeria-edit-lon");
  if (latEl) latEl.value = meta.lat != null && meta.lat !== "" ? String(meta.lat) : "";
  if (lonEl) lonEl.value = meta.lon != null && meta.lon !== "" ? String(meta.lon) : "";
  const list = $("galeria-edit-imagens-list");
  if (list) list.innerHTML = "";
  (meta.imagens || []).forEach((it) => addGaleriaEditImagemRow(it.nome || "", it.link || ""));
  const msg = $("galeria-edit-msg");
  if (msg) msg.textContent = "";
  const delBtn = $("galeria-edit-delete");
  if (delBtn) delBtn.style.display = "";
  $("galeria-edit-overlay")?.classList.remove("hidden");
}

function openGaleriaCreateModal() {
  _galeriaEditModo = "create";
  _galeriaEditNomeAtual = null;
  const title = $("galeria-edit-title");
  if (title) title.textContent = "Novo empreendimento na galeria";
  const nomeEl = $("galeria-edit-nome");
  const nomeWrap = $("galeria-edit-nome-wrap");
  if (nomeEl) {
    nomeEl.value = "";
    nomeEl.disabled = false;
  }
  if (nomeWrap) nomeWrap.style.display = "";
  const vidEl = $("galeria-edit-video");
  if (vidEl) vidEl.value = "";
  const latEl = $("galeria-edit-lat");
  const lonEl = $("galeria-edit-lon");
  if (latEl) latEl.value = "";
  if (lonEl) lonEl.value = "";
  const list = $("galeria-edit-imagens-list");
  if (list) {
    list.innerHTML = "";
    addGaleriaEditImagemRow();
  }
  const msg = $("galeria-edit-msg");
  if (msg) msg.textContent = "";
  const delBtn = $("galeria-edit-delete");
  if (delBtn) delBtn.style.display = "none";
  $("galeria-edit-overlay")?.classList.remove("hidden");
}

function closeGaleriaEditModal() {
  _galeriaEditNomeAtual = null;
  _galeriaEditModo = "edit";
  $("galeria-edit-overlay")?.classList.add("hidden");
}

function galleryPanelForProd(host, name) {
  const key = encodeURIComponent(name);
  for (const p of host.querySelectorAll(".gallery-panel")) {
    if (p.getAttribute("data-panel") === key) return p;
  }
  return null;
}

function galleryVideoEmbedUrl(meta) {
  const v = (meta.video || "").trim();
  if (!v) return "";
  const yt = youtubeEmbed(v);
  if (yt) return yt;
  return drivePreviewEmbedUrl(v) || "";
}

function galleryMetricasHtml(met) {
  return `<div class="summary-body" style="padding:12px;">
          <strong>Faixa de Preço:</strong> ${met.variacao_preco || "—"}<br/>
          <strong>Metragem:</strong> ${met.metragem || "—"}<br/>
          <strong>Preço/m²:</strong> ${met.preco_m2 || "—"}<br/>
          <strong>Data de Entrega:</strong> ${met.entrega || "—"}<br/>
          <strong>Bairro:</strong> ${met.bairro || "—"}</div>`;
}

function galleryDeactivateTabContent(host) {
  if (!_galleryActiveProductName) return;
  const name = _galleryActiveProductName;
  const m = _galleryMaps.get(name);
  if (m) {
    try {
      m.remove();
    } catch {
      /* noop */
    }
    _galleryMaps.delete(name);
  }
  const panel = galleryPanelForProd(host, name);
  const vh = panel?.querySelector(".gallery-video-host");
  if (vh) vh.innerHTML = "";
  _galleryActiveProductName = null;
}

function galleryActivateTabContent(host, cat, name, strip) {
  galleryDeactivateTabContent(host);
  const meta = cat[name] || {};
  const panel = galleryPanelForProd(host, name);
  if (!panel) return;
  const id = strip(name);
  const embed = galleryVideoEmbedUrl(meta);
  const vh = panel.querySelector(".gallery-video-host");
  if (vh) {
    if (embed) {
      vh.innerHTML = `<iframe class="gallery-video" src="${embed}" allowfullscreen title="Vídeo"></iframe>`;
    } else {
      vh.innerHTML = "<p>Sem vídeo.</p>";
    }
  }
  const mapEl = $(`map-${id}`);
  if (mapEl && typeof window.L !== "undefined" && meta.lat != null && meta.lon != null) {
    const m = window.L.map(mapEl).setView([meta.lat, meta.lon], 15);
    window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: "© OSM" }).addTo(m);
    window.L.marker([meta.lat, meta.lon]).addTo(m).bindPopup(name);
    _galleryMaps.set(name, m);
    setTimeout(() => m.invalidateSize(), 250);
  }
  _galleryActiveProductName = name;
}

async function loadGalleryCatalog() {
  const host = $("gallery-tabs-host");
  if (!host) return;
  destroyGalleryResources();
  host.innerHTML = "<p class='muted'>A carregar catálogo…</p>";
  try {
    await ensureLeaflet();
    const data = await apiGet("/api/galeria/catalogo");
    const cat = data.catalogo || {};
    const names = data.produtos || [];
    const isAdmin = data.is_admin === true;
    if (!names.length) {
      host.innerHTML = "<p>Nenhum produto no catálogo.</p>";
      return;
    }
    const strip = (s) => s.replace(/[^a-zA-Z0-9]/g, "_");
    let batch = { metricas_por_produto: {} };
    try {
      const q = encodeURIComponent(names.join(","));
      batch = await apiGet(`/api/galeria/metricas-batch?produtos=${q}`);
    } catch {
      /* fallback: métricas vazias */
    }
    const mp = batch.metricas_por_produto || {};

    let html = "";
    if (isAdmin) {
      html += `<div class="gallery-admin-toolbar">
        <button type="button" class="btn btn-secondary btn-sm btn-gallery-admin-new"><i class="fas fa-plus"></i> Novo empreendimento</button>
      </div>`;
    }
    html += '<div class="gallery-prod-tabs">';
    names.forEach((n, i) => {
      html += `<button type="button" class="tab-btn ${i === 0 ? "active" : ""}" data-prod="${encodeURIComponent(n)}">${n}</button>`;
    });
    html += "</div>";
    names.forEach((n, i) => {
      const meta = cat[n] || {};
      const id = strip(n);
      const met = mp[n] || {};
      html += `<div class="gallery-panel ${i === 0 ? "" : "hidden"}" data-panel="${encodeURIComponent(n)}">`;
      if (isAdmin) {
        html += `<div class="gallery-admin-row">
          <button type="button" class="btn btn-secondary btn-sm btn-gallery-admin-edit" data-prod="${encodeURIComponent(n)}"><i class="fas fa-pen-to-square"></i> Editar</button>
        </div>`;
      }
      html += '<div class="gallery-split">';
      html += `<div class="gallery-col"><h4>Vídeo</h4><div class="gallery-video-host"></div></div>`;
      html += `<div class="gallery-col"><h4>Mapa</h4><div class="gallery-map-wrap"><div id="map-${id}" class="gallery-map"></div><button type="button" class="gallery-map-fullscreen-btn" data-map-name="${encodeURIComponent(n)}" title="Tela cheia"><i class="fas fa-expand"></i></button></div></div></div>`;
      html += `<h4>Métricas (estoque)</h4><div class="gallery-metricas" data-metricas="${encodeURIComponent(n)}">${galleryMetricasHtml(met)}</div>`;
      const imgs = meta.imagens || [];
      const imageLinks = [];
      const bookLinks = [];
      imgs.forEach((it) => {
        let lk = it.link || "";
        if (lk.includes("drive.google.com/file/d/")) {
          const mid = lk.split("/d/")[1]?.split("/")[0];
          if (mid) lk = `https://drive.google.com/thumbnail?id=${mid}&sz=w800`;
        }
        const nameLower = (it.nome || "").toLowerCase();
        if (nameLower.includes("book") || nameLower.includes("ficha")) {
          bookLinks.push({ nome: it.nome, link: it.link || lk });
        } else {
          imageLinks.push({ nome: it.nome, link: lk });
        }
      });
      html += '<h4>Imagens</h4><div class="gallery-imgs">';
      imageLinks.forEach((it) => {
        html += `<img src="${it.link}" alt="${it.nome || ""}" class="gthumb" loading="lazy" decoding="async"/>`;
      });
      html += "</div>";
      if (bookLinks.length) {
        html += '<div class="gallery-download-btns">';
        bookLinks.forEach((it) => {
          html += `<a href="${it.link}" target="_blank" rel="noopener noreferrer" class="btn btn-secondary btn-sm"><i class="fas fa-download"></i> ${it.nome || "Baixar Book/Ficha"}</a>`;
        });
        html += "</div>";
      }
      html += "</div>";
    });
    host.innerHTML = html;

    host.querySelectorAll(".gallery-panel").forEach((panel) => {
      const key = panel.getAttribute("data-panel");
      if (!key) return;
      const name = decodeURIComponent(key);
      const meta = cat[name] || {};
      const linkList = (meta.imagens || [])
        .filter((it) => {
          const nl = (it.nome || "").toLowerCase();
          return !nl.includes("book") && !nl.includes("ficha");
        })
        .map((it) => {
          let lk = it.link || "";
          if (lk.includes("drive.google.com/file/d/")) {
            const mid = lk.split("/d/")[1]?.split("/")[0];
            if (mid) lk = `https://drive.google.com/thumbnail?id=${mid}&sz=w800`;
          }
          return lk;
        });
      panel.querySelectorAll("img.gthumb").forEach((img, idx) => {
        img.addEventListener("click", () => openGalleryModal(linkList, idx));
      });
    });

    host.querySelectorAll(".gallery-map-fullscreen-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const name = decodeURIComponent(btn.getAttribute("data-map-name") || "");
        openMapFullscreen(name);
      });
    });

    host.querySelectorAll(".gallery-prod-tabs .tab-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const key = btn.getAttribute("data-prod");
        host.querySelectorAll(".gallery-prod-tabs .tab-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        host.querySelectorAll(".gallery-panel").forEach((p) => {
          p.classList.toggle("hidden", p.getAttribute("data-panel") !== key);
        });
        const name = decodeURIComponent(key || "");
        galleryActivateTabContent(host, cat, name, strip);
      });
    });

    host.querySelector(".btn-gallery-admin-new")?.addEventListener("click", () => openGaleriaCreateModal());

    host.querySelectorAll(".btn-gallery-admin-edit").forEach((btn) => {
      btn.addEventListener("click", () => {
        const key = btn.getAttribute("data-prod");
        const nome = decodeURIComponent(key || "");
        openGaleriaEditModal(nome, cat[nome] || {});
      });
    });

    galleryActivateTabContent(host, cat, names[0], strip);
  } catch (e) {
    host.innerHTML = "<p>Erro: " + e.message + "</p>";
  }
}

$("galeria-edit-add-img")?.addEventListener("click", () => addGaleriaEditImagemRow());
$("galeria-edit-cancel")?.addEventListener("click", closeGaleriaEditModal);
$("galeria-edit-delete")?.addEventListener("click", async () => {
  const nome = _galeriaEditNomeAtual;
  if (!nome || _galeriaEditModo !== "edit") return;
  if (!confirm(`Remover «${nome}» da galeria?`)) return;
  const msg = $("galeria-edit-msg");
  try {
    await apiDelete(`/api/galeria/produto/${encodeURIComponent(nome)}`);
    closeGaleriaEditModal();
    await loadGalleryCatalog();
  } catch (e) {
    if (msg) { msg.textContent = e.message || "Erro ao excluir."; msg.style.color = "var(--cor-vermelho)"; }
  }
});
$("galeria-edit-save")?.addEventListener("click", async () => {
  const msg = $("galeria-edit-msg");
  const list = $("galeria-edit-imagens-list");
  const rows = list
    ? [...list.querySelectorAll(".galeria-edit-img-row")].map((w) => {
        const [inN, inL] = w.querySelectorAll("input");
        return { nome: inN?.value?.trim() || "", link: inL?.value?.trim() || "" };
      }).filter((r) => r.nome || r.link)
    : [];
  const video = $("galeria-edit-video")?.value?.trim() ?? "";
  const lt = $("galeria-edit-lat")?.value?.trim() ?? "";
  const ln = $("galeria-edit-lon")?.value?.trim() ?? "";

  try {
    if (_galeriaEditModo === "create") {
      const nomeNovo = $("galeria-edit-nome")?.value?.trim() ?? "";
      if (!nomeNovo) {
        if (msg) { msg.textContent = "Indique o nome do empreendimento."; msg.style.color = "var(--cor-vermelho)"; }
        return;
      }
      const body = { nome: nomeNovo, video, imagens: rows };
      const x = lt !== "" ? parseFloat(lt.replace(",", ".")) : NaN;
      const y = ln !== "" ? parseFloat(ln.replace(",", ".")) : NaN;
      if (lt !== "" && Number.isFinite(x)) body.lat = x;
      if (ln !== "" && Number.isFinite(y)) body.lon = y;
      await apiPost("/api/galeria/produto", body);
    } else {
      const nome = _galeriaEditNomeAtual;
      if (!nome) return;
      const patch = { video, imagens: rows };
      if (lt === "") patch.lat = null;
      else {
        const x = parseFloat(lt.replace(",", "."));
        if (Number.isFinite(x)) patch.lat = x;
      }
      if (ln === "") patch.lon = null;
      else {
        const y = parseFloat(ln.replace(",", "."));
        if (Number.isFinite(y)) patch.lon = y;
      }
      await apiPatch(`/api/galeria/produto/${encodeURIComponent(nome)}`, patch);
    }
    if (msg) { msg.textContent = "Guardado com sucesso."; msg.style.color = "var(--cor-azul-esc)"; }
    closeGaleriaEditModal();
    await loadGalleryCatalog();
  } catch (e) {
    if (msg) { msg.textContent = e.message || "Erro ao guardar."; msg.style.color = "var(--cor-vermelho)"; }
  }
});

/* ---------- Home banners (ADM) ---------- */
function addHomeBannerUrlRow(value = "") {
  const list = $("home-banners-url-list");
  if (!list) return;
  const wrap = document.createElement("div");
  wrap.className = "home-banners-url-row";
  const inp = document.createElement("input");
  inp.type = "url";
  inp.className = "input-field";
  inp.placeholder = "https://...";
  inp.value = value;
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "btn btn-secondary btn-sm";
  btn.textContent = "Remover";
  btn.addEventListener("click", () => wrap.remove());
  wrap.append(inp, btn);
  list.appendChild(wrap);
}

function openHomeBannersModal() {
  const ov = $("home-banners-overlay");
  const msg = $("home-banners-msg");
  if (msg) msg.textContent = "";
  const list = $("home-banners-url-list");
  if (list) list.innerHTML = "";
  apiGet("/api/home/banners")
    .then((data) => {
      const imgs = Array.isArray(data.imagens) ? data.imagens : [];
      if (!imgs.length) DEFAULT_HOME_BANNER_URLS.forEach((u) => addHomeBannerUrlRow(u));
      else imgs.forEach((u) => addHomeBannerUrlRow(u));
      ov?.classList.remove("hidden");
    })
    .catch((e) => {
      if (msg) { msg.textContent = e.message || "Erro ao carregar."; msg.style.color = "var(--cor-vermelho)"; }
    });
}

function closeHomeBannersModal() {
  $("home-banners-overlay")?.classList.add("hidden");
}

$("btn-home-banners-edit")?.addEventListener("click", () => openHomeBannersModal());
$("home-banners-cancel")?.addEventListener("click", closeHomeBannersModal);
$("home-banners-add-row")?.addEventListener("click", () => addHomeBannerUrlRow());
$("home-banners-save")?.addEventListener("click", async () => {
  const msg = $("home-banners-msg");
  const list = $("home-banners-url-list");
  const urls = list
    ? [...list.querySelectorAll(".home-banners-url-row input")].map((i) => i.value.trim()).filter(Boolean)
    : [];
  try {
    await apiPut("/api/home/banners", { imagens: urls });
    if (msg) { msg.textContent = "Guardado."; msg.style.color = "var(--cor-azul-esc)"; }
    closeHomeBannersModal();
    await loadHomeBanners({ force: true });
  } catch (e) {
    if (msg) { msg.textContent = e.message || "Erro ao guardar."; msg.style.color = "var(--cor-vermelho)"; }
  }
});

let _modalImages = [];
let _modalIdx = 0;

function openGalleryModal(images, index) {
  _modalImages = images; _modalIdx = index;
  const modal = $("gallery-modal");
  const im = $("gallery-modal-img");
  if (im) im.src = images[index] || "";
  if (modal) { modal.classList.add("is-open"); modal.setAttribute("aria-hidden", "false"); }
}
function closeGalleryModal() {
  const modal = $("gallery-modal");
  if (modal) { modal.classList.remove("is-open"); modal.setAttribute("aria-hidden", "true"); }
}
function stepGalleryModal(delta) {
  if (!_modalImages.length) return;
  _modalIdx = (_modalIdx + delta + _modalImages.length) % _modalImages.length;
  const im = $("gallery-modal-img");
  if (im) im.src = _modalImages[_modalIdx];
}
$("gallery-modal-close")?.addEventListener("click", closeGalleryModal);
$("gallery-modal-prev")?.addEventListener("click", () => stepGalleryModal(-1));
$("gallery-modal-next")?.addEventListener("click", () => stepGalleryModal(1));

/* ================================================================
   ANALYTICS
   ================================================================ */
let _chartCompra, _chartRenda, _chartFluxo;
function destroyCharts() {
  [_chartCompra, _chartRenda, _chartFluxo].forEach((c) => { try { c?.destroy(); } catch { /* noop */ } });
  _chartCompra = _chartRenda = _chartFluxo = null;
}

async function loadAnalyticsCharts() {
  const titulo = $("analytics-titulo");
  const cards = $("analytics-cards");
  try {
    await ensureChartLibs();
    const data = await apiGet("/api/analytics/cliente");
    const d = data.dados_cliente || {};
    if (titulo) titulo.textContent = `Painel do Cliente: ${d.nome || "Não informado"}`;
    if (cards) {
      cards.innerHTML = `
        <div class="hover-card"><strong>Dados pessoais</strong><p>Ranking: ${d.ranking || "—"}</p></div>
        <div class="hover-card"><strong>Renda</strong><p>R$ ${fmtBR(d.renda || 0)}</p></div>
        <div class="hover-card"><strong>Imóvel</strong><p>${d.empreendimento_nome || "—"} · ${d.unidade_id || "—"}</p></div>`;
    }
    destroyCharts();
    const Chart = window.Chart;
    if (!Chart) return;
    const comp = data.composicao_compra || [];
    const ren = data.composicao_renda || [];
    const elC = $("chart-compra"), elR = $("chart-renda"), elF = $("chart-fluxo");
    const animOff = { animation: false, animations: { colors: false, numbers: false } };
    if (elC && comp.length) {
      _chartCompra = new Chart(elC, {
        type: "pie",
        data: { labels: comp.map((x) => x.tipo), datasets: [{ data: comp.map((x) => x.valor), backgroundColor: ["#e30613","#c0392b","#94a3b8","#64748b","#f59e0b","#002c5d","#10b981"] }] },
        options: { ...animOff, plugins: { legend: { position: "bottom" } } },
      });
    }
    if (elR && ren.length) {
      _chartRenda = new Chart(elR, {
        type: "pie",
        data: { labels: ren.map((x) => x.participante), datasets: [{ data: ren.map((x) => x.renda), backgroundColor: ["#002c5d","#e30613","#f59e0b","#10b981"] }] },
        options: { ...animOff, plugins: { legend: { position: "bottom" } } },
      });
    }
    const fluxo = data.fluxo_mensal || [];
    const marc = data.marcadores || {};
    if (elF && fluxo.length) {
      const labels = fluxo.map((r) => String(r["Mês"] ?? r.Mês ?? r.mes ?? ""));
      const fin = fluxo.map((r) => Number(r.financiamento ?? 0));
      const ps = fluxo.map((r) => Number(r.pro_soluto ?? 0));
      const ato = fluxo.map((r) => Number(r.atos ?? 0));
      const hasStack = fin.some((n) => n > 0) || ps.some((n) => n > 0) || ato.some((n) => n > 0);
      const annotations = {};
      const ma = Number(marc.mes_fim_atos ?? 0);
      const mp = Number(marc.mes_fim_ps ?? 0);
      if (ma > 0 && labels.includes(String(ma))) {
        annotations.fimAtos = {
          type: "line",
          xMin: String(ma),
          xMax: String(ma),
          borderColor: "rgba(71, 85, 105, 0.95)",
          borderWidth: 2,
          borderDash: [8, 5],
          label: {
            display: true,
            content: "Fim dos atos",
            position: "start",
            backgroundColor: "rgba(71, 85, 105, 0.88)",
            color: "#fff",
            padding: 4,
            borderRadius: 4,
            font: { size: 10, weight: "600" },
          },
        };
      }
      if (mp > 0 && labels.includes(String(mp))) {
        annotations.fimPs = {
          type: "line",
          xMin: String(mp),
          xMax: String(mp),
          borderColor: "rgba(124, 58, 237, 0.95)",
          borderWidth: 2,
          borderDash: [8, 5],
          label: {
            display: true,
            content: "Fim do Pro Soluto",
            position: "start",
            backgroundColor: "rgba(124, 58, 237, 0.88)",
            color: "#fff",
            padding: 4,
            borderRadius: 4,
            font: { size: 10, weight: "600" },
          },
        };
      }
      const datasets = hasStack
        ? [
            { label: "Parcela financiamento", data: fin, backgroundColor: "rgba(0, 44, 93, 0.88)", stack: "fluxo" },
            { label: "Pro Soluto", data: ps, backgroundColor: "rgba(245, 158, 11, 0.92)", stack: "fluxo" },
            { label: "Atos", data: ato, backgroundColor: "rgba(227, 6, 19, 0.88)", stack: "fluxo" },
          ]
        : [{ label: "Total mensal (R$)", data: fluxo.map((r) => Number(r["Total"] ?? r.Total ?? 0)), backgroundColor: "#002c5d" }];
      _chartFluxo = new Chart(elF, {
        type: "bar",
        data: { labels, datasets },
        options: {
          ...animOff,
          responsive: true,
          maintainAspectRatio: true,
          interaction: { mode: "index", intersect: false },
          plugins: {
            legend: { position: "bottom" },
            tooltip: {
              callbacks: {
                label(ctx) {
                  const v = ctx.parsed.y;
                  if (v == null || Number.isNaN(v)) return `${ctx.dataset.label}: —`;
                  if (v === 0) return `${ctx.dataset.label}: R$ 0,00`;
                  return `${ctx.dataset.label}: R$ ${fmtBR(v)}`;
                },
                footer(tooltipItems) {
                  if (!tooltipItems.length || !hasStack) return "";
                  const idx = tooltipItems[0].dataIndex;
                  const row = fluxo[idx];
                  if (!row) return "";
                  const t = Number(row.Total ?? 0);
                  return `Total do mês: R$ ${fmtBR(t)}`;
                },
              },
            },
            zoom: {
              limits: { x: { minRange: 6 } },
              pan: { enabled: true, mode: "x" },
              zoom: {
                wheel: { enabled: true },
                pinch: { enabled: true },
                mode: "x",
              },
            },
            annotation: { annotations },
          },
          scales: {
            x: {
              stacked: hasStack,
              title: { display: true, text: "Mês" },
              ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 48 },
            },
            y: {
              stacked: hasStack,
              beginAtZero: true,
              title: { display: true, text: "Valor (R$)" },
              ticks: {
                callback(v) {
                  const n = Number(v);
                  if (n >= 1e6) return `R$ ${(n / 1e6).toFixed(1)}M`;
                  if (n >= 1e3) return `R$ ${(n / 1e3).toFixed(0)}k`;
                  return `R$ ${fmtBR(n)}`;
                },
              },
            },
          },
        },
      });
    }
  } catch (e) {
    if (cards) cards.textContent = "Erro: " + e.message;
  }
}

/* ================================================================
   CORE: goStep + refreshUI
   ================================================================ */

async function goStep(passo) {
  await apiPatch("/api/session", { passo_simulacao: passo });
  if (passo === "gallery") {
    loadPage("galeria");
  } else {
    loadPage("simulador");
  }
  await refreshUI();
}

function populateFormFromDadosCliente(dc) {
  if (!dc || !Object.keys(dc).length) return;
  const form = $("form-cadastro");
  if (!form) return;
  const setVal = (name, val) => { const el = form.querySelector(`[name="${name}"]`); if (el && val != null) el.value = val; };
  setVal("nome", dc.nome);
  if (dc.cpf) {
    const cpfEl = form.querySelector('[name="cpf"]');
    if (cpfEl) {
      let cpf = String(dc.cpf).replace(/\D/g, "");
      if (cpf.length === 11) cpf = cpf.slice(0,3)+"."+cpf.slice(3,6)+"."+cpf.slice(6,9)+"-"+cpf.slice(9);
      cpfEl.value = cpf;
    }
  }
  if (dc.data_nascimento) {
    const dnEl = form.querySelector('[name="data_nascimento"]');
    if (dnEl) {
      let dn = String(dc.data_nascimento);
      if (dn.includes("/")) { const p = dn.split("/"); dn = `${p[2]}-${p[1]}-${p[0]}`; }
      dnEl.value = dn.slice(0, 10);
    }
  }
  setVal("qtd_participantes", dc.qtd_participantes || 1);
  renderRendasInputs(dc.qtd_participantes || 1, dc.rendas_lista);
  setVal("ranking", dc.ranking);
  setVal("politica", dc.politica);
  const socialCb = form.querySelector('[name="social"]');
  if (socialCb) socialCb.checked = !!dc.social;
  const cotCb = form.querySelector('[name="cotista"]');
  if (cotCb) cotCb.checked = dc.cotista !== false;
}

async function refreshUI() {
  try {
    const estado = await apiGet("/api/session");
    _estadoCache = estado;
    const passo = estado.passo_simulacao || "input";

    if (passo !== "client_analytics") {
      destroyCharts();
    }

    $("panel-login").style.display = "none";
    $("main-app").style.display = "";

    setProfileInfo(estado);

    const bannersP = loadHomeBanners();

    renderStepper($("stepper-host"), passo);
    showStepSection(passo);

    const dc = estado.dados_cliente || {};
    populateFormFromDadosCliente(dc);

    const caBox = $("cliente-ativo-box");
    const btnNext = $("btn-next-input");
    if (estado.cliente_ativo && dc.nome) {
      if (caBox) { caBox.classList.remove("hidden"); $("cliente-ativo-nome").textContent = dc.nome; }
      if (btnNext) btnNext.disabled = false;
    } else {
      if (caBox) caBox.classList.add("hidden");
      if (btnNext) btnNext.disabled = true;
    }

    await bannersP;

    const shouldLoadHeavy = passo !== _lastHeavyPassoLoaded;

    if (passo === "fechamento_aprovado" && shouldLoadHeavy) await loadFechamentoContexto();
    if (passo === "guide" && shouldLoadHeavy) await loadGuideData();
    if (passo === "selection" && shouldLoadHeavy) await loadSelectionEmpreendimentos();
    if (passo === "payment_flow" && shouldLoadHeavy) await loadPaymentContexto();
    if (passo === "summary" && shouldLoadHeavy) await loadResumoBlocos();
    if (passo === "gallery" && shouldLoadHeavy) await loadGalleryCatalog();
    if (passo === "client_analytics" && shouldLoadHeavy) await loadAnalyticsCharts();

    _lastHeavyPassoLoaded = passo;

    scheduleIdle(() => updateNavIndicator());

    return estado;
  } catch (e) {
    $("main-app").style.display = "none";
    $("panel-login").style.display = "";
    throw e;
  }
}

/* ---------- (historico agora via modal — ver loadHistoricoModalResults) ---------- */

/* ================================================================
   LOGOUT
   ================================================================ */
async function doLogout() {
  try { await apiPost("/api/auth/logout", {}); } catch { try { await apiDelete("/api/session"); } catch { /* noop */ } }
  _estadoCache = null;
  _lastHeavyPassoLoaded = null;
  _homeBannersFetchedAt = 0;
  destroyCharts();
  destroyGalleryResources();
  $("main-app").style.display = "none";
  $("panel-login").style.display = "";
  const form = $("form-login");
  if (form) form.reset();
  $("login-msg").textContent = "";
}

/* ================================================================
   EVENT LISTENERS
   ================================================================ */

// --- Login ---
$("form-login")?.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const fd = new FormData(ev.target);
  const msg = $("login-msg");
  if (msg) msg.textContent = "";
  try {
    const data = await apiPost("/api/auth/login", {
      email: fd.get("email") || "",
      password: fd.get("password") || "",
    });
    if (data.ok) {
      showMsg(msg, "Login realizado!", true);
      loadPage("home");
      await refreshUI();
    } else {
      showMsg(msg, "Credenciais inválidas.", false);
    }
  } catch (e) {
    showMsg(msg, e.message || "Erro no login.", false);
  }
});


// --- Rendas dinâmicas ---
$("qtd-participantes")?.addEventListener("change", (ev) => renderRendasInputs(ev.target.value));
renderRendasInputs(1);

// --- Cadastro submit ---
$("form-cadastro")?.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const fd = new FormData(ev.target);
  const qtd = parseInt(fd.get("qtd_participantes"), 10) || 1;
  const rendas_lista = [];
  for (let i = 0; i < qtd; i++) {
    const v = fd.get(`renda_${i}`);
    rendas_lista.push(v ? parseFloat(v) : 0);
  }
  const form = ev.target;
  const cpfRaw = String(fd.get("cpf") || "").trim();
  const el = $("cadastro-msg");
  if (!validarCPF(cpfRaw)) {
    showMsg(el, "CPF inválido. Verifique os dígitos.", false);
    return;
  }
  const body = {
    nome: String(fd.get("nome") || "").trim(),
    cpf: cpfRaw,
    data_nascimento: fd.get("data_nascimento") || null,
    qtd_participantes: qtd,
    rendas_lista,
    ranking: fd.get("ranking") || "DIAMANTE",
    politica: fd.get("politica") || "Direcional",
    social: !!form.querySelector('[name="social"]')?.checked,
    cotista: form.querySelector('[name="cotista"]') ? !!form.querySelector('[name="cotista"]').checked : true,
  };
  try {
    await apiPost("/api/cliente/confirmar", body);
    showMsg(el, "Cliente ativo — pode avançar.", true);
    await refreshUI();
  } catch (e) {
    showMsg(el, e.message, false);
  }
});

// --- Buscar Base Cadastrada (dialog) ---
$("btn-buscar-base")?.addEventListener("click", () => {
  $("busca-overlay")?.classList.remove("hidden");
  $("busca-dialog-input")?.focus();
});
$("btn-close-busca")?.addEventListener("click", () => $("busca-overlay")?.classList.add("hidden"));
$("btn-busca-dialog-search")?.addEventListener("click", async () => {
  const q = $("busca-dialog-input")?.value || "";
  const ul = $("busca-dialog-results");
  if (ul) ul.innerHTML = "<li class='muted'>A pesquisar…</li>";
  try {
    const data = await apiGet(`/api/cadastros/buscar?q=${encodeURIComponent(q)}`);
    const itens = data.itens || [];
    const fonte = data.fonte || "";
    if (ul) {
      ul.innerHTML = "";
      itens.forEach((row) => {
        const li = document.createElement("li");
        const nome = row.Nome || row.nome || "—";
        const cpf = row.CPF || row.cpf || "";
        li.innerHTML = `<button type="button" class="historico-btn">${nome} - ${cpf}</button>`;
        li.querySelector("button")?.addEventListener("click", async () => {
          try {
            if (fonte === "bd_clientes" && cpf) {
              await apiPost("/api/cliente/ativar-por-cpf", { cpf: String(cpf).replace(/\D/g, "") });
            } else {
              await apiPost("/api/cliente/importar-historico", { row });
            }
            $("busca-overlay")?.classList.add("hidden");
            loadPage("simulador");
            await goStep("fechamento_aprovado");
          } catch (e) { alert(e.message); }
        });
        ul.appendChild(li);
      });
      if (!itens.length) ul.innerHTML = "<li class='muted'>Nenhum resultado.</li>";
    }
  } catch (e) {
    if (ul) ul.innerHTML = `<li class='muted'>Erro: ${e.message}</li>`;
  }
});

// --- Step navigation ---
$("btn-next-input")?.addEventListener("click", () => goStep("fechamento_aprovado"));

$("form-fechamento")?.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const fd = new FormData(ev.target);
  const num = (k) => { const v = fd.get(k); return v ? parseFloat(v) : undefined; };
  const body = {
    finan_usado: num("finan_usado"),
    fgts_sub_usado: num("fgts_sub_usado"),
    prazo_financiamento: fd.get("prazo_financiamento") ? parseInt(fd.get("prazo_financiamento"), 10) : undefined,
    sistema_amortizacao: fd.get("sistema_amortizacao") || undefined,
  };
  const el = $("fechamento-msg");
  try {
    await apiPut("/api/fechamento", body);
    showMsg(el, "Fechamento guardado.", true);
    await loadFechamentoContexto();
  } catch (e) { showMsg(el, e.message, false); }
});

$("fech-sistema")?.addEventListener("change", () => renderComparativo());
$("btn-fechamento-guide")?.addEventListener("click", () => goStep("guide"));
$("btn-fechamento-selection")?.addEventListener("click", () => goStep("selection"));
$("btn-back-fechamento_aprovado")?.addEventListener("click", () => goStep("input"));

document.querySelectorAll(".tabs-guide .tab-btn").forEach((b) => {
  b.addEventListener("click", () => {
    const tab = b.getAttribute("data-tab");
    document.querySelectorAll(".tabs-guide .tab-btn").forEach((x) => x.classList.remove("active"));
    b.classList.add("active");
    ["viaveis", "sugestoes", "estoque"].forEach((id) => {
      const p = $(`tab-panel-${id}`);
      if (p) p.classList.toggle("hidden", id !== tab);
    });
  });
});

$("guide-emp-filter")?.addEventListener("change", async (ev) => {
  const emp = ev.target.value;
  try {
    const data = await apiPost("/api/simulacao/recomendacoes", { empreendimento: emp === "Todos" ? null : emp });
    renderRecomendacoes(data);
  } catch (e) { console.error("[SIMULADOR] guide-emp-filter:", e); }
});

$("btn-next-guide")?.addEventListener("click", () => goStep("selection"));
$("btn-back-guide")?.addEventListener("click", () => goStep("fechamento_aprovado"));

$("sel-empreendimento")?.addEventListener("change", async (ev) => {
  const emp = ev.target.value;
  if (emp) await loadSelectionUnidades(emp);
});
$("sel-unidade")?.addEventListener("change", async () => { await loadTermometro(); });
$("valor-final-unidade")?.addEventListener("change", async () => { await loadTermometro(); });

$("btn-next-selection")?.addEventListener("click", async () => {
  const uid = $("sel-unidade")?.value;
  const emp = $("sel-empreendimento")?.value;
  const vf = $("valor-final-unidade")?.value;
  const el = $("unidade-msg");
  if (!uid || !emp) { showMsg(el, "Selecione empreendimento e unidade.", false); return; }
  try {
    const body = { identificador: uid };
    if (vf && parseFloat(vf) > 0) body.valor_final = parseFloat(vf);
    await apiPost("/api/estoque/selecionar", body);
    showMsg(el, "Unidade selecionada.", true);
    await goStep("payment_flow");
  } catch (e) { showMsg(el, e.message, false); }
});
$("btn-back-selection")?.addEventListener("click", () => goStep("guide"));

const _debouncedPatchPayment = debounce(patchPaymentAndRefresh, 300);
const payFields = ["pay-ato1", "pay-ato2", "pay-ato3", "pay-ato4", "pay-ps", "pay-ps-parc", "pay-vc"];
payFields.forEach((id) => {
  const el = $(id);
  if (!el) return;
  el.addEventListener("change", _debouncedPatchPayment);
  el.addEventListener("input", _debouncedPatchPayment);
});

$("btn-dist-2")?.addEventListener("click", async () => {
  const gapEl = $("gap-status");
  try {
    if (!_estadoCache) _estadoCache = await apiGet("/api/session");
    const r = restanteParaAtosParcelados(_estadoCache?.dados_cliente || {});
    if (r <= 0.01 && gapEl) {
      gapEl.className = "gap-status gap-erro";
      gapEl.textContent = "Não há saldo restante a parcelar em 30/60 (após financiamento, subsídio, PS e ato imediato). Ajuste os valores no passo anterior.";
      return;
    }
    await apiPost("/api/pagamento/distribuir", { n_parcelas: 2 });
    await loadPaymentContexto();
  } catch (e) {
    console.error("[SIMULADOR] dist-2:", e);
  }
});
$("btn-dist-3")?.addEventListener("click", async () => {
  const gapEl = $("gap-status");
  try {
    if (!_estadoCache) _estadoCache = await apiGet("/api/session");
    const r = restanteParaAtosParcelados(_estadoCache?.dados_cliente || {});
    if (r <= 0.01 && gapEl) {
      gapEl.className = "gap-status gap-erro";
      gapEl.textContent = "Não há saldo restante a parcelar em 30/60/90. Ajuste financiamento, subsídio, PS ou ato imediato.";
      return;
    }
    await apiPost("/api/pagamento/distribuir", { n_parcelas: 3 });
    await loadPaymentContexto();
  } catch (e) {
    console.error("[SIMULADOR] dist-3:", e);
  }
});

$("btn-next-payment_flow")?.addEventListener("click", () => goStep("summary"));
$("btn-back-payment_flow")?.addEventListener("click", () => goStep("selection"));

$("btn-export-dialog")?.addEventListener("click", () => $("export-overlay")?.classList.remove("hidden"));
$("btn-close-export")?.addEventListener("click", () => $("export-overlay")?.classList.add("hidden"));

$("btn-pdf")?.addEventListener("click", async () => {
  try {
    const r = await fetch("/api/pdf", { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: "{}" });
    if (!r.ok) throw new Error(await r.text());
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "resumo_simulacao.pdf"; a.click();
    URL.revokeObjectURL(url);
  } catch (e) { alert(e.message); }
});

$("btn-send-email")?.addEventListener("click", async () => {
  const email = $("export-email")?.value;
  if (!email || !email.includes("@")) { alert("E-mail inválido."); return; }
  try {
    const data = await apiPost("/api/email", { email_destino: email });
    alert(data.message || "E-mail enviado!");
  } catch (e) { alert(e.message); }
});

$("btn-salvar-sheets")?.addEventListener("click", async () => {
  const msg = $("salvar-msg");
  if (msg) msg.textContent = "A gravar…";
  try {
    const data = await apiPost("/api/salvar-simulacao", {});
    if (msg) showMsg(msg, data.message || "Salvo com sucesso!", true);
    try { await apiPatch("/api/session", { dados_cliente: {}, cliente_ativo: false, passo_simulacao: "input" }); } catch { /* noop */ }
    const form = $("form-cadastro");
    if (form) form.reset();
    renderRendasInputs(1);
    await refreshUI();
  } catch (e) { if (msg) showMsg(msg, e.message, false); }
});

$("btn-back-summary")?.addEventListener("click", () => goStep("payment_flow"));

// --- Nav links (top bar) ---
$("nav-simulador")?.addEventListener("click", () => {
  void navigateToSimuladorFromNav();
});
$("nav-galeria")?.addEventListener("click", () => {
  void withTopNavGuard(async () => {
    await goStep("gallery");
  });
});
$("nav-campanhas")?.addEventListener("click", () => {
  void withTopNavGuard(async () => {
    setAppView("campanhas");
  });
});
$("nav-treinamentos")?.addEventListener("click", () => {
  void withTopNavGuard(async () => {
    setAppView("treinamentos");
  });
});

// --- Home section buttons ---
$("home-btn-simulador")?.addEventListener("click", () => {
  void navigateToSimuladorFromNav();
});
$("home-btn-galeria")?.addEventListener("click", () => {
  void withTopNavGuard(async () => {
    await goStep("gallery");
  });
});
$("home-btn-campanhas")?.addEventListener("click", () => {
  void withTopNavGuard(async () => {
    setAppView("campanhas");
  });
});
$("home-btn-treinamentos")?.addEventListener("click", () => {
  void withTopNavGuard(async () => {
    setAppView("treinamentos");
  });
});

// --- Logo click -> home ---
$("nav-logo")?.addEventListener("click", () => {
  void withTopNavGuard(async () => {
    setAppView("home");
  });
});

// Analytics
$("btn-back-analytics")?.addEventListener("click", () => goStep("input"));

/* ================================================================
   CURRENCY FORMAT (blur/focus)
   ================================================================ */
function parseCurrencyValue(val) {
  if (val == null || val === "") return NaN;
  let s = String(val).replace(/[R$\s]/g, "");
  if (s.includes(",") && s.includes(".")) {
    s = s.replace(/\./g, "").replace(",", ".");
  } else if (s.includes(",")) {
    s = s.replace(",", ".");
  }
  return parseFloat(s);
}

function formatCurrencyField(input) {
  input.addEventListener("focus", () => {
    const n = parseCurrencyValue(input.value);
    input.type = "number";
    input.value = isNaN(n) || n === 0 ? "" : n;
  });
  input.addEventListener("blur", () => {
    const n = parseCurrencyValue(input.value);
    if (isNaN(n) || n === 0) { input.type = "text"; input.value = ""; return; }
    input.type = "text";
    input.value = "R$ " + fmtBR(n);
  });
}

const currencyFieldIds = ["fech-finan", "fech-sub", "pay-ato1", "pay-ato2", "pay-ato3", "pay-ato4", "pay-ps", "pay-vc", "valor-final-unidade", "est-pmax"];
currencyFieldIds.forEach((id) => {
  const el = $(id);
  if (el) formatCurrencyField(el);
});

// Arredondamento à curva no blur do financiamento
$("fech-finan")?.addEventListener("blur", () => {
  setTimeout(arredondarFinanciamentoCurva, 100);
});

/* ================================================================
   MAP FULLSCREEN
   ================================================================ */
$("map-fullscreen-close")?.addEventListener("click", () => {
  $("map-fullscreen-overlay")?.classList.add("hidden");
  const container = $("map-fullscreen-container");
  if (container) container.innerHTML = "";
});

async function openMapFullscreen(name) {
  const overlay = $("map-fullscreen-overlay");
  const container = $("map-fullscreen-container");
  if (!overlay || !container) return;
  try {
    await ensureLeaflet();
  } catch {
    return;
  }
  overlay.classList.remove("hidden");
  container.innerHTML = "";

  const mapDiv = document.createElement("div");
  mapDiv.style.width = "100%";
  mapDiv.style.height = "100%";
  container.appendChild(mapDiv);

  const originalMap = _galleryMaps.get(name);
  if (originalMap && typeof window.L !== "undefined") {
    const center = originalMap.getCenter();
    const zoom = originalMap.getZoom();
    const fsMap = window.L.map(mapDiv).setView(center, zoom);
    window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: "© OSM" }).addTo(fsMap);
    window.L.marker(center).addTo(fsMap).bindPopup(name);
    setTimeout(() => fsMap.invalidateSize(), 200);
  }
}

/* ================================================================
   CAMPANHAS / TREINAMENTOS
   ================================================================ */

function conteudoNormalizeItem(it) {
  return {
    ...it,
    video_url: it.video_url || "",
    imagens_drive: Array.isArray(it.imagens_drive) ? it.imagens_drive : [],
    pdfs: Array.isArray(it.pdfs) ? it.pdfs : [],
  };
}

function escapeHtml(s) {
  if (s == null) return "";
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** href / src — não usar escapeHtml (quebra ?foo=1&bar=2); bloqueia javascript:/data: */
function sanitizeUrl(u) {
  const s = String(u || "").trim();
  if (/^javascript:/i.test(s) || /^data:text\/html/i.test(s)) return "#";
  return s;
}

function conteudoCapaSrc(url) {
  if (!url) return "";
  if (typeof url === "string" && url.includes("drive.google.com/file/d/")) return driveThumbnailUrl(url);
  return url;
}

function addConteudoMediaRow(listEl, titulo = "", url = "") {
  if (!listEl) return;
  const wrap = document.createElement("div");
  wrap.className = "conteudo-media-row";
  const inT = document.createElement("input");
  inT.className = "input-field";
  inT.placeholder = "Título (opcional)";
  inT.value = titulo;
  const inU = document.createElement("input");
  inU.className = "input-field";
  inU.placeholder = "URL";
  inU.value = url;
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "btn btn-secondary btn-sm";
  btn.textContent = "Remover";
  btn.addEventListener("click", () => wrap.remove());
  wrap.append(inT, inU, btn);
  listEl.appendChild(wrap);
}

function collectConteudoMediaRows(listEl) {
  if (!listEl) return [];
  const rows = [];
  listEl.querySelectorAll(".conteudo-media-row").forEach((row) => {
    const inputs = row.querySelectorAll("input");
    const titulo = (inputs[0]?.value || "").trim();
    const url = (inputs[1]?.value || "").trim();
    if (url) rows.push({ titulo, url });
  });
  return rows;
}

function clearConteudoMediaLists() {
  const li = $("conteudo-imagens-list");
  const lp = $("conteudo-pdfs-list");
  if (li) li.innerHTML = "";
  if (lp) lp.innerHTML = "";
}

function openConteudoDetalhe(tipo, item) {
  _conteudoDetalheTipo = tipo;
  _conteudoDetalheItem = conteudoNormalizeItem(item);
  loadPage("conteudo_detalhe");
}

function renderConteudoDetalhe() {
  const host = $("conteudo-detalhe-host");
  if (!host || !_conteudoDetalheItem) {
    if (host) host.innerHTML = "<p class='muted'>Conteúdo não encontrado.</p>";
    return;
  }
  const it = _conteudoDetalheItem;
  const labelTipo = _conteudoDetalheTipo === "campanhas" ? "Campanha" : "Treinamento";
  const capa = conteudoCapaSrc(it.imagem);
  let html = `<div class="conteudo-detalhe-head">
    <span class="conteudo-detalhe-badge">${labelTipo}</span>
    <h2 class="conteudo-detalhe-title">${escapeHtml(it.titulo || "")}</h2>
    ${it.data ? `<p class="conteudo-detalhe-date"><i class="fas fa-calendar"></i> ${escapeHtml(it.data)}</p>` : ""}
  </div>`;
  if (capa) {
    html += `<div class="conteudo-detalhe-capa-wrap"><img src="${sanitizeUrl(capa)}" alt="" class="conteudo-detalhe-capa" /></div>`;
  }
  html += `<div class="conteudo-detalhe-desc">${escapeHtml(it.descricao || "").replace(/\n/g, "<br/>")}</div>`;

  const v = (it.video_url || "").trim();
  if (v) {
    const yt = youtubeEmbed(v);
    html += `<div class="conteudo-detalhe-block"><h3><i class="fas fa-video"></i> Vídeo</h3>`;
    if (yt) {
      html += `<iframe class="conteudo-detalhe-iframe" src="${sanitizeUrl(yt)}" allowfullscreen title="Vídeo"></iframe>`;
    } else if (drivePreviewEmbedUrl(v)) {
      const prev = drivePreviewEmbedUrl(v);
      html += `<iframe class="conteudo-detalhe-iframe" src="${sanitizeUrl(prev)}" allowfullscreen title="Vídeo Drive"></iframe>`;
      html += `<p class="muted"><a href="${sanitizeUrl(driveOpenUrl(v))}" target="_blank" rel="noopener noreferrer">Abrir no Google Drive <i class="fas fa-external-link-alt"></i></a></p>`;
    } else {
      html += `<p><a href="${sanitizeUrl(v)}" target="_blank" rel="noopener noreferrer" class="btn btn-secondary"><i class="fas fa-play"></i> Abrir vídeo</a></p>`;
    }
    html += `</div>`;
  }

  const imgs = it.imagens_drive || [];
  if (imgs.length) {
    html += `<div class="conteudo-detalhe-block"><h3><i class="fas fa-images"></i> Imagens</h3><div class="conteudo-detalhe-imgs">`;
    imgs.forEach((row) => {
      const raw = (row.url || "").trim();
      if (!raw) return;
      const thumb = raw.includes("drive.google.com/file/d/") ? driveThumbnailUrl(raw) : raw;
      const open = raw.includes("drive.google.com/") ? driveOpenUrl(raw) : raw;
      const t = row.titulo || "Imagem";
      html += `<a href="${sanitizeUrl(open)}" target="_blank" rel="noopener noreferrer" class="conteudo-detalhe-img-card" title="${escapeHtml(t)}">
        <img src="${sanitizeUrl(thumb)}" alt="${escapeHtml(t)}" loading="lazy" />
        <span>${escapeHtml(t)}</span>
      </a>`;
    });
    html += `</div></div>`;
  }

  const pdfs = it.pdfs || [];
  if (pdfs.length) {
    html += `<div class="conteudo-detalhe-block"><h3><i class="fas fa-file-pdf"></i> Documentos PDF</h3><div class="conteudo-detalhe-pdfs">`;
    pdfs.forEach((row) => {
      const raw = (row.url || "").trim();
      if (!raw) return;
      const href = driveOpenUrl(raw);
      const t = row.titulo || "PDF";
      const preview = drivePreviewEmbedUrl(raw);
      html += `<div class="conteudo-detalhe-pdf-item">
        <a href="${sanitizeUrl(href)}" target="_blank" rel="noopener noreferrer" class="btn btn-secondary btn-full"><i class="fas fa-file-pdf"></i> ${escapeHtml(t)}</a>`;
      if (preview) {
        html += `<iframe class="conteudo-detalhe-pdf-frame" src="${sanitizeUrl(preview)}" title="${escapeHtml(t)}"></iframe>`;
      }
      html += `</div>`;
    });
    html += `</div></div>`;
  }

  host.innerHTML = html;
}

$("conteudo-detalhe-voltar")?.addEventListener("click", () => {
  const back = _conteudoDetalheTipo === "treinamentos" ? "treinamentos" : "campanhas";
  loadPage(back);
});

async function loadCampanhas() {
  const host = $("campanhas-cards");
  const adminBar = $("campanhas-admin-bar");
  if (!host) return;
  host.innerHTML = '<div class="skeleton skeleton-card"></div>';
  try {
    const data = await apiGet("/api/conteudo/campanhas");
    const items = (data.campanhas || []).map(conteudoNormalizeItem);
    _conteudoListCache.campanhas = items;
    const isAdmin = data.is_admin === true;
    if (adminBar) adminBar.style.display = isAdmin ? "" : "none";
    renderConteudoCards(host, items, isAdmin, "campanhas");
  } catch (e) { host.innerHTML = `<p class="muted">Erro: ${e.message}</p>`; }
}

async function loadTreinamentos() {
  const host = $("treinamentos-cards");
  const adminBar = $("treinamentos-admin-bar");
  if (!host) return;
  host.innerHTML = '<div class="skeleton skeleton-card"></div>';
  try {
    const data = await apiGet("/api/conteudo/treinamentos");
    const items = (data.treinamentos || []).map(conteudoNormalizeItem);
    _conteudoListCache.treinamentos = items;
    const isAdmin = data.is_admin === true;
    if (adminBar) adminBar.style.display = isAdmin ? "" : "none";
    renderConteudoCards(host, items, isAdmin, "treinamentos");
  } catch (e) { host.innerHTML = `<p class="muted">Erro: ${e.message}</p>`; }
}

function renderConteudoCards(host, items, isAdmin, tipo) {
  if (!items.length) { host.innerHTML = '<p class="muted">Nenhum conteúdo disponível.</p>'; return; }
  let html = "";
  items.forEach((it) => {
    const capa = conteudoCapaSrc(it.imagem);
    html += `<div class="conteudo-card conteudo-card--clickable" data-tipo="${tipo}" data-id="${it.id}">`;
    if (capa) html += `<img src="${capa}" alt="${it.titulo}" class="conteudo-card-img" />`;
    html += `<div class="conteudo-card-body">
      <h4 class="conteudo-card-title">${it.titulo || ""}</h4>
      <p class="conteudo-card-desc">${it.descricao || ""}</p>
      <span class="conteudo-card-date">${it.data || ""}</span>`;
    html += `<p class="conteudo-card-hint muted"><i class="fas fa-arrow-right"></i> Clique para abrir a página completa</p>`;
    if (isAdmin) {
      html += `<div class="conteudo-card-admin">
        <button type="button" class="btn btn-secondary btn-sm conteudo-card-edit" data-id="${it.id}" data-tipo="${tipo}"><i class="fas fa-pen"></i> Editar</button>
        <button type="button" class="conteudo-card-delete" data-id="${it.id}" data-tipo="${tipo}"><i class="fas fa-trash"></i> Remover</button>
      </div>`;
    }
    html += `</div></div>`;
  });
  host.innerHTML = html;

  host.querySelectorAll(".conteudo-card--clickable").forEach((card) => {
    card.addEventListener("click", (ev) => {
      if (ev.target.closest(".conteudo-card-delete, .conteudo-card-edit, .conteudo-card-admin")) return;
      const id = card.dataset.id;
      const t = card.dataset.tipo;
      const list = _conteudoListCache[t] || [];
      const item = list.find((x) => x.id === id);
      if (item) openConteudoDetalhe(t, item);
    });
  });

  host.querySelectorAll(".conteudo-card-edit").forEach((btn) => {
    btn.addEventListener("click", (ev) => {
      ev.stopPropagation();
      const id = btn.dataset.id;
      const t = btn.dataset.tipo;
      const list = _conteudoListCache[t] || [];
      const item = list.find((x) => x.id === id);
      if (item) openConteudoEditModal(t, item);
    });
  });

  host.querySelectorAll(".conteudo-card-delete").forEach((btn) => {
    btn.addEventListener("click", async (ev) => {
      ev.stopPropagation();
      const id = btn.dataset.id;
      const t = btn.dataset.tipo;
      if (!confirm("Remover este item?")) return;
      try {
        await apiDelete(`/api/conteudo/${t}/${id}`);
        if (t === "campanhas") loadCampanhas();
        else loadTreinamentos();
      } catch (e) { alert(e.message); }
    });
  });
}

// Add content modal
$("btn-add-campanha")?.addEventListener("click", () => openConteudoModal("campanhas"));
$("btn-add-treinamento")?.addEventListener("click", () => openConteudoModal("treinamentos"));
$("btn-close-conteudo")?.addEventListener("click", () => $("conteudo-modal-overlay")?.classList.add("hidden"));
$("btn-conteudo-add-imagem")?.addEventListener("click", () => addConteudoMediaRow($("conteudo-imagens-list")));
$("btn-conteudo-add-pdf")?.addEventListener("click", () => addConteudoMediaRow($("conteudo-pdfs-list")));

function openConteudoModal(tipo) {
  $("conteudo-modal-overlay")?.classList.remove("hidden");
  $("conteudo-modal-title").textContent = tipo === "campanhas" ? "Adicionar Campanha" : "Adicionar Treinamento";
  $("conteudo-tipo").value = tipo;
  const idEl = $("conteudo-item-id");
  if (idEl) idEl.value = "";
  $("conteudo-titulo").value = "";
  $("conteudo-descricao").value = "";
  $("conteudo-imagem").value = "";
  $("conteudo-data").value = "";
  const v = $("conteudo-video");
  if (v) v.value = "";
  clearConteudoMediaLists();
}

function openConteudoEditModal(tipo, item) {
  const it = conteudoNormalizeItem(item);
  $("conteudo-modal-overlay")?.classList.remove("hidden");
  $("conteudo-modal-title").textContent = tipo === "campanhas" ? "Editar Campanha" : "Editar Treinamento";
  $("conteudo-tipo").value = tipo;
  const idEl = $("conteudo-item-id");
  if (idEl) idEl.value = it.id || "";
  $("conteudo-titulo").value = it.titulo || "";
  $("conteudo-descricao").value = it.descricao || "";
  $("conteudo-imagem").value = it.imagem || "";
  $("conteudo-data").value = it.data || "";
  const v = $("conteudo-video");
  if (v) v.value = it.video_url || "";
  clearConteudoMediaLists();
  (it.imagens_drive || []).forEach((r) => addConteudoMediaRow($("conteudo-imagens-list"), r.titulo || "", r.url || ""));
  (it.pdfs || []).forEach((r) => addConteudoMediaRow($("conteudo-pdfs-list"), r.titulo || "", r.url || ""));
}

$("form-conteudo")?.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const tipo = $("conteudo-tipo")?.value || "campanhas";
  const editId = ($("conteudo-item-id")?.value || "").trim();
  const body = {
    titulo: $("conteudo-titulo")?.value || "",
    descricao: $("conteudo-descricao")?.value || "",
    imagem: $("conteudo-imagem")?.value || "",
    data: $("conteudo-data")?.value || "",
    video_url: ($("conteudo-video")?.value || "").trim(),
    imagens_drive: collectConteudoMediaRows($("conteudo-imagens-list")),
    pdfs: collectConteudoMediaRows($("conteudo-pdfs-list")),
  };
  try {
    if (editId) {
      await apiPatch(`/api/conteudo/${tipo}/${editId}`, body);
    } else {
      await apiPost(`/api/conteudo/${tipo}`, body);
    }
    $("conteudo-modal-overlay")?.classList.add("hidden");
    if (tipo === "campanhas") loadCampanhas();
    else loadTreinamentos();
    if (_currentPage === "conteudo_detalhe" && editId && _conteudoDetalheItem?.id === editId) {
      const path = tipo === "campanhas" ? "/api/conteudo/campanhas" : "/api/conteudo/treinamentos";
      const listResp = await apiGet(path);
      const key = tipo === "campanhas" ? "campanhas" : "treinamentos";
      const updated = (listResp[key] || []).find((x) => x.id === editId);
      if (updated) {
        _conteudoDetalheItem = conteudoNormalizeItem(updated);
        renderConteudoDetalhe();
      }
    }
  } catch (e) { alert(e.message); }
});

/* ================================================================
   ARREDONDAMENTO À CURVA (blur do campo financiamento)
   ================================================================ */

async function arredondarFinanciamentoCurva() {
  const el = $("fech-finan");
  if (!el) return;
  const n = parseCurrencyValue(el.value);
  if (isNaN(n) || n <= 0) return;
  try {
    const data = await apiGet(`/api/fechamento/arredondar?valor=${n}`);
    const arred = data.valor_arredondado;
    if (arred != null && arred !== n) {
      el.type = "text";
      el.value = "R$ " + fmtBR(arred);
    }
  } catch (e) { console.warn("[SIMULADOR] arredondar curva:", e); }
}

/* ================================================================
   DEBOUNCE UTIL
   ================================================================ */

function debounce(fn, ms = 300) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}

const _debouncedApplyEstoqueFilters = debounce(() => {
  applyEstoqueFilters();
}, 280);
["est-bairro", "est-emp", "est-cob", "est-ordem"].forEach((id) => {
  $(id)?.addEventListener("change", () => _debouncedApplyEstoqueFilters());
});
$("est-pmax")?.addEventListener("change", () => _debouncedApplyEstoqueFilters());
$("est-pmax")?.addEventListener("input", () => _debouncedApplyEstoqueFilters());

/* ================================================================
   BOOT
   ================================================================ */

initProfileDropdown();
initBannerCarousel();

$("main-app").style.display = "none";

apiGet("/api/session")
  .then((s) => {
    _estadoCache = s;
    loadPage("home");
    return refreshUI();
  })
  .catch(() => {
    $("panel-login").style.display = "";
    $("main-app").style.display = "none";
  });
