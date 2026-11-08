# Checklist de troca do domínio — grupotopofertas.trade

**Objetivo:** trocar o hub antigo pelo portal sem derrubar o domínio, sem tocar em DNS e com rollback de um clique.
**Pré-requisito:** autorização do Gustavo (`DEPLOY.md`, seção 5).

## 1. O que está no ar hoje

| Item | Onde | O que é |
|---|---|---|
| `/` | repo, `index.html` | hub de links: aviso de afiliado, "ofertas em destaque" (1 oferta fixa), canais |
| `/offers.json` | repo | única oferta, lida por `app.js` |
| `/app.js`, `/styles.css` | repo | render e estilo do hub |
| `/assets/` | repo | logo e avatar |

Servido direto da raiz do repositório, sem build, no projeto `grupo-top-ofertas-hub`.

## 2. O que sai do ar com a virada

- `index.html` do hub (as 3 seções: aviso, ofertas em destaque, canais).
- `offers.json` (passa a responder 404 — nenhum link externo aponta para ele).
- `app.js` e `styles.css` antigos.
- Nada de conteúdo com URL própria é perdido: o hub não tinha páginas além da home.

## 3. O que **não** muda

- O projeto Pages (`grupo-top-ofertas-hub`) e o repositório.
- Os registros DNS de `grupotopofertas.trade` e o certificado SSL.
- As bios e os links das redes sociais (continuam apontando para o domínio).
- Os canais e os vídeos publicados.

> O domínio já está anexado ao projeto. A troca é de **conteúdo**, não de infraestrutura. Se a nova versão não subir, o deploy anterior continua no ar.

## 4. Sequência (com janela de ~30 min)

- [ ] **1. Congelar o hub.** Nenhuma edição em `index.html`/`offers.json` durante a janela.
- [ ] **2. Branch `portal-v1`** com build, dados e assets. Push.
- [ ] **3. Configurar build de *preview*** (`python build.py` → `public`).
- [ ] **4. Abrir o preview** `https://portal-v1.grupo-top-ofertas-hub.pages.dev/`.
- [ ] **5. Validar no preview:**
  - [ ] `/` 200, `/ofertas/` 200, 6 fichas 200.
  - [ ] Barra de endereço sem "not secure"; `x-robots-tag: noindex` presente.
  - [ ] 390 px (celular): hero, cards, tabela, ficha.
  - [ ] Todos os botões de afiliado abrem `meli.la` e caem no produto.
  - [ ] `sitemap.xml` e `robots.txt` corretos.
  - [ ] Nenhum "R$" em oferta sem preço conferido.
  - [ ] JSON-LD sem erro no validador.
- [ ] **6. Aprovação do Gustavo** com o preview.
- [ ] **7. Configurar build de *production*** (mesmo comando e saída).
- [ ] **8. Merge `portal-v1` → `main`.** O Pages inicia o deploy de produção.
- [ ] **9. Acompanhar o build** até "success". Se falhar, produção continua no hub antigo.
- [ ] **10. Verificar o domínio** (seção 5).
- [ ] **11. Avisar o time** que a home mudou e que `offers.json` não existe mais.

## 5. Verificação no domínio (depois do passo 9)

- [ ] `https://grupotopofertas.trade/` abre a home escura com o Kit 3 em 1.
- [ ] `https://grupotopofertas.trade/ofertas/` abre a tabela com 6 linhas.
- [ ] `https://grupotopofertas.trade/oferta/kit-3-em-1-the-black-tools/` abre a ficha com preço e data.
- [ ] `https://grupotopofertas.trade/sitemap.xml` lista 11 URLs.
- [ ] `/pagina-inexistente` devolve a página 404 da marca.
- [ ] Cadeado/HTTPS sem erro; `www` (se existir) não quebra.
- [ ] Compartilhar a home no WhatsApp mostra título, descrição e imagem.
- [ ] Celular real: abrir, rolar, clicar em "Ver oferta".
- [ ] Nenhum erro no console do navegador.
- [ ] `curl -sI https://grupotopofertas.trade/ | grep -i x-robots` **não** retorna `noindex` (produção indexa).

## 6. Rollback (se algo falhar)

1. Pages → projeto → Deployments → deploy `23146fa8-db64-46b4-ba2c-d9c7be8658bf` → **Rollback to this deployment**.
2. Alternativa: `git revert` do merge na `main`.
3. Build settings: voltar comando/saída para vazio (raiz).

Sem passo de DNS, o rollback vale em segundos.

## 7. Depois da virada (7 dias)

- [ ] Acompanhar os primeiros acessos e reclamações sobre preço.
- [ ] Rodar a primeira conferência diária e ver o estado mudar de `sem_conferência` para `igual/caiu/subiu` em pelo menos uma oferta.
- [ ] Mover o hub antigo para `legacy/` (commit separado) e remover `offers.json` da raiz.
- [ ] Registrar no README o novo fluxo: dados → build → push.

## 8. Riscos específicos do domínio

| Risco | Mitigação |
|---|---|
| Cache de HTML antigo no navegador | HTML gerado sem cache longo; `_headers` só para `/assets/*` |
| Preview aparecer no Google | Pages marca preview com `noindex` |
| Deploy novo falhar e o site "sumir" | Pages mantém o deployment anterior ativo até o novo passar |
| Perder o `offers.json` usado por alguém | arquivo vai para `legacy/`, não é apagado |
| Domínio com certificado reemitido | não ocorre: o domínio não é reanexado |
