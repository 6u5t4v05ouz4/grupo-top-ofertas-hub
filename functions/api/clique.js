/* POST /api/clique — grava um clique em link de afiliado no Analytics Engine.
   Sempre responde 204: o clique nunca deve falhar por causa da medicao. */
const ITEM = /^ML[A-Z]\d{6,}$/;

const limpar = (valor, tamanho) =>
  String(valor ?? "").replace(/[^\w@.\-/: ]/g, "").slice(0, tamanho);

export async function onRequestPost({ request, env }) {
  const semConteudo = () =>
    new Response(null, { status: 204, headers: { "cache-control": "no-store" } });

  let dados;
  try {
    dados = await request.json();
  } catch {
    return semConteudo();
  }
  if (!dados || typeof dados !== "object") return semConteudo();

  const item = limpar(dados.item_id, 20).toUpperCase();
  if (!ITEM.test(item) || !env.CLIQUES) return semConteudo();

  env.CLIQUES.writeDataPoint({
    indexes: [item],
    blobs: [
      limpar(dados.oferta, 80),
      limpar(dados.posicao, 16),
      limpar(dados.pagina, 120),
      limpar(dados.canal, 32),
      limpar(dados.destino, 24),
    ],
    doubles: [1],
  });

  return semConteudo();
}

export async function onRequest() {
  return new Response("Method Not Allowed", {
    status: 405,
    headers: { allow: "POST", "cache-control": "no-store" },
  });
}
