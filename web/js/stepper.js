/**
 * Stepper visual + visibilidade das secções (sincronizado com passo_simulacao).
 * Em `gallery` e `client_analytics` o stepper fica oculto (como no Streamlit).
 */
export const STEPS = [
  { id: "input", label: "Dados" },
  { id: "fechamento_aprovado", label: "Fechamento" },
  { id: "guide", label: "Análise" },
  { id: "selection", label: "Imóvel" },
  { id: "payment_flow", label: "Pagamento" },
  { id: "summary", label: "Resumo" },
];

export function shouldHideStepper(passo) {
  return passo === "gallery" || passo === "client_analytics";
}

export function renderStepper(hostEl, currentStepId) {
  if (!hostEl) return;
  if (shouldHideStepper(currentStepId)) {
    hostEl.innerHTML = "";
    hostEl.style.display = "none";
    return;
  }
  hostEl.style.display = "";
  let idx = STEPS.findIndex((s) => s.id === currentStepId);
  if (idx < 0) idx = 0;

  const progressPct = STEPS.length > 1 ? (idx / (STEPS.length - 1)) * 100 : 0;

  let html = '<div class="stepper-container">';
  html += '<div class="stepper-line-bg"></div>';
  html += `<div class="stepper-line-progress" style="width:${progressPct}%"></div>`;

  STEPS.forEach((step, i) => {
    let cls = "";
    let icon = String(i + 1);
    if (i < idx) {
      cls = "completed";
      icon = "✓";
    } else if (i === idx) {
      cls = "active";
    }
    html += `<div class="stepper-step ${cls}"><div class="step-bubble">${icon}</div><div class="step-label">${step.label}</div></div>`;
  });
  html += "</div>";
  hostEl.innerHTML = html;
}

export function showStepSection(stepId) {
  document.querySelectorAll("[data-step]").forEach((el) => {
    const s = el.getAttribute("data-step");
    if (s === stepId) el.classList.remove("hidden");
    else el.classList.add("hidden");
  });
}
