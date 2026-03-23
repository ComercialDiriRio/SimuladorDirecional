# Deploy e integração real (Web + FastAPI)

Este documento descreve variáveis de ambiente, autenticação em produção e opções de sessão. A aplicação alvo é **FastAPI** (`simulador_dv.api.main`) com front estático em `web/`.

## Variáveis obrigatórias (produção)

| Variável | Descrição |
|----------|-----------|
| `GOOGLE_APPLICATION_CREDENTIALS` ou `SIMULADOR_GSHEETS_CREDENTIALS` | Caminho absoluto ao JSON de conta de serviço Google (Sheets/Drive). Alternativa: `credentials.json` na raiz do projeto. |
| `SIMULADOR_PRODUCTION` | Definir `1` ou `true` para **desativar o login demo** (`demo@direcional.local`), mesmo que `SIMULADOR_API_DEMO` esteja definido. |

## Variáveis opcionais

| Variável | Descrição |
|----------|-----------|
| `SIMULADOR_API_DEMO` | `1` permite login demo apenas se **não** estiver em modo produção (`SIMULADOR_PRODUCTION`). Útil para CI e desenvolvimento local. |
| `SIMULADOR_SMTP_SERVER`, `SIMULADOR_SMTP_PORT`, `SIMULADOR_SMTP_USER`, `SIMULADOR_SMTP_PASSWORD` | Envio de e-mail com PDF (ver `simulador_dv/services/email_smtp.py`). |
| `SIMULADOR_SESSION_BACKEND` | `memory` (padrão): sessões na RAM do processo. Para várias instâncias, planear backend externo (Redis) — não incluído por defeito. |

## Proibição de demo em produção

- Com `SIMULADOR_PRODUCTION=1`, credenciais devem existir na aba **BD Logins** (carregada via `load_sistema_dataframes` / `data_loader`).
- Sem credenciais Google válidas, a API devolve `503` na leitura de dados quando aplicável.

## Conteúdo editado por ADM (ficheiros em disco)

Alterações feitas na UI por administradores (BD Logins com **ADM?=SIM**) gravam ficheiros JSON sob `simulador_dv/data/`:

| Ficheiro | Conteúdo |
|----------|----------|
| `galeria_overrides.json` | Patches ao catálogo base (`static/img/galeria/catalogo_produtos.json`), empreendimentos extra criados pelo ADM (`__extras`), e nomes ocultos (`__removidos`). |
| `home_banners.json` | Lista de URLs das imagens do carrossel da página inicial. |

Em **serverless** (ex.: Vercel) o sistema de ficheiros é em geral **efémero**: estas gravações não persistem entre deploys, salvo volume persistente ou migração futura para base de dados / object storage.

## Cache Google Sheets

- `load_sistema_dataframes()` usa TTL em memória (~300 s). Após gravações em **BD Simulações**, `invalidate_sistema_cache()` é chamado automaticamente.

## Vercel (entrada única FastAPI)

- O ficheiro [`vercel.json`](vercel.json) aponta para [`vercel_app.py`](vercel_app.py), que reexporta `app` de `simulador_dv.api.main`.
- O servidor Flask em [`app.py`](app.py) na raiz **não** é o alvo do deploy web atual; use sempre a API FastAPI + pasta `web/`.
- Em produção na Vercel: `SIMULADOR_PRODUCTION=1`, credenciais Google e variáveis SMTP conforme acima.

## Referências

- Detalhes de paridade: [`simulador_dv/api/PARITY.md`](simulador_dv/api/PARITY.md)
- Estado de sessão: [`simulador_dv/api/ESTADO_SESSAO.md`](simulador_dv/api/ESTADO_SESSAO.md)
