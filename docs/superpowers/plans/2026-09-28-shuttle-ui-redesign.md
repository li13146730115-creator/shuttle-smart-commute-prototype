# 智慧通勤移动端与 PC 端改版实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans` 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法跟踪进度。本计划不要求自动创建 git commit。

**目标：** 在现有静态原型中实现移动端日期选择、支付中订单详情/取消，以及 PC 端优惠券列表/新增和独立车票台账页面，并保持所有行为为内存演示。

**架构：** 继续使用 `data-screen` / `data-desktop-screen` 管理页面画板，使用现有 `app.js` 的内存状态和事件委托驱动导航。移动端新增 `date-picker`、`paying-order-detail` 画板；PC 端将页面状态拆为 `coupon-list`、`coupon-create`、`ticket-ledger`，不引入真实后端、持久化或新框架。

**技术栈：** 原生 HTML、CSS、JavaScript、Python `unittest`、Node.js `vm` 业务模型测试。

---

## 文件职责

- 修改 `/private/tmp/shuttle-pages.Rdpguq/mobile.html`：移除站点选择区域和运行时长文案；增加日期选择、支付中详情及取消支付画板。
- 修改 `/private/tmp/shuttle-pages.Rdpguq/desktop.html`：将优惠券管理拆成列表/新增两个画板，将商家核销改为独立车票台账画板。
- 修改 `/private/tmp/shuttle-pages.Rdpguq/app.js`：增加所选日期、日期选择、支付取消、支付中详情和 PC 页面导航逻辑；继续使用内存状态。
- 修改 `/private/tmp/shuttle-pages.Rdpguq/styles.css`：增加日期条、日历、支付详情、后台列表/搜索/表单布局样式，复用现有视觉变量。
- 修改 `/private/tmp/shuttle-pages.Rdpguq/test_site.py`：先加入本轮结构和业务失败测试，再保留并调整旧测试中已变更的页面断言。
- 不修改 `/private/tmp/shuttle-pages.Rdpguq/index.html`：现有双入口继续有效。

## 状态与接口约定

在实现前固定以下命名，避免页面和测试不一致：

```js
state.selectedDate = '2026-09-20';
state.datePickerTarget = null;
state.payingId = null;
state.orderTab = 'pending';
```

- `selectDate(state, date)`：仅接受 `YYYY-MM-DD` 字符串，更新 `selectedDate` 并清空 `datePickerTarget`。
- `book(state, id)`：把 `selectedDate` 写入新订单的 `travelDate`。
- `cancelPayment(state, id)`：仅取消状态为 `paying` 的订单，将状态改为 `cancelled`；若为当前 `payingId`，清空该字段；返回布尔值。
- `pay(state)`：禁止对已取消或不存在订单支付；现有支付成功链保持不变。
- `orderTab` 增加 `cancelled`，订单中心可查看已取消记录。
- `ticketLedger(state)` 继续排除 `pending`、`paying`、`refunded`、`cancelled`，仅返回成功购买且未退款/取消的车票。

---

### 任务 1：建立本轮失败验收测试

**文件：**
- 修改：`/private/tmp/shuttle-pages.Rdpguq/test_site.py`
- 读取参考：`mobile.html`、`desktop.html`、`app.js`

- [ ] **步骤 1：新增移动端结构失败测试**

在 `MOBILE_SCREENS` 中加入 `date-picker` 和 `paying-order-detail`，在 `DESKTOP_SCREENS` 中改为 `coupon-list`、`coupon-create`、`ticket-ledger`，并新增断言：

```python
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
```

- [ ] **步骤 2：新增 PC 页面结构失败测试**

```python
def test_desktop_has_coupon_list_create_and_ticket_ledger_pages(self):
    doc = markup('desktop.html')
    screens = [a['data-desktop-screen'] for tag, a in doc.attrs
               if tag == 'article' and 'data-desktop-screen' in a]
    self.assertEqual(screens, ['coupon-list', 'coupon-create', 'ticket-ledger'])
    page = (ROOT / 'desktop.html').read_text(encoding='utf-8')
    ledger = board(page, 'data-desktop-screen="ticket-ledger"')
    self.assertNotIn('确认核销优惠券', ledger)
    self.assertNotIn('券码查询或扫码结果', ledger)
    self.assertIn('data-ticket-ledger', ledger)
```

- [ ] **步骤 3：新增业务模型失败测试**

```python
def test_date_selection_is_used_when_booking(self):
    result = run_model(
        "const s=Demo.createState(); Demo.selectDate(s,'2026-09-23'); "
        "Demo.book(s,'route-1'); console.log(JSON.stringify({date:s.selectedDate, travelDate:s.order.travelDate}));"
    )
    self.assertEqual(result, {'date': '2026-09-23', 'travelDate': '2026-09-23'})

def test_paying_order_can_be_cancelled_and_cannot_complete(self):
    result = run_model(
        "const s=Demo.createState(); Demo.pay(s); const id=s.payingId; "
        "const cancelled=Demo.cancelPayment(s,id); "
        "const completed=Demo.completePayment(s); "
        "console.log(JSON.stringify({cancelled,completed,status:s.orders.find(o=>o.id===id).status,payingId:s.payingId}));"
    )
    self.assertEqual(result, {'cancelled': True, 'completed': False, 'status': 'cancelled', 'payingId': None})
```

- [ ] **步骤 4：运行失败测试确认失败原因**

运行：

```bash
cd /private/tmp/shuttle-pages.Rdpguq && python3 -m unittest test_site.py -v
```

预期：新增断言因缺少画板、接口和状态而失败；不得因测试语法错误或错误路径失败。

---

### 任务 2：实现移动端日期选择和路线列表改版

**文件：**
- 修改：`/private/tmp/shuttle-pages.Rdpguq/mobile.html`
- 修改：`/private/tmp/shuttle-pages.Rdpguq/app.js`
- 修改：`/private/tmp/shuttle-pages.Rdpguq/styles.css`

- [ ] **步骤 1：重构路线首页结构**

在 `route-query` 画板中删除站点选择卡片和所有“约 35 分钟/运行时间”文案，保留两条路线的早晚标识、方向、发车时间、到达时间、价格和预订按钮。日期入口使用：

```html
<button type="button" class="date-switch" data-action="open-date-picker">
  <span class="eyebrow">出行日期</span>
  <b data-selected-date>2026 年 9 月 20 日</b>
  <span>切换日期 ›</span>
</button>
```

- [ ] **步骤 2：新增日期选择画板**

新增 `data-screen="date-picker"`，包含返回按钮、月份标题、周标题、日期按钮和可点击日期：

```html
<button type="button" data-action="select-date" data-date="2026-09-20">20</button>
<button type="button" data-action="select-date" data-date="2026-09-21">21</button>
<button type="button" data-action="select-date" data-date="2026-09-22">22</button>
<button type="button" data-action="select-date" data-date="2026-09-23">23</button>
```

- [ ] **步骤 3：加入日期状态和事件**

在 `createState()` 增加 `selectedDate: '2026-09-20'`，导出 `selectDate`，并在事件处理中加入：

```js
else if (action === 'open-date-picker') {
  show('date-picker');
} else if (action === 'select-date') {
  if (selectDate(state, button.dataset.date)) {
    show('route-query');
    status('出行日期已更新（演示）。');
  }
}
```

`render()` 将 `selectedDate` 格式化写入 `[data-selected-date]` 和订单确认页 `[data-order-date]`，`book()` 将 `travelDate` 写入订单。

- [ ] **步骤 4：运行移动端结构和模型测试**

运行：

```bash
cd /private/tmp/shuttle-pages.Rdpguq && python3 -m unittest test_site.Pages.test_mobile_date_picker_and_payment_detail_markup test_site.Business.test_date_selection_is_used_when_booking -v
```

预期：日期相关测试通过；支付详情测试仍可能失败，继续下一任务。

---

### 任务 3：实现支付中订单详情与取消支付

**文件：**
- 修改：`/private/tmp/shuttle-pages.Rdpguq/mobile.html`
- 修改：`/private/tmp/shuttle-pages.Rdpguq/app.js`
- 修改：`/private/tmp/shuttle-pages.Rdpguq/styles.css`
- 修改：`/private/tmp/shuttle-pages.Rdpguq/test_site.py`

- [ ] **步骤 1：将支付中订单改为可点击入口**

`orderCard(order)` 对 `paying` 状态输出：

```js
action = '<button type="button" class="chip amber" data-action="view-paying-order" data-order-id="' + order.id + '">查看支付详情</button>';
```

- [ ] **步骤 2：新增支付详情画板和取消按钮**

新增 `data-screen="paying-order-detail"`，使用以下绑定字段：

```html
<b data-paying-route></b>
<span data-paying-date></span>
<span data-paying-time></span>
<span data-paying-order-id></span>
<span data-paying-amount></span>
<span class="chip amber">支付中</span>
<button type="button" class="secondary" data-action="cancel-payment">取消支付</button>
```

- [ ] **步骤 3：实现取消状态流转**

实现并导出：

```js
function cancelPayment(state, id) {
  const order = state.orders.find(item => item.id === id && item.status === 'paying');
  if (!order) return false;
  order.status = 'cancelled';
  if (state.payingId === id) state.payingId = null;
  return true;
}
```

在详情导航时设置 `state.payingId` 或 `state.paymentDetailId`；取消成功后回到 `order-center`，切换到 `cancelled`，提示“支付已取消（演示）”。订单中心增加“已取消”筛选按钮。`completePayment()` 对取消后的订单保持返回 `false`。

- [ ] **步骤 4：运行支付相关测试**

运行：

```bash
cd /private/tmp/shuttle-pages.Rdpguq && python3 -m unittest test_site.Business.test_paying_order_can_be_cancelled_and_cannot_complete test_site.Pages.test_order_center_has_four_status_tabs_and_refund_page_rule -v
```

预期：新增支付取消模型测试通过；订单中心旧测试需更新为包含 `cancelled` 后通过。

---

### 任务 4：拆分 PC 优惠券页面并建立独立车票台账页

**文件：**
- 修改：`/private/tmp/shuttle-pages.Rdpguq/desktop.html`
- 修改：`/private/tmp/shuttle-pages.Rdpguq/app.js`
- 修改：`/private/tmp/shuttle-pages.Rdpguq/styles.css`
- 修改：`/private/tmp/shuttle-pages.Rdpguq/test_site.py`

- [ ] **步骤 1：建立三个后台画板**

将 `data-desktop-screen` 改为以下顺序：

```text
coupon-list, coupon-create, ticket-ledger
```

每个画板侧栏都使用三个可键盘操作的 `<button data-nav>`。`coupon-list` 包含搜索字段、查询按钮、新增按钮、导出按钮和优惠券表格；`coupon-create` 承载原有完整配置字段；`ticket-ledger` 仅包含车票台账表格和 Excel 导出。

- [ ] **步骤 2：删除车票台账页优惠券核销内容**

从 `ticket-ledger` 删除券码查询卡片、优惠券卡片、剩余核销数量、核销按钮、优惠券核销台账和 `data-redeem-*` 绑定。保留完整车票表格字段：路线、班车时间、方向、购买时间、支付时间、交易时间、原始金额、优惠券抵扣金额、实付金额、所属项目、购买人、手机号、操作人、使用的优惠券。

- [ ] **步骤 3：实现 PC 导航和列表演示操作**

侧栏继续由现有 `show(name)` 切换。新增按钮导航到 `coupon-create`，查看/编辑按钮导航到 `coupon-create`，返回列表按钮导航到 `coupon-list`。搜索、查询、导出和保存操作只更新 `#demo-status`，不写入服务端或 localStorage。`render()` 只在 `ticket-ledger` 页面填充 `ticketLedger(state)`。

- [ ] **步骤 4：补充后台视觉样式**

在现有 `desktop-*` 规则基础上增加 `.desktop-search`、`.desktop-list-toolbar`、`.desktop-table-wrap`、`.desktop-form-section` 和 `.date-switch` 等样式，复用 `--navy`、`--paper`、`--blue`、`--cyan`、`--line` 和现有圆角/阴影；窄屏继续使用 `overflow-x:auto`。

- [ ] **步骤 5：运行 PC 结构测试**

运行：

```bash
cd /private/tmp/shuttle-pages.Rdpguq && python3 -m unittest test_site.Pages.test_desktop_has_coupon_list_create_and_ticket_ledger_pages test_site.Pages.test_desktop_configuration_is_editable_and_public_page_has_no_personal_name test_site.Pages.test_each_desktop_sidebar_has_keyboard_operable_navigation test_site.Pages.test_merchant_ticket_table_has_current_park_purchase_details -v
```

预期：PC 页面名称、完整配置字段、三按钮侧栏和车票台账字段全部通过。

---

### 任务 5：全量回归、静态检查和验收

**文件：**
- 修改：`/private/tmp/shuttle-pages.Rdpguq/test_site.py`（仅在旧断言与确认设计冲突时调整）
- 检查：`mobile.html`、`desktop.html`、`app.js`、`styles.css`

- [ ] **步骤 1：运行完整 Python 测试**

```bash
cd /private/tmp/shuttle-pages.Rdpguq && python3 -m unittest discover -s . -p 'test_site.py' -v
```

预期：所有测试通过，旧的优惠券核销断言已替换为“台账页不含核销内容”的新断言。

- [ ] **步骤 2：运行 JavaScript 语法检查**

```bash
cd /private/tmp/shuttle-pages.Rdpguq && node --check app.js
```

预期：退出码为 0，无语法错误。

- [ ] **步骤 3：执行页面内容验收**

检查以下结果：

```bash
cd /private/tmp/shuttle-pages.Rdpguq && python3 - <<'PY'
from pathlib import Path
mobile = Path('mobile.html').read_text(encoding='utf-8')
desktop = Path('desktop.html').read_text(encoding='utf-8')
assert '上车站点' not in mobile and '下车站点' not in mobile
assert '约 35 分钟' not in mobile and '运行时间' not in mobile
assert 'data-screen="date-picker"' in mobile
assert 'data-screen="paying-order-detail"' in mobile
assert 'data-desktop-screen="coupon-list"' in desktop
assert 'data-desktop-screen="coupon-create"' in desktop
assert 'data-desktop-screen="ticket-ledger"' in desktop
ledger = desktop.split('data-desktop-screen="ticket-ledger"', 1)[1].split('</article>', 1)[0]
assert '确认核销优惠券' not in ledger
assert 'data-action="export-excel"' in ledger
print('static acceptance: OK')
PY
```

- [ ] **步骤 4：核对 git diff，不自动提交**

```bash
cd /private/tmp/shuttle-pages.Rdpguq && git status --short && git diff -- mobile.html desktop.html app.js styles.css test_site.py
```

确认只包含本轮原型文件和计划文件；不上传敏感资料、不修改 Git 配置、不执行 commit 或 push。

---

## 规格覆盖自检

- 移动端删除站点选择：任务 1、2。
- 移动端日期入口、日历页面、日期回写订单：任务 1、2。
- 路线列表早晚标识、方向、时间、价格、预订：任务 1、2。
- 删除运行时长文案：任务 1、2、5。
- 支付中详情、取消、已取消状态和不可完成支付：任务 1、3。
- PC 优惠券列表页：任务 1、4。
- PC 优惠券新增页和全部字段：任务 1、4。
- PC 独立车票台账、完整字段、Excel 导出：任务 1、4、5。
- 删除车票台账中的优惠券核销内容：任务 1、4、5。
- 视觉风格和窄屏横向查看：任务 4、5。
- TDD 失败测试、最小实现、全量回归：任务 1 至 5。

## 实施边界

- 不新增真实支付、后台 API、localStorage、数据库或认证。
- 不修改首页入口和 GitHub Pages 配置。
- 不在执行计划阶段自动 commit；如后续需要发布，另行执行发布前确认和验证流程。
