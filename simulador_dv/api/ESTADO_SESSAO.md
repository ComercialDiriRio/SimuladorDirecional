# Estado de sessão (paridade com `st.session_state` no Streamlit)

Referência: [`simulador_dv/app.py`](../app.py) — `aba_simulador_automacao`, `tela_login`, `main`.

## Chaves de topo (API: objeto sessão)

| Chave | Tipo | Streamlit | Descrição |
|-------|------|-----------|-----------|
| `email` | str? | `user_email` | Login |
| `passo_simulacao` | str | idem | `input`, `fechamento_aprovado`, `guide`, `selection`, `payment_flow`, `summary`, `gallery`, `client_analytics` |
| `dados_cliente` | dict | idem | Ver secção abaixo |
| `cliente_ativo` | bool | idem | `True` após cadastro válido ou importação |
| `session_ui` | dict | várias `*_key` | Espelho de chaves de widget (`ps_u_key`, `ato_1_key`, `valor_final_unidade_key`, `volta_caixa_key`, `parc_ps_key`, …) |
| `user_name`, `user_phone`, … | str | sidebar | Perfil corretor |

## `dados_cliente` — cadastro (`input`)

| Chave | Origem |
|-------|--------|
| `nome`, `cpf`, `data_nascimento` | Form |
| `renda` | Soma das rendas |
| `rendas_lista` | Lista até 4 floats |
| `qtd_participantes` | 1–4 |
| `ranking` | DIAMANTE…AÇO |
| `politica` | Direcional / Emcash |
| `social`, `cotista` | bool |
| `prazo_ps_max`, `limit_ps_renda` | Pós motor |
| `finan_f_ref`, `sub_f_ref` | `motor.obter_enquadramento` |
| `finan_usado_historico`, `ps_usado_historico`, `fgts_usado_historico` | Inicializados 0 |

## `dados_cliente` — fechamento (`fechamento_aprovado`)

| Chave | Descrição |
|-------|-----------|
| `finan_usado`, `fgts_sub_usado` | Valores aprovados (default curva se 0) |
| `finan_f_ref`, `sub_f_ref` | Referência curva (atualizados a cada render) |
| `prazo_financiamento`, `sistema_amortizacao` | SAC/PRICE |

## `dados_cliente` — unidade (`selection` → `payment_flow`)

| Chave | Descrição |
|-------|-----------|
| `empreendimento_nome`, `unidade_id` | Seleção |
| `imovel_valor`, `imovel_avaliacao` | Valor final pode diferir de tabela |
| `unid_entrega`, `unid_area`, `unid_tipo`, `unid_endereco`, `unid_bairro`, `volta_caixa_ref` | Da linha estoque |
| `finan_estimado`, `fgts_sub` | Cópias auxiliares |

## `dados_cliente` — pagamento (`payment_flow`)

| Chave | Descrição |
|-------|-----------|
| `ps_usado`, `ps_parcelas`, `ps_mensal`, `ps_mensal_simples` | Pro Soluto |
| `ato_final`, `ato_30`, `ato_60`, `ato_90` | Atos |
| `entrada_total` | Soma atos |
| `parcela_financiamento` | Após cálculo |

## Transições válidas

- `input` → `input` (confirmar cadastro)
- `input` → `fechamento_aprovado` (só com `cliente_ativo` e botão “PREENCHER VALORES APROVADOS”)
- `fechamento_aprovado` → `guide` **ou** `selection` (bifurcação)
- `fechamento_aprovado` → `input` (voltar)
- `guide` → `selection`; `guide` → `fechamento_aprovado`
- `selection` → `payment_flow`; `selection` → `guide`
- `payment_flow` → `summary` se `abs(gap_final) <= 1`; senão bloqueado
- `payment_flow` → `selection`
- `summary` → `payment_flow`
- Sidebar: `input` ↔ `gallery`; histórico → `client_analytics`

## Gap final (resumo)

`gap_final = u_valor - finan - fgts - ps_usado - soma(atos) - volta_caixa` (valores numéricos alinhados ao Streamlit).
