# Grupo Top Ofertas — portal

Site estático do Grupo Top Ofertas, em Cloudflare Pages.

- Home (vitrine), arquivo, ficha por oferta, método, aviso de afiliado e canais.
- Gerado por `build.py` (Python 3.13, só biblioteca padrão) a partir de `dados/ofertas.json`.
- Saída em `public/`. **Nenhum HTML é editado à mão.**

## Comandos

```bash
python build.py           # valida dados e gera public/
python build.py --check   # só valida
python ferramentas/check.py   # não versionado; ver docs/LEIA-ME.md
```

## Regras de dados

- Preço só existe com `price_checked_at`.
- `status` e `delta` são calculados no build, nunca escritos no JSON.
- Parcelamento só entra quando é sem juros.
- Capa que mostra preço só é publicada quando há preço conferido.
- Oferta antiga não sai do ar: vira `indisponivel` ou `sem_conferencia`.

## Deploy

Cloudflare Pages, projeto `grupo-top-ofertas-hub`, branch `main`.
Build: `python build.py` · saída: `public` · Python 3.13 via `.python-version`.
Preview em qualquer branch; produção no merge para `main`.

Detalhes: `docs/DEPLOY.md` e `docs/CHECKLIST-DOMINIO.md`.

## Legado

Os arquivos do hub antigo (`index.html`, `offers.json`, `app.js`, `styles.css`) continuam na raiz até a
limpeza pós-virada. Eles não são publicados: o Pages publica somente `public/`.
