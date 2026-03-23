# Performance — Simulador DV

## Baseline (logs do servidor)

O middleware HTTP em `simulador_dv/api/main.py` regista duração por pedido (ms), exceto para `/static/*`.

**Endpoints a comparar antes/depois de otimizações:**

| Endpoint | Notas |
|----------|--------|
| `POST /api/auth/login` | Deve evitar `load_sistema_dataframes` completo (usa `load_logins_df_only`). |
| `GET /api/session` | Só memória de sessão. |
| `GET /api/home/banners` | Cache in-process + header `Cache-Control: private, max-age=60`. |
| `POST /api/simulacao/recomendacoes` | Usa cache de dataframes. |
| `GET /api/estoque` / `GET /api/estoque/filtros-meta` | Mesmo cache de sistema. |

## Variáveis de ambiente

| Variável | Efeito |
|----------|--------|
| `SIMULADOR_SISTEMA_CACHE_TTL_SEC` | TTL (s) do cache de `load_sistema_dataframes` e do contexto do simulador (mín. 30). |
| `SIMULADOR_CMS_CACHE_TTL_SEC` | TTL (s) para banners, catálogo galeria fundido e JSON de conteúdo (mín. 15). |
| `SIMULADOR_LOGINS_WORKSHEET` | Nome da aba de logins (default `BD Logins`). |

## Checklist manual (pós-deploy)

1. **Login real**: Network — não deve haver sequência longa de leituras à planilha no primeiro `POST /auth/login` além da aba de logins.
2. **Wizard**: Ao mudar de passo (ex. fechamento → guia → pagamento), o separador Home oculto **não** deve disparar `GET /api/home/banners` em cada `refreshUI` (cliente: só em `home` ou TTL 10 min).
3. **Guia**: Ao abrir o passo guia, `filtros-meta` e `recomendacoes` em paralelo; um único `GET /api/estoque` via `applyEstoqueFilters` (não dois GETs sequenciais para empreendimentos + estoque completo só para bairros).
4. **Galeria / analytics**: Chart.js e Leaflet carregam sob demanda (`web/js/lib/asset-loaders.js`); primeira página não inclui esses scripts no HTML.
5. **Estáticos**: Respostas `/static/*.js` e `.css` com `Cache-Control: public, max-age=604800`.
6. **Cold start (Vercel)**: Após deploy, primeiro utilizador ainda paga leitura Sheets; startup **não** invalida o cache do sistema só para forçar reload.

## Ficheiros principais

- Front: `web/js/simulador.js` (banners condicionais, `filtros-meta` no guia).
- Dados: `simulador_dv/services/sistema_data.py` (TTL, `load_logins_df_only`, invalidação).
- Contexto: `simulador_dv/api/data_context.py` (cache do `MotorRecomendacao` + DataFrames).
- CMS: `home_banners.py`, `galeria_catalogo.py`, `conteudo.py` (TTL in-process).
