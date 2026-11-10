#!/usr/bin/env python3
"""Checks do build: links, acessibilidade básica, dados estruturados, sitemap.

Uso: python ferramentas/check.py
Sai com código 1 se algo falhar.
"""
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

RAIZ = Path(__file__).resolve().parent.parent
PUB = RAIZ / "public"
falhas: list[str] = []
ok: list[str] = []


ROTAS_SAIDA: set[str] = set()


def rota_de_saida(href: str) -> bool:
    """Link interno que existe como 302 em _redirects (saída para o anúncio)."""
    return href.split("?")[0].split("#")[0] in ROTAS_SAIDA


class Pagina(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.h1 = 0
        self.lang = False
        self.imgs_sem_alt: list[str] = []
        self.links: list[str] = []
        self.jsonld: list[str] = []
        self._em_jsonld = False
        self._buffer: list[str] = []
        self.titulo = False
        self.canonical = False
        self.labels: list[str] = []
        self.texto: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = bool(a.get("lang"))
        if tag == "h1":
            self.h1 += 1
        if tag == "title":
            self.titulo = True
        if tag == "link" and a.get("rel") == "canonical":
            self.canonical = True
        if tag == "img" and "alt" not in a:
            self.imgs_sem_alt.append(a.get("src", "?"))
        if tag in ("a", "link", "script") and a.get("href"):
            self.links.append(a["href"])
        if tag == "img" and a.get("src"):
            self.links.append(a["src"])
        if tag == "script" and a.get("type") == "application/ld+json":
            self._em_jsonld = True
            self._buffer = []

    def handle_endtag(self, tag):
        if tag == "script" and self._em_jsonld:
            self.jsonld.append("".join(self._buffer))
            self._em_jsonld = False

    def handle_data(self, data):
        if self._em_jsonld:
            self._buffer.append(data)
        elif data.strip():
            self.texto.append(data.strip())


def pagina_de(caminho: Path) -> Pagina:
    p = Pagina()
    p.feed(caminho.read_text(encoding="utf-8"))
    return p


def existe(alvo: Path) -> bool:
    return alvo.exists() or (alvo / "index.html").exists()


def main() -> None:
    if not PUB.exists():
        print("public/ não existe — rode python build.py antes", file=sys.stderr)
        raise SystemExit(1)

    redirecionamentos = (PUB / "_redirects").read_text(encoding="utf-8") if (PUB / "_redirects").exists() else ""
    for linha in redirecionamentos.splitlines():
        partes = linha.split()
        if len(partes) >= 3 and partes[0].startswith("/"):
            ROTAS_SAIDA.add(partes[0])

    htmls = sorted(PUB.rglob("*.html"))
    if len(htmls) < 10:
        falhas.append(f"poucas páginas geradas: {len(htmls)}")

    for html in htmls:
        rel = html.relative_to(PUB).as_posix()
        p = pagina_de(html)
        if p.h1 != 1:
            falhas.append(f"{rel}: {p.h1} elementos h1 (esperado 1)")
        if not p.lang:
            falhas.append(f"{rel}: html sem lang")
        if not p.titulo:
            falhas.append(f"{rel}: sem <title>")
        if rel != "404.html" and not p.canonical:
            falhas.append(f"{rel}: sem canonical")
        if p.imgs_sem_alt:
            falhas.append(f"{rel}: imagem sem alt: {p.imgs_sem_alt}")
        for href in p.links:
            if href.startswith(("http://", "https://", "mailto:", "#", "data:")):
                continue
            alvo = (html.parent / unquote(href.split("#")[0].split("?")[0])).resolve()
            if href.startswith("/"):
                alvo = (PUB / href.lstrip("/")).resolve()
            if not existe(alvo) and not rota_de_saida(href):
                falhas.append(f"{rel}: link quebrado -> {href}")
        for bloco in p.jsonld:
            try:
                dados = json.loads(bloco)
            except json.JSONDecodeError as e:
                falhas.append(f"{rel}: JSON-LD inválido: {e}")
                continue
            if "@context" not in dados or "@type" not in dados:
                falhas.append(f"{rel}: JSON-LD sem @context/@type")
        if "mockup" in html.read_text(encoding="utf-8").lower():
            falhas.append(f"{rel}: ainda menciona mockup")

    # páginas sem preço não podem exibir valor em reais no texto
    for html in htmls:
        if "/oferta/" not in html.as_posix():
            continue
        p = pagina_de(html)
        texto = " ".join(p.texto)
        datas = re.findall(r"\d{2}/\d{2}/\d{4}", texto)
        tem_preco = "Preço conferido" in texto
        if not tem_preco and "R$" in texto:
            falhas.append(f"{html.relative_to(PUB)}: sem preço conferido mas mostra valor em reais")
        if not datas:
            falhas.append(f"{html.relative_to(PUB)}: nenhuma data de conferência/postagem no texto")

    # regra do selo x número de leituras (regressão do "preço igual" com 1 leitura)
    estados_ok = {"primeira", "igual", "caiu", "subiu", "indisponivel", "sem_conferencia"}
    for html in htmls:
        if "/oferta/" not in html.as_posix():
            continue
        bruto = html.read_text(encoding="utf-8")
        m = re.search(r'<aside class="painel" data-estado="([a-z_]+)" data-leituras="(\d+)" data-pontos="(\d+)" data-preco="([a-z]+)"', bruto)
        if not m:
            falhas.append(f"{html.relative_to(PUB)}: painel sem data-estado/data-leituras")
            continue
        estado, leituras, pontos_hist = m.group(1), int(m.group(2)), int(m.group(3))
        if estado not in estados_ok:
            falhas.append(f"{html.relative_to(PUB)}: estado desconhecido: {estado}")
        if leituras == 0 and estado not in ("sem_conferencia", "indisponivel"):
            falhas.append(f"{html.relative_to(PUB)}: 0 leituras com estado {estado}")
        if leituras == 1 and estado != "primeira":
            falhas.append(f"{html.relative_to(PUB)}: 1 leitura deve ser 'primeira', veio {estado}")
        if leituras >= 2 and estado == "primeira":
            falhas.append(f"{html.relative_to(PUB)}: {leituras} leituras não podem ser 'primeira'")
        pontos = bruto.count('class="ponto"')
        if pontos != pontos_hist:
            falhas.append(f"{html.relative_to(PUB)}: {pontos} ponto(s) na linha do tempo para {pontos_hist} leitura(s) no histórico")
        if leituras > pontos_hist:
            falhas.append(f"{html.relative_to(PUB)}: {leituras} leituras comparáveis para {pontos_hist} registradas")
        # o selo é o do painel desta ficha; a lista de outras ofertas no rodapé
        # pode legitimamente mostrar "Preço igual" de outra oferta
        m_painel = re.search(r'<aside class="painel".*?</aside>', bruto, re.S)
        selo = Pagina()
        if m_painel:
            selo.feed(m_painel.group(0))
        else:
            selo.feed(bruto)
        texto_selo = " ".join(selo.texto)
        if leituras == 1 and "Primeira conferência" not in texto_selo:
            falhas.append(f"{html.relative_to(PUB)}: selo visível deveria dizer 'Primeira conferência'")
        if leituras == 1 and "Preço igual" in texto_selo:
            falhas.append(f"{html.relative_to(PUB)}: 'Preço igual' com uma única leitura")
        texto = " ".join(pagina_de(html).texto)
        if "leitura(s)" in texto or "registrada(s)" in texto:
            falhas.append(f"{html.relative_to(PUB)}: plural abreviado com (s)")
        # o cabeçalho não pode anunciar uma conferência anterior à leitura da ficha
        m_cab = re.search(r'Última conferência <strong>(\d{2})/(\d{2}), (\d{2}:\d{2})</strong>', bruto)
        m_lido = re.search(r'Lido no anúncio em <strong>(\d{2})/(\d{2})/(\d{4}) às (\d{2}:\d{2})</strong>', bruto)
        if m_cab and m_lido:
            cab = datetime.strptime(f"{m_lido.group(3)}-{m_cab.group(2)}-{m_cab.group(1)} {m_cab.group(3)}", "%Y-%m-%d %H:%M")
            lido = datetime.strptime(f"{m_lido.group(3)}-{m_lido.group(2)}-{m_lido.group(1)} {m_lido.group(4)}", "%Y-%m-%d %H:%M")
            if lido > cab:
                falhas.append(
                    f"{html.relative_to(PUB)}: cabeçalho diz última conferência "
                    f"{m_cab.group(1)}/{m_cab.group(2)} {m_cab.group(3)}, mas a leitura é de "
                    f"{m_lido.group(1)}/{m_lido.group(2)} {m_lido.group(4)}"
                )
        # ficha com preço conferido não pode dizer que o preço não foi conferido
        if estado != "sem_conferencia" and re.search(r"não (re)?conferid|ainda não foi (re)?conferid", texto):
            falhas.append(f"{html.relative_to(PUB)}: tem preço conferido mas o texto diz que não foi conferido")
    ok.append("selo x leituras: consistente nas 6 fichas")

    # --- exatidão do valor exibido: tipo de preço, JSON-LD e cartaz ---
    dados = json.loads((RAIZ / "dados" / "ofertas.json").read_text(encoding="utf-8"))

    def valor_vista(preco: dict) -> float:
        return preco["cartao"] if preco.get("cartao") is not None else preco["pix"]

    home_html = (PUB / "index.html").read_text(encoding="utf-8")
    m_destaque = re.search(r'<section class="destaque".*?</section>', home_html, re.S)
    destaque = ""
    if m_destaque:
        m_url = re.search(r'href="(oferta/[^/"]+)/index\.html"', m_destaque.group(0))
        if m_url:
            destaque = m_url.group(1) + "/"
    texto_home = " ".join(pagina_de(PUB / "index.html").texto)

    for o in dados["ofertas"]:
        if not o.get("publish", True):
            continue
        preco = o.get("preco")
        ficha = PUB / "oferta" / o["slug"] / "index.html"
        if not ficha.exists():
            falhas.append(f"{o['slug']}: ficha não gerada")
            continue
        p = pagina_de(ficha)
        texto = " ".join(p.texto)
        if not preco:
            continue
        esperado = f"{valor_vista(preco):.2f}"
        precos = []
        for bloco in p.jsonld:
            try:
                j = json.loads(bloco)
            except json.JSONDecodeError:
                continue
            if j.get("@type") == "Product" and isinstance(j.get("offers"), dict):
                precos.append(j["offers"].get("price"))
        if not precos:
            falhas.append(f"{o['slug']}: ficha sem offers.price no JSON-LD")
        for achado in precos:
            if achado != esperado:
                falhas.append(f"{o['slug']}: JSON-LD price {achado} difere do valor conferido {esperado}")
        # anúncio que só imprime Pix: a ficha precisa dizer que o valor é do Pix
        if preco.get("cartao") is None:
            if "no Pix" not in texto:
                falhas.append(f"{o['slug']}: preço é do Pix mas a ficha não diz 'no Pix'")
            if "preço não impresso no anúncio" not in texto:
                falhas.append(f"{o['slug']}: preço é do Pix mas a ficha não avisa que o de cartão não aparece")
        # cartaz do vídeo que estampa preço diferente do conferido precisa ser explicado
        if o.get("capa_preco") is not None and abs(float(o["capa_preco"]) - valor_vista(preco)) > 0.001:
            explica_ficha = "preço do dia da gravação" in texto
            if not explica_ficha:
                falhas.append(f"{o['slug']}: cartaz estampa {o['capa_preco']} e a ficha não explica")
            if ("oferta/" + o["slug"] + "/") == destaque and "preço do dia da gravação" not in texto_home:
                falhas.append("index.html: destaque com cartaz de preço antigo sem explicação")
    ok.append("preços: JSON-LD, tipo (cartão/Pix) e cartaz conferidos")

    # sitemap
    sm = PUB / "sitemap.xml"
    try:
        raiz = ET.parse(sm).getroot()
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locs = [e.text for e in raiz.findall("s:url/s:loc", ns)]
        if len(locs) < len(htmls) - 1:
            falhas.append(f"sitemap com {len(locs)} URLs para {len(htmls)} páginas")
        for loc in locs:
            caminho = loc.replace("https://grupotopofertas.trade/", "").strip("/")
            alvo = PUB / caminho / "index.html" if caminho else PUB / "index.html"
            if not alvo.exists():
                falhas.append(f"sitemap aponta para arquivo inexistente: {loc}")
        ok.append(f"sitemap: {len(locs)} URLs válidas")
    except ET.ParseError as e:
        falhas.append(f"sitemap.xml inválido: {e}")

    # assets: só capas próprias, css, img e js
    for pasta in (PUB / "assets").iterdir():
        if pasta.name not in ("capas", "css", "img", "js"):
            falhas.append(f"assets com pasta inesperada: {pasta.name}")
    capas = list((PUB / "assets" / "capas").glob("*.jpg"))
    if len(capas) < 6:
        falhas.append(f"menos capas que ofertas: {len(capas)}")

    # analytics: nada de terceiro sem ID; clique em afiliado sempre marcado
    cfg_analytics = json.loads((RAIZ / "dados" / "analytics.json").read_text(encoding="utf-8")) \
        if (RAIZ / "dados" / "analytics.json").exists() else {}
    beacon = ((cfg_analytics.get("cloudflare_web_analytics") or {}).get("token") or "")
    beacon_ativo = bool((cfg_analytics.get("cloudflare_web_analytics") or {}).get("ativo")) and bool(beacon)
    ga4 = ((cfg_analytics.get("ga4") or {}).get("measurement_id") or "")
    meta = ((cfg_analytics.get("meta_pixel") or {}).get("id") or "")
    tiktok = ((cfg_analytics.get("tiktok_pixel") or {}).get("id") or "")
    if not (PUB / "assets" / "js" / "afiliado.js").exists():
        falhas.append("assets/js/afiliado.js ausente: clique de afiliado não seria medido")
    redirecionamentos = (PUB / "_redirects").read_text(encoding="utf-8") if (PUB / "_redirects").exists() else ""
    if "/ir/* / 302" not in redirecionamentos:
        falhas.append("_redirects sem fallback /ir/*")
    ctas = 0
    for html in htmls:
        texto = html.read_text(encoding="utf-8")
        if beacon_ativo and beacon not in texto:
            falhas.append(f"{html.relative_to(PUB)}: sem beacon do Cloudflare Web Analytics")
        if not beacon_ativo and "cloudflareinsights.com" in texto:
            falhas.append(f"{html.relative_to(PUB)}: beacon sem token configurado")
        if ga4 and f"gtag/js?id={ga4}" not in texto:
            falhas.append(f"{html.relative_to(PUB)}: GA4 configurado e ausente")
        if not ga4 and ("googletagmanager.com" in texto or "gtag('config'" in texto):
            falhas.append(f"{html.relative_to(PUB)}: GA4 sem measurement_id")
        if not meta and ("connect.facebook.net" in texto or "fbq('init'" in texto):
            falhas.append(f"{html.relative_to(PUB)}: Meta Pixel sem id")
        if not tiktok and "analytics.tiktok.com" in texto:
            falhas.append(f"{html.relative_to(PUB)}: TikTok Pixel sem id")
        for tag in re.findall(r"<a [^>]*rel=\"[^\"]*sponsored[^\"]*\"[^>]*>", texto):
            ctas += 1
            for atributo in ("data-afiliado=", "data-oferta=", "data-item=", "data-posicao="):
                if atributo not in tag:
                    falhas.append(f"{html.relative_to(PUB)}: link de afiliado sem {atributo[:-1]}")
            m = re.search(r'data-item="(ML[A-Z]\d{6,})"', tag)
            if not m:
                falhas.append(f"{html.relative_to(PUB)}: link de afiliado com item_id inválido")
            else:
                item = m.group(1)
                destino = re.search(r'/ir/([a-z0-9-]+)/', tag)
                if not destino:
                    falhas.append(f"{html.relative_to(PUB)}: CTA de {item} fora de /ir/<slug>/ (clique não seria contado)")
                elif f"/ir/{destino.group(1)}/ https://" not in redirecionamentos:
                    falhas.append(f"_redirects sem salto /ir/{destino.group(1)}/")
    if ctas == 0:
        falhas.append("nenhum link de afiliado marcado: conversão não seria medida")
    ok.append(f"analytics: {ctas} CTAs marcados · beacon {'on' if beacon_ativo else 'off'} · "
              f"GA4 {'on' if ga4 else 'off'} · Meta {'on' if meta else 'off'} · TikTok {'on' if tiktok else 'off'}")

    # robots
    robots = (PUB / "robots.txt").read_text(encoding="utf-8")
    if "Sitemap: https://grupotopofertas.trade/sitemap.xml" not in robots:
        falhas.append("robots.txt sem sitemap")
    if "Disallow: /ir/" not in robots:
        falhas.append("robots.txt sem Disallow: /ir/ (rota de saída não é página)")

    # cada salto precisa levar ao anúncio certo, e nunca a outro host
    dados_ofertas = json.loads((RAIZ / "dados" / "ofertas.json").read_text(encoding="utf-8"))
    ofertas_json = dados_ofertas["ofertas"] if isinstance(dados_ofertas, dict) else dados_ofertas
    for o in ofertas_json:
        esperado = f"/ir/{o['slug']}/ {o['link_afiliado']} 302"
        if esperado not in redirecionamentos:
            falhas.append(f"_redirects: salto ausente ou divergente para {o['slug']}")
        if not re.match(r"^https://(meli\.la|www\.mercadolivre\.com\.br|[a-z0-9-]+\.mercadolivre\.com\.br)/", o["link_afiliado"]):
            falhas.append(f"{o['slug']}: link_afiliado fora do Mercado Livre: {o['link_afiliado']}")
    ok.append(f"_redirects: {len(ofertas_json)} saltos /ir/ conferidos")

    # tamanho
    tamanho = sum(f.stat().st_size for f in PUB.rglob("*") if f.is_file())
    ok.append(f"public/: {len(htmls)} HTML · {tamanho / 1024:.0f} KB")

    for linha in ok:
        print("OK  ", linha)
    if falhas:
        print()
        for f in falhas:
            print("FALHA", f)
        raise SystemExit(1)
    print("\nTUDO OK")


if __name__ == "__main__":
    main()
