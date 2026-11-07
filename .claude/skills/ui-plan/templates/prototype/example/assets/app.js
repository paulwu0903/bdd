/* BLOCK SHOP clickable prototype (visual mockup only, no backend).
 * - Fake data lives in sessionStorage so it carries across pages.
 * - Every action updates that data directly and re-renders the page.
 * - `?state=` shows a specific screen, dialog or message for review.
 * Plain script, no build step; works when opened over file://. */
(() => {
  'use strict';

  const PAGE = document.body.dataset.page;
  const STATE = new URLSearchParams(location.search).get('state');
  const DB_KEY = 'blockshop.db.v2';

  /* ---- Pixel sprites (one char per pixel, '.' is transparent) ---- */
  const COLORS = {
    k: '#1E1E1E', w: '#E9DDC1', c: '#F7F1E3', s: '#CBBB93', p: '#D6C59D', d: '#8B5A2B', D: '#6B4420', n: '#DCCAA3', m: '#B9A57B',
    h: '#5A3A1E', g: '#5DA130', G: '#7CC04B', r: '#B5432F', e: '#8E2F22', o: '#A0662E', y: '#F2C230', x: '#C0392B',
  };
  const SPRITES = {
    shirt: [
      '................', '....kkk..kkk....', '..kkwwckkcwwkk..', '.kwwwwwdpwwwwwk.', 'kwwswwwppwwwswwk', 'kwwkwwwdpwwwkwwk', 'kkkkwwwppwwwkkkk', '...kwwwdpwwwk...',
      '...kswwppwwsk...', '...kwwwppwwwk...', '...kwwwdpwwwk...', '...kswwppwwsk...', '...kwwwppwwwk...', '...kwwwdpwwwk...', '...kkkkkkkkkk...', '................',
    ],
    tote: [
      '................', '.....kkkkkk.....', '....kh....hk....', '....kh....hk....', '..kkkhkkkkhkkk..', '..knnhnnnnhnnk..', '..knnnnnnnnnnk..', '..knnnggggnnnk..',
      '..knnnGGggnnnk..', '..knnnddddnnnk..', '..knnnddDdnnnk..', '..knnnnnnnnnnk..', '..kmnnnnnnnnmk..', '..kmmmmmmmmmmk..', '..kkkkkkkkkkkk..', '................',
    ],
    socks: [
      '................', '....kkkkkk......', '....kwwwwk......', '....kwwwwk......', '....krrrrk......', '....kwwwwk......', '....krrrrk......', '....krrrrk......',
      '....krrrrk......', '....krrrrkkkk...', '...kerrrrrrrrk..', '...keerrrrrrrrk.', '...keerrrrrrwwk.', '....kkkkkkkkkk..', '................', '................',
    ],
    grass: ['gGggggGg', 'ggGgGggg', 'gdgdggdg', 'dddddddd', 'ddDdddDd', 'dddddddd', 'dDddDddd', 'dddddddD'],
    chest: ['kkkkkkkk', 'kooooook', 'kooooook', 'kkkyykkk', 'koyyyyok', 'kooyyook', 'kooooook', 'kkkkkkkk'],
    broken: ['kkkkkkkk', 'kxxxxxxk', 'kxkxxkxk', 'kxxkkxxk', 'kxxkkxxk', 'kxkxxkxk', 'kxxxxxxk', 'kkkkkkkk'],
    coin: ['..kkkk..', '.kyyyyk.', 'kyyccyyk', 'kyycyyyk', 'kyyyyyyk', 'kyyyyysk', '.kyyssk.', '..kkkk..'],
  };
  const ICON_BY_PRODUCT = { p_linen_shirt: 'shirt', p_canvas_tote: 'tote', p_wool_socks: 'socks' };

  function sprite(name) {
    const rows = SPRITES[name] || SPRITES.broken;
    let rects = '';
    rows.forEach((row, y) => {
      for (let x = 0; x < row.length;) {
        let w = 1;
        while (row[x + w] === row[x]) w++;
        if (row[x] !== '.') rects += `<rect x="${x}" y="${y}" width="${w}" height="1" fill="${COLORS[row[x]]}"/>`;
        x += w;
      }
    });
    return `<svg class="px" viewBox="0 0 ${rows[0].length} ${rows.length}" shape-rendering="crispEdges" aria-hidden="true" focusable="false">${rects}</svg>`;
  }

  /* ---- Fake data ---- */
  const CATALOG = [
    { productId: 'p_linen_shirt', itemId: 'ci_8f21a0', name: '亞麻襯衫', price: 1280, stock: 5, qty: 1 },
    { productId: 'p_canvas_tote', itemId: 'ci_8f21a1', name: '帆布托特包', price: 890, stock: 3, qty: 1 },
    { productId: 'p_wool_socks', itemId: 'ci_8f21a2', name: '羊毛襪', price: 320, stock: 12, qty: 2 },
  ];
  const COUPONS = { SAVE100: { threshold: 1000, discount: 100 }, OLD2025: { expired: true } };
  const FREE_SHIPPING_AT = 1500, SHIPPING_FEE = 60;
  const SUBMIT_DELAY = 400; // brief "送出中…" state before leaving checkout

  const freshDb = (orders = {}) => ({
    products: Object.fromEntries(CATALOG.map(p => [p.productId, { name: p.name, price: p.price, stock: p.stock }])),
    items: CATALOG.map(p => ({ itemId: p.itemId, productId: p.productId, quantity: p.qty })),
    coupon: null, sold: [], repriced: false, orders,
  });
  function save(db) {
    try { sessionStorage.setItem(DB_KEY, JSON.stringify(db)); } catch (_) { /* storage blocked: page memory only */ }
  }
  function readDb() {
    try { return JSON.parse(sessionStorage.getItem(DB_KEY)) || freshDb(); } catch (_) { return freshDb(); }
  }

  // Derive the displayed cart (line subtotals, coupon, shipping, total).
  function priceCart(db) {
    const items = db.items.map(i => {
      const p = db.products[i.productId];
      return { itemId: i.itemId, productId: i.productId, name: p.name, unitPrice: p.price, quantity: i.quantity, subtotal: p.price * i.quantity };
    });
    const itemsTotal = items.reduce((s, i) => s + i.subtotal, 0);
    const ok = db.coupon && itemsTotal >= COUPONS[db.coupon].threshold;
    const discount = ok ? COUPONS[db.coupon].discount : 0;
    const coupon = db.coupon && { code: db.coupon, status: ok ? 'applied' : 'below_threshold', discount };
    const shippingFee = items.length && itemsTotal - discount < FREE_SHIPPING_AT ? SHIPPING_FEE : 0;
    return { items, coupon, itemsTotal, discount, shippingFee, total: itemsTotal - discount + shippingFee };
  }

  /* ---- Shared UI helpers ---- */
  const $ = (sel, root = document) => root.querySelector(sel);
  const money = n => `NT$${n.toLocaleString('en-US')}`;
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const iconFor = productId => ICON_BY_PRODUCT[productId] || 'chest';

  function announce(text) {
    const el = $('#announcer');
    el.textContent = '';
    setTimeout(() => { el.textContent = text; }, 40);
  }
  function toast(title, text, tone = 'info') {
    const el = document.createElement('div');
    el.className = `toast toast-${tone}`;
    const icon = tone === 'danger' ? 'broken' : tone === 'gold' ? 'coin' : 'grass';
    el.innerHTML = `<span class="slot slot-sm">${sprite(icon)}</span><div><p class="toast-title">${esc(title)}</p><p class="toast-text">${esc(text)}</p></div><button type="button" class="toast-x" aria-label="關閉訊息">×</button>`;
    el.querySelector('.toast-x').addEventListener('click', () => el.remove());
    $('#toasts').append(el);
    setTimeout(() => el.remove(), 9000);
  }
  function setCount(cart) {
    const n = cart.items.reduce((s, i) => s + i.quantity, 0);
    const badge = $('#cart-count');
    badge.textContent = n;
    badge.hidden = n === 0;
    $('.bag').setAttribute('aria-label', `購物車，共 ${n} 件`);
  }

  // Focus survives re-renders: elements carry data-focus keys.
  const focusKey = () => (document.activeElement && document.activeElement.dataset ? document.activeElement.dataset.focus || null : null);
  function paint(el, html, key) {
    el.innerHTML = html;
    if (!key) return;
    const swap = key.replace(/^(inc|dec):/, m => (m === 'inc:' ? 'dec:' : 'inc:'));
    let target = el.querySelector(`[data-focus="${key}"]`);
    if (!target || target.disabled) target = el.querySelector(`[data-focus="${swap}"]`);
    if (!target || target.disabled) target = el.querySelector('[data-focus-fallback]');
    if (!target) return;
    target.focus({ preventScroll: true });
    if (target.value && target.setSelectionRange) { try { target.setSelectionRange(target.value.length, target.value.length); } catch (_) { /* ignore */ } }
  }

  const loadingHTML = text => `<div class="panel state-panel" role="status" aria-busy="true">
    <div class="loader" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></div><p class="state-text">${esc(text)}</p></div>`;
  const errorHTML = msg => `<div class="panel state-panel">
    <span class="state-icon">${sprite('broken')}</span>
    <h2 class="state-title" tabindex="-1" data-focus-fallback>連線中斷</h2>
    <p class="state-text" role="alert">${esc(msg)}</p>
    <button type="button" class="btn btn-primary" data-action="retry" data-focus="retry">重試</button></div>`;

  function totalsHTML(c, editable) {
    const cp = c.coupon;
    let discount;
    if (!cp) {
      discount = `<dt>折扣</dt><dd class="num${c.discount ? ' discount' : ''}">${c.discount ? '−' : ''}${money(c.discount || 0)}</dd>`;
    } else {
      const applied = cp.status === 'applied';
      discount = `<dt>折扣<span class="tag tag-gold">${esc(cp.code)}</span>${editable
        ? `<button type="button" class="link-btn" data-action="coupon-remove" data-focus="coupon-remove" aria-label="移除優惠碼 ${esc(cp.code)}">移除</button>` : ''}</dt>
        <dd class="${applied ? 'num discount' : 'below'}">${applied ? `−${money(c.discount)}` : '未達門檻'}</dd>`;
    }
    const gap = FREE_SHIPPING_AT - (c.itemsTotal - c.discount);
    return `<dl class="sum">
      <div class="sum-row"><dt>商品小計</dt><dd class="num">${money(c.itemsTotal)}</dd></div>
      <div class="sum-row">${discount}</div>
      <div class="sum-row"><dt>運費</dt><dd class="num">${c.shippingFee ? money(c.shippingFee) : '免運'}</dd></div>
      <div class="sum-total"><dt>應付總額</dt><dd class="num-px">${money(c.total)}</dd></div>
    </dl>${editable && c.shippingFee && gap > 0 ? `<p class="sum-hint">再買 ${money(gap)} 即享免運</p>` : ''}`;
  }
  const miniHTML = (it, isSold) => `<li class="mini-item${isSold ? ' is-soldout' : ''}">
    <span class="slot slot-sm">${sprite(iconFor(it.productId))}</span>
    <span class="mini-name">${esc(it.name)}${isSold ? '<span class="tag tag-red">已售完</span>' : ''}<small class="num">${money(it.unitPrice)} × ${it.quantity}</small></span>
    <span class="mini-sub num">${money(it.subtotal)}</span></li>`;

  /* ---- Cart page ---- */
  function cartPage() {
    const view = $('#view');
    const db = readDb();
    if (STATE === 'empty') { db.items = []; db.coupon = null; } // shown only, not saved
    const rowMsg = {}; // itemId -> inline error under the row
    let couponDraft = '', couponError = '', flashId = null;

    function rowHTML(it) {
      const isSold = db.sold.includes(it.itemId);
      const [q, id, name] = [it.quantity, esc(it.itemId), esc(it.name)];
      return `<li class="item${isSold ? ' is-soldout' : ''}" data-item="${id}">
        <span class="slot slot-lg">${sprite(iconFor(it.productId))}</span>
        <div class="item-info">
          <h3 class="item-name">${name}${isSold ? '<span class="tag tag-red">已售完</span>' : ''}</h3>
          <p class="item-unit"><span class="sr-only">單價</span><span class="num${flashId === it.itemId ? ' flash' : ''}">${money(it.unitPrice)}</span></p>
        </div>
        <div class="qty" role="group" aria-label="${name} 數量">
          <button type="button" class="btn btn-sq" data-action="dec" data-id="${id}" data-focus="dec:${id}" aria-label="減少 ${name} 數量"${q <= 1 || isSold ? ' disabled' : ''}>−</button>
          <output class="qty-val num" aria-label="${name} 目前數量">${q}</output>
          <button type="button" class="btn btn-sq" data-action="inc" data-id="${id}" data-focus="inc:${id}" aria-label="增加 ${name} 數量"${q >= 99 || isSold ? ' disabled' : ''}>+</button>
        </div>
        <p class="item-sub"><span class="sr-only">小計</span><span class="num">${money(it.subtotal)}</span></p>
        <button type="button" class="btn btn-ghost btn-sm item-rm" data-action="remove" data-id="${id}" data-focus="remove:${id}" aria-label="移除 ${name}">移除</button>
        ${rowMsg[it.itemId] ? `<p class="item-msg" role="alert">${esc(rowMsg[it.itemId])}</p>` : ''}
      </li>`;
    }

    function cartHTML(cart) {
      const blocked = cart.items.some(i => db.sold.includes(i.itemId));
      const count = cart.items.reduce((s, i) => s + i.quantity, 0);
      return `<div class="layout">
        <div class="col-main">
          <section class="panel" aria-labelledby="list-title">
            <h2 class="panel-title" id="list-title" tabindex="-1" data-focus-fallback>背包物品 <span class="num">(${count})</span></h2>
            <ul class="items">${cart.items.map(rowHTML).join('')}</ul>
          </section>
          <form class="panel coupon" data-form="coupon" novalidate>
            <label class="panel-title" for="coupon-code">優惠碼</label>
            <div class="coupon-row">
              <input id="coupon-code" class="input" name="code" autocomplete="off" autocapitalize="characters" spellcheck="false" maxlength="40"
                placeholder="輸入優惠碼" value="${esc(couponDraft)}" data-focus="coupon-input"${couponError ? ' aria-invalid="true" aria-describedby="coupon-error"' : ''}>
              <button type="submit" class="btn" data-focus="coupon-apply">套用</button>
            </div>
            ${couponError ? `<p id="coupon-error" class="field-error" role="alert">${esc(couponError)}</p>` : ''}
          </form>
        </div>
        <div class="col-side">
          <section class="panel summary" aria-labelledby="sum-title">
            <h2 class="panel-title" id="sum-title">訂單摘要</h2>
            ${totalsHTML(cart, true)}
            <button type="button" class="btn btn-primary btn-block" data-action="checkout" data-focus="checkout"${blocked ? ' disabled aria-describedby="checkout-block"' : ''}>前往結帳</button>
            ${blocked ? '<p class="sum-block" id="checkout-block">請先移除已售完的物品</p>' : ''}
          </section>
        </div>
      </div>`;
    }

    const emptyHTML = () => `<div class="panel state-panel">
      <div class="empty-slots" aria-hidden="true">${'<span class="slot"></span>'.repeat(9)}</div>
      <h2 class="state-title" tabindex="-1" data-focus-fallback>購物車空空如也</h2>
      <p class="state-text">目前還沒有放進任何物品。</p>
      <button type="button" class="btn btn-primary" data-action="restock" data-focus="restock">放入推薦物品</button></div>`;

    function render(key = focusKey()) {
      const cart = priceCart(db);
      setCount(cart);
      paint(view, cart.items.length ? cartHTML(cart) : emptyHTML(), key);
      flashId = null;
    }

    function changeQty(id, delta) {
      const item = db.items.find(i => i.itemId === id);
      const q = item.quantity + delta;
      if (q < 1 || q > 99) return;
      const p = db.products[item.productId];
      delete rowMsg[id];
      if (q > p.stock) rowMsg[id] = p.stock ? `${p.name} 庫存不足，最多只能購買 ${p.stock} 件` : `${p.name} 已售完`;
      else { item.quantity = q; save(db); }
      render();
      if (!rowMsg[id]) announce(`${p.name} 數量已改為 ${q}`);
    }

    function removeItem(id, btn) {
      const item = db.items.find(i => i.itemId === id);
      const row = btn.closest('.item');
      if (!item || row.classList.contains('leaving')) return;
      row.classList.add('leaving');
      setTimeout(() => { // let the leave animation play
        db.items = db.items.filter(i => i.itemId !== id);
        db.sold = db.sold.filter(s => s !== id);
        save(db);
        render();
        announce(`已移除 ${db.products[item.productId].name}`);
      }, 300);
    }

    function applyCode() {
      const input = $('#coupon-code');
      if (input) couponDraft = input.value;
      const code = couponDraft.trim().toUpperCase();
      const rule = COUPONS[code];
      couponError = !code ? '請輸入優惠碼'
        : code.length > 32 ? '優惠碼最多 32 個字元'
        : !rule ? '查無此優惠碼，請確認後再試一次'
        : rule.expired ? '這組優惠碼已過期'
        : priceCart(db).itemsTotal < rule.threshold ? `商品小計滿 ${money(rule.threshold)} 才能使用這組優惠碼` : '';
      if (couponError) { render('coupon-input'); return; } // keep what the user typed
      db.coupon = code; // replaces any previous coupon only on success
      couponDraft = '';
      save(db);
      render();
      announce(`已套用優惠碼 ${code}`);
    }

    function dropCoupon() {
      const key = focusKey();
      db.coupon = null;
      save(db);
      render(key === 'coupon-remove' ? 'coupon-input' : key);
      announce('已移除優惠碼');
    }

    view.addEventListener('click', e => {
      const b = e.target.closest('[data-action]');
      if (!b || b.disabled) return;
      const id = b.dataset.id;
      const actions = {
        dec: () => changeQty(id, -1),
        inc: () => changeQty(id, 1),
        remove: () => removeItem(id, b),
        'coupon-remove': dropCoupon,
        checkout: () => { location.href = 'checkout.html'; },
        retry: () => render(),
        restock: () => { save(freshDb(db.orders)); location.href = 'index.html'; },
      };
      if (actions[b.dataset.action]) actions[b.dataset.action]();
    });
    view.addEventListener('submit', e => { e.preventDefault(); applyCode(); });
    view.addEventListener('input', e => { if (e.target.id === 'coupon-code') couponDraft = e.target.value; });

    if (STATE === 'loading') { view.innerHTML = loadingHTML('載入購物車中…'); return; }
    if (STATE === 'error') paint(view, errorHTML('連線不穩，暫時無法取得購物車，請稍後再試'), focusKey());
    else render();
    if (STATE === 'empty') return;

    // Demo: the tote sells out 2 s after opening `?state=soldout`.
    if (STATE === 'soldout') {
      setTimeout(() => {
        const item = db.items.find(i => i.productId === 'p_canvas_tote');
        db.products.p_canvas_tote.stock = 0;
        if (item && !db.sold.includes(item.itemId)) db.sold.push(item.itemId);
        save(db);
        if (!item) return;
        toast('物品已售完', `${db.products.p_canvas_tote.name} 已售完`, 'danger');
        render();
      }, 2000);
    }
    // Demo: the socks get cheaper 8 s after opening the cart (once per session).
    setTimeout(() => {
      const item = db.items.find(i => i.productId === 'p_wool_socks');
      if (db.repriced || !item) return;
      const p = db.products.p_wool_socks;
      const oldPrice = p.price;
      [p.price, db.repriced] = [290, true];
      save(db);
      toast('價格變動', `${p.name} 價格已從 ${money(oldPrice)} 調整為 ${money(p.price)}`, 'gold');
      flashId = item.itemId;
      if (!$('.state-panel')) render(); else flashId = null;
    }, 8000);
  }

  /* ---- Checkout page ---- */
  function checkoutPage() {
    const view = $('#view');
    const dlg = $('#price-dialog');
    const db = readDb();
    let submitting = false, notice = null, priceBumped = false, timedOut = false;

    setCount(priceCart(db));
    if (!db.items.length) { location.replace('index.html'); return; }

    const RULES = {
      name: [v => v.length > 0 && v.length <= 50, '請輸入收件人姓名'],
      phone: [v => /^09\d{8}$/.test(v), '請輸入 09 開頭的 10 碼手機號碼'],
      address: [v => v.length > 0 && v.length <= 200, '請輸入收件地址'],
    };
    const field = (id, label, control) => `<div class="field"><label for="f-${id}">${label}</label>${control}<p class="field-error" id="e-${id}" hidden></p></div>`;
    const layoutHTML = () => `<div class="layout">
      <div class="col-main">
        <form id="checkout-form" class="panel" novalidate aria-labelledby="form-title">
          <h2 class="panel-title" id="form-title" tabindex="-1" data-focus-fallback>收件資訊</h2>
          <div id="form-alert" class="alert alert-red" role="alert" tabindex="-1" hidden></div>
          ${field('name', '收件人姓名', '<input id="f-name" name="name" class="input" autocomplete="name" aria-describedby="e-name">')}
          ${field('phone', '手機號碼', '<input id="f-phone" name="phone" type="tel" class="input" inputmode="numeric" autocomplete="tel" placeholder="0912345678" aria-describedby="e-phone">')}
          ${field('address', '收件地址', '<textarea id="f-address" name="address" class="input" rows="3" autocomplete="street-address" aria-describedby="e-address"></textarea>')}
        </form>
      </div>
      <div class="col-side">
        <section class="panel" aria-labelledby="mini-title"><h2 class="panel-title" id="mini-title">物品清單</h2><ul class="mini" id="mini"></ul></section>
        <section class="panel summary" id="summary" aria-labelledby="sum-title"></section>
      </div></div>`;

    function renderAside() {
      const key = focusKey();
      const cart = priceCart(db);
      const soldItems = cart.items.filter(i => db.sold.includes(i.itemId));
      const blocked = soldItems.length > 0;
      $('#mini').innerHTML = cart.items.map(i => miniHTML(i, db.sold.includes(i.itemId))).join('');
      const note = blocked ? { tone: 'red', msg: `${soldItems.map(i => i.name).join('、')} 已售完，請回購物車調整`, back: true } : notice;
      paint($('#summary'), `<h2 class="panel-title" id="sum-title">金額明細</h2>${totalsHTML(cart, false)}
        ${note ? `<div class="alert alert-${note.tone}" role="alert"><p>${esc(note.msg)}</p>${note.back ? '<button type="button" class="btn btn-sm" data-action="back" data-focus="back">回購物車調整</button>' : ''}</div>` : ''}
        <button type="submit" form="checkout-form" class="btn btn-primary btn-block" data-focus="submit"${submitting || blocked ? ' disabled' : ''}>${submitting ? '送出中…' : '送出訂單'}</button>`, key);
    }
    const focusSubmit = () => { const b = $('[data-focus="submit"]'); if (b && !b.disabled) b.focus(); };
    const val = n => $(`#f-${n}`).value.trim();
    const showNotice = n => { notice = n; renderAside(); focusSubmit(); };

    function checkField(n) {
      const ok = RULES[n][0](val(n));
      const err = $(`#e-${n}`);
      if (ok) $(`#f-${n}`).removeAttribute('aria-invalid'); else $(`#f-${n}`).setAttribute('aria-invalid', 'true');
      [err.hidden, err.textContent] = [ok, ok ? '' : RULES[n][1]];
      return ok;
    }
    function validate() {
      const bad = Object.keys(RULES).filter(n => !checkField(n));
      if (bad.length) $(`#f-${bad[0]}`).focus();
      return !bad.length;
    }

    function submit() {
      if (submitting || db.items.some(i => db.sold.includes(i.itemId))) return;
      notice = null;
      if (!validate()) { renderAside(); return; }
      submitting = true;
      renderAside();
      const slow = STATE === 'timeout' && !timedOut; // first press hangs, then times out
      timedOut = true;
      setTimeout(() => { submitting = false; finish(slow); }, slow ? 5000 : SUBMIT_DELAY);
    }

    function finish(slow) {
      if (slow) return showNotice({ tone: 'gold', msg: '訂單可能已送出，請再按一次確認' });
      if (STATE === 'out-of-stock') {
        const it = db.items.find(i => i.productId === 'p_canvas_tote') || db.items[0];
        return showNotice({ tone: 'red', msg: `${db.products[it.productId].name} 庫存不足，請回購物車調整數量`, back: true });
      }
      if (STATE === 'price-changed' && !priceBumped) {
        priceBumped = true;
        const before = priceCart(db).total;
        const it = db.items.find(i => i.quantity === 1) || db.items[0];
        db.products[it.productId].price += Math.ceil(50 / it.quantity);
        save(db);
        renderAside();
        askPrice(before, priceCart(db).total);
        return;
      }
      // Place the order: snapshot the cart, take stock, empty the cart.
      const cart = priceCart(db);
      const d = new Date();
      const orderId = `BS${d.toLocaleDateString('sv').replace(/-/g, '')}${String(Math.floor(Math.random() * 1e4)).padStart(4, '0')}`;
      db.orders[orderId] = { orderId, items: cart.items, discount: cart.discount, shippingFee: cart.shippingFee, total: cart.total, createdAt: d.toISOString() };
      cart.items.forEach(i => { db.products[i.productId].stock -= i.quantity; });
      [db.items, db.coupon] = [[], null];
      save(db);
      location.href = `complete.html?orderId=${encodeURIComponent(orderId)}`;
    }

    function askPrice(before, after) {
      $('#pd-text').innerHTML = `物品價格有變動，應付總額已從 <s class="num">${money(before)}</s> 調整為 <strong class="num">${money(after)}</strong>。確認後將以新金額送出訂單。`;
      dlg.returnValue = '';
      dlg.showModal();
    }
    dlg.addEventListener('close', () => { if (dlg.returnValue === 'confirm') submit(); else focusSubmit(); });

    view.addEventListener('submit', e => { e.preventDefault(); submit(); });
    view.addEventListener('input', e => {
      const n = e.target.name;
      if (RULES[n] && e.target.getAttribute('aria-invalid') === 'true') checkField(n);
    });
    view.addEventListener('click', e => {
      const b = e.target.closest('[data-action]');
      if (b && !b.disabled && b.dataset.action === 'back') location.href = 'index.html';
    });

    paint(view, layoutHTML(), focusKey());
    renderAside();
  }

  /* ---- Complete page ---- */
  function completePage() {
    const view = $('#view');
    const db = readDb();
    const orderId = new URLSearchParams(location.search).get('orderId') || '';
    const order = STATE === 'not-found' ? null : db.orders[orderId];
    const time = iso => new Intl.DateTimeFormat('zh-TW', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Taipei' }).format(new Date(iso));

    const orderHTML = o => {
      const itemsTotal = o.items.reduce((s, i) => s + i.subtotal, 0);
      return `<div class="layout layout-narrow"><section class="panel receipt" aria-labelledby="done-title">
        <div class="achv"><span class="slot slot-sm">${sprite('grass')}</span>
          <div><p class="achv-kicker" aria-hidden="true">QUEST COMPLETE!</p><h2 class="achv-title" id="done-title" tabindex="-1" data-focus-fallback>訂單成立，感謝購買</h2></div></div>
        <dl class="meta">
          <div><dt>訂單編號</dt><dd class="num">${esc(o.orderId)}</dd></div>
          <div><dt>成立時間</dt><dd><time datetime="${esc(o.createdAt)}">${esc(time(o.createdAt))}</time></dd></div>
        </dl>
        <h3 class="sub-title">物品明細</h3>
        <ul class="mini">${o.items.map(i => miniHTML(i, false)).join('')}</ul>
        ${totalsHTML({ ...o, itemsTotal, coupon: null }, false)}
        <button type="button" class="btn btn-primary btn-block" data-action="continue">繼續購物</button>
      </section></div>`;
    };
    const notFoundHTML = msg => `<div class="panel state-panel">
      <span class="state-icon">${sprite('broken')}</span>
      <h2 class="state-title" tabindex="-1" data-focus-fallback>${esc(msg)}</h2>
      <p class="state-text">請確認訂單連結是否正確。</p>
      <button type="button" class="btn btn-primary" data-action="continue">回購物車</button></div>`;

    view.addEventListener('click', e => {
      const b = e.target.closest('[data-action]');
      if (b && b.dataset.action === 'continue') location.href = 'index.html';
    });
    setCount(priceCart(db));
    const key = focusKey();
    paint(view, order ? orderHTML(order) : notFoundHTML('找不到這筆訂單'), order ? key || 'none' : key);
  }

  /* ---- Boot ---- */
  document.querySelectorAll('[data-sprite]').forEach(el => { el.innerHTML = sprite(el.dataset.sprite); });
  addEventListener('pageshow', e => { if (e.persisted) location.reload(); }); // bfcache: re-read data
  const pages = { cart: cartPage, checkout: checkoutPage, complete: completePage };
  if (pages[PAGE]) pages[PAGE]();
})();
