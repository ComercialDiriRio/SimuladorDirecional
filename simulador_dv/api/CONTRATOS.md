# Contratos API `/api/v1/simulador`

Base: mesma origem do site (`/api/v1/simulador/...`). JSON `Content-Type: application/json`.

## `POST /api/v1/simulador/enquadramento`

**Entrada (campos usados):**

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `renda` | number | Renda principal |
| `social` | bool | Fator social |
| `cotista` | bool | Cotista FGTS |
| `valor_avaliacao` | number | Valor avaliação (0 usa default 350000 na faixa) |
| `fgts_sub` | number | FGTS + subsídio |
| `val_ps_limite` | number | Limite PS considerado |
| `ato_total` | number | Soma atos para orçamento |

**Saída:** `enquadramento` (finan, subsidio, faixa, renda_ref), `poder_compra` (poder_compra, ps_limite), `budget_total`, `viáveis` (lista de unidades).

## `POST /api/v1/simulador/pro_soluto`

**Entrada:** `renda`, `valor_unidade`, `politica_ui` ou `politica`, `ranking`, opcional `ps_cap_estoque`, `premissas` (dict parcial).

**Saída:** tetos PS, parcelas máx., prazo, etc. (ver resposta JSON).

## `POST /api/v1/simulador/parcela_ps`

**Entrada:** `valor_ps`, `prazo_meses` ou `parcelas`, `politica_ui`, opcional `premissas`.

**Saída:** `mensalidade_ps`, `valor_ps`, `prazo_meses`.
