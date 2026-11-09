#!/usr/bin/env python3
"""Gera o site estático do portal Grupo Top Ofertas.

Uso:
    python build.py            # valida dados e gera public/
    python build.py --check    # só valida, não escreve nada

Sem dependências: apenas a biblioteca padrão do Python 3.11+.
"""

from __future__ import annotations

import html
import json
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
SAIDA = RAIZ / "public"
SITE = "https://grupotopofertas.trade"
DADOS = RAIZ / "dados" / "ofertas.json"

CATEGORIAS = {"ferramentas", "saude", "brinquedos", "calcados", "eletronicos", "iluminacao", "casa", "cozinha"}
CANAIS = ["youtube", "instagram", "facebook", "tiktok", "telegram"]
ROTULO_CANAL = {
    "youtube": "YouTube",
    "instagram": "Instagram",
    "facebook": "Facebook",
    "tiktok": "TikTok",
    "telegram": "Telegram",
}
REDES = [
    ("Instagram", "https://www.instagram.com/grupotopofertas.br"),
    ("TikTok", "https://www.tiktok.com/@grupotopofertas"),
    ("Facebook", "https://www.facebook.com/profile.php?id=61595931852990"),
    ("YouTube", "https://www.youtube.com/@GrupoTopOfertas"),
]
BADGE = {
    "primeira": ("", "Primeira conferência", "badge--primeira"),
    "igual": ("=", "Preço igual", "badge--igual"),
    "caiu": ("↓", "Caiu", "badge--caiu"),
    "subiu": ("↑", "Subiu", "badge--subiu"),
    "indisponivel": ("—", "Indisponível", "badge--indisponivel"),
    "sem_conferencia": ("?", "Sem conferência", "badge--sem_conferencia"),
}


# --------------------------------------------------------------------------
# utilidades
# --------------------------------------------------------------------------

def esc(valor) -> str:
    return html.escape(str(valor), quote=True)


def money(valor: float | None) -> str:
    if valor is None:
        return "—"
    texto = f"{valor:,.2f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


def pct(valor: float | None) -> str:
    if valor is None:
        return ""
    return f"{valor:g}%".replace(".", ",")


def tipo_preco(preco: dict) -> str:
    """Qual valor é o "a partir de": cartão, ou Pix quando o anúncio só imprime Pix."""
    return "cartao" if preco.get("cartao") is not None else "pix"


def valor_vista(preco: dict) -> float:
    return preco["cartao"] if preco.get("cartao") is not None else preco["pix"]


def so_pix(preco: dict) -> bool:
    """Anúncio que não imprime preço de cartão: o valor mostrado é o do Pix."""
    return preco.get("cartao") is None


def quando(iso: str) -> datetime:
    return datetime.fromisoformat(iso)


def referencia_efetiva(dados: dict) -> str:
    """Referência exibida nunca fica atrás da leitura de preço mais recente.

    Se o ML Scout registra uma leitura depois da referência do arquivo, o site
    não pode anunciar uma "última conferência" anterior ao que já mostra.
    """
    referencia = quando(dados["referencia"])
    carimbo = dados["referencia"]
    for o in dados.get("ofertas", []):
        lido_iso = (o.get("preco") or {}).get("price_checked_at")
        if not lido_iso:
            continue
        lido = quando(lido_iso)
        if lido > referencia:
            referencia = lido
            carimbo = lido_iso
    return carimbo


def data(iso: str) -> str:
    return quando(iso).strftime("%d/%m/%Y")


def data_curta(iso: str) -> str:
    return quando(iso).strftime("%d/%m")


def hora(iso: str) -> str:
    return quando(iso).strftime("%H:%M")


def data_hora(iso: str) -> str:
    return f"{data(iso)} às {hora(iso)}"


def rel(profundidade: int, caminho: str) -> str:
    return "../" * profundidade + caminho.lstrip("/")


def url_absoluta(rota: str) -> str:
    return SITE + "/" + rota.lstrip("/")


def jsonld(dados: dict) -> str:
    bruto = json.dumps(dados, ensure_ascii=False, indent=2).replace("</", "<\\/")
    return f'<script type="application/ld+json">\n{bruto}\n</script>'


# --------------------------------------------------------------------------
# dados
# --------------------------------------------------------------------------

def carregar() -> dict:
    if not DADOS.exists():
        raise SystemExit(f"dados ausentes: {DADOS}")
    with DADOS.open(encoding="utf-8") as fh:
        bruto = json.load(fh)

    erros: list[str] = []
    if bruto.get("schema_version") != 1:
        erros.append("schema_version deve ser 1")
    for campo in ("referencia", "ofertas"):
        if not bruto.get(campo):
            erros.append(f"campo de topo obrigatório: {campo}")

    vistos: set[str] = set()
    for o in bruto.get("ofertas", []):
        nome = o.get("slug", "?")
        for campo in ("slug", "titulo", "titulo_curto", "categoria", "veredito", "capa",
                      "capa_alt", "disponibilidade", "postado_em", "videos", "link_afiliado",
                      "historico_preco"):
            if campo not in o:
                erros.append(f"{nome}: campo obrigatório ausente: {campo}")
        if o.get("slug") in vistos:
            erros.append(f"slug duplicado: {o.get('slug')}")
        vistos.add(o.get("slug", ""))
        if o.get("categoria", {}).get("slug") not in CATEGORIAS:
            erros.append(f"{nome}: categoria inválida")
        if o.get("capa") and not (RAIZ / o["capa"]).exists():
            erros.append(f"{nome}: capa não existe no disco: {o['capa']}")
        if "status" in o or "delta" in o:
            erros.append(f"{nome}: status/delta são calculados no build, não vêm do JSON")
        quando(o["postado_em"])
        for canal, url in o.get("videos", {}).items():
            if canal not in CANAIS:
                erros.append(f"{nome}: canal desconhecido: {canal}")
            if not str(url).startswith("https://"):
                erros.append(f"{nome}: vídeo precisa ser https: {canal}")
        if not o.get("videos"):
            erros.append(f"{nome}: precisa de pelo menos um vídeo")
        preco = o.get("preco")
        if preco is not None:
            if not preco.get("price_checked_at"):
                erros.append(f"{nome}: preço sem price_checked_at")
            if preco.get("fonte") not in ("anuncio", "api"):
                erros.append(f"{nome}: preço.fonte deve ser anuncio ou api")
            if preco.get("cartao") is None and preco.get("pix") is None:
                erros.append(f"{nome}: preço sem valor de cartão nem de Pix")
            parcelas = preco.get("parcelas")
            if parcelas and not parcelas.get("sem_juros"):
                erros.append(f"{nome}: parcelamento só entra quando é sem juros")
            tipo = tipo_preco(preco)
            hist = o.get("historico_preco") or []
            pontos = [h for h in hist if h.get(tipo) is not None]
            if not pontos:
                erros.append(f"{nome}: preço sem histórico de {tipo}")
            else:
                ultimo = pontos[-1]
                if abs(ultimo[tipo] - preco[tipo]) > 0.001:
                    erros.append(f"{nome}: último ponto do histórico difere de preco.{tipo}")
                if ultimo.get("em") != preco.get("price_checked_at"):
                    erros.append(f"{nome}: último ponto do histórico difere de price_checked_at")
            if valor_vista(preco) <= 0:
                erros.append(f"{nome}: valor à vista precisa ser positivo")
        else:
            if o.get("disponibilidade") not in ("Unknown", "OutOfStock"):
                erros.append(f"{nome}: sem preço, disponibilidade deve ser Unknown")
        # preço estampado na capa do vídeo: se estiver anotado, precisa ser número
        if o.get("capa_preco") is not None:
            if not o.get("capa_tem_preco"):
                erros.append(f"{nome}: capa_preco exige capa_tem_preco")
            try:
                float(o["capa_preco"])
            except (TypeError, ValueError):
                erros.append(f"{nome}: capa_preco precisa ser número")

    if erros:
        print("FALHA NA VALIDAÇÃO:\n" + "\n".join(" - " + e for e in erros), file=sys.stderr)
        raise SystemExit(1)
    return bruto


def calcular_estado(oferta: dict) -> dict:
    """Calcula status e delta a partir do histórico. Nunca vem escrito à mão."""
    preco = oferta.get("preco")
    if preco is None:
        status = "indisponivel" if oferta["disponibilidade"] == "OutOfStock" else "sem_conferencia"
        return {"status": status, "delta": None, "rotulo": BADGE[status][1]}

    # comparação só entre leituras do mesmo tipo: cartão com cartão, Pix com Pix.
    tipo = tipo_preco(preco)
    pontos = [h for h in oferta.get("historico_preco", []) if h.get(tipo) is not None]
    delta = None
    status = "primeira"
    if oferta["disponibilidade"] == "OutOfStock":
        status = "indisponivel"
    elif len(pontos) >= 2:
        delta = round(pontos[-1][tipo] - pontos[-2][tipo], 2)
        status = "igual"
        if delta < 0:
            status = "caiu"
        elif delta > 0:
            status = "subiu"

    rotulo = BADGE[status][1]
    if status == "caiu":
        rotulo = f"Caiu {money(abs(delta))}"
    elif status == "subiu":
        rotulo = f"Subiu {money(delta)}"
    return {"status": status, "delta": delta, "rotulo": rotulo}


def preparar(dados: dict) -> list[dict]:
    referencia = quando(referencia_efetiva(dados))
    ofertas = []
    for o in dados["ofertas"]:
        if not o.get("publish", True):
            continue
        o["_estado"] = calcular_estado(o)
        o["_preco"] = o.get("preco")
        o["_url"] = f"oferta/{o['slug']}/"
        o["_conferida_24h"] = bool(
            o["_preco"]
            and timedelta(0) <= referencia - quando(o["_preco"]["price_checked_at"]) <= timedelta(hours=24)
        )
        ofertas.append(o)
    ofertas.sort(key=lambda x: x["postado_em"], reverse=True)
    return ofertas


# --------------------------------------------------------------------------
# blocos de interface
# --------------------------------------------------------------------------

def cabecalho(tema: str, profundidade: int, referencia: str) -> str:
    logo = rel(profundidade, "assets/img/logo-horizontal.svg")
    home = rel(profundidade, "index.html")
    nav = [
        ("index.html#dia", "Verificadas hoje"),
        ("ofertas/index.html", "Arquivo"),
        ("como-conferimos/index.html", "Como conferimos"),
        ("canais/index.html", "Canais"),
    ]
    links = "".join(
        f'<a href="{rel(profundidade, destino)}">{esc(rotulo)}</a>' for destino, rotulo in nav
    )
    if tema == "vitrine":
        selo = f'<span class="topo__selo">{esc(data_curta(referencia))} · {esc(hora(referencia))}</span>'
        return f"""<header class="topo">
  <div class="envoltorio topo__interno">
    <a class="marca" href="{home}" aria-label="Grupo Top Ofertas — início">
      <img src="{logo}" alt="Grupo Top Ofertas" width="1800" height="600" />
    </a>
    <nav class="topo__nav" aria-label="Navegação principal">{links}</nav>
    {selo}
  </div>
</header>"""
    meta = f'<p class="topo__meta">Última conferência <strong>{esc(data_curta(referencia))}, {esc(hora(referencia))}</strong></p>'
    return f"""<header class="topo">
  <div class="envoltorio topo__interno">
    <a class="marca" href="{home}" aria-label="Grupo Top Ofertas — início">
      <img src="{logo}" alt="Grupo Top Ofertas" width="1800" height="600" />
    </a>
    <nav class="topo__nav" aria-label="Navegação principal">{links}</nav>
    {meta}
  </div>
</header>"""


def rodape(profundidade: int) -> str:
    logo = rel(profundidade, "assets/img/logo-horizontal.svg")
    home = rel(profundidade, "index.html")
    redes = "".join(
        f'<li><a href="{url}" target="_blank" rel="noopener noreferrer">{esc(nome)}</a></li>'
        for nome, url in REDES
    )
    return f"""<footer class="rodape" id="canais">
  <div class="envoltorio">
    <div class="rodape__grade">
      <div>
        <a class="marca" href="{home}" aria-label="Grupo Top Ofertas — início">
          <img src="{logo}" alt="Grupo Top Ofertas" width="1800" height="600" />
        </a>
        <p class="rodape__texto">
          Achados selecionados e conferidos, com o vídeo de cada recomendação e o preço do dia da conferência.
          Participamos do Programa de Afiliados do Mercado Livre.
        </p>
      </div>
      <div>
        <h2>Canais oficiais</h2>
        <ul class="rodape__canais">{redes}</ul>
      </div>
    </div>
    <div class="rodape__base">
      <span>© 2026 Grupo Top Ofertas · <a href="{rel(profundidade, 'aviso-de-afiliado/index.html')}">Aviso de afiliado</a></span>
      <span>Preços sujeitos a alteração · conferidos no anúncio</span>
    </div>
  </div>
</footer>"""


def head(titulo: str, descricao: str, rota: str, tema: str, capa: str | None = None,
         jsonld_bloco: str = "", og_tipo: str = "website") -> str:
    profundidade = rota.count("/")
    css = "assets/css/vitrine.css" if tema == "vitrine" else "assets/css/arquivo.css"
    og = url_absoluta(capa) if capa else url_absoluta("assets/img/logo-horizontal-1800x600.png")
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{esc(titulo)}</title>
<meta name="description" content="{esc(descricao)}" />
<link rel="canonical" href="{url_absoluta(rota)}" />
<link rel="icon" href="{rel(profundidade, 'favicon.svg')}" type="image/svg+xml" />
<link rel="stylesheet" href="{rel(profundidade, css)}" />
<meta property="og:type" content="{og_tipo}" />
<meta property="og:site_name" content="Grupo Top Ofertas" />
<meta property="og:locale" content="pt_BR" />
<meta property="og:title" content="{esc(titulo)}" />
<meta property="og:description" content="{esc(descricao)}" />
<meta property="og:url" content="{url_absoluta(rota)}" />
<meta property="og:image" content="{og}" />
<meta name="twitter:card" content="summary_large_image" />
{jsonld_bloco}
</head>"""


def badge(estado: dict, extra: str = "") -> str:
    sinal, _, classe = BADGE[estado["status"]]
    classe_total = f"badge {classe}" + (f" {extra}" if extra else "")
    glifo = (f'<span class="badge__sinal" aria-hidden="true">{sinal}</span> ' if sinal else "")
    return f'<span class="{classe_total}">{glifo}{esc(estado["rotulo"])}</span>' 


def usar_capa(oferta: dict) -> bool:
    """Capa com preço só entra quando existe preço conferido (o cartaz não pode anunciar preço velho)."""
    if not oferta.get("capa"):
        return False
    if oferta.get("capa_tem_preco") and not oferta.get("preco"):
        return False
    return True


def capa_bloco(oferta: dict, profundidade: int, classe: str, classe_vazia: str) -> str:
    if usar_capa(oferta):
        return (f'<div class="{classe}"><img src="{rel(profundidade, oferta["capa"])}" '
                f'alt="{esc(oferta["capa_alt"])}" width="720" height="1280" loading="lazy" /></div>')
    logo = rel(profundidade, "assets/img/avatar-master.svg")
    return (f'<div class="{classe} {classe_vazia}">'
            f'<span class="capa-marca"><img src="{logo}" alt="" width="1800" height="600" /></span></div>')


def painel_preco(oferta: dict, profundidade: int) -> str:
    preco = oferta.get("preco")
    estado = oferta["_estado"]
    if not preco:
        return f"""<div class="painel__estado">
          <p class="rotulo">Preço</p>
          {badge(estado)}
        </div>
        <p class="painel__vazio">Sem preço confirmado</p>
        <p class="painel__sem">
          O número só aparece depois da leitura no anúncio, com data e hora. Esta oferta ainda não passou pela
          conferência diária, então não mostramos valor nenhum.
        </p>
        <div class="painel__linha"><span>Última leitura</span><span>—</span></div>
        <div class="painel__linha"><span>Publicado em</span><span>{esc(data(oferta["postado_em"]))}</span></div>
        <div class="painel__linha"><span>Vídeo</span><span>{len(oferta["videos"])} canais</span></div>
        <a class="btn btn--primario" href="{esc(oferta["link_afiliado"])}" target="_blank" rel="noopener noreferrer sponsored">
          Abrir anúncio no Mercado Livre
        </a>
        <p class="aviso-afiliado">Link de afiliado: podemos receber comissão pela compra, sem custo adicional para você.
        Confira o preço na página do anúncio.</p>"""

    parcelas = preco.get("parcelas")
    linha_parcela = ("—" if not parcelas
                     else f'{parcelas["quantidade"]}x {money(parcelas["valor"])} sem juros')
    de = f'de <s>{money(preco["de"])}</s>' if preco.get("de") else ""
    desconto = f' · {pct(preco["desconto_pct"])} OFF' if preco.get("desconto_pct") else ""
    pix = (f'<div class="painel__linha"><span>No Pix</span><span>{money(preco["pix"])}</span></div>'
           if preco.get("pix") and not so_pix(preco) else "")
    cartao_ausente = ('<div class="painel__linha"><span>No cartão</span>'
                      '<span>preço não impresso no anúncio</span></div>' if so_pix(preco) else "")
    vendedor = (f'<div class="painel__linha"><span>Vendido por</span><span>{esc(oferta["vendedor"])}</span></div>'
                if oferta.get("vendedor") else "")
    avaliacao = (""
                 if not oferta.get("avaliacao")
                 else f'<div class="painel__linha"><span>Avaliações</span>'
                      f'<span>{str(oferta["avaliacao"]["nota"]).replace(".", ",")} de 5 · '
                      f'{oferta["avaliacao"]["opinioes"]} opiniões</span></div>')
    return f"""<div class="painel__estado">
          <p class="rotulo">Preço conferido</p>
          {badge(estado)}
        </div>
        <div class="preco">
          <p class="preco__de">{de}{desconto}</p>
          <p class="preco__valor"><small>a partir de</small>{money(valor_vista(preco))}{'<small> no Pix</small>' if so_pix(preco) else ''}</p>
        </div>
        {pix}
        {cartao_ausente}
        <div class="painel__linha"><span>Parcelado</span><span>{linha_parcela}</span></div>
        {vendedor}
        {avaliacao}
        <p class="painel__conferido">
          Lido no anúncio em <strong>{esc(data_hora(preco["price_checked_at"]))}</strong>
          (horário de Brasília). Preço e estoque podem mudar depois disso.
        </p>
        <a class="btn btn--primario" href="{esc(oferta["link_afiliado"])}" target="_blank" rel="noopener noreferrer sponsored">
          Ver oferta no Mercado Livre
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M7 17 17 7M9 7h8v8"/></svg>
        </a>
        <p class="aviso-afiliado">Link de afiliado: podemos receber comissão pela compra, sem custo adicional para você.</p>"""


# --------------------------------------------------------------------------
# páginas
# --------------------------------------------------------------------------

def pagina_home(ofertas: list[dict], referencia: str) -> str:
    destaque = ofertas[0]
    conferidas = [o for o in ofertas if o["_conferida_24h"]]
    outras_dia = [o for o in conferidas if o["slug"] != destaque["slug"]]
    sem_preco = [o for o in ofertas if o["_estado"]["status"] == "sem_conferencia"]
    estado = destaque["_estado"]

    preco = destaque.get("preco")
    if preco:
        de = f'de <s>{money(preco["de"])}</s>' if preco.get("de") else ""
        desconto = f' · {pct(preco["desconto_pct"])} OFF no anúncio' if preco.get("desconto_pct") else ""
        valor = (f'<p class="preco__valor"><small>a partir de</small>{money(valor_vista(preco))}'
                 f'{"<small> no Pix</small>" if so_pix(preco) else ""}</p>')
        parcela = f'{preco["parcelas"]["quantidade"]}x {money(preco["parcelas"]["valor"])} sem juros' \
            if preco.get("parcelas") else ""
        pix = (f'<span>· {money(preco["pix"])} no Pix</span>'
               if preco.get("pix") and not so_pix(preco) else "")
        bloco_preco = f"""<div class="preco">
          <p class="preco__de">{de}{desconto}</p>
          {valor}
          <p class="preco__parcela">{parcela} {pix}</p>
        </div>"""
        conferido = (f'Preço lido no anúncio em <strong>{esc(data_hora(preco["price_checked_at"]))}</strong>. '
                     f'Pode mudar depois disso — <a href="como-conferimos/index.html">veja como conferimos</a>.')
        # capa que estampa preço: o cartaz é do dia da gravação, e o texto diz isso
        if (destaque.get("capa") and destaque.get("capa_preco") is not None
                and abs(destaque["capa_preco"] - valor_vista(preco)) > 0.001):
            conferido += (f' O cartaz do vídeo mostra o preço do dia da gravação, '
                          f'{money(destaque["capa_preco"])}; vale o preço conferido acima.')
    else:
        bloco_preco = '<p class="preco__vazio">Sem preço confirmado</p>'
        conferido = ('Ainda sem preço conferido. O número só aparece depois da leitura no anúncio, '
                     'com data e hora.')

    selos = []
    if destaque.get("avaliacao"):
        selos.append(f'{str(destaque["avaliacao"]["nota"]).replace(".", ",")}★ em '
                     f'{destaque["avaliacao"]["opinioes"]} avaliações')
    if destaque.get("vendedor"):
        selos.append(esc(destaque["vendedor"]))
    if preco and preco.get("desconto_pct"):
        selos.append("Sem cupom no anúncio")
    if destaque.get("ficha"):
        selos.append("Ficha do anúncio conferida")
    selos_html = "".join(f"<li>{s}</li>" for s in selos)

    video_principal = destaque["videos"].get("youtube") or next(iter(destaque["videos"].values()))
    if usar_capa(destaque):
        capa = rel(0, destaque["capa"])
        capa_alt = destaque["capa_alt"]
        classe_video = "video"
    else:
        capa = rel(0, "assets/img/avatar-master.svg")
        capa_alt = ""
        classe_video = "video video--vazia"
        destaque = dict(destaque, capa=None)

    # "Verificadas hoje" só aparece quando há outra oferta conferida além do destaque.
    if outras_dia:
        if len(outras_dia) == 1:
            o = outras_dia[0]
            cards = f"""<ul class="hoje hoje--unica">
        <li>
          <article class="mini mini--largo">
            {capa_bloco(o, 0, "mini__foto", "mini__foto--marca")}
            <div class="mini__corpo">
              <span class="mini__cat">{esc(o["categoria"]["rotulo"])}</span>
              <h3 class="mini__titulo"><a href="{o["_url"]}index.html">{esc(o["titulo_curto"])}</a></h3>
              <p class="mini__preco">{money(valor_vista(o["_preco"])) + (" no Pix" if so_pix(o["_preco"]) else "") if o["_preco"] else "Sem preço"}</p>
              <p class="mini__detalhe">{esc(o["_estado"]["rotulo"])}</p>
              <p class="mini__conf">Conferido {esc(data_curta(o["_preco"]["price_checked_at"]))}, {esc(hora(o["_preco"]["price_checked_at"]))}</p>
            </div>
          </article>
        </li>
      </ul>"""
        else:
            itens = "".join(mini_card(o, 0) for o in outras_dia)
            cards = f'<ul class="hoje">{itens}</ul>'
        secao_dia = f"""<section class="secao" id="dia" aria-labelledby="dia-titulo">
      <div class="secao__cabecalho">
        <div>
          <span class="kicker">Conferência do dia</span>
          <h2 id="dia-titulo">Verificadas hoje</h2>
          <p>Preço lido no anúncio nas últimas 24 horas.</p>
        </div>
        <p class="secao__nota"><strong>{len(conferidas)}</strong> {'conferida' if len(conferidas) == 1 else 'conferidas'} · última às {esc(hora(referencia))}</p>
      </div>
      {cards}
    </section>"""
    else:
        secao_dia = ""

    cartoes = "".join(item_card(o, 0) for o in ofertas[:3])
    restantes = max(len(ofertas) - 3, 0)

    capa_og = destaque.get("capa")
    jsonld_bloco = jsonld({
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "Ofertas conferidas — Grupo Top Ofertas",
        "url": SITE + "/",
        "numberOfItems": len(ofertas),
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1,
             "url": url_absoluta(o["_url"]), "name": o["titulo"]}
            for i, o in enumerate(ofertas)
        ],
    })

    return f"""{head(
        "Grupo Top Ofertas — ofertas conferidas com preço e data",
        "Ofertas selecionadas do Mercado Livre com o vídeo de cada recomendação e o preço lido no anúncio, com data e hora. Arquivo de tudo o que já foi postado.",
        "", "vitrine", capa_og, jsonld_bloco, "website")}
<body>
<a class="skip" href="#conteudo">Pular para o conteúdo</a>
{cabecalho("vitrine", 0, referencia)}
<main id="conteudo">
  <div class="envoltorio">
    <section class="destaque" id="dia" aria-labelledby="destaque-titulo">
      <div>
        <span class="destaque__etiqueta">Oferta de hoje · {esc(data_curta(referencia))}</span>
        <h1 class="destaque__titulo" id="destaque-titulo">{esc(destaque["titulo_curto"])}</h1>
        <p class="destaque__veredito">{esc(destaque["veredito"])}</p>
        {bloco_preco}
        <ul class="selos">{selos_html}</ul>
        <p class="conferido">{conferido}</p>
        <div class="acoes">
          <a class="btn btn--primario" href="{esc(destaque["link_afiliado"])}" target="_blank" rel="noopener noreferrer sponsored">
            Ver oferta no Mercado Livre
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M7 17 17 7M9 7h8v8"/></svg>
          </a>
          <a class="btn btn--secundario" href="{destaque["_url"]}index.html">Ficha completa</a>
        </div>
        <p class="aviso-afiliado">Link de afiliado: podemos receber comissão pela compra, sem custo adicional para você.</p>
      </div>
      <a class="{classe_video}" href="{esc(video_principal)}" target="_blank" rel="noopener noreferrer">
        <img src="{capa}" alt="{esc(capa_alt)}" width="720" height="1280" />
        <span class="video__play" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
        </span>
        <span class="video__legenda"><span>Vídeo{(' · ' + str(destaque['duracao_video_s']) + ' s') if destaque.get('duracao_video_s') else ''}</span><span>{esc(ROTULO_CANAL['youtube'] if 'youtube' in destaque['videos'] else 'Vídeo')}</span></span>
      </a>
    </section>

    <div class="numeros" role="list" aria-label="Resumo do arquivo">
      <div role="listitem"><strong>{len(ofertas)}</strong><span>ofertas no arquivo</span></div>
      <div role="listitem"><strong>{len(conferidas)}</strong><span>{'conferida hoje' if len(conferidas) == 1 else 'conferidas hoje'}</span></div>
      <div role="listitem"><strong>{len(sem_preco)}</strong><span>sem conferência</span></div>
    </div>

    {secao_dia}

    <section class="secao secao--faixa" id="arquivo" aria-labelledby="arquivo-titulo">
      <div class="secao__cabecalho">
        <div>
          <span class="kicker">Arquivo</span>
          <h2 id="arquivo-titulo">Tudo o que já foi postado</h2>
          <p>Oferta publicada não sai do ar: ganha estado de preço e continua indexada.</p>
        </div>
        <p class="secao__nota"><a href="ofertas/index.html">Ver arquivo completo ({len(ofertas)})</a></p>
      </div>
      <ul class="grade">{cartoes}</ul>
      {f'<p class="aviso-afiliado">{restantes} {"oferta mais antiga" if restantes == 1 else "ofertas mais antigas"} no <a href="ofertas/index.html">arquivo completo</a>.</p>' if restantes else ''}
    </section>

    <section class="secao" id="metodo">
      <div class="metodo">
        <div>
          <span class="kicker">Regra do portal</span>
          <h2>Nenhum preço sem data e hora</h2>
          <p>O número só aparece depois da leitura no anúncio. Quando muda, a oferta não é apagada: ganha selo e novo registro.</p>
        </div>
        <ol class="passos">
          <li><span aria-hidden="true">1</span><div><strong>Abrimos o anúncio</strong>sem sessão, com o link de afiliado, e lemos o preço da tela.</div></li>
          <li><span aria-hidden="true">2</span><div><strong>Registramos data e hora</strong>da leitura, o valor no cartão e no Pix, e o parcelamento só quando é sem juros.</div></li>
          <li><span aria-hidden="true">3</span><div><strong>Comparamos com a postagem</strong>e marcamos preço igual, caiu, subiu ou indisponível.</div></li>
        </ol>
      </div>
    </section>
  </div>
</main>
{rodape(0)}
</body>
</html>
"""


def mini_card(oferta: dict, profundidade: int) -> str:
    preco = oferta["_preco"]
    valor = money(valor_vista(preco)) if preco else "Sem preço"
    if preco and so_pix(preco):
        valor += " no Pix"
    detalhe = oferta["_estado"]["rotulo"] if not preco else (
        f'{preco["parcelas"]["quantidade"]}x {money(preco["parcelas"]["valor"])} sem juros'
        if preco.get("parcelas") else oferta["_estado"]["rotulo"])
    conferido = (f'Conferido {data_curta(preco["price_checked_at"])}, {hora(preco["price_checked_at"])}'
                 if preco else "Aguardando conferência")
    return f"""<li>
          <article class="mini">
            {capa_bloco(oferta, profundidade, "mini__foto", "mini__foto--marca")}
            <div class="mini__corpo">
              <span class="mini__cat">{esc(oferta["categoria"]["rotulo"])}</span>
              <h3 class="mini__titulo"><a href="{rel(profundidade, oferta["_url"] + 'index.html')}">{esc(oferta["titulo_curto"])}</a></h3>
              <p class="mini__preco">{valor}</p>
              <p class="mini__detalhe">{esc(detalhe)}</p>
              <p class="mini__conf">{esc(conferido)}</p>
            </div>
          </article>
        </li>"""


def item_card(oferta: dict, profundidade: int) -> str:
    preco = oferta["_preco"]
    estado = oferta["_estado"]
    if preco:
        valor = money(valor_vista(preco))
        detalhe = (f'{preco["parcelas"]["quantidade"]}x {money(preco["parcelas"]["valor"])} sem juros'
                   if preco.get("parcelas") else ("no Pix" if so_pix(preco) else "no anúncio"))
        rodape_preco = f"Conferido <strong>{esc(data_curta(preco['price_checked_at']))}, {esc(hora(preco['price_checked_at']))}</strong>"
    else:
        valor = "Sem preço confirmado"
        detalhe = "aguardando conferência"
        rodape_preco = "Aguardando conferência"
    return f"""<li>
          <article class="item">
            <div style="position:relative">
              {capa_bloco(oferta, profundidade, "item__foto", "item__foto--marca")}
              {badge(estado, "item__selo")}
            </div>
            <div class="item__corpo">
              <span class="item__meta">{esc(oferta["categoria"]["rotulo"])} · {esc(data_curta(oferta["postado_em"]))}</span>
              {badge(estado, "item__selo-mobile")}
              <h3 class="item__titulo"><a href="{rel(profundidade, oferta["_url"] + 'index.html')}">{esc(oferta["titulo_curto"])}</a></h3>
              <p class="item__preco{' item__preco--vazio' if not preco else ''}">{valor}<small>{esc(detalhe)}</small></p>
              <p class="item__rodape"><span>{rodape_preco}</span><span>{esc(oferta["item_id"])}</span></p>
            </div>
          </article>
        </li>"""


def pagina_arquivo(ofertas: list[dict], referencia: str) -> str:
    linhas = []
    for o in ofertas:
        estado = o["_estado"]
        preco = o["_preco"]
        if preco:
            valor = money(valor_vista(preco))
            extra = ("no Pix" if so_pix(preco) else
                     (f'{preco["parcelas"]["quantidade"]}x {money(preco["parcelas"]["valor"])}'
                      if preco.get("parcelas") else (f'de {money(preco["de"])}' if preco.get("de") else "")))
            valor_html = f'{valor}<small>{esc(extra)}</small>'
            conferido = f'{data_curta(preco["price_checked_at"])}, {hora(preco["price_checked_at"])}'
        else:
            valor_html = '<span class="linha__preco--vazio">sem preço confirmado</span>'
            conferido = "—"
        linhas.append(f"""<li class="linha" role="row">
            <span class="linha__produto" role="cell">
              {capa_bloco(o, 1, "thumb", "thumb--marca")}
              <span>
                <a class="linha__nome" href="{rel(1, o["_url"] + 'index.html')}">{esc(o["titulo"])}</a>
                <span class="linha__meta">{esc(o["item_id"])} · {esc(o["categoria"]["rotulo"])}</span>
              </span>
            </span>
            <span class="linha__data" role="cell">{esc(data_curta(o["postado_em"]))}</span>
            <span class="linha__preco" role="cell">{valor_html}</span>
            <span role="cell">{badge(estado)}</span>
            <span class="linha__conf" role="cell">{esc(conferido)}</span>
          </li>""")

    jsonld_bloco = jsonld({
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "Arquivo de ofertas — Grupo Top Ofertas",
        "url": url_absoluta("ofertas/"),
        "hasPart": [{"@type": "Product", "name": o["titulo"], "url": url_absoluta(o["_url"])}
                    for o in ofertas],
    })

    return f"""{head(
        "Arquivo de ofertas — Grupo Top Ofertas",
        f"Todas as {len(ofertas)} ofertas já publicadas pelo Grupo Top Ofertas, com o estado do preço na última conferência. Oferta publicada não sai do ar.",
        "ofertas/", "arquivo", None, jsonld_bloco, "website")}
<body>
<a class="skip" href="#conteudo">Pular para o conteúdo</a>
{cabecalho("arquivo", 1, referencia)}
<main id="conteudo">
  <div class="envoltorio">
    <section class="secao" aria-labelledby="arquivo-titulo">
      <div class="secao__cabecalho">
        <div>
          <p class="rotulo">Arquivo</p>
          <h1 id="arquivo-titulo" style="margin:0;font-size:32px;letter-spacing:-.025em;color:#0F1B32">Todas as ofertas publicadas</h1>
          <p>Toda recomendação continua aqui, com o estado do preço na última leitura.</p>
        </div>
        <p class="secao__nota">{len(ofertas)} ofertas · nenhuma removida</p>
      </div>

      <div class="tabela" role="table" aria-labelledby="arquivo-titulo">
        <div class="tabela__cabecalho" role="row">
          <span role="columnheader">Produto</span>
          <span role="columnheader">Postado</span>
          <span role="columnheader">Preço conferido</span>
          <span role="columnheader">Estado</span>
          <span role="columnheader">Conferido em</span>
        </div>
        <ul class="linhas" role="rowgroup">
          {''.join(linhas)}
        </ul>
      </div>
      <p class="aviso-afiliado">
        Última conferência do arquivo: {esc(data_hora(referencia))} (horário de Brasília).
        "Sem preço confirmado" significa que a oferta está no arquivo, mas o preço ainda não foi lido no anúncio
        depois da postagem — e o portal não mostra número sem essa leitura.
      </p>
    </section>

    <section class="metodo" aria-labelledby="metodo-titulo" style="margin-bottom:44px">
      <div>
        <h2 id="metodo-titulo">Como o estado é calculado</h2>
        <p>O selo vem da comparação entre a última leitura e a anterior. Nada é digitado à mão.</p>
      </div>
      <ol class="passos">
        <li><span aria-hidden="true">1</span><div><strong>Sem preço lido</strong>a oferta fica em "sem conferência" e nenhum número é exibido.</div></li>
        <li><span aria-hidden="true">2</span><div><strong>Com uma leitura</strong>o selo é "primeira conferência": não existe comparação ainda.</div></li>
        <li><span aria-hidden="true">3</span><div><strong>Com duas ou mais</strong>o build compara e marca preço igual, caiu ou subiu.</div></li>
        <li><span aria-hidden="true">4</span><div><strong>Anúncio fora do ar</strong>vira "indisponível" e a página continua publicada.</div></li>
      </ol>
    </section>
  </div>
</main>
{rodape(1)}
</body>
</html>
"""


def pagina_oferta(oferta: dict, ofertas: list[dict], referencia: str) -> str:
    profundidade = 2
    estado = oferta["_estado"]
    preco = oferta["_preco"]
    video_principal = oferta["videos"].get("youtube") or next(iter(oferta["videos"].values()))
    canais = "".join(
        f'<li><a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(ROTULO_CANAL[c])} ↗</a></li>'
        for c, url in oferta["videos"].items()
    )
    ficha_html = ""
    if oferta.get("ficha"):
        ficha_html = f"""<section class="bloco" aria-labelledby="ficha-titulo">
      <div class="bloco__cabecalho">
        <h2 id="ficha-titulo">Ficha do anúncio</h2>
        <p class="bloco__nota">Somente o que está na página do produto.</p>
      </div>
      <ul class="ficha-lista">
        {''.join(f'<li>{esc(v)}</li>' for v in oferta["ficha"])}
      </ul>
    </section>"""

    if preco:
        historico = "".join(
            f"""<li>
          <span class="ponto" aria-hidden="true"></span>
          <time datetime="{esc(p["em"])}">{esc(data(p["em"]))} · {esc(hora(p["em"]))}</time>
          <span class="valor">{money(p["cartao"] if p.get("cartao") is not None else p.get("pix"))}
          {'<small> no Pix</small>' if p.get('cartao') is None else ''}</span>
          <span class="nota">{'Primeira conferência — preço que entrou no vídeo.' if i == 0 else 'Reconferência.'}
          {f' No Pix, {money(p["pix"])}.' if p.get('pix') and p.get('cartao') is not None else ''}</span>
        </li>"""
            for i, p in enumerate(oferta["historico_preco"])
        )
        bloco_tempo = f"""<section class="bloco" aria-labelledby="linha-titulo">
      <div class="bloco__cabecalho">
        <h2 id="linha-titulo">Linha do tempo do preço</h2>
        <p class="bloco__nota">{len(oferta["historico_preco"])} {'leitura registrada' if len(oferta['historico_preco']) == 1 else 'leituras registradas'} · a próxima entra na conferência diária.</p>
      </div>
      <ol class="linha-tempo">{historico}</ol>
    </section>"""
    else:
        bloco_tempo = """<section class="bloco" aria-labelledby="linha-titulo">
      <div class="bloco__cabecalho">
        <h2 id="linha-titulo">Linha do tempo do preço</h2>
        <p class="bloco__nota">Nenhuma leitura registrada.</p>
      </div>
      <p class="aviso-afiliado">Esta oferta foi publicada, mas ainda não teve o preço lido no anúncio depois da
      postagem. Assim que a conferência diária acontecer, o valor e a data entram aqui.</p>
    </section>"""

    outras = [o for o in ofertas if o["slug"] != oferta["slug"]][:3]
    outras_html = "".join(f"""<li>
          <a class="outra" href="{rel(profundidade, o["_url"] + 'index.html')}">
            {capa_bloco(o, profundidade, "thumb", "thumb--marca")}
            <span>
              <strong>{esc(o["titulo_curto"])}</strong>
              <small>{esc(o["categoria"]["rotulo"])} · {esc(o["_estado"]["rotulo"])}</small>
            </span>
          </a>
        </li>""" for o in outras)

    capa = oferta.get("capa") if usar_capa(oferta) else None
    if capa:
        capa_html = (f'<img src="{rel(profundidade, capa)}" alt="{esc(oferta["capa_alt"])}" '
                     f'width="720" height="1280" />')
    else:
        capa_html = (f'<span class="capa-marca capa-marca--ficha">'
                     f'<img src="{rel(profundidade, "assets/img/avatar-master.svg")}" '
                     f'alt="" width="1080" height="1080" />'
                     f'<span class="capa-vazia__txt">Abrir o vídeo no canal</span></span>')

    dados_estruturados = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": oferta["titulo"],
        "sku": oferta["item_id"],
        "description": oferta["veredito"],
        "image": [url_absoluta(capa)] if capa else [url_absoluta("assets/img/logo-horizontal-1800x600.png")],
        "url": url_absoluta(oferta["_url"]),
    }
    if oferta.get("marca"):
        dados_estruturados["brand"] = {"@type": "Brand", "name": oferta["marca"]}
    if preco:
        dados_estruturados["offers"] = {
            "@type": "Offer",
            "url": url_absoluta(oferta["_url"]),
            "priceCurrency": preco["moeda"],
            "price": f'{valor_vista(preco):.2f}',
            "availability": "https://schema.org/InStock" if oferta["disponibilidade"] == "InStock"
            else "https://schema.org/OutOfStock",
            "seller": {"@type": "Organization", "name": "Mercado Livre"},
        }
    if capa:
        dados_estruturados["subjectOf"] = {
            "@type": "VideoObject",
            "name": f'Vídeo: {oferta["titulo_curto"]}',
            "thumbnailUrl": url_absoluta(capa),
            "uploadDate": oferta["postado_em"],
            "url": video_principal,
        }
    migalhas = jsonld({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Início", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Arquivo", "item": url_absoluta("ofertas/")},
            {"@type": "ListItem", "position": 3, "name": oferta["titulo_curto"], "item": url_absoluta(oferta["_url"])},
        ],
    })

    return f"""{head(
        f'{oferta["titulo_curto"]} — {estado["rotulo"]} | Grupo Top Ofertas',
        oferta["veredito"],
        oferta["_url"], "arquivo", capa,
        jsonld(dados_estruturados) + "\n" + migalhas, "product")}
<body>
<a class="skip" href="#conteudo">Pular para o conteúdo</a>
{cabecalho("arquivo", profundidade, referencia)}
<main id="conteudo">
  <div class="envoltorio">
    <nav class="migalhas" aria-label="Você está aqui">
      <a href="{rel(profundidade, 'index.html')}">Início</a> <span aria-hidden="true">/</span>
      <a href="{rel(profundidade, 'ofertas/index.html')}">Arquivo</a> <span aria-hidden="true">/</span>
      <span aria-current="page">{esc(oferta["titulo_curto"])}</span>
    </nav>

    <header class="ficha-topo">
      <p class="rotulo">{esc(oferta["categoria"]["rotulo"])} · {esc(oferta["item_id"])}</p>
      <h1>{esc(oferta["titulo"])}</h1>
      <p class="ficha-topo__veredito">{esc(oferta["veredito"])}</p>
      <p class="ficha-topo__meta">
        <span>Publicado em {esc(data(oferta["postado_em"]))}</span>
        <span>Vídeo em {len(oferta["videos"])} canais</span>
        <span>{esc(estado["rotulo"])}</span>
      </p>
    </header>

    <div class="ficha">
      <div class="ficha__midia">
        <a class="video video--ficha{' video--vazia' if not capa else ''}" href="{esc(video_principal)}" target="_blank" rel="noopener noreferrer">
          {capa_html}
          <span class="video__play" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
          </span>
          <span class="video__legenda"><span>Vídeo do produto</span><span>{esc(ROTULO_CANAL['youtube'] if 'youtube' in oferta['videos'] else 'Vídeo')}</span></span>
        </a>
        <ul class="canais-video" aria-label="Onde assistir ao vídeo">{canais}</ul>
        <p class="capa-fonte">{'Imagem: capa do vídeo publicado em ' + esc(data(oferta['postado_em'])) + '. Nenhuma foto do anúncio é usada no site.' if capa else 'A capa deste vídeo traz o preço do dia da gravação. Sem conferência atual, ela não é exibida — a página usa a marca no lugar.'}{(' O cartaz estampa o preço do dia da gravação, ' + money(oferta['capa_preco']) + '.') if (capa and oferta.get('capa_preco') is not None) else ''}</p>
      </div>

      <aside class="painel" data-estado="{estado['status']}" data-leituras="{len([h for h in oferta['historico_preco'] if preco and h.get(tipo_preco(preco)) is not None])}" data-pontos="{len(oferta['historico_preco'])}" data-preco="{tipo_preco(preco) if preco else 'nenhum'}">
        {painel_preco(oferta, profundidade)}
      </aside>
    </div>

    {ficha_html}
    {bloco_tempo}

    <section class="bloco" aria-labelledby="outras-titulo">
      <div class="bloco__cabecalho">
        <h2 id="outras-titulo">Outras ofertas do arquivo</h2>
        <p class="bloco__nota"><a href="{rel(profundidade, 'ofertas/index.html')}">Ver todas</a></p>
      </div>
      <ul class="outras">{outras_html}</ul>
    </section>
  </div>
</main>
{rodape(profundidade)}
</body>
</html>
"""


def pagina_texto(titulo: str, descricao: str, rota: str, corpo: str, referencia: str) -> str:
    profundidade = rota.count("/")
    return f"""{head(titulo, descricao, rota, "arquivo")}
<body>
<a class="skip" href="#conteudo">Pular para o conteúdo</a>
{cabecalho("arquivo", profundidade, referencia)}
<main id="conteudo">
  <div class="envoltorio">
    <article class="texto">
      {corpo}
    </article>
  </div>
</main>
{rodape(profundidade)}
</body>
</html>
"""


def pagina_como(referencia: str) -> str:
    corpo = f"""
      <p class="rotulo">Método</p>
      <h1>Como conferimos o preço</h1>
      <p class="lead">O portal não é um agregador de cupom. É o arquivo do que o canal recomendou, com o preço lido no
      anúncio e a data dessa leitura.</p>

      <h2>O que é conferido</h2>
      <ul>
        <li>O preço no cartão, direto da página do anúncio.</li>
        <li>O preço no Pix, quando o anúncio mostra um.</li>
        <li>Quando o anúncio só imprime o preço no Pix, o portal mostra esse valor, marcado como Pix, e diz que o preço de cartão não aparece no anúncio.</li>
        <li>O parcelamento, somente quando é sem juros.</li>
        <li>Se o anúncio está no ar e se o link de afiliado abre o produto.</li>
        <li>A data e a hora da leitura, em horário de Brasília.</li>
      </ul>

      <h2>O que não é conferido</h2>
      <ul>
        <li>Frete, prazo de entrega e estoque por região.</li>
        <li>Cupons que exigem seguir a loja ou outra ação.</li>
        <li>Preço de terceiros, de agregador ou de print antigo.</li>
      </ul>

      <div class="nota">
        <p><strong>Regra dura:</strong> nenhum preço aparece sem data e hora. Se a oferta foi publicada e o preço ainda
        não foi lido depois disso, a página mostra "sem preço confirmado" em vez de um número.</p>
      </div>

      <h2>Com que frequência</h2>
      <p>As ofertas mais recentes são conferidas uma vez por dia útil. As mais antigas entram numa revisão semanal.
      O portal não promete preço em tempo real: mostra sempre a data da última leitura.</p>

      <h2>Como o estado é calculado</h2>
      <ul>
        <li><strong>Primeira conferência:</strong> só existe uma leitura, então não há comparação — e o selo diz isso.</li>
        <li><strong>Preço igual:</strong> a partir da segunda leitura, o valor é o mesmo da anterior.</li>
        <li><strong>Caiu / subiu:</strong> a diferença em reais entre as duas últimas leituras.</li>        <li><strong>Indisponível:</strong> o anúncio saiu do ar.</li>
        <li><strong>Sem conferência:</strong> ainda não houve leitura depois da postagem.</li>
        <li><strong>Comparação do mesmo tipo:</strong> cartão com cartão, Pix com Pix. Um valor de Pix nunca é comparado com um de cartão.</li>
      </ul>
      <p>O cálculo é feito no build do site, a partir do histórico de leituras. O histórico é só de acréscimo:
      um ponto antigo nunca é reescrito.</p>

      <h2>Links de afiliado</h2>
      <p>Participamos do Programa de Afiliados do Mercado Livre. Ao comprar por um link do site, podemos receber
      comissão, sem custo adicional para você. <a href="../aviso-de-afiliado/index.html">Aviso completo</a>.</p>

      <p class="aviso-afiliado">Última conferência registrada: {esc(data_hora(referencia))} (horário de Brasília).</p>
    """
    return pagina_texto("Como conferimos o preço — Grupo Top Ofertas",
                        "O método do portal: o que é conferido, com que frequência, o que não é conferido e como o estado do preço é calculado.",
                        "como-conferimos/", corpo, referencia)


def pagina_aviso(referencia: str) -> str:
    corpo = """
      <p class="rotulo">Transparência</p>
      <h1>Aviso de links de afiliado</h1>
      <p class="lead">Os links de oferta deste site são links de afiliado do Mercado Livre.</p>

      <h2>O que isso significa</h2>
      <p>Quando você compra por um link do Grupo Top Ofertas, podemos receber uma comissão do Mercado Livre.
      O preço que você paga é o mesmo do anúncio — a comissão não é um custo adicional.</p>

      <h2>Preço e disponibilidade</h2>
      <p>O preço exibido é o que estava no anúncio na data e hora informadas em cada oferta. Preço, estoque,
      frete e promoções podem mudar a qualquer momento. Confira sempre o valor final na página do Mercado Livre
      antes de comprar.</p>

      <h2>O que o site não faz</h2>
      <ul>
        <li>Não vende produto nem processa pagamento.</li>
        <li>Não garante preço, estoque ou prazo de entrega.</li>
        <li>Não publica preço sem data e hora de conferência.</li>
      </ul>

      <h2>Programa de afiliados</h2>
      <p>O Grupo Top Ofertas participa do Programa de Afiliados do Mercado Livre e segue as regras do programa
      sobre identificação de conteúdo publicitário.</p>

      <p class="aviso-afiliado">Dúvidas sobre uma oferta: fale com o canal pelo Instagram, TikTok, Facebook ou YouTube.</p>
    """
    return pagina_texto("Aviso de links de afiliado — Grupo Top Ofertas",
                        "Como funcionam os links de afiliado do Grupo Top Ofertas, o que muda no preço e o que o site não garante.",
                        "aviso-de-afiliado/", corpo, referencia)


def pagina_canais(referencia: str) -> str:
    itens = "".join(
        f'<li><a href="{url}" target="_blank" rel="noopener noreferrer">{esc(nome)}</a> — {esc(url)}</li>'
        for nome, url in REDES
    )
    corpo = f"""
      <p class="rotulo">Onde encontrar</p>
      <h1>Canais oficiais</h1>
      <p class="lead">Os vídeos de cada oferta saem primeiro nos canais. O portal guarda o vídeo e o preço conferido.</p>
      <ul>{itens}</ul>
      <p class="aviso-afiliado">Estes são os canais oficiais do Grupo Top Ofertas. Desconfie de perfis com nome parecido
      que não estejam nesta lista.</p>
    """
    return pagina_texto("Canais oficiais — Grupo Top Ofertas",
                        "Instagram, TikTok, Facebook e YouTube oficiais do Grupo Top Ofertas.",
                        "canais/", corpo, referencia)


def pagina_404() -> str:
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Página não encontrada — Grupo Top Ofertas</title>
<meta name="robots" content="noindex" />
<link rel="icon" href="/favicon.svg" type="image/svg+xml" />
<link rel="stylesheet" href="/assets/css/arquivo.css" />
</head>
<body>
<main id="conteudo">
  <div class="envoltorio">
    <article class="texto">
      <p class="rotulo">404</p>
      <h1>Essa página não existe</h1>
      <p>O endereço pode ter mudado ou o link estar errado. As ofertas publicadas ficam no arquivo.</p>
      <p><a href="/">Ir para a página inicial</a> · <a href="/ofertas/">Ver o arquivo de ofertas</a></p>
    </article>
  </div>
</main>
</body>
</html>
"""


# --------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------

def escrever(caminho: str, conteudo: str) -> None:
    destino = SAIDA / caminho
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(conteudo, encoding="utf-8", newline="\n")


def gerar_sitemap(ofertas: list[dict], referencia: str) -> str:
    def ultima_mudanca(o: dict) -> str:
        datas = [o.get("atualizado_em"), o.get("postado_em"), (o.get("preco") or {}).get("price_checked_at")]
        return max([d for d in datas if d], key=quando)

    paginas = [
        ("", referencia),
        ("ofertas/", referencia),
        ("como-conferimos/", referencia),
        ("aviso-de-afiliado/", referencia),
        ("canais/", referencia),
    ] + [(o["_url"], ultima_mudanca(o)) for o in ofertas]
    urls = "".join(
        f"  <url>\n    <loc>{url_absoluta(rota)}</loc>\n    <lastmod>{data(iso)[6:10]}-{data(iso)[3:5]}-{data(iso)[0:2]}</lastmod>\n  </url>\n"
        for rota, iso in paginas
    )
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{urls}</urlset>\n")


def main() -> None:
    dados = carregar()
    referencia = referencia_efetiva(dados)
    ofertas = preparar(dados)

    if "--check" in sys.argv:
        print(f"OK · {len(ofertas)} ofertas · referência {data_hora(referencia)}")
        for o in ofertas:
            print(f"  {o['_url']:45} {o['_estado']['status']}")
        return

    if SAIDA.exists():
        shutil.rmtree(SAIDA)
    SAIDA.mkdir(parents=True)

    # só o que o site usa: capas próprias, identidade e CSS. Nenhuma foto de anúncio entra no build.
    for pasta in ("capas", "css", "img"):
        shutil.copytree(RAIZ / "assets" / pasta, SAIDA / "assets" / pasta)
    shutil.copyfile(RAIZ / "assets" / "img" / "logo-horizontal.svg", SAIDA / "favicon.svg")

    escrever("index.html", pagina_home(ofertas, referencia))
    escrever("ofertas/index.html", pagina_arquivo(ofertas, referencia))
    for o in ofertas:
        escrever(f"oferta/{o['slug']}/index.html", pagina_oferta(o, ofertas, referencia))
    escrever("como-conferimos/index.html", pagina_como(referencia))
    escrever("aviso-de-afiliado/index.html", pagina_aviso(referencia))
    escrever("canais/index.html", pagina_canais(referencia))
    escrever("404.html", pagina_404())
    escrever("sitemap.xml", gerar_sitemap(ofertas, referencia))
    escrever("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n")
    escrever("_headers", "/assets/*\n  Cache-Control: public, max-age=604800\n")
    escrever("_redirects",
             "/index.html / 301\n"
             "/offers.json / 301\n"
             "/app.js / 301\n"
             "/styles.css / 301\n")
    escrever(".nojekyll", "")

    paginas = len(list(SAIDA.rglob("*.html")))
    tamanho = sum(f.stat().st_size for f in SAIDA.rglob("*") if f.is_file())
    conferidas = sum(1 for o in ofertas if o["_conferida_24h"])
    print(f"build ok · {paginas} páginas · {len(ofertas)} ofertas · {conferidas} conferida(s) em 24 h · "
          f"{tamanho / 1024:.0f} KB · referência {data_hora(referencia)}")
    for o in ofertas:
        print(f"  {o['_url']:45} {o['_estado']['status']:16} {money(valor_vista(o['_preco'])) if o['_preco'] else 'sem preço'}")


if __name__ == "__main__":
    main()
