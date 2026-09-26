# Monster V2 技术文档

> 最后更新: 2026-09-26  
> 范围: monster-v2 页面 + V2_DATA 生成管线 + 前端改造 + 图片缓存 + Tools 集成

---

## 1. 架构总览

```
API (static.nanoka.cc)
  │  JSON: monster.json (索引) + zh/monster/{api_parent_id}.json (详情)
  │  WebP: assets/gi/{icon}.webp (图标)
  ▼
reliance/build_v2_data.py  ────→  gi/CH/monster-v2-data.js (V2_DATA)
reliance/update_v2_monster.py     (单 ID 增量更新 + 图标缓存)
  │
  ▼
javascripts/monster-v2.js  ────→  gi/monster-v2/index.html (用户页面)
manifest.json                      (版本标签 + diff 新怪物列表)
stylesheets/monster-v2.css         (页面样式)
```

---

## 2. 文件清单

### 核心程序

| 文件 | 用途 |
|------|------|
| `reliance/build_v2_data.py` | 全量构建 V2_DATA（API 直连，幂等） |
| `reliance/update_v2_monster.py` | 单 ID 增量更新 + 图标自动缓存 |
| `reliance/v2_build_utils.py` | 公共模块（两个脚本共用的函数/常量） |
| `javascripts/monster-v2.js` | v2 前端页面（读取 V2_DATA，渲染 UI） |
| `stylesheets/monster-v2.css` | v2 页面样式（从 `javascripts/` 移入标准位置） |
| `manifest.json` | `gi.Current_Ver` 版本号 + `gi.diff.monster` 新怪物列表 |
| `server.py` | `/gi_monster_v2_update` + `/gi_monster_v2_cache_icons` 路由 |
| `javascripts/tools.js` | `sendGIMonsterV2Update` + `sendGIMonsterV2CacheImg` 前端处理 |

### 数据文件

| 文件 | 用途 |
|------|------|
| `gi/CH/monster-v2-data.js` | V2_DATA 输出（≈1.9MB，含 List + Variants + Kingdoms...） |
| `gi/CH/computer.js` | 老数据源（_Monsters / _Kingdoms / LevelCurves / _computer_） |
| `homdgcat-res/monster/` | 怪物图标缓存（webp → PNG，从 API CDN 下载） |
| `reliance/output/api_cache/` | API 响应缓存（JSON，避免重复下载） |
| `reliance/output/suffix_map.json` | Suffix 映射表（API 原始后缀 → 中文显示名） |
| `reliance/output/coefficients.json` | HP/ATK 归一化系数 |

### 已归档

| 原路径 | 归档位置 |
|--------|----------|
| `reliance/monster_data/` | `_archive/monster_data/` |
| `gi/CH/monster-variants.js` | `_archive/monster-variants.js` |

---

## 3. V2_DATA 结构

```javascript
window.V2_DATA = {
  List: {              // 父怪列表（513 条，以本地 key 为索引）
    "101": { _id, Name, Title: ["标题"], Icon: ["UI_MonsterIcon_..."], Color, HP, HPCurve, ATK, ATKCurve, RESBase, Immune, ... }
  },
  Variants: {          // 变种表（1350 条，以 API child_id 为索引）
    "10101": { _id, ParentId, Suffix, HP, HPCurve, ATK, ATKCurve, RESBase, Immune, ... }
  },
  Kingdoms: [          // 分类体系（13 个王国，含 Classes → Monsters[]）
    { ID, Name, Classes: [{ Name, Monsters: [mid, ...] }] }
    // 第 13 个为"友善生物"（动物类怪物）
    // ★ Class 的 Name 来自 API title 字段（子分类名），不是本地 Title
  ],
  LevelCurves: {       // 等级曲线（200 级 × N 条曲线）
    "100": { "1": 123.45, "2": 67.89, ... }
  },
  Tuts: {},            // 教程数据
  Tutorials: {},       // 文本数据
  VariantIndex: {}     // 可选：pid → [cid, cid, ...] 索引
};
```

> **重要**：`Title` 和 `Icon` 字段必须是数组格式（如 `["值"]` / `[]`），前端用 `.forEach` 和 `.length` / `[index]` 取值。

### 子分类（Class）归属机制

**怪物本身没有"属于哪个 Class"的字段。** 归属关系存储在 `V2_DATA.Kingdoms` 的顶层树形结构中：

```javascript
Kingdoms: [
  {
    ID: 6,
    Name: "异种魔兽",      // Kingdom 名（computer.js 本地手工维护）
    Classes: [
      { Name: "残体合成造兽", Monsters: [63107] },  // Class 名 = API title
      { Name: "鸟身蛇尾的裂壳者", Monsters: [63108] },
    ]
  }
]
```

前端渲染：遍历 Kingdoms → Classes → Monsters[]，用 mid 去 V2_DATA.List 查找卡片数据。

**一个怪物属于哪个 Class，取决于它出现在哪个 `Classes[].Monsters[]` 列表中，跟 List 条目内部没有关联字段。**

### API 字段 ↔ 本地归属映射

| API 字段 | 映射到 | 示例 |
|----------|--------|------|
| `codex` | Kingdom ID（`CODEX_TO_KINGDOM`） | `ELEMENTAL` → Kingdom 0「元素生命」 |
| `title` | Class 名（子分类） | `"残体合成造兽"` |
| `name` | `V2_DATA.List[*].Name` | `"嵌合鳄蹄兽"` |
| `desc` | `V2_DATA.List[*].Desc` | 描述文本 |
| `icon` | `V2_DATA.List[*].Icon[0]` | `"UI_MonsterIcon_..."` |

`update_v2_monster.py` 的 `auto_assign_kingdom()` 自动从 API `codex` → Kingdom ID、API `title` → Class 名，写入 V2_DATA.Kingdoms 和 computer.js。

### 字段区分对照

| 名称 | 来源 | 存入位置 | 说明 |
|------|------|----------|------|
| API `title` | API detail | `Kingdoms[*].Classes[*].Name` | **子分类名**，如"残体合成造兽" |
| API `special_names` | API detail | 未使用 | 如"无神智的游荡者" |
| 本地 `Title` | local `_Monsters` | `List[*].Title` | 详情页标题数组，本地手工维护 |
| API `name` | API detail | `List[*].Name` | 怪物显示名 |
| API `codex` | API detail | → Kingdom ID | 上级分类映射 |

### 字段来源优先级

| 优先级 | 来源 | 说明 |
|--------|------|------|
| 1 | 本地 `_Monsters` | 本地有值用本地 |
| 2 | API 原始 JSON | 本地无值用 API |
| 3 | null | 都无值用 null |

- **RESBase**: 本地父层 + API child.sub_hurt 展开的**并集**
- **变种 HP/HPCurve**: 优先 API，父曲线 = 7/20/40 时强制用父值
- **变种 ATK/ATKCurve**: 同上
- **01 变种 HP/ATK**: 直接抄本地父值（P0-2 规则）
- **纯 API 怪物**（无本地 `_Monsters` 数据）：Title / Icon 从 API 取值时须包装为数组，Desc / Name 直接取字符串

### Suffix 规则

- API `monster_name` 去掉父怪名前缀 → 得到原始 suffix
- 白名单内（`_StimulatedAI` → "简化AI" 等）→ 显示中文
- 白名单外 → `Suffix = ""`（归零，显示为"基础"）
- 白名单定义在 `reliance/output/suffix_map.json`

---

## 4. 前端改造（monster-v2.js）

### 已完成的改造

| 改造项 | 说明 |
|--------|------|
| 动态加载 | 只加载 `monster-v2-data.js` + `manifest.json`，失败兜底 |
| 全局变量 | `_Monsters`→`V2_DATA.List`，`_Kingdoms`→`V2_DATA.Kingdoms`，`_Tuts`→`V2_DATA.Tuts`，`_Tutorials`→`V2_DATA.Tutorials` |
| buildDisplayData | 删除，替换为 `getMonsterData(pid, cid)` + `getVariantsForParent(pid)` |
| 变种名 | 用 Suffix 字段：`""` → "基础"，非空 → 显示 Suffix |
| info bar | 显示 "父名 · Suffix" 或只显示父名 |
| 默认变种 | 选 Suffix==="" 的（而非 id.endsWith('01')） |
| 无变种父怪 | 不显示变种区块，单形态处理 |
| 变种卡片 HP/ATK | 用等级曲线计算（`state.level` × `state.mul`），实时更新 |
| MUL 倍率 | 新增 `state.mul`，默认 3.75，calc-bar 有输入框 |
| 详情页 HP/ATK | 纯数字，去掉"丘丘"/"野伏"等曲线单位后缀 |
| 减抗去重 | calc-bar 删掉重复的减抗输入框（归等效血量区管理） |
| 版本标签 | `<b>6.3</b>` 分类名用 `manifest.json` 的 `Current_Ver` 动态替换 |
| 新怪物列表 | `<b>6.3</b>` 分类下不遍历 Kingdoms.Classes，改用 `diff.monster` 从 List 实时查找渲染 |
| 友善生物 | HP=null 时卡片/详情显示"友善生物"，`calcStatValue` 提前返回 null |

### 版本标签机制

```
manifest.json  ──加载──►  diffMonsters = [901, 51346, 63107, ...]
                          currentVer   = "7.1v4"

renderKingdoms()  →  kingdom.Name === '<b>6.3</b>' → 显示 currentVer

renderMonsters(kingdom):
  if kingdom.Name === '<b>6.3</b>':
    遍历 diffMonsters → V2_DATA.List[mid] → 渲染卡片
    (不读 Kingdoms.Classes 的硬编码列表)
```

### 计算公式

```
HP  = LevelCurves[state.level][curve] × data.HP  × state.mul
ATK = LevelCurves[state.level][curve] × data.ATK × state.mul
```

> 动物类怪物 HP/ATK 为 null 时 `calcStatValue` 返回 null，`formatHpAtk` / `formatHpQuick` 显示"友善生物"。

### man 状态

```
state = {
  kingdomId, selectedId, currentChildId, curKingdom,
  panelOpen: false,
  level: 100,
  resDecrease: 0,
  mul: 3.75,
  effHpCalc: null
}
```

---

## 5. 图片缓存管线

### 流程

```
static.nanoka.cc/assets/gi/{icon}.webp
  │  requests GET (timeout 30s)
  ▼
PIL Image.open(BytesIO(content))
  │  .save(path, "PNG")
  ▼
homdgcat-res/monster/{icon}.png
  │  getIconUrl() → /homdgcat-res/monster/{icon}.png
  ▼
前端 <img> 标签
```

### 入口

| 入口 | 触发方式 | 修改 V2_DATA？ |
|------|---------|---------------|
| `update_single_monster()` | 数据更新后自动 | ✅ 是 |
| `cache_icons_for_monster()` | Tools 界面单独调用 | ❌ 否 |
| CLI: `python -c "...cache_icons_for_monster('63107')"` | 命令行 | ❌ 否 |

### 特性

- 幂等：图标已存在则跳过（不重复下载）
- 容错：下载失败不阻断流程，只打日志
- 目录自动创建：`os.makedirs(icon_dir, exist_ok=True)`

---

## 6. Tools 界面集成

### 侧边栏

```
GI 怪物V2更新        ← 数据更新 + 自动缓存图标
```

### GI 怪物V2数据更新工具

```
[怪物ID]  [API版本号]  [跳过缓存]
[发送更新请求]
──── 结果 ────

────────────── (分割线)
怪物图标缓存
[怪物ID (可复用上方ID)]
[缓存图标]
──── 结果 ────
```

### API 路由

| 路由 | 调用函数 | 操作 |
|------|---------|------|
| POST `/gi_monster_v2_update` | `update_single_monster()` | 更新数据 + 自动缓存图标 |
| POST `/gi_monster_v2_cache_icons` | `cache_icons_for_monster()` | 仅下载图标，不修改数据 |

---

## 7. 常用命令

```powershell
# 全量构建
python reliance\build_v2_data.py

# 单 ID 增量更新（按 API child ID）
python reliance\update_v2_monster.py 20010101

# 按本地 key 更新
python reliance\update_v2_monster.py 101

# 强制跳过 API 缓存
python reliance\update_v2_monster.py 101 --force

# 指定 API 版本
python reliance\update_v2_monster.py 101 --api-version 7.2.0

# 独立图标缓存（不动数据）
python -c "from reliance.update_v2_monster import cache_icons_for_monster; cache_icons_for_monster('20010101')"
```

---

## 8. 数据保全自检

1. 输出 513 个 List 条目 ✓
2. 1350 个变种 Variants 条目 ✓
3. 本地父怪 vs API 匹配：299 找到 / 214 未找到（含 6 个纯 API 新怪物 + 2 个动物）
4. 无孤儿变种或无父 Variants ✓
5. RESBase 为本地 + API 并集 ✓
6. HPCurve=7/20 继承正确 ✓
7. 纯 API 怪物 Title/Icon 为数组格式 ✓
8. 图标缓存命中（已存在则跳过） ✓

---

## 9. 验证命令

```powershell
# 确认 monster-v2.js 无旧引用
grep -rn "_Monsters\|_MonsterVariants\|buildDisplayData\|getCurveUnit\|_computer_" javascripts/monster-v2.js

# 确认旧资源未加载
# 打开 /gi/monster-v2/ → Network 面板 → 只应出现 monster-v2-data.js

# 验证 Title/Icon 数组格式
python -c "import json;f=open('gi/CH/monster-v2-data.js',encoding='utf-8');raw=f.read();idx=raw.index('var V2_DATA = ');data=json.loads(raw[raw.index('{',idx):].rstrip(';')); bad=[k for k,v in data['List'].items() if not isinstance(v.get('Title'),list)]; print('Bad Title:',bad or 'None')"

# 幂等性验证
python reliance/build_v2_data.py && python reliance/build_v2_data.py
# 两次输出 md5 应一致
```

---

## 10. 已知数据特征

| 项目 | 数值 |
|------|------|
| 父怪总数（List） | 513 |
| 变种总数（Variants） | 1350 |
| API 能找到的父怪 | 299 |
| API 找不到的父怪 | 214（纯本地 + 6 纯 API 新增 + 动物） |
| 王国数 | 13（含"友善生物"） |
| LevelCurves 等级数 | 200 |
| API 版本 | 7.1.50 |
| Current_Ver | 7.1v4 |
| 默认 MUL | 3.75（多人模式倍率） |
| 输出文件大小 | ≈1.9MB |

---

## 11. 规定/铁律

1. **只改 reliance/ 脚本**，不动 `gi/CH/computer.js` 等老数据文件
2. **只改 monster-v2.js**，不动 UI 结构（HTML/CSS）
3. **不动老页面** `/gi/monster`，保持回归兼容
4. 幂等：同一套输入多次运行输出一致
5. 断点续跑：`update_v2_monster.py` 只改指定怪物条目
6. 数据源以 API 原始 JSON 为准，本地优先补充
7. **Title / Icon 必须是数组**：纯 API 怪物回填时必须 `[value]` 包装，不能存裸字符串
8. 图片缓存位置固定为 `homdgcat-res/monster/`，webp 转 png