import html.parser
import json
import pathlib
import subprocess
import unittest

ROOT = pathlib.Path(__file__).parent


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
''' % (json.dumps(['coupon-management', 'shuttle-rules', 'merchant-verification'] if desktop else
                     ['route-query', 'order-confirmation', 'coupon-selection', 'coupon-center',
                      'exchange-confirmation', 'my-coupons', 'boarding-ticket']),
          'true' if desktop else 'false')
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

    def test_mobile_preserves_seven_393_by_852_screens(self):
        doc = markup('mobile.html')
        screens = [a['data-screen'] for tag, a in doc.attrs if tag == 'article' and 'data-screen' in a]
        self.assertEqual(screens, ['route-query', 'order-confirmation', 'coupon-selection',
                                   'coupon-center', 'exchange-confirmation', 'my-coupons', 'boarding-ticket'])
        self.assertIn('393px', (ROOT / 'styles.css').read_text())
        self.assertIn('852px', (ROOT / 'styles.css').read_text())

    def test_desktop_preserves_three_1920_by_1080_screens(self):
        doc = markup('desktop.html')
        screens = [a['data-desktop-screen'] for tag, a in doc.attrs if tag == 'article' and 'data-desktop-screen' in a]
        self.assertEqual(screens, ['coupon-management', 'shuttle-rules', 'merchant-verification'])
        css = (ROOT / 'styles.css').read_text()
        self.assertIn('1920px', css)
        self.assertIn('1080px', css)

    def test_desktop_configuration_is_editable_and_public_page_has_no_personal_name(self):
        doc = markup('desktop.html')
        labels = [a.get('aria-label') for tag, a in doc.attrs if tag == 'input']
        self.assertIn('优惠券名称', labels)
        self.assertIn('发车前分钟数', labels)
        self.assertIn('金卡会员兑换积分', labels)
        self.assertNotIn('张 * 明', (ROOT / 'desktop.html').read_text(encoding='utf-8'))

    def test_coupon_selection_count_reflects_threshold_and_demo_ticket_disclaimer(self):
        page = (ROOT / 'mobile.html').read_text(encoding='utf-8')
        selection = page.split('data-screen="coupon-selection"', 1)[1].split('</article>', 1)[0]
        self.assertIn('<span class="active">可使用 1</span>', selection)
        self.assertIn('<span>不可使用 1</span>', selection)
        self.assertIn('不读取服务端时间', page)

    def test_each_desktop_sidebar_has_keyboard_operable_navigation(self):
        page = (ROOT / 'desktop.html').read_text(encoding='utf-8')
        destinations = ['coupon-management', 'shuttle-rules', 'merchant-verification']
        for board in page.split('<article class="desktop-board"')[1:]:
            sidebar = board.split('</aside>', 1)[0]
            doc = Markup()
            doc.feed(sidebar)
            self.assertEqual([a.get('data-nav') for tag, a in doc.attrs if tag == 'button'], destinations)
            self.assertFalse(any(tag == 'span' for tag, _ in doc.attrs))

    def test_redemption_badge_and_remaining_count_have_render_targets(self):
        page = (ROOT / 'desktop.html').read_text(encoding='utf-8')
        merchant = page.split('data-desktop-screen="merchant-verification"', 1)[1].split('</article>', 1)[0]
        self.assertIn('data-redeem-badge', merchant)
        self.assertIn('data-redeem-remaining', merchant)

    def test_both_exchange_buttons_open_the_same_confirmation_with_selected_id(self):
        page = (ROOT / 'mobile.html').read_text(encoding='utf-8')
        center = page.split('data-screen="coupon-center"', 1)[1].split('</article>', 1)[0]
        doc = Markup()
        doc.feed(center)
        self.assertEqual([a.get('data-exchange-id') for tag, a in doc.attrs if a.get('data-action') == 'exchange-preview'], ['three', 'five'])
        confirm = page.split('data-screen="exchange-confirmation"', 1)[1].split('</article>', 1)[0]
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
    def test_no_coupon_selection_or_submission_before_booking(self):
        result = run_model('const s = Demo.createState(); '
                           'const choose = Demo.chooseCoupon(s,"three"); '
                           'const none = Demo.chooseCoupon(s,null); '
                           'const submit = Demo.submit(s); '
                           'console.log(JSON.stringify({choose,none,submit,order:s.order,coupon:s.selectedCoupon}));')
        self.assertFalse(result['choose'])
        self.assertFalse(result['none'])
        self.assertFalse(result['submit'])
        self.assertIsNone(result['order'])
        self.assertIsNone(result['coupon'])

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

    def test_no_prebooking_submit_or_coupon_navigation(self):
        result = run_ui('act("select-coupon"); const couponScreen=boards.find(b=>!b.hidden).getAttribute(); '
                        'act("submit"); console.log(JSON.stringify({couponScreen, '
                        'submitDisabled:element(\'[data-action="submit"]\').disabled, '
                        'status:element("#demo-status").textContent}));')
        self.assertEqual(result['couponScreen'], 'route-query')
        self.assertTrue(result['submitDisabled'])
        self.assertNotIn('提交成功', result['status'])

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
