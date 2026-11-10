# Analytics do portal

Mede **tráfego** (visitas e páginas) e **conversão** (clique no link de afiliado do Mercado Livre),
sem terceiro obrigatório e sem mudar nada na aparência do site.

## O que está ativo

| Camada | Como | Onde ver | Precisa de ID? |
|---|---|---|---|
| Visitas e páginas | Cloudflare Web Analytics (beacon de 1 linha no `<head>`) | Cloudflare → Web Analytics → `grupotopofertas.trade` | não (token público, em `dados/analytics.json`) |
| Clique em afiliado | `assets/js/afiliado.js` → `POST /api/clique` → Analytics Engine (`portal_cliques`) | SQL API / dashboard | não |
| Cliques por caminho (conferência) | Analytics da zona (domínio é proxy da Cloudflare) | Zone → Analytics → Top paths `/api/clique` | não |
| GA4 | gtag carregado **só** se houver `measurement_id` | GA4 | **sim — pendente** |
| Meta Pixel | snippet carregado **só** se houver `id` | Ads Manager | **sim — pendente** |
| TikTok Pixel | snippet carregado **só** se houver `id` | TikTok Ads | **sim — pendente** |

IDs ficam em `dados/analytics.json`. Vazio = nada é carregado (nenhum script de terceiro, nenhuma
requisição extra). O build recusa ID fora do formato conhecido (`G-…`, 10–20 dígitos, etc.), então
não há como injetar script por esse arquivo.

## Como o clique é medido

Todo CTA de oferta carrega `data-afiliado="mercadolivre"`, `data-oferta`, `data-item` (MLB…) e
`data-posicao` (`destaque-home`, `ficha`, `ficha-sem-preco`). O `afiliado.js` escuta o clique em
fase de captura, dispara `affiliate_click` no GA4 quando existe, `AffiliateClick` no Meta,
`ClickButton` no TikTok, e manda um `sendBeacon` para `/api/clique`.

- O link **não** é envelopado nem redirecionado: se a medição falhar, a pessoa cai no Mercado Livre
  do mesmo jeito. O endpoint sempre responde `204`.
- O beacon manda `canal` (`utm_source` ou host de origem: `instagram.com`, `tiktok.com`, `direto`…),
  o que permite comparar conversão por canal.
- `functions/api/clique.js` grava 5 campos e recusa item fora do padrão `ML[A-Z]` + dígitos.
- `/api/` está em `Disallow` no `robots.txt` e não é indexado.

Consulta de exemplo (SQL API, dataset `portal_cliques`):

```sql
SELECT blob1 AS oferta, blob4 AS canal, count() AS cliques
FROM portal_cliques
WHERE timestamp > now() - INTERVAL '7' DAY
GROUP BY oferta, canal ORDER BY cliques DESC
```

## O que depende do Gustavo

1. **GA4:** criar a propriedade e mandar o `G-…` → colar em `dados/analytics.json` → build e push.
2. **Meta Pixel e TikTok Pixel:** os IDs das contas de anúncio, mesmo caminho.
3. Nada de acesso extra: a conta Cloudflare já está conectada e o beacon usa token público.

## Verificação

`python ferramentas/check.py` falha se: faltar o beacon numa página, houver gtag/fbq/ttq sem ID
configurado, algum CTA ficar sem os `data-*`, o `afiliado.js` ou o `functions/api/clique.js`
desaparecerem, ou o `robots.txt` perder o `Disallow: /api/`.
