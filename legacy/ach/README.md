# Legacy: SR 成就页旧实现归档

## 文件清单

```
legacy/ach/
├── achsr.js                # 旧逻辑脚本（原 /javascripts/achsr.js）
├── data/
│   └── CH/
│       └── Achievement.js  # 旧数据脚本（原 /sr/data/CH/Achievement.js）
└── README.md               # 本文件
```

## 原路径

| 归档文件 | 原路径 | 说明 |
|---------|--------|------|
| achsr.js | `/javascripts/achsr.js` | 成就页逻辑：数据加载、卡片墙渲染、弹层、版本筛选 |
| data/CH/Achievement.js | `/sr/data/CH/Achievement.js` | 成就数据：`_achievementdata`、`_achievementvers`、`_achievement`、`_option`、`_achievementseries` |

## 新路径

| 新文件 | 路径 | 说明 |
|-------|------|------|
| 新逻辑 | `/javascripts/achsr.js` | 重写为左侧分组栏 + 右侧列表布局 |
| JSON 主数据 | `/sr/data/{lang}/ach.json` | 清单文件：版本、分组、统计 |
| JSON 分组数据 | `/sr/data/{lang}/ach/{seriesId}.json` | 按分组拆分的成就明细 |
| 更新脚本 | `/reliance/sr/ach/update.py` | 从 API 生成 JSON 数据 |
| 转换脚本 | `/reliance/sr/ach/convert_legacy.py` | 从旧 JS 转换为 JSON（一次性） |

## 回滚步骤

### 场景 A：新逻辑有问题，需恢复旧逻辑

1. **恢复逻辑脚本**：
   ```bash
   copy legacy\ach\achsr.js javascripts\achsr.js
   ```

2. **清除 localStorage**（如有新版本缓存冲突）：
   浏览器开发者工具 → Application → Local Storage → 清除 `ach:sr:done`

### 场景 B：只需恢复旧数据

1. **恢复数据文件**：
   ```bash
   copy legacy\ach\data\CH\Achievement.js sr\data\CH\Achievement.js
   ```

### 场景 C：全量回滚（新数据 + 新逻辑全部撤回）

1. **恢复旧逻辑**：同场景 A
2. **恢复旧数据**：同场景 B
3. **删除新文件**（可选）：
   ```bash
   rmdir /s /q sr\data\CH\ach
   del sr\data\CH\ach.json
   ```

## 数据格式差异

### 旧格式（JS 全局变量）

```javascript
// 通过 <script src="/sr/data/CH/Achievement.js"> 加载
var _achievementdata = [3.8, 1563, 3.7, 1538]
var _achievementvers = ["3.8", "3.7", ...]
var _achievement = [
  { "_id": 4010101, "Ver": 1.0, "Series": 1, "Name": "...", "Desc": "...", "Reward": 20 },
  ...
]
var _option = ["全部", "3.8", "3.7", ...]
var _achievementseries = [
  { "_id": 1, "Name": "我，开拓者", "Icon": "CultivateAchievementIcon.png", "Count": 24 },
  ...
]
```

### 新格式（JSON 静态文件）

```json
// sr/data/CH/ach.json（清单）
{
  "updatedAt": "",
  "latestVersion": "3.8",
  "totalNum": 1563,
  "prevVersion": "3.7",
  "prevTotalNum": 1538,
  "totalReward": 9295,
  "versions": ["3.8", "3.7", ...],
  "groups": [
    { "id": 1, "name": "我，开拓者", "icon": "CultivateAchievementIcon.png", "num": 24, "reward": 335 },
    ...
  ]
}

// sr/data/CH/ach/1.json（分组明细）
[
  { "id": 4010101, "name": "炽燃不灭的琥珀", "desc": "...", "ver": "1.0", "reward": 20 },
  ...
]
```

### 主要变化

- `Ver` 字段从浮点数改为字符串（`1.0` → `"1.0"`）
- `Series` 字段移除（文件本身即分组）
- 分组图标 `Icon` 保留在 `ach.json.groups[i].icon`
- 无 `hidden` 字段（SR 没有隐藏成就）