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
- 都用 `dispatchAction({type:'showTip'})` 高亮当前期数，并绑定 `$('body').on('mouseleave','#chart')` 在鼠标移出后恢复高亮。
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
- **当前期高亮**: `seriesIndex: 1` —— **⚠️ 疑点/缺陷**：series 只有 1 个（下标 `0`），这里传 `1` 越界，mouseleave 处理器中同样如此，会造成提示无法命中。

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

### 3.1 高风险 / 建议修复

| # | 问题 | 涉及 | 说明与建议 |
|---|------|------|-----------|
| 1 | **`seriesIndex` 越界** | `as.js` | 仅 1 条 series 却传 `seriesIndex: 1`（两处：渲染末尾 + mouseleave）。showTip 命中不了，建议改为 `0`。 |
| 2 | **重复 `echarts.init()` 且不 `dispose()`** | 全部 | 每次 `writeData()` 都 `echarts.init` 新实例并赋值给全局 `myChart`，旧实例未 `dispose()`，频繁切换会累积内存/实例。建议：若**已存在实例则 `setOption` 复用**，或 `myChart.dispose()` 后再 init。 |
| 3 | **`myChart` 隐式全局、无空值保护** | 全部 | `myChart = echarts.init(...)` 未声明 `var`，泄漏为全局；mouseleave 里直接使用 `myChart` 若尚未初始化会报错。建议局部 `var` + 判空（`myChart && myChart.dispatchAction(...)`）。 |
| 4 | **`$('.f_text').html()` 依赖 DOM 取 floor** | as / chaos / fiction | 在 chartoption 里和 showTip 数据下标处反复 `$('.f_text').html()` 读走楼层名，职责耦合 DOM。建议在 `writeData()` 顶部缓存 `var floor_name = ...` 一次复用（chaos/fiction 已本地缓存变量，但 showTip/mouseleave 仍重复读取）。 |

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
| 高亮 seriesIndex | 0 | **1（疑误）** | 1 | 0 |
| 独立函数 | ✅ `renderHpChart` | ❌ | ❌ | ❌ |