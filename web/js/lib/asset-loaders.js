/**
 * Carregamento lazy de Chart.js (+ plugins) e Leaflet para reduzir trabalho no primeiro paint.
 */

function scriptAlreadyLoaded(src) {
  for (const s of document.querySelectorAll("script[src]")) {
    if (s.getAttribute("src") === src) return true;
  }
  return false;
}

function loadScript(src) {
  return new Promise((resolve, reject) => {
    if (scriptAlreadyLoaded(src)) {
      resolve();
      return;
    }
    const s = document.createElement("script");
    s.src = src;
    s.crossOrigin = "anonymous";
    s.onload = () => resolve();
    s.onerror = () => reject(new Error(`Falha ao carregar ${src}`));
    document.head.appendChild(s);
  });
}

function loadScriptSequential(urls) {
  return urls.reduce((p, url) => p.then(() => loadScript(url)), Promise.resolve());
}

let _chartLibsPromise = null;

export function ensureChartLibs() {
  if (typeof window !== "undefined" && window.Chart) {
    return Promise.resolve();
  }
  if (_chartLibsPromise) return _chartLibsPromise;
  _chartLibsPromise = loadScriptSequential([
    "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js",
    "https://cdn.jsdelivr.net/npm/hammerjs@2.0.8/hammer.min.js",
    "https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1/dist/chartjs-plugin-zoom.min.js",
    "https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1/dist/chartjs-plugin-annotation.min.js",
  ]);
  return _chartLibsPromise;
}

let _leafletPromise = null;

export function ensureLeaflet() {
  if (typeof window !== "undefined" && window.L) {
    return Promise.resolve();
  }
  if (_leafletPromise) return _leafletPromise;
  const href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
  let hasLeafletCss = false;
  for (const l of document.querySelectorAll("link[rel='stylesheet']")) {
    if (l.getAttribute("href") === href) hasLeafletCss = true;
  }
  if (!hasLeafletCss) {
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = href;
    link.crossOrigin = "";
    document.head.appendChild(link);
  }
  _leafletPromise = loadScript("https://unpkg.com/leaflet@1.9.4/dist/leaflet.js");
  return _leafletPromise;
}
