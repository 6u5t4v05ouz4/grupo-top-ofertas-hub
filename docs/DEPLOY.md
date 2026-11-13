# Plano de deploy — portal Grupo Top Ofertas

**Nada foi publicado.** Este é o plano para quando o Gustavo autorizar.

## 1. Estado atual do projeto (verificado na API hoje)

| Item | Valor |
|---|---|
| Projeto Pages | `grupo-top-ofertas-hub` |
| Repositório | `github.com/6u5t4v05ouz4/grupo-top-ofertas-hub` (privado) |
| Branch de produção | `main` |
| Domínios | `grupo-top-ofertas-hub.pages.dev` e `grupotopofertas.trade` |
| Build config | **vazio** — sem comando de build, publica a raiz do repo |
| Último deploy de produção | `23146fa8-db64-46b4-ba2c-d9c7be8658bf` (03/11/2026 19:04 UTC) |
| Previews | habilitados para todos os branches |

O site no ar é o hub antigo, servido direto da raiz do repositório.

## 2. O que muda

| Configuração | Antes | Depois |
|---|---|---|
| Comando de build | *(nenhum)* | `python build.py` |
| Diretório de saída | *(raiz)* | `public` |
| Diretório raiz | *(raiz)* | *(raiz, sem mudança)* |
| Versão do Python | — | 3.13 (arquivo `.python-version` no repo) |
| DNS / domínio | — | **nada muda** |

O domínio `grupotopofertas.trade` já está anexado ao projeto. Trocar o conteúdo não exige mexer em DNS, nameserver ou certificado: o Pages serve a nova versão do mesmo projeto, e o SSL continua o mesmo.

## 3. Opção A — build no Pages (recomendada)

**Por quê:** o repositório guarda dados e código, não HTML gerado. Cada oferta vira um diff pequeno, e o build valida o contrato antes de publicar.

1. **Branch + push** (sem tocar na `main`):
   ```bash
   git checkout -b portal-v1
   # copiar build.py, dados/, assets/{capas,css,img}, .python-version
   git add build.py dados assets .python-version
   git commit -m "portal: build estático v1 (home B, arquivo e ficha A)"
   git push -u origin portal-v1
   ```
2. **Build do preview** no projeto Pages → Settings → Build → *Preview*:
   - Build command: `python build.py`
   - Output directory: `public`
   - (Root directory vazio.)
   Esse ajuste afeta só previews; produção continua no hub antigo.
3. **Validar** em `https://portal-v1.grupo-top-ofertas-hub.pages.dev/`:
   - 12 páginas, 6 fichas, sitemap e robots respondendo.
   - `curl -I` mostra `x-robots-tag: noindex` (preview não é indexado).
   - 390 px, 768 px e 1440 px; links de afiliado abrindo; JSON-LD válido.
4. **Aprovação do Gustavo** com o preview na tela.
5. **Produção:** Settings → Build → *Production* com o mesmo comando e saída.
6. **Merge** de `portal-v1` na `main` (PR). O Pages gera o deploy de produção.
7. **Verificar** o domínio (seção 6).
8. **Limpeza:** mover o hub antigo (`index.html`, `offers.json`, `app.js`, `styles.css`, `assets/` antigo) para `legacy/` num commit separado, só depois de 7 dias sem incidente.

Rollback em qualquer passo: o deploy anterior continua sendo o ativo até o novo build passar.

## 4. Opção B — artefato (fallback)

Se o build no Pages falhar por versão de Python ou permissão:

1. Rodar `python build.py` localmente.
2. Commitar o conteúdo de `public/` na raiz do repo (ou manter `public/` e configurar só `Output directory: public`, sem build command).
3. Push na `main`.

Custo: HTML gerado no repositório e risco de divergir de `dados/ofertas.json`. Só usar se A não passar.

## 5. O que eu preciso do Gustavo

1. **Autorização para push** no repositório privado (o acesso GitHub já funciona; falta o "ok").
2. **Autorização para mudar o build do projeto Pages** (preview primeiro, produção depois).
3. **Aprovação da virada** com o checklist de domínio.

Não preciso de token do Cloudflare, nem de senha, nem de acesso ao DNS. O domínio já está no projeto e não será alterado.

## 6. O que eu faço

- Preparo o branch e o commit com os arquivos finais.
- Rodo `python build.py` e `python ferramentas/check.py` antes de cada push.
- Configuro o build de preview e acompanho o log até passar.
- Valido as 12 páginas no preview e no domínio.
- Documento o resultado e o rollback.

## 7. Verificação pós-virada

```bash
curl -sI https://grupotopofertas.trade/ | head -1                 # 200
curl -sI https://grupotopofertas.trade/ofertas/ | head -1          # 200
curl -sI https://grupotopofertas.trade/oferta/kit-3-em-1-the-black-tools/ | head -1
curl -s  https://grupotopofertas.trade/sitemap.xml | head -5
curl -s  https://grupotopofertas.trade/robots.txt
curl -s -o /dev/null -w "%{http_code}\n" https://grupotopofertas.trade/pagina-inexistente   # 404
```

- HTTPS sem aviso de certificado.
- Open Graph: colar a URL no validador de preview (Facebook/WhatsApp).
- Rich results: validador do Google para `/oferta/kit-3-em-1-the-black-tools/`.
- Mobile real: abrir no celular, testar os botões de afiliado.
- Conferir que `/offers.json` agora responde 404 (não é mais usado).

## 8. Rollback

1. Pages → Deployments → deployment `23146fa8…` (03/11) → **Rollback to this deployment**.
2. Se o problema for de dados, `git revert` do commit da oferta e novo push.
3. Se o problema for de configuração, voltar build command/output para vazio (raiz).

Como o domínio não é alterado, o rollback é imediato e não depende de DNS.

## 9. Riscos do deploy

| Risco | Probabilidade | Mitigação |
|---|---|---|
| Build no Pages não achar Python | baixa (imagem v3 tem 3.13) | `.python-version` no repo; plano B |
| Erro no build por dado inválido | baixa (build valida) | build falha e o deploy anterior fica |
| Cache antigo no domínio | baixa | `_headers` só para `/assets/*`; HTML sem cache longo |
| Preview indexado | baixa | Pages adiciona `noindex` em preview |
| Perder o hub antigo | baixa | arquivos ficam no repo até a limpeza |

---

## Leitura de preço da oferta de 09/11 (panelas)

O brief v2 anotou “outros meios R$ 179,90”, mas esse valor vem da linha *3 produtos novos a partir de
R$ 179,90* (outros vendedores), não do buy box. O box do item imprime só **R$ 170,90 no Pix** e
12x com Mercado Parcelado (com juros). Conferido no navegador em 09/11 19:02: `de R$ 264,90`,
35% OFF, 4,8 · 379 opiniões. Por isso a oferta entrou como **só-Pix** (`cartao: null`), e a
linha “No cartão” diz que o preço não foi impresso no anúncio.

## Histórico de deploy (executado)

| Quando (UTC) | Deployment | O que foi |
|---|---|---|
| 2026-11-08 17:49 | `d620d8f7-04ae-4235-974d-dcac2284d9e5` (preview) | primeiro build do portal, branch `portal-v1` |
| 2026-11-08 18:04 | `90b703b8-4580-4035-be35-01d6272f773b` | primeiro deploy de produção do portal |
| 2026-11-09 22:08 | `4809d0b0-e6d9-40f7-a205-8cb30103d23a` | **produção atual** (commit `b6ca244`, dados de `c943c91`): oferta nova do jogo de panelas antiaderente 10 peças, R$ 170,90 no Pix (o anúncio só imprime Pix), capa do cartaz e ficha do anúncio preenchidas |
| 2026-11-09 21:47 | `78a5098f-c733-4fc0-8d8f-fb77814831a9` | produção anterior (commit `b4c3d77`, dados de `a483b34`): kit 589,90 (-4,04), colchão 179,99 (-20,00), ATENTU e Kappa iguais, refletor primeira leitura 40,20, maquininha em preço só-Pix |
| 2026-11-08 22:32 | `8967b757-8879-477e-b857-93cb82c26189` | produção anterior (commit `6571431`): preços conferidos pelo ML Scout, referência em 18:33 e vereditos corrigidos |
| 2026-11-08 22:05 | `37df7766-93cb-48de-8cab-a789086b6064` | primeira conferência das 4 ofertas sem preço + 2ª leitura do kit (commit `31dac0a`) |
| 2026-11-08 18:11 | `8c57b765-6087-47ca-a280-ee7b1c287404` | portal v1 na virada (commit `82daadf`) |
| 2026-11-03 19:04 | `23146fa8-db64-46b4-ba2c-d9c7be8658bf` | hub antigo, anterior à virada (rollback para o site antigo) |

Config aplicada no projeto: build `python build.py`, saída `public`, raiz do repo, Python 3.13 via `.python-version`.
DNS e domínio não foram tocados — o alias do projeto continua o mesmo.

### Rollback

1. Portal com problema: Pages → Deployments → `8967b757…` (08/11 22:12) → Rollback.
2. Portal sem os preços de 09/11: `37df7766…` (22:05) → Rollback.
3. Portal sem os preços novos: `8c57b765…` (18:11) → Rollback.
4. Voltar ao hub antigo: `23146fa8…` → Rollback.
5. Legado: `/index.html`, `/offers.json`, `/app.js` e `/styles.css` respondem **301** para `/`.

### Preço só-Pix e cartaz com preço antigo (2026-11-09)

Dois casos que o build tratava errado e agora têm regra explícita:

1. **Anúncio que só imprime Pix** (MLB78872569): o valor lido entrou como `cartao` e o build
   comparou 20,61 (Pix) com 22,90 (cartão), exibindo "Caiu R$ 2,29" — falso. Agora `cartao`
   pode ser `null`, o valor aparece com o rótulo "no Pix", a linha "No cartão" diz "preço não
   impresso no anúncio", e o selo compara Pix com Pix (`igual`).
2. **Cartaz do vídeo com preço de outro dia**: a capa do kit estampa R$ 593,94, mas o preço de
   hoje é 589,90. As capas passam a declarar `capa_preco`; quando o valor estampado difere do
   conferido, a home e a ficha dizem que é o preço do dia da gravação.

`check.py` ganhou quatro travas para isso: `data-preco` + `data-pontos` no painel, JSON-LD
`offers.price` igual ao valor conferido, ficha de preço só-Pix obrigada a dizer "no Pix" e
"preço não impresso no anúncio", e cartaz divergente obrigado a ser explicado (ficha e destaque
da home). As quatro foram testadas com falha plantada.

### Fila de build do Pages (2026-11-08)

Travou em `queued` três vezes (22:02, 22:10 e antes em 18:07). O que resolve: apagar
o deployment enfileirado (`DELETE /pages/projects/grupo-top-ofertas-hub/deployments/<id>`)
e dar um commit vazio na `main`. O primeiro build de cada push não sai da fila; o
segundo roda em ~2 min. O site antigo continua no ar durante a espera.

### Pendências pós-virada

- [ ] 7 dias sem incidente: mover `index.html`, `offers.json`, `app.js`, `styles.css` e `assets/` antigo para `legacy/`.
- [x] Primeira rodada diária do ML Scout: 5 das 6 ofertas saíram de `sem_conferencia` em 08/11 18:33.
- [x] Refletor VERUNTO: primeira leitura em 09/11 (R$ 40,20), selo "Primeira conferência".
- [ ] Contrato v1.1: o campo `cartao` aceita `null` (preço só-Pix). Os consumidores do JSON
      (rotina do ML Scout, Publisher) precisam gravar `pix` nesse caso, não copiar o Pix em `cartao`.
- [ ] Ficha técnica vazia em 4 ofertas (colchão, carrinho, tênis, maquininha): `ficha: []` e veredito sem detalhe do produto — falta o que o vídeo afirma. A oferta de 09/11 (panelas) já entrou com `ficha` preenchida a partir do próprio anúncio; serve de modelo.
- [ ] Rollback: o portal anterior à oferta nova é `78a5098f…` (09/11 21:47).
- [ ] Validar Open Graph e rich results no domínio.

### Rodada diária de 11/11/2026 (oferta nova + preços do dia)

- Oferta nova: **MLB4860621979** (auxiliar de partida + compressor 4 em 1 MidiaFone), capa do vídeo v2,
  preço relido por mim às **19:01 BRT**: R$ 143,99 no Pix (63% OFF de R$ 390,00) e R$ 159,99 em outros
  meios. Por isso `cartao: 159.99` e `pix: 143.99`; `capa_preco` ficou **sem declaração** — o cartaz
  estampa exatamente o Pix de hoje, então não há preço velho a explicar, e declarar o cartaz faria a
  home dizer que "vale o preço conferido acima" (o de cartão), o que inverteria a oferta do vídeo.
- Preços que mudaram na reconferência do ML Scout (11/11 18:32): panelas 170,90 → **174,71** (subiu
  R$ 3,81), kit 3 em 1 589,90 → **574,90**, colchão 179,99 → **181,00** (Pix 171,95), tênis 134,67 →
  **129,99**. Carrinho ficou igual. Maquininha e refletor seguem com leitura de 09/11.
- `build.py`: a linha do tempo do preço só diz "preço que entrou no vídeo" quando a oferta tem **um**
  valor à vista; quando tem cartão e Pix ela diz "Primeira conferência." e lista o Pix ao lado — antes
  afirmava que o valor de cartão era o do vídeo.
- Repositório: a pasta local havia perdido o `.git` e cinco arquivos versionados (`.gitignore`,
  `README.md`, `app.js`, `index.html`, `offers.json`, `styles.css`, `docs/`). Restaurado a partir do
  clone do GitHub (histórico intacto, nada reescrito) e só então aplicadas as mudanças de dados.
- Deployment `687ecd4b-d7b0-4645-9dd1-cefc65722615` (conteúdo em `e04d835`, gatilho `c993ae4`); a fila travou de
  novo em `queued` e o enfileirado foi apagado antes do commit de gatilho, como nas rodadas anteriores.
  Produção anterior: `de1b69df-3127-4d64-86c1-67999772aa93`.
- Verificado no domínio: `/`, `/ofertas/`, a ficha nova e as 7 antigas, `/canais/`, `/como-conferimos/`
  em 200; HTML servido byte-idêntico ao build local; `/ir/<slug>/` em 302 para o `meli.la`; sitemap com
  13 URLs incluindo a nova; 404 real.

### Rodada diária de 12/11/2026 (oferta nova + preços do dia)

- Oferta nova: **MLB5155902053** (lixeira automática 16 L Tempo Real), capa do vídeo de 12/11 (md5
  `9293b1bd…`, confere com o pacote do Publisher), postada 12:49 BRT nos 4 canais.
- Preço relido por mim às **19:00 BRT** em `meli.la/1b6NCu3`: **R$ 59,37** (de R$ 159,99, 62% OFF),
  vendedor ISRAELCOMERCIOLTDA. O anúncio não separa Pix nem parcela, então o valor entrou em `cartao`
  com `pix: null` (o site mostra o preço sem o selo "no Pix"), e `capa_preco: 59.37` porque o cartaz
  estampa esse mesmo valor. A oferta BGX (R$ 61,91 / 76%) não foi usada.
- Preços do dia (ML Scout, 18:31 BRT): kit 3 em 1 574,90 → **639,90** (Pix 588,71; a página voltou ao
  preço cheio de cartão), colchão 181,00 → **179,99** (Pix 170,99), tênis 129,99. Carrinho, panelas e
  auxiliar sem mudança; maquininha e refletor seguem com leitura de 09/11. O auxiliar entrou só com Pix
  porque o anúncio não exibiu mais o valor "em outros meios".
- Deployment `1419847a-1fcf-429c-82d1-50d76e49c9cf` (gatilho `b347cfa`, conteúdo `de7dc0d`). A fila
  travou em `queued` de novo: enfileirado apagado e commit vazio, como nas rodadas anteriores.
  Produção anterior: `687ecd4b-d7b0-4645-9dd1-cefc65722615`.
- Verificado no domínio: `/`, `/ofertas/`, a ficha nova e as 8 antigas, `/canais/`, `/como-conferimos/`
  em 200; ficha nova mostra R$ 59,37 e a referência 12/11 às 19:00; kit mostra 639,90 / 588,71;
  sitemap com 14 URLs incluindo a nova; `/ir/lixeira-automatica-16l-tempo-real/` em 302 para o
  `meli.la`; 404 real.

### Rodada diária de 13/11/2026 (oferta nova + preços do dia)

- Oferta nova: **MLB5735296442** (kit 2 câmeras Wi-Fi iCSee HW A8), capa do vídeo de 13/11 v2
  (md5 `186054b9…`, confere com o pacote do Publisher e com o MD5 do `notes`), postada 08:37 BRT nos
  4 canais. Veredito escrito só com o que o vídeo afirma; a ficha repete o aviso de 2,4 GHz e do
  microSD não incluso.
- Preço relido por mim às **19:01 BRT** em `meli.la/1f19TeV` (200 sem sessão, tag
  `caicara_north_shore`): **R$ 185,99 em outros meios** e **R$ 176,69 no Pix** (o cartão mostra
  "49% OFF no Pix" e "R$ 185,99 em outros meios"), de R$ 349,00 — 46% OFF no valor de cartão. Entrou
  com `cartao: 185.99`, `pix: 176.69` e `desconto_pct: 46`, e `capa_preco: 185.99` porque o cartaz
  estampa esse valor. Não declarei `avaliacao`: o brief lido com sessão dizia 4,8 / 67.682, mas o card
  sem sessão de hoje mostrava 4,9 — divergência que não dá para fixar com honestidade.
- Preços do dia (ML Scout, 18:31 BRT): auxiliar 143,99 → **151,99** no Pix (61% OFF); kit 3 em 1
  639,90 → **589,90** com 10x R$ 58,99 sem juros e sem preço de Pix no anúncio; lixeira, panelas e
  carrinho sem mudança (só nova leitura). Colchão (12/11), tênis (11/11), maquininha e refletor
  (09/11) seguem com a leitura anterior.
- Deployment `ce504890-e52a-49d2-a248-e60393ca416c` (gatilho `64f0dbc`, conteúdo `faa4875`). A fila
  travou em `queued` de novo: o enfileirado `561f1afb` foi apagado e o build retomou com o commit vazio.
  Produção anterior: `1419847a-1fcf-429c-82d1-50d76e49c9cf`.
- Verificado no domínio: `/`, `/ofertas/`, a ficha nova e as 9 antigas, `/canais/`, `/como-conferimos/`
  em 200 e byte-idênticos ao build local; ficha nova mostra R$ 185,99, R$ 176,69 no Pix e leitura
  13/11 às 19:01; kit mostra 589,90 / 10x 58,99; sitemap com 15 URLs incluindo a nova;
  `/ir/kit-2-cameras-seguranca-ip-wifi-icsee/` em 302 para o `meli.la`; 404 real.
