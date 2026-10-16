# 成就页 TODO 文档

> 本文档记录成就页（GI / SR）当前实现的状态、遗留问题与待办事项。
> 以当前代码和存储为准。旧勘查报告 `docs/ach-survey.md` 已标记为过时，不复用。
>
> **方向基线：见 `docs/project-vision.md`。** 本项目定为方向 A（渐进、不全面重构），
> 本清单所有改动须遵守「保留存量 DOM/class、视觉可复原」的约束；当与 vision 冲突时以 vision 为准。

## 现状快照

### 入口与脚本

| 游戏 | 页面入口 | 脚本 | 状态 |
|------|---------|------|------|
| GI | `gi/ach/index.html` | `javascripts/ach_gi.js` | ✅ 页面引用正常 |
| SR | `sr/ach/index.html` | `javascripts/ach_sr.js` | ✅ 页面引用正常 |

### 数据存储

| 游戏 | 元数据 | 分组明细 | 字段 |
|------|--------|---------|------|
| GI | `/gi/CH/ach/ach.json` | `/gi/CH/ach/groups/{id}.json`（0~66） | meta: `totalNum/totalPrimo/versions/groups(id,name,num,reward)`；成就: `id/name/desc/ver/hidden/reward/total` |
| SR | `/sr/data/CH/ach.json` | `/sr/data/CH/ach/{1..9}.json` | meta: `latestVersion/prevVersion/totalNum/prevTotalNum/versions/groups(id,name,icon,num)`；成就: `id/name/desc/ver/reward` |

> 注：目前仅存在 `CH` 语言数据，其他语言会 404。

### 已实现功能

- 分组侧栏（含「全部」；SR 另有「新增」视图）
- 搜索（匹配 name + desc）
- 版本过滤下拉
- 隐藏成就开关（GI）
- 勾选完成进度（localStorage 持久化）
- URL hash 状态存取 / 恢复
- GI 兼容旧版隐式 `#ID` 传参

---

## TODO 清单

### 高优先级

- [ ] **SR 增加 `hashchange` 监听**
  - 现状：`ach_gi.js` 绑定了 `$(window).on('hashchange', ...)` 实现前进/后退同步；`ach_sr.js` 只在首次加载时 `parseHash()`，无监听，浏览器前进/后退无法同步分组与版本。
  - 目标：两页行为一致。

- [ ] **非 CH 语言数据处理**
  - 现状：GI 只有 `gi/CH/`，SR 只有 `sr/data/CH/`；其他 `lang3` 下 `ach.json` 404。
  - `ach_gi.js` 有 `.fail()` 提示；`ach_sr.js` 的 `$.getJSON` 无 fail 处理，失败时静默空白。
  - 目标：SR 补 `.fail()` 提示；评估是否需要多语言数据或明确降级策略。

- [ ] **统一两页渲染范式（渐进）**
  - 现状：`ach_sr.js` 使用全站 `$(...).render()` 模板引擎；`ach_gi.js` 全部使用原生 jQuery DOM 拼接（`.append/.html/.text`）。
  - 目标：统一到同一渲染做法，消除风格割裂。
  - 约束（方向 A）：**必须沿用现有 DOM 结构与 class**，只改"拼 DOM 的方式"，不改视觉；是否自研引擎由 `renderer-contract.md` 决定，不擅自铺开。

### 中优先级

- [ ] **`ach_sr.js` 移除 `loadAndRender` 中的 `var self = this` 死代码**
  - 现状：`self._loading` 挂到 `undefined`/全局，所谓加载去重实际未生效。
  - 目标：删除死代码，或真正实现 `state` 层面的去重。

- [ ] **搜索输入防抖**
  - 现状：SR/GI 每次键盘输入都全量重渲染列表，数据量大时可能卡顿。
  - 目标：加入 debounce，减少重渲染。

- [ ] **`ach_gi.js` 的 `.html()` 注入安全**
  - 现状：`<div class="ach-desc">').html(ach.desc)` 直接以 HTML 插入数据字段。
  - 目标：确认数据为纯文本则改用 `.text()`；确需富文本则显式声明并做清洗。

- [ ] **`loadAllGroups` 拼接顺序稳定**
  - 现状：并发 fetch 按完成顺序 `concat`，分组顺序可能与侧栏不一致。
  - 目标：按 `meta.groups` 顺序稳定输出。

- [ ] **统一 hash 参数格式**
  - 现状：GI 存 `group/ver/search/hide`；SR 只存 `group/ver`，且 SR `parseHash` 多了 `decodeURIComponent`。
  - 目标：统一编码与字段。

### 低优先级 / 可选

- [ ] 「新增视图」加载优化：SR 现先加载全部分组再按最新版本过滤，可改为按版本分片数据。
- [ ] `ach_gi.js` / `ach_sr.js` 高度重复，评估抽取公共层，仅差异化数据路径与 schema。
- [ ] 清理 `gi/CH/ach.js`、`sr/data/CH/Achievement.js` 等旧数据文件（若已无引用）。