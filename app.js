(function () {
  'use strict';

  const list = document.getElementById('offers-list');
  const empty = document.getElementById('offers-empty');

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function renderOffer(o) {
    const tag = o.tag ? `<span class="offer-card__tag">${escapeHtml(o.tag)}</span>` : '';
    const meta = o.note ? `<p class="offer-card__meta">${escapeHtml(o.note)}</p>` : '';
    const card = document.createElement('article');
    card.className = 'offer-card';
    card.innerHTML = `
      ${tag}
      <h3 class="offer-card__title">${escapeHtml(o.title || 'Oferta')}</h3>
      ${o.description ? `<p class="offer-card__desc">${escapeHtml(o.description)}</p>` : ''}
      ${meta}
      <a class="offer-card__cta" href="${escapeHtml(o.url)}" target="_blank" rel="noopener noreferrer sponsored">
        ${escapeHtml(o.cta || 'Ver oferta no Mercado Livre')}
      </a>
    `;
    return card;
  }

  async function load() {
    try {
      const res = await fetch('offers.json', { cache: 'no-store' });
      if (!res.ok) throw new Error('fetch failed');
      const data = await res.json();
      const offers = Array.isArray(data.offers) ? data.offers : [];
      if (offers.length === 0) {
        empty.hidden = false;
        return;
      }
      offers.forEach((o) => list.appendChild(renderOffer(o)));
    } catch (e) {
      empty.hidden = false;
      empty.textContent = 'Não foi possível carregar as ofertas.';
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', load);
  } else {
    load();
  }
})();
