/* All data is temporary and exists only in this page. No payment or backend requests. */
(function (root) {
  'use strict';
  const routes = {
    'route-1': { route: '海智园 1 号线', from: '园区南门', to: '软件园', time: '08:30', arrival: '09:05', price: 8 },
    'route-2': { route: '海智园 2 号线', from: '园区南门', to: '软件园', time: '09:10', arrival: '09:45', price: 8 }
  };
  function createState() {
    return {
      order: null, selectedCoupon: null, points: 1280, coupons: { three: 1, five: 1 },
      exchanged: {}, redeemed: false, ticketState: 'static',
      orderTab: 'pending', refundTarget: null, payingId: null, orderSeq: 4,
      orders: [
        { id: 'o-1', route: '海智园 1 号线', from: '园区南门', to: '软件园', time: '08:30', price: 8, status: 'completed' },
        { id: 'o-2', route: '海智园 2 号线', from: '园区南门', to: '软件园', time: '09:10', price: 8, status: 'pending' },
        { id: 'o-3', route: '海智园 1 号线', from: '园区南门', to: '软件园', time: '08:30', price: 8, status: 'paying' },
        { id: 'o-4', route: '海智园 2 号线', from: '园区南门', to: '软件园', time: '09:10', price: 8, status: 'invoiced' }
      ]
    };
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
    if (!state.coupons[id] || (id === 'five' && state.order.price < 10) || !['three', 'five'].includes(id)) return false;
    state.selectedCoupon = id;
    return true;
  }
  function total(state) {
    if (!state.order) return 0;
    return Math.max(0, state.order.price - (state.selectedCoupon === 'three' ? 3 : state.selectedCoupon === 'five' ? 5 : 0));
  }
  function pay(state) {
    if (!state.order) return false;
    const amount = total(state);
    let target = state.order.id ? state.orders.find(item => item.id === state.order.id && item.status === 'pending') : null;
    if (target) {
      target.status = 'paying';
      target.paid = amount;
    } else {
      target = { ...state.order, id: 'o-' + (++state.orderSeq), paid: amount, status: 'paying' };
      state.orders.push(target);
    }
    state.payingId = target.id;
    return true;
  }
  function completePayment(state) {
    const order = state.orders.find(item => item.id === state.payingId && item.status === 'paying');
    if (!order) return false;
    order.status = 'completed';
    state.payingId = null;
    return true;
  }
  function ordersByStatus(state, status) { return state.orders.filter(order => order.status === status); }
  function requestRefund(state, id) {
    const order = state.orders.find(item => item.id === id && item.status === 'completed');
    if (!order) return false;
    state.refundTarget = id;
    return true;
  }
  function confirmRefund(state) {
    const order = state.orders.find(item => item.id === state.refundTarget && item.status === 'completed');
    if (!order) return false;
    order.status = 'refunded';
    state.refundTarget = null;
    return true;
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
  const api = { routes, createState, book, chooseCoupon, total, pay, completePayment, ordersByStatus,
    requestRefund, confirmRefund, previewExchange, exchange, redeem };
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
  const ledgerSeed = '<tr><td>CPN 511 002</td><td>09-26 18:42</td><td>海智班车</td></tr>' +
    '<tr><td>CPN 511 018</td><td>09-27 08:05</td><td>海智班车</td></tr>';
  const ledgerNew = '<tr><td>CPN 826 193</td><td>09-27 08:24</td><td>海智班车</td></tr>';
  function orderCard(order) {
    const meta = order.from && order.to ? order.from + ' → ' + order.to + ' · ' + order.time : order.time;
    let action = '';
    if (order.status === 'pending') action = '<button type="button" class="chip amber" data-action="pay-order" data-order-id="' + order.id + '">去支付</button>';
    else if (order.status === 'paying') action = '<span class="chip">支付中</span>';
    else if (order.status === 'invoiced') action = '<span class="chip">已开票</span>';
    else if (order.status === 'completed') action = '<button type="button" class="chip" data-action="refund" data-order-id="' + order.id + '">申请退票</button>';
    else if (order.status === 'refunded') action = '<span class="chip">已退款</span>';
    return '<div class="card order-card" data-order-id="' + order.id + '">' +
      '<div class="row"><div><b>' + order.route + '</b><div class="muted">' + meta + '</div></div>' + action + '</div>' +
      '<div class="row"><span class="muted">09 月 20 日 · ¥' + (order.paid || order.price).toFixed(2) + '</span>' +
      '<span class="muted">订单号 ' + order.id.toUpperCase() + '</span></div></div>';
  }
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
      const ledger = $('[data-ledger]');
      if (ledger) ledger.innerHTML = state.redeemed ? ledgerSeed + ledgerNew : ledgerSeed;
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
    const payButton = $('[data-action="pay"]');
    if (payButton) payButton.disabled = !state.order;
    const couponButton = $('[data-action="select-coupon"]');
    if (couponButton) couponButton.disabled = !state.order;
    text('[data-order-route]', order.route);
    text('[data-order-stops]', order.from + ' → ' + order.to);
    text('[data-order-time]', order.time);
    text('[data-order-price]', '¥' + order.price.toFixed(2));
    text('[data-order-subtotal]', '¥' + order.price.toFixed(2));
    text('[data-order-discount]', '-¥' + (state.selectedCoupon === 'three' ? 3 : state.selectedCoupon === 'five' ? 5 : 0).toFixed(2));
    text('[data-order-total]', '¥' + total({ ...state, order }).toFixed(2));
    text('[data-order-coupon]', state.selectedCoupon === 'three' ? '班车立减券 -¥3 ›' : state.selectedCoupon === 'five' ? '通勤满减券 -¥5 ›' : '不使用优惠券 ›');
    text('[data-pay-label]', '模拟支付 · ¥' + total({ ...state, order }).toFixed(2));
    const payingOrder = state.orders.find(item => item.id === state.payingId);
    text('[data-pay-amount]', '¥' + (payingOrder ? payingOrder.paid : total({ ...state, order })).toFixed(2));
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
    const refundOrder = state.orders.find(item => item.id === state.refundTarget);
    const refundAmount = refundOrder ? '¥' + (refundOrder.paid || refundOrder.price).toFixed(2) : '¥0.00';
    text('[data-refund-route]', refundOrder ? refundOrder.route : '');
    text('[data-refund-amount]', refundAmount);
    text('[data-refund-paid]', refundAmount);
    const list = $('[data-order-list]');
    if (list) {
      const items = ordersByStatus(state, state.orderTab);
      list.innerHTML = items.length ? items.map(orderCard).join('') : '<div class="card"><p class="muted">暂无相关订单（演示数据）。</p></div>';
    }
    doc.querySelectorAll('[data-ticket-state]').forEach(section => { section.hidden = section.dataset.ticketState !== state.ticketState; });
    doc.querySelectorAll('[data-ticket-tab]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.ticketTab === state.ticketState)));
    doc.querySelectorAll('[data-order-tab]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.orderTab === state.orderTab)));
  }
  doc.addEventListener('click', event => {
    const button = event.target.closest('button[data-nav], button[data-action], button[data-ticket-tab], button[data-order-tab]');
    if (!button || button.disabled) return;
    if (button.dataset.nav) { show(button.dataset.nav); return; }
    if (button.dataset.ticketTab) { state.ticketState = button.dataset.ticketTab; render(); return; }
    if (button.dataset.orderTab) { state.orderTab = button.dataset.orderTab; render(); return; }
    const action = button.dataset.action;
    if (action === 'book') { if (book(state, button.dataset.route)) show('order-confirmation'); }
    else if (action === 'pay') { if (pay(state)) show('payment-success'); }
    else if (action === 'payment-done') {
      if (completePayment(state)) { show('purchase-success'); status('模拟支付确认完成：订单已转为已完成（演示）。'); }
    }
    else if (action === 'pay-order') {
      const target = state.orders.find(item => item.id === button.dataset.orderId && item.status === 'pending');
      if (target) {
        state.order = { route: target.route, from: target.from, to: target.to, time: target.time, price: target.price, id: target.id };
        state.selectedCoupon = state.coupons.three > 0 ? 'three' : null;
        show('order-confirmation');
      }
    }
    else if (action === 'refund') { if (requestRefund(state, button.dataset.orderId)) show('refund'); }
    else if (action === 'refund-confirm') {
      if (confirmRefund(state)) { show('order-center'); status('退票成功（演示）：订单已转为已退款，刷新页面后恢复。'); }
    }
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
    } else if (action === 'draft' || action === 'publish') {
      status((action === 'draft' ? '草稿已模拟保存' : '优惠券已模拟发布') + '；无真实后台写入，刷新页面后重置。');
    } else if (action === 'redeem') {
      const ok = redeem(state, 'haizhi');
      render();
      status(ok ? '优惠券模拟核销成功，已写入核销台账；乘车票状态不受影响。' : '此优惠券已核销，不可重复操作。');
    }
  });
  boards.forEach(board => { board.hidden = board !== current; });
  render();
})(typeof window !== 'undefined' ? window : globalThis);
