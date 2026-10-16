# 渲染层契约（Renderer Contract）

> 本契约落实 `docs/project-vision.md` 的「数据与样式解耦、视觉可复原」原则。
> 它是「JS 如何把数据变成可被 CSS 呈现的 DOM」的约定 —— 无论最终用哪种实现。
> 优先级：第三部分（硬性约束）在方向 A 下必须遵守；第二部分（渲染范式 / 引擎）为待定决策。
> 与 `project-vision.md` 冲突时，以 vision 为准。

---

## 第一部分：结论回顾（为什么要有这份契约）

- 本项目最宝贵的资产 = **数据 JSON + 视觉样式 CSS**。
- JS 只是"实现层"：产出**符合现有 class/结构 的 DOM**，样式完全交给 CSS。
- 因此**视觉可复原**的充要条件 = 「新实现产出的 DOM 结构 / class 序列」与旧的一致。
- 这份契约就是把这个"如何保持一致"的规则书面化，避免反复返工。

---

## 第二部分：渲染范式与引擎选型

### 2.1 现状引擎（`$(...).render()`，位于 `plugins/thin.js`）

- 作者：Li Wei（本站作者），本仓库自研，头注 **GPL v3+**。
- 调用链：
  - `thin.render(view, data)` → 对 view 里每个 `selector` 执行 `$(selector).empty().render({data, template: view[selector]})`。
  - `$.fn.render({data, template})` → 按模板类型（string / object / function / array）分发到 `render_by_data` / `render_by_templates` / `render_template`。
  - `render_template` → 字符串用 `render_content`（`[[field]]` 填充）；对象走 `render_object_template`；函数则调用后把返回值当字符串内容。
- 能力：
  - 对象模板字段：`e`（元素名）、`t`（内容，注意是 `t`）、`a`（attribute）、`class`、`id`、`name`、`style`、`width`、`height`、`options`、`bind`（双向绑定）、`value`、`selected`、`when`（条件渲染）、`data` / `datapath`（取数）、`event` / `click`。
  - 顶层流转控制：`if`、`switch/case`、`foreach`、`tab`、`ajax`、`multiview`（由 `render_object_template` 按 else-if 顺序分派）。
  - 数据获取：`dataWalker` 沿 `data_of_thin` 容器链用 `[[path]]` 取值；`.`, `..`, `/` 路径语法。
- 已知限制（实测于源码）：
  1. **默认不转义**：`render_content`（thin.js 973-990 行）对 `[[field]]` 的值是 `value == undefined ? '' : value`，**直接拼入，无 HTML 转义**。
  2. **取名字符集受限**：`[[field]]` 正则是 `[[[a-zA-Z0-9\-\./_]*]]` —— 不支持空格 / 中文 / `$` 等字段名，不支持方法调用、`[i]` 下标。
  3. **控制流只在对象模板顶层分发**（`if/foreach/switch` 等是 `render_object_template` 的顺序分派，非对任意嵌套对象递归生效）；嵌套条件主要靠 `when`，语法有限。
  4. **全量重建**：`thin.render` 每次 `$(selector).empty()` 再重画，无增量/虚拟 DOM。
  5. 数据作用域依赖 `data_of_thin` 向上查找（`nearest_datacontainer`），嵌套时易踩坑。
  6. 运行时带较多 `console.log`（含 `thin.render` 起始处打日志），调试噪音。

### 2.2 两个可选路线（待定）

| 路线 | 做法 | 优点 | 代价 |
|------|------|------|------|
| **R1：统一用现有 `$(...).render()`** | 把 ach_gi 从原生 jQuery 拼接改为用 render()，与 ach_sr 一致 | 零新依赖、符合代码库既有习惯、改动局促在一次性 | 保留上述限制（转义/取名字符集/控制流），需在契约里靠约定补齐 |
| **R2：自研极简渲染模块** | 新建一个小型渲染层，目的性解决 R1 的限制 | 可做**默认转义**、数据访问走 JS/value 优先、控制流能嵌套、无构建 | 新增自研件，需写、试、养熟；GPL 背景下须注意与 thin 的关系 |

**当前决定**：**采用 R2（自研极简渲染引擎）**，不采用 R1。
理由（记录在案）：
- ach 目前无紧急问题，正好为"地基"腾出窗口：**先把自研引擎写好、养熟**，之后任何新页面/翻新页直接复用，避免每次都在 thin 的短板（转义/取名字符集/嵌套控制流）上绕行。
- 与其"先 R1 适配 ach、下次翻新又撞墙"，不如一次投入把引擎做成通用地基，再回头适配 ach_gi / ach_sr 两边。
- R2 由**第三部分硬性约束**兜底，不会破坏数据与样式（视觉仍可复原）。

> 决策已定（见第四部分 Rend-2）。自研引擎是本契约涉及的核心工程。

### 2.3 R2：自研极简引擎 —— 接口契约（设计图纸）

**定位**：替代 thin 做"数据 → DOM"的极简层。**默认转义**、数据访问自由、控制流可嵌套、无构建、自包含可 `script` 引入。**不追求虚拟 DOM / 双向绑定**（页面多为列表/详情静态数据，用不上）。

**对外 API（草案）**

- `X.render(container, template, data)`：把 `data` 渲染进 `container`。
  - `template` 为数组 → 对数组内每一项按同一模板迭代渲染（列表）；
  - `template` 为对象 → 节点模板；
  - `template` 为函数 → `fn({container, data, value})` 返回节点/字符串；
  - `container` 可为选择器/元素。
- `X.escape(str)`：HTML 转义工具（`& < > " '`）。
- 字符串填充令牌：`{{path}}`（**转义**）、`{{{path}}}`（**不转义**，显式富文本）。

**节点模板对象字段**

| 字段 | 说明 |
|------|------|
| `e` | 元素名，缺省 `div` |
| `t` | 内容：字符串 / 子节点对象 / 节点数组（可嵌套 → 解决 thin 的嵌套难题） |
| `class` `id` `name` | 类名/ID/name |
| `a` | attribute 对象，值可为字符串或 `fn({value,data})` |
| `style` | 样式对象，值可为字符串或函数 |
| `when` | 条件（值 / `fn({data,value})`）为真才渲染该节点 |
| `foreach` | 覆盖数据源：值可为数组或 `fn({data})` 返回数组，配合 `t` 迭代 |
| `if`/`switch` | 顶层/嵌套条件（与 `foreach` 同层级互斥） |

**数据访问**：字段值支持：字面值、`fn({data, value})`、`{{path}}` 点路径（`.` / `..` 上溯，参考 thin 语义但命名更自由）。

**行为约定（对齐第三部分硬性约束）**：
- **默认转义**：所有来自数据的字符串按文本处理并转义；用 `{{{path}}}` 才显式允许 HTML。
- **不改 class/结构**：由调用方保证，引擎只负责按模板生成，绝不擅自增删。
- 每次渲染清空目标容器（与 thin 语义一致），无增量。

---

## 第三部分：硬性约束（方向 A 下必须遵守）

> 第二部分的路线之争不影响这里的约束 —— 无论选 R1 还是 R2，都必须满足。

### 3.1 结构与 class 纪律（视觉可复原的根本）

1. **不改 class / 结构**：任何渲染改动的产物，其 `DOM 层级 + class 序列` 必须与现状一致。只允许改"用代码生成 DOM 的方式"，不允许"顺手改 class 或删改结构"。
2. **CSS 为主体**：所有视觉（颜色、间距、布局、字体、动画）一律放在 `stylesheets/**` 与页面 `<link>` 的 CSS 中，JS 端**不得内联硬编码样式**去替代/覆盖 CSS（个别 `style` 动态值除外，且须注明）。
3. **对照验收**：涉及渲染的改动，需对目标页面做"改动前 / 后"对照，核对颜色、间距、布局、hover/active 态无走样，确认视觉可复原后再收工。

### 3.2 转义与安全（R1 尤其关键，因现有引擎不转义）

1. **数据字段默认按文本处理，必须转义**：凡来自数据文件、且可能含外部/用户内容、需按**纯文本**展示的字段（如 `desc`、`name` 这类），一律**转义**后再进 DOM（rico `text()` / `createTextNode` / escape 函数），**不得用 `.html()` 直接插入**。
2. 若某字段**确需富文本/HTML**，须显式声明，并对来源做明确限制（信任来源白名单），否则不得当作 HTML。
3. 现有 `ach_gi.js` 中 `<div class="ach-desc">').html(ach.desc)` 这类为**待整改项**（见 `docs/ach-todo.md` 中优先级）。

### 3.3 数据加载与作用域

1. 数据文件路径与字段结构**冻结**，见 `docs/ach-todo.md`「数据存储」表；增删字段须先改契约/清单，不得在代码里随手约定新字段。
2. 渲染时的数据作用域遵循现有 `data_of_thin` / 就近容器规则（若选 R1）；不引入与现有规则冲突的作用域机制。

### 3.4 加载与依赖

1. 渲染所需脚本按现有顺序直引：`plugins/jquery.js` →（需要时）`plugins/thin.js` → 页面逻辑（`javascripts/*.js`）。
2. 新增渲染模块（若走 R2）须**自包含、可独立 `<script>` 引入**，不破坏现有加载顺序，不改变存量页的依赖。

---

## 第四部分：决策记录（Decision Record）

- **Rend-1（已定）**：自研极简引擎 R2 为渲染层方向；R1（统一用 thin）不采用。理由见 2.2「当前决定」。
- **Rend-2（进行中）**：已定 R2 接口契约（2.3 节）。下一步：按此实现 `plugins/renderer.js`，在 ach_gi / ach_sr 上试点并写 DEMO 验证。
- 待定项：
  - R2 具体文件命名/放置（当前建议 `plugins/renderer.js`，与 thin 同目录作为替代位）。
  - ach_gi / ach_sr 是否在 R2 就绪后立即适配，或分开逐个适配（受方向 A 与 `ach-todo.md` 约束）。
- 引擎选择/范式每有变更，须在此追加决策记录，避免"该来改去"。

---

## 附：与既有文档的关系

- `docs/project-vision.md` —— 方向基线（本契约的上位）。（本文件依赖其第 2、4 节）
- `docs/ach-todo.md` —— ach 具体待办（引用本契约 3.2 的转义整改项）。
- `docs/ach-survey.md` —— 已标记过时，不引用。