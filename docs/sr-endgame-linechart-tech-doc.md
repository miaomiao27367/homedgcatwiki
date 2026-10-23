# SR 周常玩法「血量演化」折线图技术文档

> 最后更新: 2026-10-17
> 范围: 异相仲裁 / 末日幻影(AS) / 混沌回忆(MoC) / 虚构叙事(Pure Fiction) 四个页面的 ECharts 折线图
> 关联文件: `javascripts/arbitration.js`、`javascripts/as.js`、`javascripts/chaos.js`、`javascripts/fiction.js`

---

## 1. 概览

四个页面都通过 **ECharts 折线图** 展示各期/各层副本的**总血量演化趋势**，调用方式与实现极其相似：

| 页面 | 脚本 | 行为 | 折线图函数 | 图表标题 key | 数据源 |
|------|------|------|-----------|--------------|--------|
| 异相仲裁 | `arbitration.js` | Anomaly Arbitration | `renderHpChart()`（独立函数） | 内联字符串 | `_arbitrationhp` |
| 末日幻影 | `as.js` | Apocalyptic Shadow | 内联在 `writeData()` | `Chart_Title_AS` | `_chaoshp` |
| 混沌回忆 | `chaos.js` | Memory of Chaos | 内联在 `writeData()` | `Chart_Title_MoC` | `_chaoshp` |
| 虚构叙事 | `fiction.js` | Pure Fiction | 内联在 `writeData()` | `Chart_Title_Fiction` | `_fictionhp` |

共同点：
- 都使用 `echarts.init(document.getElementById('chart'))` 初始化，图表挂载点为页面模板里的 `<div id="chart">`（class=`chart_container`）。
- 都在 `writeData()` 流程末尾调用/渲染，切换版本或层数时重新生成。
- 都用 `dispatchAction({type:'showTip'})` 高亮当前期数；其中 chaos/fiction/arbitration 额外绑定 `$('body').on('mouseleave','#chart')` 在鼠标移出后恢复高亮，**as.js 没有** `#chart` 的 mouseleave 处理器。
- 都支持 `#NOLAZY` 时关闭 tooltip：`if ($("#NOLAZY").val()) option.tooltip.show = false`。

---

## 2. 各图具体实现

### 2.1 异相仲裁 — arbitration.js `renderHpChart()`

- 位置: [arbitration.js:L738-L886](file:///C:/Users/Lenovo/Desktop/homdgcatwiki/homdgcatwiki/javascripts/arbitration.js#L738-L886)，由 [writeData](file:///C:/Users/Lenovo/Desktop/homdgcatwiki/homdgcatwiki/javascripts/arbitration.js#L732) 调用。
- **X 轴**: 从 `_schedule` 取出 `Time != ' - '` 的版本名，按 `_id` 升序排列（右侧越新）。
- **Y 轴**: 数值型；对 `>= 10000` 的值以 `(v/10000).toFixed(1) + '万'` 格式化（四张图中唯一带 Y 轴缩放的）。
- **折线（5 条）**，按“有有效数据才显示”过滤（数据存在、非空、且存在 `> 0` 的点）：

| key | 名称(CH) | 颜色 |
|-----|----------|------|
| `TrialA` | 普通总血量 (Knight I) | `#cc0000` |
| `TrialB` | 骑士二 (Knight II) | `#2545ba` |
| `TrialC` | 骑士三 (Knight III) | `#f29e38` |
| `FinalEasy` | 将杀王棋 (Checkmate) | `#00cc00` |
| `FinalHard` | 将杀王棋·绝境 (Zugzwang) | `#9900cc` |

- **当前期高亮**: `myChart.dispatchAction({type:'showTip', dataIndex: _arbitrationhp.Index[cur_schedule_ver] || 0, seriesIndex: 0})`。
- 独立成函数，命名与职责最清晰；也是四张图中唯一“先筛选再加 series”的实现。

### 2.2 末日幻影 — as.js

- 位置: [as.js:L1323-L1385](file:///C:/Users/Lenovo/Desktop/homdgcatwiki/homdgcatwiki/javascripts/as.js#L1323-L1385)，**内联**在 [writeData()](file:///C:/Users/Lenovo/Desktop/homdgcatwiki/homdgcatwiki/javascripts/as.js#L851) 内，无独立函数。
- **X 轴**: `_chaoshp[floor_name].Name`（floor 取自 `$('.f_text').html()`）。
- **Y 轴**: 数值型，无缩放。
- **折线（1 条）**: `name: txt.Fiction_HP[lang]`（“总血量”），`data: _chaoshp[floor_name].HP`，颜色 `#cc0000`。注意此处复用了 `Fiction_HP` 文案 key（语义为“总血量”，可接受，但命名与模块不符）。
- **当前期高亮**: `seriesIndex: 0`（修正前为 `1`，与单条 series 不匹配，会导致无法高亮当前期）。此脚本无 `#chart` 的 mouseleave 恢复逻辑。

### 2.3 混沌回忆 — chaos.js

- 位置: [chaos.js:L685-L762](file:///C:/Users/Lenovo/Desktop/homdgcatwiki/homdgcatwiki/javascripts/chaos.js#L685-L762)，**内联**在 [writeData()](file:///C:/Users/Lenovo/Desktop/homdgcatwiki/homdgcatwiki/javascripts/chaos.js#L498) 内。
- **X 轴**: `_chaoshp[floor_name].Name`。
- **Y 轴**: 数值型，无缩放。
- **图例**: `legend.data = [txt.DPC_S[lang], txt.DPC_M[lang]]`。
- **折线（2 条）**:

| 名称 | data | 颜色 |
|------|------|------|
| 总血量（单攻）`DPC_S` | `_chaoshp[floor_name].Single` | `#cc0000` |
| 总血量（群攻）`DPC_M` | `_chaoshp[floor_name].Multi` | `#2545ba` |

- **当前期高亮**: `seriesIndex: 1`（对应第 2 条，脚本（含 mouseleave）= 传给 Multi 线，与巨大血量展示一致，属预期）。

### 2.4 虚构叙事 — fiction.js

- 位置: [fiction.js:L686-L763](file:///C:/Users/Lenovo/Desktop/homdgcatwiki/homdgcatwiki/javascripts/fiction.js#L686-L763)，**内联**在 [writeData()](file:///C:/Users/Lenovo/Desktop/homdgcatwiki/homdgcatwiki/javascripts/fiction.js#L491) 内。
- **X 轴**: `_fictionhp[floor_name].Name`。
- **Y 轴**: 数值型，无缩放。
- **折线（1 条）**: `name: txt.Fiction_HP[lang]`，`data: _fictionhp[floor_name].HP`，未显式指定颜色（走 ECharts 默认色板）。
- **visualMap（唯一使用方）**: `type:'piecewise'` 且 `show:false`，按 `dimension:0`（= X 轴层数下标）着色：
  - `lte: 9` → `#2545ba`
  - `gt: 9, lte: 10` → `#cc0000`
  - `gt: 10` → `#cc0000`（⚠️ 与上一条完全相同，冗余，可合并为 `gt: 9`）
- **当前期高亮**: `seriesIndex: 0`（正确，仅一条线）。

---

## 3. 共同代码审查结论

### 3.1 高风险 / 建议修复（含复查结论）

> 所有条目均已逐项复查，区分「真实缺陷」与「非问题/纯防御性」，避免惊扰正常功能与视觉。

| # | 问题 | 涉及 | 复查结论与状态 |
|---|------|------|-----------|
| 1 | **`seriesIndex` 越界** | `as.js` | ✅ **确认缺陷，已修复**：仅 1 条 series 却传 `seriesIndex: 1`，导致页面加载时无法高亮当前期；已改为 `0`（与 fiction/arbitration 一致）。末影幻影无 `#chart` 的 mouseleave，故仅此一处。 |
| 2 | **重复 `echarts.init()` 且不 `dispose()`** | 全部 | ⚠️ **复查为非问题**：ECharts 4/5 对同一 DOM 重复 `init` 会返回**已有实例**并复用（仅触发控制台 warning），并不会累积内存泄漏。为避免无谓改动、保持视觉稳定，**未改动**。若介意 warning，可自行加 `if (myChart) myChart.dispose()`（需先 `var myChart`，且首帧防护需声明以避免 ReferenceError）。 |
| 3 | **`myChart` 隐式全局、无空值保护** | 全部 | ⚠️ **复查为非问题**：`writeData()` 在页面加载时必先生成图表，此后才可能触发 mouseleave，运行时不会因 `myChart` 未定义而崩溃。属纯防御性，**未改动**。 |
| 4 | **`$('.f_text').html()` 依赖 DOM 取 floor** | as / chaos / fiction | ⚠️ **复查为可维护性问题，非 bug**：仅职责耦合，功能正确。**未改动**以避免范围蔓延。 |

### 3.2 一致性与可维护性

- **内联 vs 独立函数不一致**：只有 `arbitration.js` 抽出了 `renderHpChart()`，其余三个埋在 `writeData()` 末尾。建议统一抽成各自的 `renderChart()` 函数，减少 `writeData()` 体积、便于独立维护与测试。
- **数据源命名**：`as.js` 与 `chaos.js` 都读 `_chaoshp`（末日幻影复用混沌数据对象），`fiction.js` 用 `_fictionhp`，arbitration 用 `_arbitrationhp`。命名不一致易混淆，建议统一为 `_{mode}hp`（如 `_ashp`）。
- **文案 key 复用**：`as.js` 折线名为 `txt.Fiction_HP`，尽管语义“总血量”可用，仍建议增加 `txt.AS_HP`（或复用 `DPC_A`）以清晰归口。
- **visualMap 冗余分段**：fiction 的 `gt:9,lte:10` 与 `gt:10` 同色，可合并。

### 3.3 建议增强（可选）

- 缺少 `window.resize` 监听：容器尺寸变化时图表不缩放，建议 `window.addEventListener('resize', () => myChart && myChart.resize())`（并记得移除）。
- `renderHpChart()` 的归一化 Y 轴格式化值得推广到其余四图，提升大数值可读性。
- 四图结构高度重复，可考虑抽取公共 `buildLineChartOption(domId, optionFragment)` 工具统一初始化/复用/销毁逻辑，降低三处重复。

---

## 4. 图表配置差异速查

| 项 | arbitration | as | chaos | fiction |
|----|-------------|----|----|---------|
| X 轴数据 | `_schedule` 版本名(过滤 `-`) | `_chaoshp.Name` | `_chaoshp.Name` | `_fictionhp.Name` |
| 线条数 | 5（动态过滤） | 1 | 2 | 1 |
| 图例 legend | 有 | 无 | 有 | 无 |
| Y 轴格式化 | `万` | 无 | 无 | 无 |
| visualMap | 无 | 无 | 无 | 有（分段着色） |
| 高亮 seriesIndex | 0 | 0（已由 1 修正） | 1 | 0 |
| 独立函数 | ✅ `renderHpChart` | ❌ | ❌ | ❌ |
| 对策血量开关 | ✅ `ctr_switch` | ✅ | ✅ | ✅ |

---

## 5. 「对策血量」功能（新增）

为四个模式各自提供一个全局开关（彼此独立），在一个开关下可为折线图追加一条可选的对策血量折线，用于展示对策性 buff 下的折算血量。**对策血量为独立手动分析数据，不接入构建脚本、不参与任何折算公式，直接按数组读值显示。**

### 5.1 设计约定

- **四个模式独立**：各页面各自持有 `counter_mode`（默认 `1`=显示），互不影响。
- **无数据即隐藏**：当某模式当前无任何对策血量数据时，开关整体隐藏（`.ctr_button` 不显示）。
- **有数据默认显示**：存在数据时开关显示且默认开启（`slider_on`），点按可切换 `counter_mode` 并重绘。
- **文案 key**：`txt.CounterHP`（CH「对策血量」/ EN「Counter HP」）。
- **颜色**：对策折线统一使用珊瑚色 `#ff7f50`，与既有色（红 `#cc0000`、蓝 `#2545ba`、橙 `#f29e38`、绿 `#00cc00`、紫 `#9900cc`）区分。
- **通用构造函数**：`txt.js` 新增全局 `counterSeries(data, label)` —— 空数组/缺失/全 0 一律返回 `null`（不渲染），否则返回一条 line 系列。

### 5.2 各模式数据读取位置

| 模式 | 读取字段（每 floor） | 说明 |
|------|----------------------|------|
| 末日幻影 as.js | `_chaoshp[floor].CounterHP`（数组） | 单条主线外追加 |
| 混沌回忆 chaos.js | `_chaoshp[floor].CounterHP`（数组） | 在 `Single`/`Multi` 后追加 |
| 虚构叙事 fiction.js | `_fictionhp[floor].CounterHP`（数组） | 单条主线外追加 |
| 异相仲裁 arbitration.js | `_arbitrationhp.Counter[key]`（按系列） | 按已验证系列逐一追加，key 同 `allSeries[i].key`（`TrialA/TrialB/TrialC/FinalEasy/FinalHard`） |

### 5.3 开关样式与事件

- 复用既有 `.slider_switch` + `.slider_on` 视觉态。
- 独立 class `ctr_switch`，外层容器加 `ctr_button` 以便按需 `toggle` 隐藏，不与星启等批量 `slider_on` 操作冲突。
- 点击事件：翻转 `counter_mode`（仲裁/其余三个可按现有风格直接 `writeData()`，或显式增删 `slider_on` 后重绘）。
- 开关显隐与高亮态在 `writeData()`（仲裁在 `renderHpChart()`）中动态计算。

### 5.4 实现位置速查

- `txt.js`：`CounterHP` 文案 + 全局 `counterSeries()`。
- `arbitration.js`：系列 IIFE 内追加循环；`renderHpChart()` 内按 `_arbitrationhp.Counter` 是否非空计算 `.ctr_button` 显隐；视觉插在 `ms_switch` 之后。
- `as.js` / `chaos.js` / `fiction.js`：`writeData()` 末尾 chart 段追加开关显隐逻辑；系列改为 IIFE 组装并 `push` 对策系列；视觉插在各自 `ms_switch` 之后。
- 注意：fiction 的 `visualMap` 已加 `seriesIndex: 0`，使分段着色仅作用于主线（下标 0），对策折线保持自身颜色，不受分段染色影响。

### 5.5 「空位」与显示样式

对策血量不是贯穿所有期的普通第二曲线，而是**只存在于有对策概念的若干期**的分支。为了呈现「从基础线分出、又落回基础线」的分支效果，`counterSeries(data, base, label)` 对数据做如下处理：

- **真对策点**（非 0 非 null）：正常画线，并显示标记（默认 `symbol:'circle'`、`symbolSize: 8`）。
- **紧邻对策点前后的空位**（`null`/`0`）：用 `base` 基础线对应期的值补齐，作为**分支连接段**——让对策点向左/向右连回基础线，形成分支而非孤立点。连接段不带标记。
- **其余较远的空位**：保持隐藏（`null`），不与基础线重叠绘制。

各模式的 `base`（分支落点基准线）：
- 末日 as.js → `_chaoshp[floor].HP`
- 混沌 chaos.js → `_chaoshp[floor].Multi`
- 虚构 fiction.js → `_fictionhp[floor].HP`
- 仲裁 arbitration.js → 对应系列 `_arbitrationhp[key]`

数据写法：填数字 → 出现对策分支折线与圆点；留空/`0` → 仅在该点前后提供分支连接或隐藏。

**逐层可自定义（对象写法 `{ data, name, color, symbol, symbolSize, connectNulls }`）**：
- `name` 折线名；`color` 折线/点颜色（默认 `#ff7f50`）。
- `symbol` 对策点标记（默认 `circle`）；`symbolSize` 标记大小（默认 `8`）。
- `connectNulls` 是否跨空位连线（默认 `false`）。