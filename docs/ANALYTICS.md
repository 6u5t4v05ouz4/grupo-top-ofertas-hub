# Analytics do portal

Mede **tráfego** (visitas e páginas) e **conversão** (clique no link de afiliado do Mercado Livre)
sem terceiro obrigatório, sem storage, sem custo e sem mudar nada na aparência do site.

## O que está ativo

| Camada | Como | Onde ver | Precisa de ID? |
|---|---|---|---|
| Visitas, páginas, país, referrer | Cloudflare Web Analytics (1 linha de beacon no `<head>`) | CF → Web Analytics → `grupotopofertas.trade` | não |
| Clique em afiliado (conversão) | cada CTA aponta para `/ir/<slug>/`, que responde **302** para o link `meli.la` da oferta | CF → zona `grupotopofertas.trade` → Analytics → HTTP requests, por caminho | não |
| GA4 | gtag carregado **só** se houver `measurement_id` | GA4 | **sim — pendente** |
| Meta Pixel | snippet **só** se houver `id` | Ads Manager | **sim — pendente** |
| TikTok Pixel | snippet **só** se houver `id` | TikTok Ads | **sim — pendente** |

IDs ficam em `dados/analytics.json`. Vazio = nada é carregado (nenhum script de terceiro, nenhuma
requisição extra). O build recusa ID fora do formato conhecido (`G-…`, 10–20 dígitos, etc.).

## Por que 302 e não evento JavaScript

O primeiro desenho mandava o clique para uma Pages Function com Analytics Engine. Analytics Engine
não está habilitado na conta e só pode ser ligado pelo dashboard — o deploy falha com
`You need to enable Analytics Engine`. O 302 resolve o mesmo problema com o que já existe:

- o clique é uma requisição HTTP ao domínio, contada nos analytics da zona (que já é proxy Cloudflare);
- funciona com JS bloqueado, com bloqueador de anúncio e em navegador in-app (Instagram/TikTok);
- não precisa de binding, banco, função, cookie nem consentimento;
- o visitante continua caindo no anúncio: o salto é 302 e o destino é o mesmo link de afiliado.

## Como funciona

1. Todo CTA de oferta tem `href="/ir/<slug>/"` e `data-afiliado`, `data-oferta`, `data-item`,
   `data-posicao` (`destaque-home`, `ficha`, `ficha-sem-preco`).
2. `_redirects` publica uma linha por oferta: `/ir/<slug>/ https://meli.la/XXXX 302`, mais
   `/ir/* / 302` como rede de segurança (slug desconhecido volta para a home).
3. `assets/js/afiliado.js` (1 KB, `defer`) escuta o clique e dispara `affiliate_click` no GA4,
   `AffiliateClick` no Meta e `ClickButton` no TikTok **se** existirem. Sem ID, não faz nada.
4. `/ir/` está em `Disallow` no `robots.txt` e não aparece no sitemap.

Leitura de conversão: visitas por `clientRequestPath` (páginas) contra requisições a `/ir/<slug>/`.
O `Referer` de cada requisição a `/ir/` diz de qual página veio o clique, e as UTM dos posts dizem
de qual rede.

## O que depende do Gustavo

1. **GA4:** criar a propriedade e mandar o `G-…` → colar em `dados/analytics.json` → build e push.
2. **Meta Pixel e TikTok Pixel:** os IDs das contas de anúncio, mesmo caminho.
3. Opcional: habilitar Analytics Engine no dashboard, se algum dia quisermos evento por clique com
   canal dentro do próprio CF.

## Verificação

`python ferramentas/check.py` falha se: faltar o beacon numa página, houver gtag/fbq/ttq sem ID,
algum CTA ficar sem os `data-*`, algum CTA apontar fora de `/ir/<slug>/`, faltar o salto
correspondente em `_redirects`, algum salto divergir do `link_afiliado`, o destino não for Mercado
Livre, sumir o fallback `/ir/*`, ou o `robots.txt` perder o `Disallow: /ir/`.
