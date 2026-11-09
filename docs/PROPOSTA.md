# Portal Grupo Top Ofertas — proposta v1 (fechada)

**Status:** versão de produção construída e validada localmente. **Nada publicado.**
**Data:** 08/11/2026
**Pasta:** `C:\Users\gusta\OpenBot\Shared\portal-grupotopofertas\`
**Site no ar hoje:** hub antigo em `https://grupotopofertas.trade` (intocado)

---

## 1. Decisões aplicadas

| Decisão | Como ficou |
|---|---|
| Direção | **Híbrido:** home na direção B (vitrine escura), arquivo e ficha na direção A (editorial claro) |
| Preço | conferência 1× por dia nas 5 mais recentes; quem confere é o ML Scout; o build consome o JSON |
| Imagens | **só capa de vídeo nossa**; nenhuma foto do anúncio; sem capa, entra a marca |
| Escopo v1 | home + ficha por oferta + arquivo. Sem busca, sem filtro, sem paginação |
| Deploy | Cloudflare Pages, mesmo projeto e domínio; plano em `DEPLOY.md` |

---

## 2. O que foi entregue

```
portal-grupotopofertas/
  build.py                    gerador único, só biblioteca padrão
  dados/ofertas.json          dados de produção (6 ofertas reais)
  assets/capas/               6 capas 720x1280, só de vídeos nossos
  assets/css/vitrine.css      home (direção B)
  assets/css/arquivo.css      arquivo, ficha e páginas de texto (direção A)
  assets/img/                 logo, símbolo da marca
  public/                     site gerado (12 páginas, 684 KB)
  preview/                    screenshots do resultado real
  ferramentas/check.py        checagens automáticas
  ferramentas/shot.py         screenshot com viewport real (inclusive 390 px)
  mockup-a/ mockup-b/         exploração de design que originou as duas direções
  PROPOSTA.md DEPLOY.md CHECKLIST-DOMINIO.md LEIA-ME.md
```

Comandos:

```bash
python build.py          # valida dados, calcula estados e gera public/
python build.py --check  # só valida
python ferramentas/check.py
```

---

## 3. Arquitetura

- **Estático, sem framework e sem JavaScript no cliente.**
- **Um script de build** (`build.py`, ~700 linhas) lê `dados/ofertas.json`, valida o contrato, calcula o estado de cada oferta e escreve HTML em `public/`.
- **Templates em Python**, sem motor de template: menos dependência, diff legível, saída determinística.
- **Dois CSS**: um para a home (vitrine), outro para arquivo/ficha/texto. Sem dependência entre páginas.
- **Assets locais**, nenhuma requisição a terceiros (sem fonte externa, sem script de analytics).
- **Cloudflare Pages** publica `public/`. Ver `DEPLOY.md` para build, branch e o que muda na conta.

Por que não framework: o volume é ~1 oferta/dia, o conteúdo é texto e imagem, e não há estado de usuário. Estático entrega LCP baixo, custo zero e rollback por commit.

---

## 4. Árvore de URLs final

| URL | Página | Tema |
|---|---|---|
| `/` | home: oferta do dia + resumo + últimas 3 do arquivo + método | vitrine |
| `/ofertas/` | arquivo completo, tabela densa, 6 ofertas | arquivo |
| `/oferta/<slug>/` | ficha: vídeo, preço conferido, ficha do anúncio, linha do tempo, outras | arquivo |
| `/como-conferimos/` | método, o que é e não é conferido, frequência | arquivo |
| `/aviso-de-afiliado/` | transparência de afiliado | arquivo |
| `/canais/` | Instagram, TikTok, Facebook, YouTube | arquivo |
| `/404.html` | página não encontrada | arquivo |
| `/sitemap.xml` | 11 URLs com `lastmod` | — |
| `/robots.txt` | libera tudo + sitemap | — |

Regras de URL:

- `/oferta/<slug>/` é imutável depois de publicado. Oferta fora do ar continua na URL com estado `indisponível`.
- Sem paginação na v1: o arquivo cabe numa tabela. Quando passar de ~40 ofertas, entra `/ofertas/pagina/2/`.
- Nenhum redirecionamento necessário: o hub antigo só tinha `/`.

---

## 5. Contrato de dados v1

Um arquivo `dados/ofertas.json` com um array. Campos por oferta:

| Campo | Tipo | Obrigatório | Regra |
|---|---|---|---|
| `slug` | string | sim | kebab-case, único, imutável |
| `publish` | bool | sim | `false` não gera página |
| `item_id` | string | sim | `MLB…` do anúncio |
| `catalog_id` | string \| null | não | quando é anúncio de catálogo |
| `titulo` | string | sim | como está no anúncio |
| `titulo_curto` | string | sim | até 42 caracteres, para cards |
| `categoria` | `{slug, rotulo}` | sim | slug em lista fechada no build |
| `marca` | string \| null | não | do anúncio |
| `veredito` | string | sim | uma linha, sem promessa de resultado |
| `capa` | caminho \| null | não | **capa do vídeo**, local, 9:16 |
| `capa_alt` | string | sim | descrição da capa |
| `capa_tem_preco` | bool | não | capa que mostra preço: só é exibida quando existe preço conferido |
| `capa_preco` | number | não | valor estampado na capa; se diferir do preço conferido, a página diz que é o preço do dia da gravação |
| `preco` | objeto \| null | não | `null` = nenhum valor exibido |
| `preco.cartao` | number \| null | sim, se há preço | valor da tela no cartão; `null` quando o anúncio só imprime Pix |
| `preco.pix` | number \| null | não | só se a tela mostra Pix; **obrigatório** quando `cartao` é `null` |
| `preco.parcelas` | `{quantidade, valor, sem_juros}` \| null | não | **só sem juros** |
| `preco.de` | number \| null | não | preço riscado do anúncio |
| `preco.desconto_pct` | number \| null | não | o que a tela informa, não calcular |
| `preco.moeda` | string | sim | `BRL` |
| `preco.fonte` | `anuncio` \| `api` | sim | a tela manda; se divergir da API, fica `anuncio` |
| `preco.price_checked_at` | ISO 8601 com offset | sim | `2026-11-08T13:20:00-03:00` |
| `disponibilidade` | `InStock` \| `OutOfStock` \| `Unknown` | sim | sem preço, só `Unknown` |
| `videos` | `{youtube, instagram, facebook, tiktok, telegram}` | sim (≥1) | URL por canal; ausente = não publicado naquele canal |
| `duracao_video_s` | number \| null | não | usada na legenda da capa |
| `postado_em` | ISO 8601 | sim | primeiro post |
| `atualizado_em` | ISO 8601 | sim | última alteração do registro |
| `link_afiliado` | URL | sim | validado sem sessão antes de publicar |
| `ficha[]` | string[] | não | só o que está na página do anúncio |
| `vendedor` | string \| null | não | loja oficial, quando identificada |
| `avaliacao` | `{nota, opinioes}` \| null | não | só se lida no anúncio e datada |
| `historico_preco[]` | `{em, cartao, pix, status}` | sim, se há preço | append-only; cada ponto traz o valor do tipo correspondente |
| `conferido_por` | string \| null | sim se há preço | quem leu o preço |

Topo do arquivo: `schema_version` (1), `referencia` (data/hora da última carga, usada para "hoje"), `atualizado_em`.

### Cálculo do estado (no build, nunca à mão)

```
tipo   = "cartao" se preco.cartao != null, senão "pix"
pontos = histórico com o campo desse tipo != null

sem preço + disponibilidade OutOfStock -> indisponivel
sem preço                              -> sem_conferencia
com preço + OutOfStock                 -> indisponivel
com preço, 1 ponto no histórico        -> primeira   (selo "Primeira conferência")
com preço, 2+ pontos:
  delta = último[tipo] - penúltimo[tipo]
  |delta| < 0,01 -> igual
  delta < 0      -> caiu (mostra "Caiu R$ X")
  delta > 0      -> subiu (mostra "Subiu R$ X")
```

A comparação é **sempre do mesmo tipo**: cartão com cartão, Pix com Pix. Se o anúncio deixa de imprimir o preço de cartão, o portal passa a mostrar o Pix marcado como Pix e compara com o Pix anterior — nunca desconta o valor de cartão do dia anterior do valor de Pix de hoje.

Estados possíveis: `primeira`, `igual`, `caiu`, `subiu`, `indisponivel`, `sem_conferencia`.

`primeira` existe porque **com uma só leitura não há comparação**. Chamar de "preço igual" seria afirmar algo que o histórico não sustenta. O selo só vira `igual` a partir da segunda leitura, com o mesmo valor.

O JSON **não aceita** `status` nem `delta` escritos à mão: o build rejeita o arquivo se esses campos existirem.

### Regras de integridade aplicadas no build (falha = não gera)

- preço sem `price_checked_at` → erro.
- parcelamento com juros → erro.
- último ponto do histórico diferente de `preco.cartao`/`preco.pix` (conforme o tipo) ou de `price_checked_at` → erro.
- `capa_preco` sem `capa_tem_preco`, ou valor não numérico → erro.
- capa apontando para arquivo inexistente → erro.
- vídeo sem `https://` → erro.
- slug duplicado, categoria fora da lista, oferta sem vídeo → erro.

### Regra de composição da home

- A seção "Verificadas hoje" só aparece quando existe oferta conferida nas últimas 24 h **diferente do destaque**. No dia 1, o destaque é a única conferida, então a home mostra o resumo (6 / 1 / 5) e vai direto ao arquivo. É proposital: não duplicar a mesma oferta em dois blocos.
- **Selo com uma leitura diz "Primeira conferência", não "Preço igual".** "Preço igual" só existe a partir da
  segunda leitura com o mesmo valor; o build não deixa o texto abreviar plural ("1 leitura registrada").
- **Capa com preço só aparece com preço conferido.** As capas do ATENTU e do tênis Kappa trazem "R$ 74,90 / 62% OFF" e "R$ 134,67 / 48% OFF" pintados no vídeo. Sem conferência, o site usa a marca no lugar — o cartaz não pode anunciar um preço que o portal não confere.

---

## 6. Dados de produção (08/11)

| Oferta | Item | Postado | Estado | Preço |
|---|---|---|---|---|
| Kit 3 em 1 The Black Tools | MLB4702102583 | 08/11 | primeira conferência | R$ 593,94 (Pix R$ 571,04 · 10x R$ 59,39) |
| Carrinho 4x4 ATENTU | MLB77708054 | 06/11 | sem conferência | — |
| Colchão Dellamed Air Plus | MLB4212913071 | 06/11 | sem conferência | — |
| Tênis Kappa Pulse Supra | MLB5857442960 | 05/11 | sem conferência | — |
| Maquininha Dragão Crowley | MLB78872569 | 04/11 | sem conferência | — |
| Kit 2 Refletores 400W VERUNTO | MLB6797156948 | 02/11 | sem conferência | — |

Só a oferta de 08/11 tem preço conferido por mim. As outras cinco aparecem sem número, com o estado honesto — é a regra funcionando, não uma falha de conteúdo. O ML Scout preenche as cinco na primeira rodada diária.

Capas: seis arquivos 720×1280, extraídos dos nossos vídeos (`Shared/Transfers` e entrega de 08/11). A do refletor é um quadro do próprio vídeo, porque não existia capa em arquivo.

---

## 7. SEO e dados estruturados

- **Home:** `ItemList` com as 6 ofertas.
- **Ficha:** `Product` + `Offer` (preço, moeda, disponibilidade, URL) + `BreadcrumbList`; `VideoObject` quando existe capa e vídeo.
- **Arquivo:** `CollectionPage` com `hasPart`.
- `canonical`, Open Graph e Twitter Card em todas as páginas. OG de oferta sem capa usa o logo da marca, nunca a foto de outro produto.
- `sitemap.xml` com `lastmod` por oferta e `robots.txt` apontando para ele.
- Sem `aggregateRating` no JSON-LD: a nota do anúncio aparece no texto, com a data da leitura, mas não vira rich snippet sem captura datada.

---

## 8. Manutenção

1. ML Scout confere as 5 mais recentes 1× por dia útil e entrega o bloco de dados + print.
2. Dev atualiza `dados/ofertas.json`, roda `python build.py`, `python ferramentas/check.py` e faz commit `oferta: <slug> <data>`.
3. Auto-deploy roda no push da `main`.
4. Mudança de **dados de oferta** com link validado: auto-deploy autorizado.
5. **Layout, marca, analytics, privacidade, domínio:** revisão do Gustavo antes.
6. Oferta errada em produção: `git revert` do commit (não editar no painel).

---

## 9. Limites conhecidos

- O preço é uma fotografia com hora, não tempo real. A página sempre diz quando foi lido.
- O estado só muda quando entra um novo ponto no histórico; não há previsão de preço.
- Sem busca: 6 ofertas é navegável; a partir de ~40, entra paginação estática.
- O site não tem analytics. Se entrar, é decisão de privacidade e revisão do Gustavo.
- Sem capa, o card fica com a marca. Isso acontece hoje em 2 ofertas porque a capa anuncia preço.

---

## 10. O que falta para publicar

1. Autorização para **push no repositório privado** `grupo-top-ofertas-hub`.
2. Autorização para **mudar o build do projeto no Pages** (comando `python build.py`, saída `public`) — preview primeiro, produção depois.
3. Aprovação da **virada do domínio** com o checklist (`CHECKLIST-DOMINIO.md`).
4. Confirmar se a ordem das ofertas sem preço no arquivo (mais recente primeiro) está boa.

Nada disso é feito sem o "ok" — o site atual segue no ar, sem alteração.
