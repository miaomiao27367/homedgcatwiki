# 成就页维护记录

> 成就页（GI / SR）当前实现状态与遗留事项。
> 以当前代码和存储为准。
>
> **方向基线：见 `docs/project-vision.md`。** 两页为独立实现（ach_sr=thin 模板、ach_gi=jQuery 拼接），
> 不强求统一写法，仅保证显示一致；改动须遵守「保留存量 DOM/class、视觉可复原」约束。

## 现状快照

| 游戏 | 页面入口 | 脚本 | 范式 | 状态 |
|------|---------|------|------|------|
| GI | `gi/ach/index.html` | `javascripts/ach_gi.js` | jQuery 拼接 | ✅ 页面引用正常 |
| SR | `sr/ach/index.html` | `javascripts/ach_sr.js` | thin 模板 | ✅ 页面引用正常 |

### 数据存储

| 游戏 | 元数据 | 分组明细 | 字段 |
|------|--------|---------|------|
| GI | `/gi/CH/ach/ach.json` | `/gi/CH/ach/groups/{id}.json`（0~66） | meta: `totalNum/totalPrimo/versions/groups(id,name,num,reward)`；成就: `id/name/desc/ver/hidden/reward/total` |
| SR | `/sr/data/CH/ach.json` | `/sr/data/CH/ach/{1..9}.json` | meta: `latestVersion/prevVersion/totalNum/prevTotalNum/versions/groups(id,name,icon,num)`；成就: `id/name/desc/ver/reward` |

> 注：目前仅存在 `CH` 语言数据，其他语言会 404（脚本已带 `.fail()` 提示）。

### 已实现功能

- 分组侧栏（含「全部」；SR 另有「新增」视图）；SR 侧栏顶部显示最新/上一版本总成就数
- 搜索（匹配 name + desc，均已防抖）
- 版本过滤下拉
- 隐藏成就开关（GI）
- 勾选完成进度（localStorage 持久化）
- URL hash 状态存取 / 恢复；浏览器前进/后退同步（两页均已实现 `hashchange`）
- 数据加载 `.fail()` 提示（两页）
- GI 成就描述富文本白名单清洗（仅放行 `<color>`/`<b>`）
- GI 全部视图按 `meta.groups` 顺序稳定拼接
- GI 兼容旧版隐式 `#ID` 传参

## 遗留事项

### 数据 / 决策层（非代码逻辑）

- [ ] **非 CH 语言数据**：除 `CH` 外无其他语言 `ach.json` / 分组数据。脚本侧 `.fail()` 已避免静默空白；是否补充多语言数据或明确降级策略，属数据/产品决策，未定案。

### 可选优化

- [ ] SR「新增视图」加载优化：现先加载全部分组再按最新版本过滤，可改为按版本分片数据。
- [ ] 清理旧数据文件（`gi/CH/ach.js`、`sr/data/CH/Achievement.js` 等）：`scripts/update-ach.js` / `convert-ach.js` 仍有引用，需确认无页面依赖后再删。

---

> 说明：代码层主要收尾已完成（hashchange、fail 处理、死代码、防抖、富文本清洗、分组顺序稳定、摘要移位）。
> 本记录仅保留仍未定案的数据/决策层事项，供后续维护参考。