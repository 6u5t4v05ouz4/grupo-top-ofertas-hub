# Portal Grupo Top Ofertas — versão de produção (não publicada)

Build estático do portal: home na direção B (vitrine escura), arquivo e fichas na direção A (editorial).
**Nada foi publicado no domínio.** O hub antigo continua no ar em `https://grupotopofertas.trade`.

## Comandos

```bash
python build.py           # valida dados, calcula estados e gera public/
python build.py --check   # valida sem escrever
python ferramentas/check.py   # links, a11y básica, JSON-LD, sitemap
```

Abrir: `public/index.html` (funciona por `file://`, os links são relativos).

## Estrutura

```
build.py                    gerador (só biblioteca padrão, Python 3.11+)
.python-version             fixa 3.13 no build do Cloudflare Pages
dados/ofertas.json          dados de produção (6 ofertas reais)
assets/capas/               6 capas 9:16, só de vídeos nossos
assets/css/vitrine.css      home (B)
assets/css/arquivo.css      arquivo, ficha, páginas de texto (A)
assets/img/                 logo e símbolo da marca
public/                     saída do build (12 páginas, ~684 KB)
preview/                    screenshots do resultado real
ferramentas/shot.py         screenshot via Chrome DevTools (viewport 390 px real)
ferramentas/check.py        checagens automáticas
mockup-a/ mockup-b/         exploração de design (histórico, não vai para o site)
PROPOSTA.md                 contrato de dados, arquitetura, riscos
DEPLOY.md                   plano de deploy no Cloudflare Pages
CHECKLIST-DOMINIO.md        troca do domínio, sem mexer em DNS
```

## Regras que o build aplica

- Preço sem `price_checked_at` não é gerado.
- `status` e `delta` são calculados do histórico, não vêm do JSON (o build rejeita se vierem).
- Parcelamento com juros não entra.
- Capa que mostra preço só aparece quando existe preço conferido.
- Último ponto do histórico tem de bater com `preco.cartao` e com `price_checked_at`.
- Imagem de capa precisa existir no disco.

## Dados de hoje

- 6 ofertas do `posted_products`; só a de 08/11 (Kit 3 em 1 The Black Tools) tem preço conferido: R$ 593,94, lido às 13:20.
- As outras 5 estão como `sem_conferencia`, sem número, de propósito.
- Capas: 6 arquivos de vídeos nossos. A do refletor é um quadro do próprio vídeo.
- Nenhuma foto de anúncio do Mercado Livre é usada no site.

## O que ainda não foi feito

- Nenhum deploy, push, alteração de Pages, DNS, domínio ou bio.
- Nenhuma oferta nova conferida no Mercado Livre nesta rodada.
- Nenhum analytics, busca ou filtro (fora do escopo v1).
