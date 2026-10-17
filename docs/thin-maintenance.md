# Thin 维护文档（Thin Maintenance）

> 本文档记录现有渲染引擎 **thin.js** 的能力、语法、已知问题与修复原则。
> 定位：**基于 thin 修复 bug 的可操作手册**（见 `project-vision.md` 的 Dec-2 决策）。
> 配套：`ach-todo.md` 记录具体页面待办；本文档侧重引擎本身。

## 1. thin.js 是什么

- 作者：Li Wei，2018 年，开源（GPL），本项目一直沿用。
- 一句话定位：**基于 jQuery 的轻量模板渲染框架**，模板既可以是对象，也可以是字符串/数组/函数。
- 体积：约 1100 行，无构建步骤，直接 `<script>` 引入。
- 依赖：jQuery（`$`）。jQuery 在此是 thin 的**运行依赖**，不是可选件。

## 2. 核心能力

### 2.1 `$().render()`（最主要接口）
`$(container).render(参数)` 是 thin 的入口，参数三种形态：

| 形态 | 说明 | 典型用法 |
|------|------|----------|
| 数组 | `template:` 省略，直接传模板数组 | `$.render([{div:...},{p:...}])` |
| `{template, data}` | 模板与数据分离 | `$.render({data, template})` |
| `{template, data, datapath/...}` | 对象模板（含控制流） | 见下 |

### 2.2 模板对象（template object）
一个 JS 对象即一个元素节点。键的含义（保留字段）：

| 键 | 作用 |
|----|------|
| `e` | 显式标签名（覆盖化简） |
| `t` | 元素文本内容（可含 `[[path]]` 数据占位） |
| `a` | 属性对象，如 `{href}` `{src}` |
| `class` `id` `name` | 常见属性快捷键 |
| `style` | 内联样式对象 |
| `width` `height` | 尺寸（数字自动加 `px`） |
| `event` | 事件绑定（对象 / 对象数组） |
| `click` | click 简写 |
| `when` | 条件渲染（函数或字符串路径） |
| `if` | 分支渲染 |
| `switch` / `case` | 多分支 |
| `foreach` | 循环 |
| `tab` / `multiview` / `ajax` | 高级组件 |
| `bind` | 表单双向绑定（`path` 路径） |
| `timer` | 定时器（interval/delay） |
| `options` | select 选项 |
| `input`/`textarea`/`select`/`button`/`img`/`div` | 标签化简 |

### 2.3 任意标签简写（兜底语义）
若 `e` 未指定，thin 取**首个非保留键**作为 HTML 标签名，其值作为内容：

```js
{ span: '文本', class: 'x' }   // → <span class="x">文本</span>
{ h2: '标题' }                 // → <h2>标题</h2>
{ schedule: {...}, style: {...} } // → <schedule>...</schedule>（自定义标签）
```

> **注意**：`schedule` / `section` **不是 thin 内置组件**，是通过此兜底生成的自定义 HTML 标签，由 CSS 造型。txt.js 的"导航组件"实为"自定义标签 + 模板语法 + 事件回调"的复合。

### 2.4 数据插值
- `[[path]]`：在字符串模板中从**最近数据容器**取值。
- `{{path}}`：全局取值（IE 命名分组问题，当前部分禁用）。
- 数据附着：渲染时 `element.data_of_thin = 数据`，子节点通过 `nearest_datacontainer()` 向上追溯最近数据。

### 2.5 事件与表单收集
- `event`/`click` 回调收到统一形参：`{sender, type, event, org_data, new_data}`。
- 点击时 thin 自动**收集容器内所有 `input/select/textarea/checkbox/radio/contenteditable` 值**到 `new_data`。
- checkbox 收集为数组，radio 收集为单个值。

### 2.6 其它全局设施
| 接口 | 作用 |
|------|------|
| `poplayer(p)` | 弹层：`{header,class,width,height,render/template+data,onclose}`，可拖拽、可关闭 |
| `popDrag(bar,target)` | 拖拽 |
| `thin.render(view,data)` | 声明式渲染（selector→template 映射） |
| `thin.routeTo` / `thin.cookie` / `thin.parseUrl` | 路由 / cookie / URL 解析 |

## 3. 已知问题与避坑

### 3.1 语义：`.render` 是「追加」而非「清空」
原版薄 `.render()` 把内容**追加**到容器，不清空已有内容。容易误用：
- 想"重渲染"必须先手动 `empty()`（thin 内部 `thin.render` 会 empty，但 `$().render` 不会）。
- 多个来源先后 append 到同一容器时，会出现"覆盖"错觉——实际是堆积。

### 3.2 `[[path]]` 依赖最近数据容器，容易取错层级
- 嵌套模板时 `nearest_datacontainer` 找的是**最近的**有 `data_of_thin` 的节点。
- 若某层没附着数据，会一直上溯到祖先，可能取到非预期数据，调试时要留意层级。

### 3.3 `[[path]]` 无转义，存在注入风险
- 字符串插值和 `t` 文本走 innerHTML 直接插入。**不可信数据需自行转义**，引擎默认不转义。
- 修复实例：monster / ach 数据为自有 JSON（作者可信），风险可控；但若接入用户输入需额外处理。

### 3.4 事件自动 `preventDefault`
- 非 keydown / 非 radio / 非 checkbox 的点击会被 `e.preventDefault()`。若某元素需要默认行为（如需要钩子跳转），需在回调内自行处理或绕过。

### 3.5 `{{path}}` 的 IE 命名分组问题
- 正则用了 `(?<name>...)` 命名分组，IE 不支持，当前多数分支已注释禁用。**不要在 IE 兼容场景依赖全局取值**。

### 3.6 setTimer 的 interval 泄漏风险
- `timer.interval` 挂到 `p.c.interval`，需容器在 DOM 中才清理；重复渲染可能累积定时器。

## 4. 修复原则（与 project-vision 对齐）

1. **只修 bug，不重写引擎**。除非某功能确实缺失且影响多页，否则不新增 thin 语法。
2. **不动 CSS 与数据结构**。修复只在 JS 实现层。
3. **行为兼容优先**。改动后保证现有页面 DOM/class 不变、视觉可复原。
4. **小步 + git**：每次改动可独立回滚，避免大爆炸。

## 5. 与 jQuery 的关系（附：jQuery 必要性）

thin.js 大量使用 jQuery：
- `$.fn.extend({render})` 扩展了 jQuery 原型 → 页面写 `$(x).render()`。
- `$(document).on()` 事件委托、`$('input', ctx).each()` 表单收集、`.val()`、`.html()` 等。

**结论**：当前 thin 绑定 jQuery，**jQuery 不可移除**。若想摆脱 jQuery，等价于重写 thin——这与 Dec-2「不重写」冲突。因此现状是 **jQuery + thin 一起维护**，不在本阶段剥离。

> 若未来确要脱离 jQuery，正确路径是**评估自研/换引擎**而非剥 jQuery——那是另一个决策，已由 Dec-2 推迟。

## 6. 模块化方向（页面怎么写）

### 6.1 现状痛点（用户观察）
- 页面 JS（如 `ach_sr.js`）**没有组件/模块意识**，功能（加载数据、渲染列表、过滤、存档、hash）平铺为一个文件。
- 全站最大"模块"是 `txt.js`（1563 行）：**数据（links 导航树、多语言文案、元素表）+ 渲染（popLinks/加载遮罩/版权条）+ 交互（语言切换）全部耦合在一个文件**，函数名模糊（`lm`/`mod`/`a_section_white` 等），中心理上"词不达意"。
- 这些"组件"实为 thin 兜底生成的自定义标签（`schedule`/`section`）；标签是摆设，靠 CSS + 模板语法 + 事件拼出导航。

### 6.2 模块化切分建议（渐进）
目标不是引入框架，而是**把 txt.js / 页面 JS 按职责拆小**，仍跑在 thin + jQuery 上：

1. **数据层（配置）**：抽出 `links`、多语言文案、元素/减益表 → 独立 `data/*.js`（纯数据，无 DOM 逻辑）。
2. **通用函数层**：`popLinks`、`Loading_Template`、语言切换、`custom_string` → `common/*.js`，挂在 `window.xx` 下。
3. **组件层（可选改造）**：把 `schedule`/`section` 这类"自定义标签 + 事件"提炼成**真正的函数组件**（不做模板 diff，保持 thin 语义），如 `navMenu(config)`、`popNav(config)`，入参数据、出参 DOM，内部仍用 `$().render()`。
4. **页面层**：`ach_*.js` 只做"取数据 → 调组件 → 渲染"，不再把全部交互塞在一个文件。

### 6.3 切分时的边界
- 所有拆分**不得改变最终 DOM 结构与 class**（CSS 依赖它）。
- `data_of_thin` 的数据附着语义要保留，否则 `[[path]]` 断裂。
- 拆出的纯数据文件没有副作用，可最先做、风险最低。

## 7. 行动建议（下次处理顺序）
1. 先从 txt.js「数据区」（`links`、文案、元素表）抽出成 `data/l.*.js` —— 零渲染风险，纯搬运。✓ 最小收益最大
2. 再把 `popLinks`/加载遮罩/版权条做成显式命名函数，并从 txt.js 提纯。
3. 页面（ach）——逐个接入上述通用函数，去掉重复代码。

---

## 8. 未定案：txt.js 拆分的规范（重要）

> **当前状态：未定案，暂时不要动手拆 txt.js。**
> 只完成了"分析方向"（第 6 节），但以下是悬而未决、必须先在文档里定清楚的问题。
> 这些不解决就拆 = 制造新的耦合。

### 8.1 未决定的规范问题
1. **数据区放哪 / 怎么组织**
   - `links` 树、多语言文案、元素/减益表：是放 `javascripts/data/*.js`，还是 `plugins/`？目录约定未定。
   - 纯数据文件用**全局变量**（现状 `var links`）还是 **IIFE 模块导出**？全站其他脚本怎么拿到它（`window.links`？命名空间？）—— 引用方式未定。
2. **组件层是否建 / 建在哪**
   - `schedule`/`section` 是"自定义标签 + CSS + 事件"的伪组件。是否要提炼成真函数组件（`navMenu()` 等）？放哪个目录？**未定**。
   - 若组件化，是做成返回 DOM 的函数、还是接受容器 + 入参渲染？**未定**。
3. **拆分粒度与边界**
   - 拆到多细？文件之间如何互相引用（加载顺序由 HTML `<script>` 控制？）**未定**。
   - 依赖关系怎么声明（避免 `A 用到 B` 但 B 未先加载）？**未定**。
4. **与既有全局变量/单页入口的兼容**
   - 现有页面（几百个）仍在 HTML 里按序 `<script>` 引 txt.js。拆分后这两百个页面怎么拿到新产物？是否仍保留一个聚合入口？**未定**。

### 8.2 决定后的约束
- 一切拆分仍受 Dec-1（渐进不重构）+ Dec-2（不引框架）约束，不得破坏 DOM/class/数据。
- 建议在 `project-vision.md` 增加一条「模块/目录规范」暂定项，或本文件第 8 节定案后再固化。

### 8.3 当前结论
**txt.js 拆分延后，先完成 ach 页面本身的收尾。** 拆分规范待专题讨论后再定，避免在规范未明时动手制造新耦合。