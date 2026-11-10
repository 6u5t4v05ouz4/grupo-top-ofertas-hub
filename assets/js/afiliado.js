/* Clique em link de afiliado: um evento por clique, sem bloquear a navegacao. */
(function () {
  "use strict";

  function origem() {
    try {
      var q = new URLSearchParams(location.search);
      var u = (q.get("utm_source") || "").toLowerCase();
      if (u) return u.slice(0, 24);
      if (!document.referrer) return "direto";
      return new URL(document.referrer).hostname.replace(/^www\./, "").slice(0, 24);
    } catch (e) {
      return "desconhecido";
    }
  }

  function enviar(d) {
    try {
      if (window.gtag) window.gtag("event", "affiliate_click", d);
      if (window.fbq) window.fbq("trackCustom", "AffiliateClick", { item_id: d.item_id });
      if (window.ttq) window.ttq.track("ClickButton", { content_id: d.item_id });
      // O clique e contado no 302 de /ir/<slug>/ (analytics da zona).
      // Aqui so disparam as ferramentas que tiverem ID configurado.
    } catch (e) {}
  }

  document.addEventListener("click", function (ev) {
    var alvo = ev.target;
    var a = alvo && alvo.closest ? alvo.closest("a[data-afiliado]") : null;
    if (!a) return;
    enviar({
      item_id: a.getAttribute("data-item") || "",
      oferta: a.getAttribute("data-oferta") || "",
      posicao: a.getAttribute("data-posicao") || "",
      pagina: location.pathname,
      canal: origem(),
      destino: a.getAttribute("data-afiliado") || ""
    });
  }, true);
})();
