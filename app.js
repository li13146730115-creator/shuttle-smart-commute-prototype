/* All data is temporary and exists only in this page. No payment or backend requests. */
(function (root) {
  'use strict';
  const routes = {
    'route-1': { route: '海智园 1 号线', from: '园区南门', to: '软件园', time: '08:30', arrival: '09:05', price: 8 },
    'route-2': { route: '海智园 2 号线', from: '园区南门', to: '软件园', time: '09:10', arrival: '09:45', price: 8 }
  };
  function createState() {
    return { order: null, selectedCoupon: null, points: 1280, coupons: { three: 1, five: 1 }, exchanged: {}, redeemed: false, ticketState: 'static' };
  }
  function book(state, id) {
    if (!routes[id]) return false;
    state.order = { ...routes[id] };
    state.selectedCoupon = state.coupons.three > 0 ? 'three' : null;
    return true;
  }
  function chooseCoupon(state, id) {
    if (!state.order) return false;
    if (id === null) { state.selectedCoupon = null; return true; }
    if (!state.order || !state.coupons[id] || (id === 'five' && state.order.price < 10) || !['three', 'five'].includes(id)) return false;
    state.selectedCoupon = id;
    return true;
  }
  function total(state) {
    if (!state.order) return 0;
    return Math.max(0, state.order.price - (state.selectedCoupon === 'three' ? 3 : state.selectedCoupon === 'five' ? 5 : 0));
  }
  const exchangeOptions = {
    three: { cost: 240, name: '海智班车立减券', value: '¥3' },
    five: { cost: 400, name: '通勤满减券', value: '¥5' }
  };
  function previewExchange(state, id) {
    const option = exchangeOptions[id];
    if (!option || state.exchanged[id] || state.points < option.cost) return null;
    return { ...option, before: state.points, after: state.points - option.cost };
  }
  function submit(state) { return !!state.order; }
  function exchange(state, id) {
    const preview = previewExchange(state, id);
    if (!preview) return false;
    state.points -= preview.cost;
    state.coupons[id] += 1;
    state.exchanged[id] = true;
    return true;
  }
  function redeem(state, merchant) {
    if (merchant !== 'haizhi' || state.redeemed) return false;
    state.redeemed = true;
    return true;
  }
  const api = { routes, createState, book, chooseCoupon, total, previewExchange, submit, exchange, redeem };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (!root.document) return;
  const doc = root.document;
  const state = createState();
  const mobile = !!doc.querySelector('[data-screen]');
  const selector = mobile ? '[data-screen]' : '[data-desktop-screen]';
  const boards = [...doc.querySelectorAll(selector)];
  let pendingExchangeId = null;
  let current = boards[0];
  const $ = (query, base = doc) => base.querySelector(query);
  function text(query, value, base = doc) { const element = $(query, base); if (element) element.textContent = String(value); }
  function status(message) { const area = $('#demo-status'); if (area) { area.textContent = message; area.hidden = false; } }
  function show(name) {
    const board = boards.find(item => item.getAttribute(mobile ? 'data-screen' : 'data-desktop-screen') === name);
    if (!board) return;
    current = board;
    boards.forEach(item => { item.hidden = item !== board; });
    doc.querySelectorAll('[data-nav]').forEach(button => button.setAttribute('aria-current', button.dataset.nav === name ? 'page' : 'false'));
    render();
  }
  function render() {
    if (!mobile) {
      text('[data-redeem-state]', state.redeemed ? '优惠券已核销，不能重复核销' : '优惠券有效，可由当前商家核销');
      text('[data-redeem-badge]', state.redeemed ? '已核销' : '待核销');
      text('[data-redeem-remaining]', (state.redeemed ? 372 : 373) + ' 张');
      const redeemButton = $('[data-action="redeem"]');
      if (redeemButton) redeemButton.disabled = state.redeemed;
      return;
    }
    const order = state.order || routes['route-1'];
    const preview = pendingExchangeId && previewExchange(state, pendingExchangeId);
    if (preview) {
      text('[data-exchange-value]', preview.value);
      text('[data-exchange-name]', preview.name);
      text('[data-exchange-cost]', preview.cost + ' 积分');
      text('[data-points-before]', preview.before.toLocaleString('zh-CN'));
      text('[data-points-after]', preview.after.toLocaleString('zh-CN'));
      text('[data-exchange-confirm]', '确认兑换 ' + preview.cost + ' 积分');
    }
    const confirm = $('[data-action="exchange-confirm"]');
    if (confirm) confirm.disabled = !preview;
    const submitButton = $('[data-action="submit"]');
    const couponButton = $('[data-action="select-coupon"]');
    if (submitButton) submitButton.disabled = !state.order;
    if (couponButton) couponButton.disabled = !state.order;
    text('[data-order-route]', order.route);
    text('[data-order-stops]', order.from + ' → ' + order.to);
    text('[data-order-time]', order.time);
    text('[data-order-price]', '¥' + order.price.toFixed(2));
    text('[data-order-subtotal]', '¥' + order.price.toFixed(2));
    text('[data-order-discount]', '-¥' + (state.selectedCoupon === 'three' ? 3 : state.selectedCoupon === 'five' ? 5 : 0).toFixed(2));
    text('[data-order-total]', '¥' + total({ ...state, order }).toFixed(2));
    text('[data-order-coupon]', state.selectedCoupon === 'three' ? '班车立减券 -¥3 ›' : state.selectedCoupon === 'five' ? '通勤满减券 -¥5 ›' : '不使用优惠券 ›');
    text('[data-submit-label]', '模拟提交订单 · ¥' + total({ ...state, order }).toFixed(2));
    text('[data-points]', state.points.toLocaleString('zh-CN'));
    text('[data-coupon-three-count]', state.coupons.three);
    text('[data-coupon-five-count]', state.coupons.five);
    const five = $('[data-action="coupon-five"]');
    if (five) five.disabled = order.price < 10 || state.coupons.five < 1;
    ['three', 'five'].forEach(id => {
      text('[data-selection-' + id + ']', state.selectedCoupon === id ? '已选择' : '选择');
      const exchangeButton = $('[data-action="exchange-' + id + '"]');
      if (exchangeButton) exchangeButton.disabled = !!state.exchanged[id];
    });
    doc.querySelectorAll('[data-ticket-state]').forEach(section => { section.hidden = section.dataset.ticketState !== state.ticketState; });
    doc.querySelectorAll('[data-ticket-tab]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.ticketTab === state.ticketState)));
  }
  doc.addEventListener('click', event => {
    const button = event.target.closest('button[data-nav], button[data-action], button[data-ticket-tab]');
    if (!button || button.disabled) return;
    if (button.dataset.nav) { show(button.dataset.nav); return; }
    if (button.dataset.ticketTab) { state.ticketState = button.dataset.ticketTab; render(); return; }
    const action = button.dataset.action;
    if (action === 'book') { book(state, button.dataset.route); show('order-confirmation'); }
    else if (action === 'select-coupon') { if (state.order) show('coupon-selection'); }
    else if (action === 'coupon-three' || action === 'coupon-five' || action === 'coupon-none') {
      const coupon = action === 'coupon-three' ? 'three' : action === 'coupon-five' ? 'five' : null;
      if (chooseCoupon(state, coupon)) { show('order-confirmation'); status('优惠券选择已更新（演示）。'); }
    } else if (action === 'exchange-preview') {
      pendingExchangeId = button.dataset.exchangeId || null;
      if (pendingExchangeId) show('exchange-confirmation');
    } else if (action === 'exchange-confirm') {
      if (pendingExchangeId && exchange(state, pendingExchangeId)) {
        pendingExchangeId = null;
        show('my-coupons');
        status('兑换成功（演示）：积分和优惠券数量已更新。');
      }
    } else if (action === 'submit') { if (state.order) status('模拟提交成功：无真实订单、支付或后端请求。'); }
    else if (action === 'draft' || action === 'publish' || action === 'save-rules') status(({ draft: '草稿已模拟保存', publish: '优惠券已模拟发布', 'save-rules': '配置已模拟保存' })[action] + '；刷新页面后重置。');
    else if (action === 'redeem') { const ok = redeem(state, 'haizhi'); render(); status(ok ? '优惠券模拟核销成功；乘车票状态不受影响。' : '此优惠券已核销，不可重复操作。'); }
  });
  boards.forEach(board => { board.hidden = board !== current; });
  render();
})(typeof window !== 'undefined' ? window : globalThis);
