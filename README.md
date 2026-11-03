# Grupo Top Ofertas — Hub de links (rascunho)

Site estático, portável, mobile-first. Pronto para Cloudflare Pages (ou qualquer host estático). Sem build step.

## Arquivos
- `index.html` — estrutura e acessibilidade.
- `styles.css` — estilos (paleta V1: navy/teal/amarelo/off-white).
- `app.js` — renderiza ofertas a partir de `offers.json`.
- `offers.json` — ofertas editáveis (sem preço/desconto inventado).
- `assets/` — logo e avatar (identidade V1).

## Editar ofertas
Edite `offers.json`. Campos: `title`, `description`, `tag`, `note`, `cta`, `url`. Não invente preço/desconto; confirme no Mercado Livre. Use apenas links autorizados.

## Validação local
```bash
python -m http.server 8080
# abrir http://localhost:8080
```
JSON: `python -m json.tool offers.json`

## Acessibilidade
- Skip link, headings semânticos, foco visível, alvos ≥44px, contraste navy/teal.

## Deploy
Apenas após aprovação explícita do Gustavo. Este rascunho não foi publicado nem alterou DNS/bio.

## Deploy
Repositório privado `grupo-top-ofertas-hub` conectado ao Cloudflare Pages (branch principal, auto-deploy). Domínio pages.dev do Cloudflare. Sem DNS customizado.

## Manutenção de ofertas
- Editar `offers.json` (title, description, tag, note, cta, url).
- Auto-deploy autorizado apenas para dados de ofertas com link de afiliado validado.
- Mudanças de layout/marca, analytics/tracking, privacidade/segurança ou domínio exigem revisão do Gustavo.
- Não publicar posts em redes sociais (aprovação por post separada).
- Outros agents devem encaminhar ofertas verificadas para o Dev Fullstack.

## Status
Publicado em Cloudflare Pages (pages.dev). Conteúdo sujeito a revisão.
