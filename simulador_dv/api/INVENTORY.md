# Inventário de fluxos (UI Streamlit → API REST)

Referência: [`simulador_dv/app.py`](../app.py) — `passo_simulacao`, `aba_simulador_automacao()`, `tela_login()`.

## Passos de simulação (`passo_simulacao`)

| ID | Descrição | Estado servidor |
|----|-----------|-----------------|
| `input` | Dados do cliente, ranking, política PS | `PATCH /api/session` + `PUT /api/cliente` |
| `fechamento_aprovado` | Valores aprovados | `PUT /api/fechamento` |
| `guide` | Recomendações IDEAL/SEGURO/FACILITADO | `POST /api/simulacao/recomendacoes` |
| `selection` | Escolha de imóvel | `GET /api/estoque`, `POST /api/estoque/selecionar` |
| `payment_flow` | Fluxo de pagamento | `POST /api/pagamento/simular` |
| `summary` | Resumo, PDF, e-mail | `GET /api/resumo`, `POST /api/pdf`, `POST /api/email` |

## Endpoints implementados (OpenAPI `/api/docs`)

| Método | Caminho | Request | Response |
|--------|---------|---------|----------|
| GET | `/api/health` | — | `{ "status": "ok" }` |
| GET | `/api/premissas/default` | — | Objeto premissas |
| POST | `/api/pro-soluto/metricas` | `MetricasProSolutoIn` | `MetricasProSolutoOut` |
| POST | `/api/auth/login` | `{ "email", "password" }` | `LoginOut` (+ cookie `sim_session_id`) |
| POST | `/api/auth/logout` | — | `{ "ok": true }` |
| POST | `/api/session` | `SessionCreateIn` | `SessionCreatedOut` + cookie |
| GET | `/api/session` | `Session` cookie ou `X-Session-Id` | `EstadoSessaoOut` |
| PATCH | `/api/session` | `SessionPatchIn` | `EstadoSessaoOut` |
| DELETE | `/api/session` | — | limpa cookie |
| PUT | `/api/cliente` | `ClienteIn` | `EstadoSessaoOut` |
| PUT | `/api/fechamento` | `FechamentoIn` | `EstadoSessaoOut` |
| POST | `/api/simulacao/recomendacoes` | `RecomendacoesIn` (opcional) | JSON recomendações |
| GET | `/api/estoque` | query: bairro, empreendimento, cobertura_min_pct, ordem, preco_max | `{ itens, total }` |
| POST | `/api/estoque/selecionar` | `UnidadeSelecionarIn` | `{ ok, unidade }` |
| POST | `/api/pagamento/simular` | `PagamentoSimIn` | `{ fluxo, linhas }` |
| GET | `/api/resumo` | — | `ResumoOut` |
| POST | `/api/pdf` | `PdfRequest` opcional | `application/pdf` |
| POST | `/api/email` | `EmailRequest` | `{ ok, message }` |

## DTOs (ver `simulador_dv/api/schemas_flow.py`)

- `EstadoSessaoOut`, `SessionPatchIn`, `ClienteIn`, `FechamentoIn`, `RecomendacoesIn`, `PagamentoSimIn`, `ResumoOut`, `PdfRequest`, `EmailRequest`.

## Dados (Google Sheets)

- `simulador_dv/services/sistema_data.py` — `load_sistema_dataframes()` com cache TTL (gspread + `credentials.json` / `GOOGLE_APPLICATION_CREDENTIALS`, ou fallback Streamlit `st.connection`).
- `simulador_dv/services/data_loader.py` — `load_logins_dataframe()` para login quando só Streamlit tem secrets.

## Galeria e analytics

- `GET /api/galeria/catalogo` — JSON do catálogo (ficheiros como em `app.py`).
- `GET /api/galeria/empreendimento/{nome}` — meta + métricas cruzadas com estoque.
- `GET /api/analytics/cliente` — composição compra/renda + fluxo mensal (painel Streamlit).
- `POST /api/cliente/importar-historico` — corpo `{ "row": { ... } }` (linha BD Simulações).
- `GET /api/resumo/blocos-html` — secções HTML do resumo.

## Front web

- `web/index.html` — secções `data-step` (incl. `gallery`, `client_analytics`) + stepper oculto nesses passos.
- `web/js/api.js`, `web/js/stepper.js`, `web/js/simulador.js`.
- `web/static/img/logoAzul.png` — logo (cópia de `static/img/` para servir em `/static/`).
