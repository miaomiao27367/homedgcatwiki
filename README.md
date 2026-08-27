
# HomDGCat Wiki's Mirror

---

一个玉衡杯本地镜像，仅包含中文版本 仅个人学习使用

---

## 文件结构

```
homdgcatwiki/
├── server.bat              # Start HTTP server
├── server.py               # HTTP server
├── index.html              
├── gi/                     # Genshin Impact part
│   ├── CH/Avatar/          # data for characters
│   ├── CH/Relic/           # data for relics
│   ├── gcg/                # data for GCG cards
│   │   ├── index.html      # GCG browser entry
│   ├── 3boss/              # data for 3BOSS
│   └── ...
├── sr/                     # Star Rail part
│   ├── data/CH/            # data
│   └── ...
├── about/                  # about page
├── javascripts/            # JS scripts
│   ├── gcg.js              # GCG core logic
│   ├── char.js             # character page logic
│   ├── home.js             # home logic
│   ├── spine_char.js       # Spine animation component for characters
│   └── ...
├── stylesheets/            # CSS styles
├── plugins/                # third-party libraries (jQuery)
├── images/                 # image resources (gitignore)
├── spine/                  # Spine animation resources (gitignore)
└── fonts/                  # font files
```

---

## 怪物HP计算公式

前端JS（`EndgameEnemyWaveBoard` 的 `se` 函数）计算链：

```
HP = HPBase x HPModifyRatio x EliteGroup.HPRatio x HardLevelGroup.HPRatio x (1 + ParamList[1])
```

其中 `ParamList[1]` 来自 infinite wave 的 `param_list[1]`，Fiction（虚构叙事）所有楼层均走此路径。

Python端（`hsr_fiction_v2.py` / `hsr_chaos_v2.py`）与前端等价，但数据源不同：

| 前端 | Python |
|------|--------|
| API `monstervalue.json` → `HPBase` | `Monster.js` → `Stats.HP`（= HPBase/93 x HPModifyRatio） |
| API `HardLevelGroup.json` → `level` | `LevelCurves.js` → `level-1`（= HPRatio x 93） |

两者互相抵消，结果一致。Monster.js 精度略低，误差在百万分之0.06以内，可忽略。

Star模式（混沌/虚构）额外走 `param_list[1]`，倍率 = `1 + param_list[1]`，每个wave独立控制。`HPAdd` 字段仅作元数据记录，不参与计算。`HPCount` 仅用于前端显示（如 `HP x 2`），不乘入HP值。

详细追踪见 `reliance/` 目录下各 v2 脚本。