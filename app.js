/* All data is temporary and exists only in this page. No payment or backend requests. */
(function (root) {
  'use strict';
  const routes = {
    'route-1': { route: '海智园 1 号线', from: '软件园', to: '海智园', direction: '地铁到园区', period: '早', time: '08:30', arrival: '09:05', price: 8 },
    'route-2': { route: '海智园 2 号线', from: '海智园', to: '软件园', direction: '园区到地铁', period: '晚', time: '09:10', arrival: '09:45', price: 8 }
  };
  function createState() {
    return {
      order: null, selectedCoupon: null, selectedDate: '2026-09-20', datePickerTarget: null, points: 1280, coupons: { three: 1, five: 1 },
      exchanged: {}, redeemed: false, ticketState: 'static',
      orderTab: 'pending', refundTarget: null, invoiceTarget: null, invoiceTitle: 'personal', payingId: null, orderSeq: 4,
      orders: [
        { id: 'o-1', route: '海智园 1 号线', from: '软件园', to: '海智园', direction: '地铁到园区', period: '早', time: '08:30', price: 8, status: 'completed', buyTime: '2026-09-20 08:16', payTime: '2026-09-20 08:18', transactionTime: '2026-09-20 08:18', original: 8, discount: 3, paid: 5, operator: '通勤用户', buyer: '李明', phone: '138****8216', project: '海智园通勤项目', coupon: '海智班车立减券（¥3）' },
        { id: 'o-2', route: '海智园 2 号线', from: '海智园', to: '软件园', direction: '园区到地铁', period: '晚', time: '09:10', price: 8, status: 'pending' },
        { id: 'o-3', route: '海智园 1 号线', from: '软件园', to: '海智园', direction: '地铁到园区', period: '早', time: '08:30', price: 8, status: 'paying' },
        { id: 'o-4', route: '海智园 2 号线', from: '海智园', to: '软件园', direction: '园区到地铁', period: '晚', time: '09:10', price: 8, status: 'invoiced', buyTime: '2026-09-20 08:42', payTime: '2026-09-20 08:43', transactionTime: '2026-09-20 08:43', original: 8, discount: 0, paid: 8, operator: '通勤用户', buyer: '王芳', phone: '139****4502', project: '海智园通勤项目', coupon: '未使用' }
      ]
    };
  }
  function selectDate(state, date) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return false;
    state.selectedDate = date;
    state.datePickerTarget = null;
    return true;
  }
  function book(state, id) {
    if (!routes[id]) return false;
    state.order = { ...routes[id], travelDate: state.selectedDate };
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
  function cancelPayment(state, id) {
    const order = state.orders.find(item => item.id === id && item.status === 'paying');
    if (!order) return false;
    order.status = 'cancelled';
    if (state.payingId === id) state.payingId = null;
    return true;
  }
  function ordersByStatus(state, status) { return state.orders.filter(order => order.status === status); }
  function ticketLedger(state, filters = {}) {
    const statusLabels = { completed: '已完成', refunded: '已退款', invoiced: '已完成' };
    return state.orders
      .filter(order => order.buyTime && statusLabels[order.status])
      .filter(order => !filters.status || order.status === filters.status)
      .filter(order => !filters.time || order.buyTime.startsWith(filters.time))
      .map(order => ({
        id: order.id,
        status: statusLabels[order.status],
        route: order.route, time: order.time, period: order.period, direction: order.direction,
        buyTime: order.buyTime, payTime: order.payTime, transactionTime: order.transactionTime,
        original: order.original, discount: order.discount, paid: order.paid,
        project: order.project, buyer: order.buyer, phone: order.phone,
        operator: order.operator, coupon: order.coupon
      }));
  }
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
  function requestInvoice(state, id) {
    const order = state.orders.find(item => item.id === id && item.status === 'completed');
    if (!order) return false;
    state.invoiceTarget = id;
    return true;
  }
  function confirmInvoice(state) {
    const order = state.orders.find(item => item.id === state.invoiceTarget && item.status === 'completed');
    if (!order) return false;
    order.status = 'invoiced';
    state.invoiceTarget = null;
    return true;
  }
  function exportTicketLedger(doc, rows) {
    const headers = ['路线', '班车时间', '方向', '购买时间', '支付时间', '交易时间', '原始金额', '优惠券抵扣金额', '实付金额', '所属项目', '购买人', '手机号', '操作人', '使用的优惠券'];    const body = rows.map(row => [row.route, row.time, row.direction, row.buyTime, row.payTime, row.transactionTime, '¥' + row.original.toFixed(2), '¥' + row.discount.toFixed(2), '¥' + row.paid.toFixed(2), row.project, row.buyer, row.phone, row.operator, row.coupon]);
    const table = '<table><thead><tr>' + headers.map(value => '<th>' + value + '</th>').join('') + '</tr></thead><tbody>' + body.map(row => '<tr>' + row.map(value => '<td>' + value + '</td>').join('') + '</tr>').join('') + '</tbody></table>';
    const anchor = doc.createElement && doc.createElement('a');
    if (!anchor) return false;
    anchor.href = 'data:application/vnd.ms-excel;charset=utf-8,' + encodeURIComponent('<meta charset="utf-8">' + table);
    anchor.download = '园区班车车票台账.xls';
    if (doc.body && doc.body.appendChild) doc.body.appendChild(anchor);
    if (anchor.click) anchor.click();
    if (doc.body && doc.body.removeChild) doc.body.removeChild(anchor);
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
  const api = { routes, createState, selectDate, book, chooseCoupon, total, pay, completePayment, cancelPayment, ordersByStatus,
    ticketLedger, requestRefund, confirmRefund, requestInvoice, confirmInvoice, previewExchange, exchange, redeem };
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
  function orderCard(order) {
    const meta = order.from && order.to ? order.from + ' → ' + order.to + ' · ' + order.time : order.time;
    let action = '';
    if (order.status === 'pending') action = '<button type="button" class="chip amber" data-action="pay-order" data-order-id="' + order.id + '">去支付</button>';
    else if (order.status === 'paying') action = '<button type="button" class="chip" data-action="view-paying-order" data-order-id="' + order.id + '">查看支付详情</button>';
    else if (order.status === 'invoiced') action = '<span class="chip">已开票</span>';
    else if (order.status === 'completed') action = '<button type="button" class="chip" data-action="request-invoice" data-order-id="' + order.id + '">发起开票</button><button type="button" class="chip" data-action="refund" data-order-id="' + order.id + '">申请退票</button>';
    else if (order.status === 'refunded') action = '<span class="chip">已退款</span>';
    else if (order.status === 'cancelled') action = '<span class="chip">已取消</span>';
    return '<div class="card order-card" data-order-id="' + order.id + '">' +
      '<div class="row"><div><b>' + order.route + '</b><div class="muted">' + meta + '</div></div>' + action + '</div>' +
      '<div class="row"><span class="muted">' + (order.travelDate || '2026-09-20').slice(5).replace('-', ' 月 ') + ' 日 · ¥' + (order.paid || order.price).toFixed(2) + '</span>' +
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
      const rows = ticketLedger(state, state.ledgerFilters || {});
      const ticketLedgerBody = $('[data-ticket-ledger]');
      if (ticketLedgerBody) ticketLedgerBody.innerHTML = rows.map(row => '<tr><td>' + row.route + '</td><td>' + row.time + '</td><td>' + row.direction + '</td><td>' + row.buyTime + '</td><td>' + row.payTime + '</td><td>' + row.transactionTime + '</td><td>¥' + row.original.toFixed(2) + '</td><td>¥' + row.discount.toFixed(2) + '</td><td>¥' + row.paid.toFixed(2) + '</td><td>' + row.project + '</td><td>' + row.buyer + '</td><td>' + row.phone + '</td><td>' + row.operator + '</td><td>' + row.coupon + '</td><td>' + row.status + '</td></tr>').join('');
      const ticketLedgerExport = $('[data-ticket-ledger-export]');
      if (ticketLedgerExport) ticketLedgerExport.textContent = JSON.stringify(rows);
      const couponCatalog = [
        { name: '海智班车立减券', type: '直减 ¥3', project: '海智园通勤项目', grantTime: '2026-09-20 10:00', status: '启用' },
        { name: '通勤满减券', type: '满 ¥10 减 ¥5', project: '海智园通勤项目', grantTime: '2026-10-01 09:00', status: '启用' }
      ];
      const couponFilters = state.couponFilters || { name: '', time: '' };
      const couponHits = couponCatalog
        .filter(item => !couponFilters.name || item.name.includes(couponFilters.name))
        .filter(item => !couponFilters.time || item.grantTime.startsWith(couponFilters.time));
      const couponResult = $('[data-coupon-filter-result]');
      if (couponResult) couponResult.innerHTML = couponHits.map(item => '<div class="card"><div class="row"><div><b>' + item.name + '</b><div class="muted">' + item.type + ' · ' + item.project + ' · 发放 ' + item.grantTime + '</div></div><span class="chip green">' + item.status + '</span></div></div>').join('');
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
    function formatDate(date) {
      const parts = date.split('-');
      return parts[1] + ' 月 ' + parts[2] + ' 日';
    }
    text('[data-selected-date]', formatDate(state.selectedDate));
    text('[data-order-date]', formatDate(order.travelDate || state.selectedDate));
    text('[data-order-date-label]', formatDate(order.travelDate || state.selectedDate));
    doc.querySelectorAll('[data-date]').forEach(button => {
      button.setAttribute('aria-pressed', String(button.dataset.date === state.selectedDate));
    });
    text('[data-order-price]', '¥' + order.price.toFixed(2));
    text('[data-order-subtotal]', '¥' + order.price.toFixed(2));
    text('[data-order-discount]', '-¥' + (state.selectedCoupon === 'three' ? 3 : state.selectedCoupon === 'five' ? 5 : 0).toFixed(2));
    text('[data-order-total]', '¥' + total({ ...state, order }).toFixed(2));
    text('[data-order-coupon]', state.selectedCoupon === 'three' ? '班车立减券 -¥3 ›' : state.selectedCoupon === 'five' ? '通勤满减券 -¥5 ›' : '不使用优惠券 ›');
    text('[data-pay-label]', '模拟支付 · ¥' + total({ ...state, order }).toFixed(2));
    const payingOrder = state.orders.find(item => item.id === state.payingId);
    text('[data-pay-amount]', '¥' + (payingOrder ? payingOrder.paid : total({ ...state, order })).toFixed(2));
    text('[data-paying-route]', payingOrder ? payingOrder.route : '');
    text('[data-paying-date]', payingOrder ? formatDate(payingOrder.travelDate || state.selectedDate) : '');
    text('[data-paying-time]', payingOrder ? payingOrder.time : '');
    text('[data-paying-order-id]', payingOrder ? payingOrder.id.toUpperCase() : '');
    text('[data-paying-amount]', payingOrder ? '¥' + (payingOrder.paid || payingOrder.price).toFixed(2) : '¥0.00');
    text('[data-paying-status]', payingOrder ? '支付中' : '');
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
    const invoiceOrder = state.orders.find(item => item.id === state.invoiceTarget);
    const invoiceAmount = invoiceOrder ? '¥' + (invoiceOrder.paid || invoiceOrder.price).toFixed(2) : '¥0.00';
    text('[data-invoice-route]', invoiceOrder ? invoiceOrder.route : '');
    text('[data-invoice-paid]', invoiceAmount);
    text('[data-invoice-amount]', invoiceAmount);
    ['personal', 'company'].forEach(id => {
      text('[data-invoice-title-' + id + ']', state.invoiceTitle === id ? '已选择' : '选择');
    });
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
    const button = event.target.closest('button[data-nav], button[data-action], button[data-ticket-tab], button[data-order-tab], button[data-date]');
    if (!button || button.disabled) return;
    if (button.dataset.nav) { show(button.dataset.nav); return; }
    if (button.dataset.date) { if (selectDate(state, button.dataset.date)) show('route-query'); return; }
    if (button.dataset.ticketTab) { state.ticketState = button.dataset.ticketTab; render(); return; }
    if (button.dataset.orderTab) { state.orderTab = button.dataset.orderTab; render(); return; }
    const action = button.dataset.action;
    if (action === 'open-date-picker') { state.datePickerTarget = state.selectedDate; show('date-picker'); }
    else if (action === 'select-date') { if (selectDate(state, button.dataset.date)) show('route-query'); }
    else if (action === 'book') { if (book(state, button.dataset.route)) show('order-confirmation'); }
    else if (action === 'pay') { if (pay(state)) show('payment-success'); }
    else if (action === 'payment-done') {
      if (completePayment(state)) { show('purchase-success'); status('模拟支付确认完成：订单已转为已完成（演示）。'); }
    }
    else if (action === 'view-paying-order') {
      const target = state.orders.find(item => item.id === button.dataset.orderId && item.status === 'paying');
      if (target) { state.payingId = target.id; show('paying-order-detail'); }
    }
    else if (action === 'cancel-payment') {
      if (cancelPayment(state, state.payingId)) { state.orderTab = 'cancelled'; show('order-center'); status('支付已取消（演示）。'); }
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
    else if (action === 'request-invoice') {
      if (requestInvoice(state, button.dataset.orderId)) { state.invoiceTitle = 'personal'; show('invoice-application'); }
    }
    else if (action === 'invoice-title') {
      if (['personal', 'company'].includes(button.dataset.title)) { state.invoiceTitle = button.dataset.title; render(); }
    }
    else if (action === 'invoice-submit') {
      if (confirmInvoice(state)) { show('order-center'); status('开票申请已提交（演示）：订单已转为已开票，刷新页面后恢复。'); }
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
    } else if (action === 'cancel-create') {
      show('coupon-list');
    } else if (action === 'view-coupons') {
      status('已加载当前园区优惠券（演示数据）；未连接真实后台。');
    } else if (action === 'add-coupon') {
      status('已打开新增优惠券表单（演示）；填写后点击确认发布即可模拟提交。');
    } else if (action === 'invoice-entry') {
      state.orderTab = 'completed';
      show('order-center');
    } else if (action === 'orders-entry') {
      show('order-center');
    } else if (action === 'filter-coupons') {
      state.couponFilters = {
        name: button.dataset.couponName || (($('[aria-label="搜索优惠券"]') || {}).value || ''),
        time: button.dataset.couponTime || (($('[aria-label="发放时间"]') || {}).value || '')
      };
      render();
    } else if (action === 'filter-ledger') {
      state.ledgerFilters = {
        status: button.dataset.ledgerStatus || (($('[aria-label="车票状态"]') || {}).value || ''),
        time: button.dataset.ledgerTime || (($('[aria-label="购票时间"]') || {}).value || '')
      };
      render();
    } else if (action === 'export-excel') {
      status(exportTicketLedger(doc, ticketLedger(state)) ? '车票台账已导出（演示 Excel 文件）。' : '当前环境不支持导出。');
    }
  });
  boards.forEach(board => { board.hidden = board !== current; });
  render();
})(typeof window !== 'undefined' ? window : globalThis);
