import html.parser
import json
import pathlib
import subprocess
import unittest

ROOT = pathlib.Path(__file__).parent

MOBILE_SCREENS = ['route-query', 'order-confirmation', 'payment-success', 'purchase-success',
                  'order-center', 'coupon-selection', 'coupon-center', 'exchange-confirmation',
                  'my-coupons', 'boarding-ticket', 'refund']
DESKTOP_SCREENS = ['coupon-management', 'merchant-verification']


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

    def test_order_center_has_four_status_tabs_and_refund_page_rule(self):
        page = (ROOT / 'mobile.html').read_text(encoding='utf-8')
        center = board(page, 'data-screen="order-center"')
        doc = Markup()
        doc.feed(center)
        tabs = [a.get('data-order-tab') for tag, a in doc.attrs if tag == 'button' and 'data-order-tab' in a]
        self.assertEqual(tabs, ['pending', 'paying', 'completed', 'invoiced'])
        for label in ('待支付', '支付中', '已完成', '已开票'):
            self.assertIn(label, center)
        self.assertIn('data-order-list', center)
        refund = board(page, 'data-screen="refund"')
        self.assertIn('data-action="refund-confirm"', refund)
        self.assertIn('发车前 30 分钟', refund)
        self.assertIn('data-refund-route', refund)

    def test_desktop_drops_rules_page_and_hardcodes_rules(self):
        doc = markup('desktop.html')
        screens = [a['data-desktop-screen'] for tag, a in doc.attrs if tag == 'article' and 'data-desktop-screen' in a]
        self.assertEqual(screens, DESKTOP_SCREENS)
        page = (ROOT / 'desktop.html').read_text(encoding='utf-8')
        self.assertNotIn('screen-nav', page)
        self.assertNotIn('shuttle-rules', page)
        self.assertIn('发车前 30 分钟', page)
        css = (ROOT / 'styles.css').read_text(encoding='utf-8')
        self.assertIn('1920px', css)
        self.assertIn('1080px', css)

    def test_desktop_configuration_is_editable_and_public_page_has_no_personal_name(self):
        doc = markup('desktop.html')
        labels = [a.get('aria-label') for tag, a in doc.attrs if tag == 'input']
        self.assertIn('优惠券名称', labels)
        self.assertIn('金卡会员兑换积分', labels)
        self.assertNotIn('张 * 明', (ROOT / 'desktop.html').read_text(encoding='utf-8'))

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
        merchant = board(page, 'data-desktop-screen="merchant-verification"')
        self.assertIn('data-redeem-badge', merchant)
        self.assertIn('data-redeem-remaining', merchant)
        self.assertIn('data-ledger', merchant)
        for column in ('券码', '核销时间', '操作人'):
            self.assertIn(column, merchant)

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


class Business(unittest.TestCase):
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

    def test_redemption_render_changes_badge_quantity_and_button_once(self):
        result = run_ui('act("redeem"); const first = {badge:element("[data-redeem-badge]").textContent, '
                        'remaining:element("[data-redeem-remaining]").textContent, '
                        'disabled:element(\'[data-action="redeem"]\').disabled}; '
                        'act("redeem"); console.log(JSON.stringify({first, remaining:element("[data-redeem-remaining]").textContent}));', desktop=True)
        self.assertEqual(result['first'], {'badge': '已核销', 'remaining': '372 张', 'disabled': True})
        self.assertEqual(result['remaining'], '372 张')

    def test_redeem_appends_ledger_row_once(self):
        result = run_ui('const before = element("[data-ledger]").innerHTML; '
                        'act("redeem"); act("redeem"); '
                        'const after = element("[data-ledger]").innerHTML; '
                        'console.log(JSON.stringify({beforeHasNew: before.includes("CPN 826 193"), '
                        'afterHasNew: after.includes("CPN 826 193"), '
                        'rows: (after.match(/<tr>/g) || []).length}));', desktop=True)
        self.assertFalse(result['beforeHasNew'])
        self.assertTrue(result['afterHasNew'])
        self.assertEqual(result['rows'], 3)

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


if __name__ == '__main__':
    unittest.main()
