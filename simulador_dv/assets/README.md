# Assets do Simulador (Streamlit)

Ficheiros de front-end separados do código Python.

| Pasta | Conteúdo |
|-------|------------|
| `css/` | Tema global (`streamlit_theme.css`), overrides de botão (`streamlit_button_azul.css`). |
| `js/` | `scroll_to_top.js`, `gallery_modal.js` (lightbox da galeria). |
| `html/` | Fragmentos HTML estáticos (`gallery_modal.html`). |

A injeção no Streamlit é feita por [`simulador_dv/ui/inject.py`](../ui/inject.py).

Para regenerar o tema principal a partir de `app.py` (se voltar a haver CSS embutido):

```bash
python scripts/extract_streamlit_css.py
```

Ponto de entrada da app: `streamlit run simulador_dv/streamlit_app.py` ou `python -m simulador_dv.streamlit_app`.
