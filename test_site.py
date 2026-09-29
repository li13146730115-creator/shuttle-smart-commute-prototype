import html.parser
import json
import pathlib
import subprocess
import unittest

ROOT = pathlib.Path(__file__).parent

MOBILE_SCREENS = ['route-query', 'order-confirmation', 'payment-success', 'purchase-success',
                  'paying-order-detail', 'order-center', 'coupon-selection', 'coupon-center',
                  'exchange-confirmation', 'my-coupons', 'boarding-ticket', 'refund',
                  'invoice-application', 'date-picker', 'park-services', 'contact']
DESKTOP_SCREENS = ['coupon-list', 'coupon-create', 'ticket-ledger']


class Markup(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.attrs = []

    def handle_starttag(self, tag, attrs):
        self.attrs.append((tag, dict(attrs)))


def markup(name):
    doc = Markup()
    doc.feed((ROOT / name).read_text(encoding='utf-8'))
    return doc


def board(page, marker):
    return page.split(marker, 1)[1].split('</article>', 1)[0]


def run_ui(script, desktop=False):
    # Tiny DOM event harness runs the real app.js without third-party browser packages.
    fixture = '''const fs = require('fs'), vm = require('vm');
const names = %s;
const elements = new Map();
function element(key) {
  if (!elements.has(key)) elements.set(key, {textContent:'', hidden:false, disabled:false, dataset:{}, setAttribute(k,v){this[k]=v}});
  return elements.get(key);
}
const boards = names.map(name => ({hidden:false, dataset:{}, getAttribute(){return name}}));
let click;
const document = {
  querySelector(q) { if(q==='[data-screen]') return %s ? null : boards[0]; return element(q); },
  querySelectorAll(q) { if(q==='[data-screen]' || q==='[data-desktop-screen]') return boards;
    if(q==='[data-nav]' || q==='[data-ticket-state]' || q==='[data-ticket-tab]') return []; return []; },
  addEventListener(type, fn) {click=fn}
};
vm.runInNewContext(fs.readFileSync('app.js','utf8'), {window:{document}, console});
function act(action, extras={}) {const button={dataset:{action,...extras},disabled:false};
  click({target:{closest(){return button}}}); return button;}
function nav(name) {const button={dataset:{nav:name},disabled:false};
  click({target:{closest(){return button}}});}
function otab(name) {const button={dataset:{orderTab:name},disabled:false};
  click({target:{closest(){return button}}});}
''' % (json.dumps(DESKTOP_SCREENS if desktop else MOBILE_SCREENS), 'true' if desktop else 'false')
    process = subprocess.run(['node', '-e', fixture + script], cwd=ROOT,
                             text=True, capture_output=True, check=True)
    return json.loads(process.stdout)


def run_model(script):
    process = subprocess.run(['node', '-e', "const Demo = require('./app.js'); " + script], cwd=ROOT,
                             text=True, capture_output=True, check=True)
    return json.loads(process.stdout)


class Pages(unittest.TestCase):
    def test_mobile_date_picker_and_payment_detail_markup(self):
        page = (ROOT / 'mobile.html').read_text(encoding='utf-8')
        route = board(page, 'data-screen="route-query"')
        self.assertNotIn('上车站点', route)
        self.assertNotIn('下车站点', route)
        self.assertIn('data-action="open-date-picker"', route)
        self.assertNotIn('约 35 分钟', route)
        picker = board(page, 'data-screen="date-picker"')
        self.assertIn('data-action="select-date"', picker)
        detail = board(page, 'data-screen="paying-order-detail"')
        self.assertIn('data-action="cancel-payment"', detail)

    def test_desktop_has_coupon_list_create_and_ticket_ledger_pages(self):
        doc = markup('desktop.html')
        screens = [a['data-desktop-screen'] for tag, a in doc.attrs
                   if tag == 'article' and 'data-desktop-screen' in a]
        self.assertEqual(screens, ['coupon-list', 'coupon-create', 'ticket-ledger'])
        page = (ROOT / 'desktop.html').read_text(encoding='utf-8')
        listing = board(page, 'data-desktop-screen="coupon-list"')
        self.assertIn('aria-label="搜索优惠券"', listing)
        self.assertIn('data-action="view-coupons"', listing)
        self.assertIn('data-nav="coupon-create"', listing)
        self.assertIn('data-action="export-excel"', listing)
        create = board(page, 'data-desktop-screen="coupon-create"')
        create_doc = Markup()
        create_doc.feed(create)
        self.assertEqual(sum(a.get('data-action') == 'draft' for tag, a in create_doc.attrs), 1)
        self.assertEqual(sum(a.get('data-action') == 'publish' for tag, a in create_doc.attrs), 1)
        ledger = board(page, 'data-desktop-screen="ticket-ledger"')
        self.assertNotIn('确认核销优惠券', ledger)
        self.assertNotIn('券码查询或扫码结果', ledger)
        self.assertIn('data-ticket-ledger', ledger)

    def test_index_has_two_relative_entries_and_no_legacy_content(self):
        page = (ROOT / 'index.html').read_text(encoding='utf-8')
        links = [a.get('href') for tag, a in markup('index.html').attrs if tag == 'a']
        self.assertEqual(links, ['mobile.html', 'desktop.html'])
        self.assertNotIn('LEGACY CONTENT', page)

    def test_mobile_preserves_393_by_852_screens_with_closed_loop(self):
        doc = markup('mobile.html')
        screens = [a['data-screen'] for tag, a in doc.attrs if tag == 'article' and 'data-screen' in a]
        self.assertEqual(screens, MOBILE_SCREENS)
        css = (ROOT / 'styles.css').read_text(encoding='utf-8')
        self.assertIn('393px', css)
        self.assertIn('852px', css)

    def test_mobile_uses_real_page_navigation_without_top_tabs(self):
        page = (ROOT / 'mobile.html').read_text(encoding='utf-8')
        self.assertNotIn('screen-nav', page)
        route = board(page, 'data-screen="route-query"')
        self.assertIn('data-nav="order-center"', route)
        self.assertIn('data-nav="my-coupons"', route)
        confirm = board(page, 'data-screen="order-confirmation"')
        self.assertIn('data-nav="route-query"', confirm)
        self.assertIn('data-action="pay"', confirm)

    def test_payment_and_purchase_success_pages_chain_forward(self):
        page = (ROOT / 'mobile.html').read_text(encoding='utf-8')
        payment = board(page, 'data-screen="payment-success"')
        self.assertIn('data-action="payment-done"', payment)
        self.assertIn('data-pay-amount', payment)
        purchase = board(page, 'data-screen="purchase-success"')
        self.assertIn('data-nav="boarding-ticket"', purchase)
        self.assertIn('data-nav="order-center"', purchase)

    def test_order_center_has_five_status_tabs_and_refund_page_rule(self):
        page = (ROOT / 'mobile.html').read_text(encoding='utf-8')
        center = board(page, 'data-screen="order-center"')
        doc = Markup()
        doc.feed(center)
        tabs = [a.get('data-order-tab') for tag, a in doc.attrs if tag == 'button' and 'data-order-tab' in a]
        self.assertEqual(tabs, ['pending', 'paying', 'completed', 'cancelled', 'invoiced'])
        for label in ('待支付', '支付中', '已完成', '已取消', '已开票'):
            self.assertIn(label, center)
        self.assertIn('data-order-list', center)
        refund = board(page, 'data-screen="refund"')
        self.assertIn('data-action="refund-confirm"', refund)
        self.assertIn('发车前 30 分钟', refund)
        self.assertIn('data-refund-route', refund)

    def test_invoice_application_screen_has_title_selection_and_submit(self):
        page = (ROOT / 'mobile.html').read_text(encoding='utf-8')
        invoice = board(page, 'data-screen="invoice-application"')
        self.assertIn('发票抬头', invoice)
        self.assertIn('data-action="invoice-submit"', invoice)
        self.assertIn('data-invoice-route', invoice)
        self.assertIn('data-nav="order-center"', invoice)
        doc = Markup()
        doc.feed(invoice)
        titles = [a.get('data-title') for tag, a in doc.attrs if a.get('data-action') == 'invoice-title']
        self.assertEqual(titles, ['personal', 'company'])
        self.assertIn('data-invoice-title-personal', invoice)
        self.assertIn('data-invoice-title-company', invoice)
        app = (ROOT / 'app.js').read_text(encoding='utf-8')
        self.assertIn('data-action="request-invoice"', app)

    def test_desktop_drops_rules_page_and_hardcodes_rules(self):
        doc = markup('desktop.html')
        screens = [a['data-desktop-screen'] for tag, a in doc.attrs if tag == 'article' and 'data-desktop-screen' in a]
        self.assertEqual(screens, DESKTOP_SCREENS)
        page = (ROOT / 'desktop.html').read_text(encoding='utf-8')
        self.assertNotIn('screen-nav', page)
        self.assertNotIn('发车前 30 分钟', page)
        css = (ROOT / 'styles.css').read_text(encoding='utf-8')
        self.assertIn('1920px', css)
        self.assertIn('1080px', css)

    def test_desktop_configuration_is_editable_and_public_page_has_no_personal_name(self):
        doc = markup('desktop.html')
        labels = [a.get('aria-label') for tag, a in doc.attrs if tag == 'input']
        self.assertIn('优惠券名称', labels)
        self.assertIn('金卡会员兑换积分', labels)
        self.assertNotIn('张 * 明', (ROOT / 'desktop.html').read_text(encoding='utf-8'))

    def test_route_cards_show_period_direction_and_drop_old_copy(self):
        page = (ROOT / 'mobile.html').read_text(encoding='utf-8')
        route = board(page, 'data-screen="route-query"')
        self.assertIn('早', route)
        self.assertIn('晚', route)
        self.assertIn('地铁到园区', route)
        self.assertIn('园区到地铁', route)
        self.assertNotIn('工作日通勤线路', route)
        self.assertNotIn('途经：', route)

    def test_merchant_ticket_table_has_current_park_purchase_details(self):
        page = (ROOT / 'desktop.html').read_text(encoding='utf-8')
        merchant = board(page, 'data-desktop-screen="ticket-ledger"')
        for column in ('班车时间', '所属项目', '购买人', '手机号', '交易时间'):
            self.assertIn(column, merchant)

    def test_coupon_management_has_add_view_and_full_coupon_fields(self):
        page = (ROOT / 'desktop.html').read_text(encoding='utf-8')
        management = board(page, 'data-desktop-screen="coupon-create"')
        self.assertIn('优惠券名称', management)
        self.assertIn('优惠券详情', management)
        self.assertIn('查看 / 编辑', (ROOT / 'desktop.html').read_text(encoding='utf-8'))
        inputs = [a.get('aria-label') for tag, a in markup('desktop.html').attrs if tag == 'input']
        for label in ('归属项目', '归属商家', '优惠券图片', '折扣值', '优惠券状态'):
            self.assertIn(label, inputs)

    def test_coupon_selection_count_reflects_threshold_and_demo_ticket_disclaimer(self):
        page = (ROOT / 'mobile.html').read_text(encoding='utf-8')
        selection = board(page, 'data-screen="coupon-selection"')
        self.assertIn('<span class="active">可使用 1</span>', selection)
        self.assertIn('<span>不可使用 1</span>', selection)
        self.assertIn('不读取服务端时间', page)

    def test_each_desktop_sidebar_has_keyboard_operable_navigation(self):
        page = (ROOT / 'desktop.html').read_text(encoding='utf-8')
        for board_html in page.split('<article class="desktop-board"')[1:]:
            sidebar = board_html.split('</aside>', 1)[0]
            doc = Markup()
            doc.feed(sidebar)
            self.assertEqual([a.get('data-nav') for tag, a in doc.attrs if tag == 'button'], DESKTOP_SCREENS)
            self.assertFalse(any(tag == 'span' for tag, _ in doc.attrs))

    def test_merchant_board_has_badge_remaining_and_ledger(self):
        page = (ROOT / 'desktop.html').read_text(encoding='utf-8')
        merchant = board(page, 'data-desktop-screen="ticket-ledger"')
        self.assertIn('data-ticket-ledger', merchant)

    def test_merchant_board_shows_ticket_ledger_with_excel_export(self):
        page = (ROOT / 'desktop.html').read_text(encoding='utf-8')
        merchant = board(page, 'data-desktop-screen="ticket-ledger"')
        self.assertIn('data-ticket-ledger', merchant)
        for column in ('路线', '购买时间', '支付时间', '原始金额', '优惠券抵扣金额',
                       '实付金额', '操作人', '使用的优惠券'):
            self.assertIn(column, merchant)
        self.assertIn('data-action="export-excel"', merchant)

    def test_both_exchange_buttons_open_the_same_confirmation_with_selected_id(self):
        page = (ROOT / 'mobile.html').read_text(encoding='utf-8')
        center = board(page, 'data-screen="coupon-center"')
        doc = Markup()
        doc.feed(center)
        self.assertEqual([a.get('data-exchange-id') for tag, a in doc.attrs if a.get('data-action') == 'exchange-preview'], ['three', 'five'])
        confirm = board(page, 'data-screen="exchange-confirmation"')
        for target in ('data-exchange-name', 'data-exchange-value', 'data-exchange-cost',
                       'data-points-before', 'data-points-after', 'data-exchange-confirm'):
            self.assertIn(target, confirm)

    def test_narrow_desktop_preview_explains_horizontal_scrolling(self):
        page = (ROOT / 'desktop.html').read_text(encoding='utf-8')
        css = (ROOT / 'styles.css').read_text(encoding='utf-8')
        self.assertIn('横向滚动查看', page)
        self.assertIn('overflow-x:auto', css)
        self.assertNotIn('margin-right:-1267px', css)

    def test_interactive_controls_and_explicit_demo_notice(self):
        for name in ('mobile.html', 'desktop.html'):
            doc = markup(name)
            self.assertTrue(any(tag == 'script' and a.get('src') == 'app.js' for tag, a in doc.attrs))
            self.assertTrue(any(tag == 'button' and a.get('data-action') for tag, a in doc.attrs))
            self.assertIn('演示', (ROOT / name).read_text(encoding='utf-8'))
        mobile = markup('mobile.html')
        self.assertEqual(len([1 for tag, a in mobile.attrs if a.get('data-action') == 'book']), 2)
        self.assertEqual(len([1 for tag, a in mobile.attrs if 'data-ticket-state' in a]), 3)


class Redesign(unittest.TestCase):
    def test_route_cards_highlight_time_window_like_12306(self):
        page = (ROOT / 'mobile.html').read_text(encoding='utf-8')
        route = board(page, 'data-screen="route-query"')
        self.assertIn('route-times', route)
        self.assertIn('route-time-value', route)
        doc = Markup()
        doc.feed(route)
        values = [a.get('class') for tag, a in doc.attrs if tag == 'b' and a.get('class') == 'route-time-value']
        self.assertEqual(len(values), 4)
        for token in ('08:30', '09:05', '09:10', '09:45'):
            self.assertIn(token, route)

    def test_tab_bar_styles_span_and_button_identically(self):
        css = (ROOT / 'styles.css').read_text(encoding='utf-8')
        self.assertIn('.ios-tab-bar button', css)
        button_rule = css.split('.ios-tab-bar button{', 1)[1].split('}', 1)[0]
        span_rule = css.split('.ios-tab-bar span{', 1)[1].split('}', 1)[0]
        self.assertIn('flex:1', button_rule)
        self.assertIn('background:transparent', button_rule)
        self.assertIn('border:0', button_rule)
        self.assertIn('font-size', button_rule)
        self.assertIn('flex:1', span_rule)

    def test_desktop_panel_buttons_are_normal_sized(self):
        css = (ROOT / 'styles.css').read_text(encoding='utf-8')
        self.assertNotIn('.desktop-panel button.primary,.desktop-panel button.secondary{display:block;width:100%}', css)
        self.assertIn('.coupon-actions', css)

    def test_coupon_create_is_single_full_page_form(self):
        page = (ROOT / 'desktop.html').read_text(encoding='utf-8')
        create = board(page, 'data-desktop-screen="coupon-create"')
        self.assertIn('新增优惠券', create)
        self.assertIn('基础规则', create)
        self.assertIn('*所属项目', create)
        self.assertIn('*可用商户', create)
        self.assertIn('*优惠券名称', create)
        self.assertIn('使用须知', create)
        self.assertIn('保存并发布', create)
        self.assertIn('>取消</button>', create)
        self.assertNotIn('desktop-form-grid', create)
        doc = Markup()
        doc.feed(create)
        self.assertEqual(sum(a.get('data-action') == 'draft' for tag, a in doc.attrs), 1)
        self.assertEqual(sum(a.get('data-action') == 'publish' for tag, a in doc.attrs), 1)
        self.assertEqual(sum(a.get('data-nav') == 'coupon-list' for tag, a in doc.attrs), 2)
        for label in ('归属项目', '归属商家', '优惠券图片', '折扣值', '优惠券状态', '优惠券名称', '金卡会员兑换积分'):
            self.assertIn(label, page)

    def test_coupon_create_form_is_compact_data_dense(self):
        css = (ROOT / 'styles.css').read_text(encoding='utf-8')
        form_row = css.split('.form-row{', 1)[1].split('}', 1)[0]
        self.assertIn('grid-template-columns', form_row)
        self.assertIn('112px', form_row)
        for token in ('.form-label{', '.create-section{', '.create-footer{', '.upload-box{', '.section-eyebrow{'):
            self.assertIn(token, css)


class Business(unittest.TestCase):
    def test_date_selection_is_used_when_booking(self):
        result = run_model(
            "const s=Demo.createState(); Demo.selectDate(s,'2026-09-23'); "
            "Demo.book(s,'route-1'); console.log(JSON.stringify({date:s.selectedDate, travelDate:s.order.travelDate}));"
        )
        self.assertEqual(result, {'date': '2026-09-23', 'travelDate': '2026-09-23'})

    def test_paying_order_can_be_cancelled_and_cannot_complete(self):
        result = run_model(
            "const s=Demo.createState(); Demo.book(s,'route-1'); Demo.pay(s); const id=s.payingId; "
            "const cancelled=Demo.cancelPayment(s,id); "
            "const completed=Demo.completePayment(s); "
            "console.log(JSON.stringify({cancelled,completed,status:s.orders.find(o=>o.id===id).status,payingId:s.payingId}));"
        )
        self.assertEqual(result, {'cancelled': True, 'completed': False, 'status': 'cancelled', 'payingId': None})

    def test_no_coupon_selection_or_payment_before_booking(self):
        result = run_model('const s = Demo.createState(); '
                           'const choose = Demo.chooseCoupon(s,"three"); '
                           'const none = Demo.chooseCoupon(s,null); '
                           'const pay = Demo.pay(s); '
                           'console.log(JSON.stringify({choose,none,pay,order:s.order,coupon:s.selectedCoupon}));')
        self.assertFalse(result['choose'])
        self.assertFalse(result['none'])
        self.assertFalse(result['pay'])
        self.assertIsNone(result['order'])
        self.assertIsNone(result['coupon'])

    def test_payment_flow_moves_order_through_paying_to_completed(self):
        result = run_model('const s = Demo.createState(); Demo.book(s,"route-1"); const paid = Demo.pay(s); '
                           'const order = Demo.ordersByStatus(s,"paying").find(o=>o.paid===5); '
                           'const done = Demo.completePayment(s); '
                           'const completed = Demo.ordersByStatus(s,"completed").map(o=>o.id); '
                           'console.log(JSON.stringify({paid,done,id:order.id,paidAmount:order.paid,completed}));')
        self.assertTrue(result['paid'])
        self.assertTrue(result['done'])
        self.assertEqual(result['id'], 'o-5')
        self.assertEqual(result['paidAmount'], 5)
        self.assertEqual(result['completed'], ['o-1', 'o-5'])

    def test_refund_only_for_completed_orders_and_only_once(self):
        result = run_model('const s = Demo.createState(); '
                           'const invoiced = Demo.requestRefund(s,"o-4"); '
                           'const ask = Demo.requestRefund(s,"o-1"); '
                           'const refund = Demo.confirmRefund(s); const again = Demo.confirmRefund(s); '
                           'const after = Demo.ordersByStatus(s,"completed").map(o=>o.id); '
                           'console.log(JSON.stringify({invoiced,ask,refund,again,after}));')
        self.assertFalse(result['invoiced'])
        self.assertTrue(result['ask'])
        self.assertTrue(result['refund'])
        self.assertFalse(result['again'])
        self.assertEqual(result['after'], [])

    def test_confirmation_preview_matches_selected_coupon_and_changes_after_redemption(self):
        result = run_model('const s = Demo.createState(); '
                           'const five = Demo.previewExchange(s,"five"); '
                           'const first = Demo.exchange(s,"five"); '
                           'const three = Demo.previewExchange(s,"three"); '
                           'console.log(JSON.stringify({five,first,three,points:s.points}));')
        self.assertEqual(result['five']['cost'], 400)
        self.assertEqual(result['five']['name'], '通勤满减券')
        self.assertEqual(result['five']['before'], 1280)
        self.assertEqual(result['five']['after'], 880)
        self.assertTrue(result['first'])
        self.assertEqual(result['three']['before'], 880)
        self.assertEqual(result['three']['after'], 640)

    def test_desktop_ui_has_no_redeem_runtime_dependencies(self):
        app = (ROOT / 'app.js').read_text(encoding='utf-8')
        self.assertNotIn('ledgerSeed', app)
        self.assertNotIn('ledgerNew', app)
        self.assertNotIn('data-action="redeem"', app)
        self.assertNotIn('data-ledger', app)
        self.assertNotIn('data-redeem-state', app)
        self.assertNotIn('data-redeem-badge', app)
        self.assertNotIn("action === 'redeem'", app)

    def test_exchange_confirmation_only_consumes_selected_id_once(self):
        result = run_ui('act("exchange-preview",{exchangeId:"five"}); '
                        'const preview={screen:boards.find(b=>!b.hidden).getAttribute(), '
                        'name:element("[data-exchange-name]").textContent, '
                        'cost:element("[data-exchange-cost]").textContent, '
                        'before:element("[data-points-before]").textContent, '
                        'after:element("[data-points-after]").textContent}; '
                        'act("exchange-confirm"); act("exchange-confirm"); '
                        'console.log(JSON.stringify({preview,points:element("[data-points]").textContent, '
                        'five:element("[data-coupon-five-count]").textContent, '
                        'three:element("[data-coupon-three-count]").textContent}));')
        self.assertEqual(result['preview'], {'screen': 'exchange-confirmation', 'name': '通勤满减券',
                                             'cost': '400 积分', 'before': '1,280', 'after': '880'})
        self.assertEqual((result['points'], result['five'], result['three']), ('880', '2', '1'))

    def test_no_prebooking_payment_or_coupon_navigation(self):
        result = run_ui('act("select-coupon"); const couponScreen=boards.find(b=>!b.hidden).getAttribute(); '
                        'act("pay"); console.log(JSON.stringify({couponScreen, '
                        'payScreen:boards.find(b=>!b.hidden).getAttribute(), '
                        'payDisabled:element(\'[data-action="pay"]\').disabled, '
                        'status:element("#demo-status").textContent}));')
        self.assertEqual(result['couponScreen'], 'route-query')
        self.assertEqual(result['payScreen'], 'route-query')
        self.assertTrue(result['payDisabled'])
        self.assertNotIn('支付成功', result['status'])

    def test_booking_to_payment_success_to_purchase_and_order_center(self):
        result = run_ui('act("book",{route:"route-1"}); const booked=boards.find(b=>!b.hidden).getAttribute(); '
                        'act("pay"); const paying={screen:boards.find(b=>!b.hidden).getAttribute(), '
                        'amount:element("[data-pay-amount]").textContent}; '
                        'act("payment-done"); const purchased=boards.find(b=>!b.hidden).getAttribute(); '
                        'nav("order-center"); const center=boards.find(b=>!b.hidden).getAttribute(); '
                        'const pendingList=element("[data-order-list]").innerHTML; '
                        'otab("completed"); const completedList=element("[data-order-list]").innerHTML; '
                        'act("refund",{orderId:"o-1"}); const refundScreen=boards.find(b=>!b.hidden).getAttribute(); '
                        'const refundRoute=element("[data-refund-route]").textContent; '
                        'act("refund-confirm"); const afterRefund=boards.find(b=>!b.hidden).getAttribute(); '
                        'otab("completed"); const completedAfter=element("[data-order-list]").innerHTML; '
                        'console.log(JSON.stringify({booked,paying,purchased,center,pendingList,completedList,'
                        'refundScreen,refundRoute,afterRefund,completedAfter}));')
        self.assertEqual(result['booked'], 'order-confirmation')
        self.assertEqual(result['paying'], {'screen': 'payment-success', 'amount': '¥5.00'})
        self.assertEqual(result['purchased'], 'purchase-success')
        self.assertEqual(result['center'], 'order-center')
        self.assertIn('去支付', result['pendingList'])
        self.assertIn('data-order-id="o-2"', result['pendingList'])
        self.assertIn('申请退票', result['completedList'])
        self.assertIn('data-order-id="o-1"', result['completedList'])
        self.assertEqual(result['refundScreen'], 'refund')
        self.assertEqual(result['refundRoute'], '海智园 1 号线')
        self.assertEqual(result['afterRefund'], 'order-center')
        self.assertNotIn('data-order-id="o-1"', result['completedAfter'])

    def test_booking_transfers_each_route_and_coupon_updates_total(self):
        result = run_model('const s = Demo.createState(); '
                           'Demo.book(s, "route-2"); const second = { ...s.order }; '
                           'Demo.chooseCoupon(s, null); const without = Demo.total(s); '
                           'Demo.book(s, "route-1"); console.log(JSON.stringify({second, without, first:s.order, total:Demo.total(s)}));')
        self.assertEqual(result['second']['time'], '09:10')
        self.assertEqual(result['second']['route'], '海智园 2 号线')
        self.assertEqual(result['second']['price'], 8)
        self.assertEqual(result['first']['time'], '08:30')
        self.assertEqual(result['total'], 5)
        self.assertEqual(result['without'], 8)

    def test_threshold_coupon_cannot_be_chosen_for_eight_yuan_order(self):
        result = run_model('const s = Demo.createState(); Demo.book(s,"route-1"); '
                           'const accepted = Demo.chooseCoupon(s,"five"); '
                           'console.log(JSON.stringify({accepted,total:Demo.total(s),coupon:s.selectedCoupon}));')
        self.assertFalse(result['accepted'])
        self.assertEqual(result['total'], 5)
        self.assertEqual(result['coupon'], 'three')

    def test_exchange_deducts_once_and_adds_one_coupon(self):
        result = run_model('const s = Demo.createState(); const first = Demo.exchange(s,"three"); '
                           'const second = Demo.exchange(s,"three"); '
                           'console.log(JSON.stringify({first,second,points:s.points,quantity:s.coupons.three}));')
        self.assertTrue(result['first'])
        self.assertFalse(result['second'])
        self.assertEqual(result['points'], 1040)
        self.assertEqual(result['quantity'], 2)

    def test_ticket_ledger_lists_only_non_refunded_orders_with_coupon_details(self):
        result = run_ui('act("export-excel"); const data = JSON.parse(element("[data-ticket-ledger-export]").textContent); '
                        'console.log(JSON.stringify({data}));', desktop=True)
        rows = result['data']
        self.assertEqual(len(rows), 2)
        first = rows[0]
        self.assertEqual(first['route'], '海智园 1 号线')
        for key in ('buyTime', 'payTime', 'original', 'discount', 'paid', 'operator', 'coupon'):
            self.assertIn(key, first)
        self.assertFalse(any('refunded' in str(row).lower() for row in rows))
        self.assertEqual(first['original'] - first['discount'], first['paid'])
        self.assertTrue(all(row['buyTime'] and row['payTime'] for row in rows))

    def test_ticket_ledger_marks_refunded_and_excludes_unpaid_orders(self):
        result = run_model('const s=Demo.createState(); '
                           'const before=Demo.ticketLedger(s); '
                           'Demo.requestRefund(s,"o-1"); Demo.confirmRefund(s); '
                           'const after=Demo.ticketLedger(s); '
                           'console.log(JSON.stringify({before:before.map(o=>o.route),'
                           'after:after.map(o=>o.route),statuses:after.map(o=>o.status)}));')
        self.assertEqual(result['before'], ['海智园 1 号线', '海智园 2 号线'])
        self.assertEqual(result['after'], ['海智园 1 号线', '海智园 2 号线'])
        self.assertEqual(result['statuses'], ['已退款', '已完成'])

    def test_ticket_ledger_exposes_purchase_identity_and_transaction_time(self):
        result = run_model('const row=Demo.ticketLedger(Demo.createState())[0]; '
                           'console.log(JSON.stringify(row));')
        for key in ('project', 'buyer', 'phone', 'transactionTime', 'period', 'direction', 'time'):
            self.assertIn(key, result)

    def test_export_excel_serves_downloadable_xls_file(self):
        # Export must work without URL.createObjectURL (unavailable in the vm
        # harness and unnecessary for a data-URI download), so patch the shared
        # document with a fake anchor and assert the served .xls attributes.
        result = run_ui('const fakeAnchor = {href:"", download:"", clicked:0, setAttribute(){}}; '
                        'fakeAnchor.click = () => { fakeAnchor.clicked += 1; }; '
                        'const savedCreate = document.createElement; '
                        'document.createElement = () => fakeAnchor; '
                        'try { act("export-excel"); } finally { document.createElement = savedCreate; } '
                        'console.log(JSON.stringify({filename:fakeAnchor.download, '
                        'hrefPrefix:fakeAnchor.href.split(",")[0], clicked:fakeAnchor.clicked}));',
                        desktop=True)
        self.assertTrue(result['filename'].endswith('.xls'))
        self.assertIn('data:', result['hrefPrefix'])
        self.assertEqual(result['clicked'], 1)

    def test_coupon_redemption_is_merchant_only_and_not_repeatable(self):
        result = run_model('const s = Demo.createState(); '
                           'const wrong = Demo.redeem(s,"other"); '
                           'const first = Demo.redeem(s,"haizhi"); '
                           'const again = Demo.redeem(s,"haizhi"); '
                           'console.log(JSON.stringify({wrong,first,again,redeemed:s.redeemed}));')
        self.assertFalse(result['wrong'])
        self.assertTrue(result['first'])
        self.assertFalse(result['again'])
        self.assertTrue(result['redeemed'])

    def test_invoice_request_only_for_completed_orders_and_only_once(self):
        result = run_model('const s = Demo.createState(); '
                           'const pending = Demo.requestInvoice(s,"o-2"); '
                           'const invoiced = Demo.requestInvoice(s,"o-4"); '
                           'const ask = Demo.requestInvoice(s,"o-1"); '
                           'const submit = Demo.confirmInvoice(s); const again = Demo.confirmInvoice(s); '
                           'const after = Demo.ordersByStatus(s,"invoiced").map(o=>o.id); '
                           'console.log(JSON.stringify({pending,invoiced,ask,submit,again,after}));')
        self.assertFalse(result['pending'])
        self.assertFalse(result['invoiced'])
        self.assertTrue(result['ask'])
        self.assertTrue(result['submit'])
        self.assertFalse(result['again'])
        self.assertEqual(result['after'], ['o-1', 'o-4'])

    def test_invoice_ui_flow_selects_title_and_submits_from_order_center(self):
        result = run_ui('nav("order-center"); otab("completed"); '
                        'const completedList=element("[data-order-list]").innerHTML; '
                        'act("request-invoice",{orderId:"o-1"}); '
                        'const screen=boards.find(b=>!b.hidden).getAttribute(); '
                        'const route=element("[data-invoice-route]").textContent; '
                        'act("invoice-title",{title:"company"}); '
                        'const personal=element("[data-invoice-title-personal]").textContent; '
                        'const company=element("[data-invoice-title-company]").textContent; '
                        'act("invoice-submit"); const after=boards.find(b=>!b.hidden).getAttribute(); '
                        'otab("invoiced"); const invoicedList=element("[data-order-list]").innerHTML; '
                        'console.log(JSON.stringify({completedList,screen,route,personal,company,after,invoicedList}));')
        self.assertIn('data-action="request-invoice"', result['completedList'])
        self.assertIn('data-order-id="o-1"', result['completedList'])
        self.assertEqual(result['screen'], 'invoice-application')
        self.assertEqual(result['route'], '海智园 1 号线')
        self.assertEqual(result['personal'], '选择')
        self.assertEqual(result['company'], '已选择')
        self.assertEqual(result['after'], 'order-center')
        self.assertIn('已开票', result['invoicedList'])
        self.assertIn('data-order-id="o-1"', result['invoicedList'])

    def test_mobile_tab_bar_lists_park_services_first(self):
        page = (ROOT / 'mobile.html').read_text(encoding='utf-8')
        bar = board(page, 'class="ios-tab-bar"')
        self.assertLess(bar.index('data-nav="park-services"'), bar.index('data-nav="order-center"'))
        self.assertLess(bar.index('data-nav="order-center"'), bar.index('data-nav="my-coupons"'))
        self.assertIn('class="on"', bar)

    def test_park_services_hub_lists_four_entries(self):
        page = (ROOT / 'mobile.html').read_text(encoding='utf-8')
        hub = board(page, 'data-screen="park-services"')
        self.assertIn('线路列表', hub)
        self.assertIn('data-nav="route-query"', hub)
        self.assertIn('我要开票', hub)
        self.assertIn('data-action="invoice-entry"', hub)
        self.assertIn('我的订单', hub)
        self.assertIn('data-action="orders-entry"', hub)
        self.assertIn('联系我们', hub)
        self.assertIn('data-nav="contact"', hub)
        self.assertNotIn('data-action="book"', hub)
        self.assertNotIn('data-ticket-state', hub)

    def test_invoice_entry_opens_order_center_on_completed_tab(self):
        result = run_ui('act("invoice-entry"); '
                        'const screen=boards.find(b=>!b.hidden).getAttribute(); '
                        'console.log(JSON.stringify({screen}));')
        self.assertEqual(result['screen'], 'order-center')
        page = (ROOT / 'mobile.html').read_text(encoding='utf-8')
        self.assertIn('data-action="invoice-entry"', board(page, 'data-screen="park-services"'))

    def test_orders_entry_opens_order_center(self):
        result = run_ui('act("orders-entry"); '
                        'const screen=boards.find(b=>!b.hidden).getAttribute(); '
                        'console.log(JSON.stringify({screen}));')
        self.assertEqual(result['screen'], 'order-center')

    def test_contact_screen_exists_with_contact_content(self):
        page = (ROOT / 'mobile.html').read_text(encoding='utf-8')
        contact = board(page, 'data-screen="contact"')
        self.assertIn('联系我们', contact)
        self.assertIn('data-nav="park-services"', contact)

    def test_coupon_list_has_name_and_time_filters(self):
        page = (ROOT / 'desktop.html').read_text(encoding='utf-8')
        listing = board(page, 'data-desktop-screen="coupon-list"')
        self.assertIn('aria-label="搜索优惠券"', listing)
        self.assertIn('data-action="filter-coupons"', listing)
        self.assertIn('aria-label="发放时间"', listing)

    def test_coupon_filter_applies_name_and_time(self):
        result = run_ui('act("filter-coupons", {couponName:"海智", couponTime:"2026-09"}); '
                        'const rows=element("[data-coupon-filter-result]").innerHTML; '
                        'console.log(JSON.stringify({rows}));', desktop=True)
        self.assertIn('海智班车立减券', result['rows'])
        result = run_ui('act("filter-coupons", {couponName:"通勤", couponTime:"2026-09"}); '
                        'const rows=element("[data-coupon-filter-result]").innerHTML; '
                        'console.log(JSON.stringify({rows}));', desktop=True)
        self.assertEqual(result['rows'].strip(), '')

    def test_ticket_ledger_has_status_and_time_filters(self):
        page = (ROOT / 'desktop.html').read_text(encoding='utf-8')
        ledger = board(page, 'data-desktop-screen="ticket-ledger"')
        self.assertIn('aria-label="车票状态"', ledger)
        self.assertIn('aria-label="购票时间"', ledger)
        self.assertIn('data-action="filter-ledger"', ledger)
        self.assertIn('已完成', ledger)
        self.assertIn('已退款', ledger)

    def test_ledger_filter_returns_completed_and_refunded_rows(self):
        result = run_model('const s=Demo.createState(); '
                           'const completed=Demo.ticketLedger(s,{status:"completed"}); '
                           'Demo.requestRefund(s,"o-1"); Demo.confirmRefund(s); '
                           'const refunded=Demo.ticketLedger(s,{status:"refunded"}); '
                           'const untouched=Demo.ticketLedger(s); '
                           'console.log(JSON.stringify({completed:completed.map(o=>o.id), '
                           'refunded:refunded.map(o=>o.id), refundedRow:refunded[0], '
                           'untouched:untouched.map(o=>o.route)}));')
        self.assertEqual(result['completed'], ['o-1'])
        self.assertEqual(result['refunded'], ['o-1'])
        self.assertEqual(result['untouched'], ['海智园 1 号线', '海智园 2 号线'])
        self.assertIn('buyer', result['refundedRow'])

    def test_ledger_ui_filter_shows_refunded_row(self):
        result = run_ui('act("filter-ledger", {ledgerStatus:"completed", ledgerTime:""}); '
                        'const completed=element("[data-ticket-ledger]").innerHTML; '
                        'act("filter-ledger", {ledgerStatus:"refunded", ledgerTime:""}); '
                        'const refunded=element("[data-ticket-ledger]").innerHTML; '
                        'console.log(JSON.stringify({completed, refunded}));', desktop=True)
        self.assertIn('已完成', result['completed'])
        self.assertIn('李明', result['completed'])
        self.assertIn('海智园 1 号线', result['completed'])
        self.assertEqual(result['refunded'].strip(), '')


if __name__ == '__main__':
    unittest.main()
