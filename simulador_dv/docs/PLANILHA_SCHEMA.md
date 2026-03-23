# Schema da planilha Google (Simulador DV)

A app lê o ID da planilha a partir de `ID_GERAL` em `simulador_dv/config/constants.py` (URL com `/d/<id>/`).

Defina `DISABLE_SHEETS_CMS=1` no ambiente para ignorar as abas de conteúdo abaixo e usar só ficheiros em `simulador_dv/data/` e `static/`.

## Abas de dados principais (já usadas por `sistema_data`)

| Aba | Uso |
|-----|-----|
| BD Simulações | Histórico e gravação de simulações (`simulacao_sheets.COLUNAS_BD_SIMULACOES`) |
| BD Clientes | Lista de clientes + merge com última simulação por CPF |
| BD Estoque Filtrada | Estoque + métricas da galeria |
| BD Ranking | Políticas de PS (transformação em `politicas_ps.bd_ranking_to_politicas_dataframe`) |
| PROCX Localização - BD Estoque | Opcional: enriquecer Bairro/Endereço no estoque |
| BD Financiamentos / BD Politicas | Conforme `sistema_data` |

### Cabeçalho BD Simulações

Deve coincidir com `COLUNAS_BD_SIMULACOES` em `simulador_dv/services/simulacao_sheets.py` (paridade com o Streamlit / `nova_linha`). Colunas principais:

`Nome`, `CPF`, `Data de Nascimento`, `Prazo Financiamento`, `Renda Part. 1`–`4` e `Renda Part. 4.1`, `Ranking`, `Política de Pro Soluto`, `Fator Social`, `Cotista FGTS`, limites e valores finais, atos, corretor, `Data/Horário`, amortização, parcelas, `Volta ao Caixa`.

## Abas de conteúdo (CMS via `sheets_cms.py`)

### BD Home

| Coluna | Tipo | Obrigatório | Notas |
|--------|------|-------------|--------|
| Ordem | número | recomendado | Ordem do carrossel |
| URL_Imagem | texto (URL) | sim | Imagem de fundo do slide |
| Titulo | texto | não | Pode alimentar `alt`/overlay no futuro |
| Ativo | Sim/Não | não | Linhas inativas são ignoradas na leitura |

**Fallback:** `simulador_dv/data/home_banners.json`.

### BD Galeria Empreendimentos

| Coluna | Tipo | Obrigatório | Notas |
|--------|------|-------------|--------|
| Empreendimento | texto | sim | Chave única (pode usar `Nome_Exibicao` na leitura se `Empreendimento` vazio) |
| Video_URL | URL | não | YouTube / embed |
| Latitude / Longitude | número | não | Mapa na galeria |
| Imagens_JSON | JSON | não | Objeto `{ "nome_arquivo": "https://..." }` ou lista `{nome, link}` |
| Ficha_PDF | URL | não | Ligado como documento na galeria |
| Ativo | Sim/Não | não | Default ativo |
| Ordem | número/texto | não | Reservado |

**Leitura:** funde por cima do catálogo JSON + `galeria_overrides.json`. **Escrita (ADM):** `upsert`/`delete` na aba ao criar/editar/excluir na API de galeria.

**Fallback:** `static/img/galeria/catalogo_produtos.json` + `simulador_dv/data/galeria_overrides.json`.

### BD Galeria Mídias (campanhas / treinamentos)

| Coluna | Tipo | Obrigatório | Notas |
|--------|------|-------------|--------|
| Id | texto | sim | Estável (ex. `camp-xxxxxxxx`) |
| Tipo | texto | sim | `campanha` ou `treinamento` (ou contendo «treina») |
| Titulo | texto | sim | |
| Descricao | texto | não | |
| Imagem | URL | não | Capa |
| Data | texto | não | Exibição livre |
| Video_URL | URL | não | |
| Ordem | número | não | |
| Imagens_Drive_JSON | JSON | não | Lista `[{ "titulo", "url" }]` |
| Pdfs_JSON | JSON | não | Lista `[{ "titulo", "url" }]` |

**Fallback:** `simulador_dv/data/conteudo.json`.

## Migração JSON local → Sheets

1. Criar as abas com a **primeira linha** exatamente com os cabeçalhos acima (sem apagar dados existentes noutras abas).
2. **Home:** copiar cada URL de `home_banners.json` (`imagens[]`) para uma linha (`Ordem` 1, 2, …).
3. **Galeria:** para cada chave em `catalogo_produtos.json` / overrides, uma linha com `Empreendimento`; serializar mapa nome→URL de imagens em `Imagens_JSON`.
4. **Mídias:** exportar cada item de `conteudo.json` (`campanhas` / `treinamentos`) para uma linha; `Tipo` = `campanha` ou `treinamento`; serializar listas em JSON nas colunas `*_JSON`.

Após migração, pode manter os JSON como cópia de segurança: a API continua a gravar no disco **e** tenta espelhar nas abas quando estas existem e as credenciais estão configuradas.
