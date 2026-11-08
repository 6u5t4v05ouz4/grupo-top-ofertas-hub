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
