# Simulador DV (pacote)

## Estrutura

| Caminho | Conteúdo |
|---------|----------|
| `app.py` | Aplicação Streamlit (lógica Python, fluxos, PDF, e-mail). Estilos/JS/HTML estáticos em `assets/`. |
| `ui/inject.py` | Carrega `.css` / `.html` / `.js` de `assets/` e injeta no Streamlit. |
| `assets/css/` | Tema visual (`streamlit_theme.css`, `streamlit_button_azul.css`). |
| `assets/js/` | `scroll_to_top.js`, `gallery_modal.js`. |
| `assets/html/` | Fragmentos HTML (ex.: modal da galeria). |
| `config/constants.py` | URLs do Google Sheets, paleta de cores. |
| `config/taxas_comparador.py` | **E1/E4** e offset **30%** (λ no comparador). |
| `data/premissas.py` | Valores padrão da aba **PREMISSAS** (Excel) e leitura de planilha `BD Premissas` / `PREMISSAS`. |
| `data/politicas_ps.py` | Tabela **POLITICAS** (faixa renda, % PS, prazo) — defaults do Excel se a aba não existir. |
| `core/comparador_emcash.py` | Juros do **financiamento** do imóvel + delegação de **parcela PS Emcash** para `pro_soluto_comparador`. |
| `core/pro_soluto_comparador.py` | **I5** (PMT×(1+E1)), **J8/G14** (parcela máx.), **L8/G15** (valor máx. PS vs cap %VU). |
| `streamlit_app.py` | Alias de entrada (`python -m simulador_dv.streamlit_app`). **UI legada Streamlit** — manter até paridade total com a web. |
| `api/main.py` | **FastAPI**: JSON em `/api/*`, OpenAPI em `/api/docs`. |
| `api/INVENTORY.md` | Fluxos e contratos DTO (migração da UI). |
| `api/PARITY.md` | Matriz de paridade Streamlit vs API + testes. |
| `services/data_loader.py` | Dados para API sem `st.session_state` (ex.: logins via Sheets quando disponível). |
| `../web/` | Front estático na raiz do repo: `index.html`, `css/app.css`, `js/app.js`. |

## Deploy e produção

Ver [`../DEPLOY.md`](../DEPLOY.md) na raiz do repositório (variáveis Google Sheets, `SIMULADOR_PRODUCTION`, SMTP, sessão).

## UI web (Python API + HTML + CSS + JS) — recomendado para novo desenvolvimento

1. Instalar dependências: `pip install -r requirements.txt` (inclui `fastapi`, `uvicorn`, `httpx`).
2. Arrancar o servidor:

```bash
uvicorn simulador_dv.api.main:app --reload --host 0.0.0.0 --port 8000
```

3. Abrir no browser: `http://127.0.0.1:8000/` (HTML estático) e documentação OpenAPI: `http://127.0.0.1:8000/api/docs`.

4. **Login demo** (sem BD): definir variável de ambiente `SIMULADOR_API_DEMO=1` e usar `demo@direcional.local` / `demo`.

5. Testes API: `pytest simulador_dv/tests/test_api.py`.

## Entrada Streamlit (legado)

Na raiz do projeto:

```bash
streamlit run simulador_dv/streamlit_app.py
```

(ou `python -m simulador_dv.streamlit_app`. Na raiz do repo pode existir `diresimulator.py` / `streamlit_monolith.py` como bundle monolítico gerado; o desenvolvimento modular usa `simulador_dv/`.)

O Streamlit **não** é o caminho principal para a separação em 4 linguagens; a **UI alvo** é `web/` + `simulador_dv/api/`.

## Premissas no Google Sheets

Crie a aba **`BD Premissas`** (ou **`PREMISSAS`**) com colunas semelhantes ao Excel (rótulo na coluna A, valor na B), por exemplo: `DIRE PRE`, `DIRE POS`, `EMCASH`, `TX EMCASH`, `IPCA EMCASH`, `RENDA F2`… — ver `data/premissas.py` (`_LABEL_MAP`).

Sem a aba, usam-se os defaults extraídos do workbook de referência.

## Taxa de juros

- **Política Emcash** (`politica` contém `"EMCASH"`): taxa mensal = `emcash_fin_m` (padrão **0,0089** a.m., célula **PREMISSAS!B4** / **E2** do comparador).
- **Demais**: taxa anual **direcional_fin_aa_pct** (padrão **8,16%**), convertida para mensal como no código legado.

Fluxo, parcela do financiamento e comparativo SAC/PRICE usam `resolver_taxa_financiamento_anual_pct(dados_cliente, premissas)`.

Funções auxiliares: `parcela_ps_emcash_pmt`, `valor_ps_ajustado_comparador`, `metricas_comparador_tx`.

## Pro Soluto (comparador)

### Regras oficiais (UI e motor)

1. **Limite máximo de PS (`ps_max_efetivo`)**  
   Menor valor entre: (a) teto do comparador × política (**L8/G15** com **POLITICAS** e **PV** da parcela J8), (b) **% do VU** da linha POLITICAS, (c) **limite da coluna PS_*** do estoque da unidade, quando existir. Na interface de fechamento mostra-se **apenas** esse valor (equivalente ao “teto calculado” / lado direito do Excel), sem repetir o limite de estoque ao lado.

2. **Parcela máxima sobre renda (C43 / G14)**  
   `(λ − 30%) × renda`, com **λ** vindo da linha **POLITICAS** da classificação efetiva (espelha **K3**, **X3**, **AJ3**… por bloco no **COMPARADOR TX EMCASH**: Emcash, Diamante, Ouro, etc.). Na UI mostra-se só este valor, alinhado ao simulador Excel (**700** no exemplo típico). **J8** (`×(1−E1)`) entra apenas no cálculo interno de **L8**; não é exibida como segunda “parcela máxima”.

3. **Mensalidade do PS (célula I5 do comparador)**  
   `(PMT(E2, n, PV) × -1) × (1+E1)` em `parcela_ps_pmt` — **não** usar apenas `PS ÷ n`.  
   **`E2` é sempre `emcash_fin_m` (**PREMISSAS B4** / **E2** global do COMPARADOR TX EMCASH)**, igual ao Excel **I5**, independentemente de o produto na UI ser Emcash ou Direcional. A política de venda altera **tier / POLITICAS** (tetos, prazo), não a taxa do PS nesta fórmula. O **financiamento do imóvel** (SAC/PRICE etc.) continua usando a taxa Direcional/Emcash própria noutros pontos do código.

   Com premissas padrão e **84** parcelas, exemplos de referência (I5): 30k → **~528,64**; 35k → **~616,74**; 39.663 → **~698,91** (simulador Excel). Valores mais baixos (ex. 35k → **564,61**) aparecem se o PMT usar por engano a **taxa do financiamento Direcional** em vez de **B4** — o motor correto para mensalidade PS é sempre **I5** (**B4**).

- **Parcela mensal:** ver `parcela_ps_pmt` / `parcela_ps_para_valor` em `core/pro_soluto_comparador.py`.
- **Tetos:** `metricas_pro_soluto` combina **POLITICAS** (planilha `POLITICAS` no Sheets) com limite da coluna **PS_*** do estoque.
