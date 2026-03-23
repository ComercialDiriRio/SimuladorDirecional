# Configuração do Clerk no Simulador Direcional

O login do app pode usar **Clerk** em vez do form de e-mail/senha. Quando as variáveis do Clerk estão definidas, a tela de login exibe o componente de Sign-in do Clerk; caso contrário, o form tradicional (BD Logins) é usado.

---

## 1. Criar aplicação no Clerk

1. Acesse [dashboard.clerk.com](https://dashboard.clerk.com) e crie uma conta ou faça login.
2. Crie uma **Application** (ex.: "Simulador Direcional").
3. Anote:
   - **Publishable Key** (começa com `pk_test_` ou `pk_live_`).
   - **Secret Key** (começa com `sk_test_` ou `sk_live_`) — em API Keys.
   - **Frontend API** (URL do tipo `https://xxxx.clerk.accounts.dev`) — em Configure → Domains ou na própria Publishable Key (o domínio do Clerk).
   - **Issuer** — costuma ser a mesma URL do Frontend API (ex.: `https://xxxx.clerk.accounts.dev`). Aparece no JWT em `iss`.

---

## 2. Variáveis de ambiente

Defina no `.env` (ou no painel da Vercel/hosting) as seguintes variáveis:

| Variável | Obrigatória | Descrição |
|----------|-------------|-----------|
| `CLERK_PUBLISHABLE_KEY` | Sim | Chave pública (ex.: `pk_test_...`). Usada no frontend para carregar o Clerk. |
| `CLERK_ISSUER` | Sim | Issuer do JWT (ex.: `https://seu-dominio.clerk.accounts.dev`). Deve terminar **sem** barra. |
| `CLERK_FRONTEND_API` | Sim* | URL do Frontend API (ex.: `https://seu-dominio.clerk.accounts.dev`). Usada para carregar o script do Clerk no browser. |
| `CLERK_SECRET_KEY` | Recomendado | Chave secreta (ex.: `sk_test_...`). Necessária para o backend obter e-mail e nome do usuário (e para enriquecer com BD Logins). |
| `CLERK_JWKS_URL` | Não | URL do JWKS. Se não for definida, o backend usa `CLERK_ISSUER + /.well-known/jwks.json`. |

\* Sem `CLERK_FRONTEND_API`, o script do Clerk não é injetado e o login por form continua sendo usado.

**Exemplo `.env`:**

```env
CLERK_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxxxxxxxxxxxxxx
CLERK_ISSUER=https://quick-marten-12.clerk.accounts.dev
CLERK_FRONTEND_API=https://quick-marten-12.clerk.accounts.dev
CLERK_SECRET_KEY=<cole_sua_secret_key_do_dashboard_clerk>
```

---

## 3. Onde encontrar no Dashboard do Clerk

- **API Keys:** **Configure** → **API Keys** → Publishable key e Secret key.
- **Frontend API / Issuer:** Em **Configure** → **Domains** ou na URL que aparece ao lado da Publishable key (domínio do Clerk para sua aplicação). Use a mesma URL como `CLERK_ISSUER` e `CLERK_FRONTEND_API`.

---

## 4. Comportamento do app

- **Com Clerk configurado:** A tela de login mostra o componente de Sign-in do Clerk. Após o usuário entrar, o frontend envia o JWT para `POST /api/clerk_session`. O backend valida o token (JWKS), obtém o e-mail (e, com Secret Key, o nome) e:
  - Se existir um registro na **BD Logins** com esse e-mail, devolve esse usuário (Nome, Cargo, Imobiliária, etc.).
  - Caso contrário, devolve um usuário padrão com o nome/e-mail do Clerk.
- **Sem Clerk:** Continua o fluxo antigo: form de e-mail/senha e `POST /api/login` contra a planilha BD Logins.

---

## 5. BD Logins (planilha)

A planilha **BD Logins** continua sendo usada como **perfil do corretor**: o backend busca por **e-mail** (coluna Email) e, se achar, devolve Nome, Cargo, Imobiliária, etc. Não é necessário armazenar senha na planilha quando o Clerk está ativo.

---

## 6. Dependências

Foram adicionadas ao `requirements.txt`:

- `PyJWT[crypto]` — para validar o JWT do Clerk (JWKS).
- `requests` — para chamar a API do Clerk (obter dados do usuário quando `CLERK_SECRET_KEY` está definida).

Instale com: `pip install -r requirements.txt`

---

## 7. Resumo do que foi alterado

- **Backend (`app.py`):** Variáveis Clerk, `_clerk_verify_token`, `_clerk_get_user_info`, endpoint `POST /api/clerk_session`, e injeção de `clerk_enabled`, `clerk_publishable_key` e `clerk_script_url` no template.
- **Template (`templates/index.html`):** Bloco de config Clerk, script do Clerk (quando ativo), div `#clerk-sign-in-root` e form tradicional dentro de `#login-form-root`.
- **Frontend (`static/js/script.js`):** `initClerkWhenReady`, `clerkSyncSession`, lógica em `DOMContentLoaded` para mostrar Clerk ou form, e `logout()` chamando `Clerk.signOut()` quando Clerk está ativo.
