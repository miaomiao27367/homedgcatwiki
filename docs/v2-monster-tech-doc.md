# Monster V2 技术文档

> 最后更新: 2026-09-25  
> 范围: monster-v2 页面 + V2_DATA 生成管线 + 前端改造

---

## 1. 架构总览

```
API (static.nanoka.cc)
  │  JSON: monster.json (索引) + zh/monster/{api_parent_id}.json (详情)
  ▼
reliance/build_v2_data.py  ────→  gi/CH/monster-v2-data.js (V2_DATA)
reliance/update_v2_monster.py     (单 ID 增量更新)
  │
  ▼
javascripts/monster-v2.js  ────→  gi/monster-v2/index.html (用户页面)
```

---

## 2. 文件清单

### 核心程序（保留，不动老文件）

| 文件 | 用途 |
|------|------|
| `reliance/build_v2_data.py` | 全量构建 V2_DATA（API 直连，幂等） |
| `reliance/update_v2_monster.py` | 单 ID 增量更新（按本地 key 或 API child ID） |
| `reliance/v2_build_utils.py` | 公共模块（两个脚本共用的函数/常量） |
| `javascripts/monster-v2.js` | v2 前端页面（读取 V2_DATA，渲染 UI） |

### 数据文件

| 文件 | 用途 |
|------|------|
| `gi/CH/monster-v2-data.js` | V2_DATA 输出（≈1.9MB，含 List + Variants + Kingdoms...） |
| `gi/CH/computer.js` | 老数据源（_Monsters / _Kingdoms / LevelCurves / _computer_） |
| `reliance/output/api_cache/` | API 响应缓存（~194 个 JSON，避免重复下载） |
| `reliance/output/suffix_map.json` | Suffix 映射表（API 原始后缀 → 中文显示名） |
| `reliance/output/coefficients.json` | HP/ATK 归一化系数（阶段 A 校准记录） |

### 已归档

| 原路径 | 归档位置 |
|--------|----------|
| `reliance/monster_data/` | `_archive/monster_data/` |
| `gi/CH/monster-variants.js` | `_archive/monster-variants.js` |

---

## 3. V2_DATA 结构

```javascript
window.V2_DATA = {
  List: {              // 父怪列表（507 条，以本地 _Monsters key 为索引）
    "101": { _id, Name, Icon, Color, HP, HPCurve, ATK, ATKCurve, RESBase, Immune, ... }
  },
  Variants: {          // 变种表（1338 条，以 API child_id 为索引）
    "10101": { _id, ParentId, Suffix, HP, HPCurve, ATK, ATKCurve, RESBase, Immune, ... }
  },
  Kingdoms: [          // 分类体系（12 个王国，含 Classes → Monsters[]）
    { Name, Classes: [{ Name, Monsters: [mid, ...] }] }
  ],
  LevelCurves: {       // 等级曲线（200 级 × N 条曲线）
    "100": { "1": 123.45, "2": 67.89, ... }
  },
  Tuts: {},            // 教程数据
  Tutorials: {},       // 文本数据
  VariantIndex: {}     // 可选：pid → [cid, cid, ...] 索引
};
```

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
| 动态加载 | 只加载 `monster-v2-data.js`，失败兜底空 V2_DATA |
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

### 计算公式

```
HP  = LevelCurves[state.level][curve] × data.HP  × state.mul
ATK = LevelCurves[state.level][curve] × data.ATK × state.mul
```

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

## 5. 常用命令

```powershell
# 全量构建
cd reliance; python build_v2_data.py

# 单 ID 更新（按本地 key）
python update_v2_monster.py --local-key 101

# 单 ID 更新（按 API child ID）
python update_v2_monster.py --child-id 10101

# 强制重新下载 API（不走缓存）
python update_v2_monster.py --local-key 101 --no-cache

# 指定 API 版本
python update_v2_monster.py --local-key 101 --api-version 7.2.0
```

---

## 6. 数据保全自检（build_v2_data.py 内置）

1. 输出 507 个 List 条目 ✓
2. 1338 个变种 Variants 条目 ✓
3. 本地 507 个父怪 vs API 299 个找到 / 208 个未找到 ✓
4. 无孤儿变种或无父 Variants ✓
5. RESBase 为本地 + API 并集 ✓
6. HPCurve=7/20 继承正确 ✓

---

## 7. 验证命令

```powershell
# 确认 monster-v2.js 无旧引用
grep -rn "_Monsters\|_MonsterVariants\|buildDisplayData\|getCurveUnit\|_computer_" javascripts/monster-v2.js

# 确认旧资源未加载
# 打开 /gi/monster-v2/ → Network 面板 → 只应出现 monster-v2-data.js

# 幂等性验证
python reliance/build_v2_data.py && python reliance/build_v2_data.py
# 两次输出 md5 应一致
```

---

## 8. 已知数据特征

| 项目 | 数值 |
|------|------|
| 父怪总数（List） | 507 |
| 变种总数（Variants） | 1,338 |
| API 能找到的父怪 | 299 |
| API 找不到的父怪 | 208（纯本地数据，无变种） |
| 王国数 | 12 |
| LevelCurves 等级数 | 200 |
| API 版本 | 7.1.50 |
| 默认 MUL | 3.75（多人模式倍率） |
| 输出文件大小 | ≈1.9MB |

---

## 9. 规定/铁律

1. **只改 reliance/ 脚本**，不动 `gi/CH/computer.js` 等老数据文件
2. **只改 monster-v2.js**，不动 UI 结构（HTML/CSS）
3. **不动老页面** `/gi/monster`，保持回归兼容
4. 幂等：同一套输入多次运行输出一致
5. 断点续跑：`update_v2_monster.py` 只改指定怪物条目
6. 数据源以 API 原始 JSON 为准，本地优先补充