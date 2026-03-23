# Matriz de paridade (Streamlit vs API + web)

Referência de negócio: `simulador_dv/app.py` — `aba_simulador_automacao()` e `tela_login()`.

Estado de sessão documentado em `simulador_dv/api/ESTADO_SESSAO.md`.

| Passo / área | Streamlit | API | Web (`web/`) | Automatizado |
|--------------|-----------|-----|--------------|--------------|
| Health | — | `GET /api/health` | `initHealth` | `test_health` |
| Premissas | `DEFAULT_PREMISSAS` | `GET /api/premissas/default` | — | `test_premissas_default` |
| Métricas PS | `metricas_pro_soluto` | `POST /api/pro-soluto/metricas` | `<details>` dev | `test_metricas_pro_soluto` |
| Login | `tela_login` | `POST /api/auth/login` + cookie | `form-login` | `test_auth_demo`, `test_login_demo_session_email` |
| Sessão | `st.session_state` | `POST/GET/PATCH /api/session` | `wizard-wrap` + stepper | `test_session_create_and_get` (incl. `cliente_ativo`, `session_ui`) |
| Cadastro `input` | `form_cadastro` + validações | `POST /api/cliente/confirmar`, `PUT /api/cliente` | `form-cadastro` (confirmar) | — |
| Busca histórico | `dialog_buscar_cliente` | `GET /api/cadastros/buscar?q=` | sidebar busca | `test_cadastros_buscar_requires_session` |
| `fechamento_aprovado` | curva + valores | `PUT /api/fechamento`, `GET /api/fechamento/contexto` | `form-fechamento` + bifurcação | manual |
| Bifurcação | Recomendação vs direto | `PATCH /api/session` `passo_simulacao` | botões guide / selection | manual |
| `guide` | IDEAL / SEGURO / FACILITADO | `POST /api/simulacao/recomendacoes` | tabs + JSON | `test_recomendacoes_endpoint` |
| `selection` | cascata + termómetro | `GET /api/estoque/empreendimentos`, `/unidades`, `GET /api/selection/termometro`, `POST /api/estoque/selecionar` | selects + termómetro | `test_selection_termometro_requires_params` |
| `payment_flow` | PS, gap, atos, distribuição | `GET /api/pagamento/contexto`, `PATCH /api/pagamento/estado`, `GET /api/pagamento/gap`, `POST /api/pagamento/distribuir`, `POST /api/pagamento/simular` | formulários + bloqueio gap | `test_pagamento_simular` |
| `summary` | PDF, e-mail, Sheets | `GET /api/resumo`, `POST /api/pdf`, `POST /api/email`, `POST /api/salvar-simulacao` | JSON, PDF, salvar | `test_salvar_simulacao_sem_credenciais_sheets` (503 ou 200) |
| Linha Sheets | `nova_linha` em `BD Simulações` | `simulador_dv/services/simulacao_sheets.py` | botão «Concluir e salvar» | `test_simulacao_sheets.TestNovaLinhaSheets` |
| **`gallery`** | Catálogo + Folium + imagens | `GET /api/galeria/catalogo`, `GET /api/galeria/empreendimento/{nome}` | Secção galeria + Leaflet + modal | manual |
| **`client_analytics`** | Altair (pizza + barras) | `GET /api/analytics/cliente` | Chart.js + cards | manual |
| Importar histórico | Sidebar BD Simulações | `POST /api/cliente/importar-historico` `{ row }` | Lista clicável na sidebar | `test_historico_import` |
| Resumo HTML | `summary-header` / `summary-body` | `GET /api/resumo/blocos-html` | `#resumo-blocos-html` | manual |
| Produção (sem demo) | — | `SIMULADOR_PRODUCTION=1` bloqueia login demo | — | `test_auth_production` |
| Defaults fechamento | `finan_usado`/`fgts` da curva se 0 | `aplicar_defaults_fechamento` | — | `test_fechamento_ui` |

## Critérios de aceitação (números iguais ao Streamlit)

1. **Pro Soluto:** mesmos `renda`, `valor_unidade`, política e ranking → `parcela_max_g14`, `ps_max_efetivo` alinhados ao Streamlit.
2. **Recomendações:** mesmo `dados_cliente` + `df_estoque` → grupos `ideal` / `seguro` / `facilitado` e `empreendimentos_viaveis`, `mensagem`.
3. **Fluxo de pagamento:** mesmos parâmetros de simulação → `fluxo` mensal coerente com o gráfico Streamlit.
4. **Sheets:** `build_nova_linha_simulacao` reproduz `Poder de Aquisição Médio`, `Capacidade de Entrada`, `Volta ao Caixa` e restantes colunas da linha no Streamlit.

## Transições válidas

- `input` → `fechamento_aprovado`
- `fechamento_aprovado` → `guide` **ou** `selection`
- `guide` → `selection`
- `selection` → `payment_flow`
- `payment_flow` → `summary` apenas se `|gap| ≤ 1` (`GET /api/pagamento/gap` → `pode_avancar_resumo`)
- Sidebar: `input` ↔ `gallery`; histórico → `client_analytics` (via importar)

O stepper **oculta-se** em `gallery` e `client_analytics` (como no Streamlit).

A API não valida obrigatoriamente a sequência em todos os endpoints; o front aplica o bloqueio de gap no passo 5.

## Checklist manual por ecrã

1. **Login / sessão:** `GET /api/session` mostra `cliente_ativo: false`, `passo_simulacao: input` após criar sessão.
2. **Cadastro:** `POST /api/cliente/confirmar` com CPF válido e rendas → `cliente_ativo: true`; avançar para fechamento.
3. **Fechamento:** `PUT /api/fechamento` → testar «Recomendações» e «Estoque direto».
4. **Guide:** recomendações com 3 tabs preenchidas.
5. **Selection:** carregar empreendimentos, unidades, termómetro, selecionar unidade.
6. **Pagamento:** `PATCH /estado` e `GET /gap` até verde; «Avançar → Resumo» desbloqueado.
7. **Resumo:** `GET /api/resumo`, `GET /api/resumo/blocos-html`, PDF descarrega; `POST /api/salvar-simulacao` com credenciais Google (503 sem credenciais).
8. **Galeria:** navegação → catálogo JSON + métricas por empreendimento + mapa.
9. **Analytics:** após importar histórico, gráficos e fluxo mensal.
10. **Produção:** com `SIMULADOR_PRODUCTION=1`, login demo não funciona.

## Como validar

```bash
uvicorn simulador_dv.api.main:app --reload
```

Abrir `http://127.0.0.1:8000/` e percorrer o fluxo; comparar números com o Streamlit para os mesmos inputs.

```bash
python -m pytest simulador_dv/tests/ -q
```
