# Legacy: 成就页旧实现归档

## 文件清单

```
legacy/ach/
├── page.ach.js          # 旧逻辑脚本（原 /javascripts/ach.js）
├── data/
│   └── CH.js            # 旧数据脚本（原 /gi/CH/ach.js）
└── README.md            # 本文件
```

## 原路径

| 归档文件 | 原路径 | 说明 |
|---------|--------|------|
| page.ach.js | `/javascripts/ach.js` | 成就页逻辑：数据加载、表格渲染、弹层、筛选 |
| data/CH.js | `/gi/CH/ach.js` | 成就数据：`_AchievementData`、`_AchievementGroup`、`_Achievement` |

## 回滚步骤

### 场景 A：新逻辑有问题，需恢复旧逻辑

1. **恢复逻辑脚本**：
   ```bash
   copy legacy\ach\page.ach.js javascripts\ach.js
   ```

2. **恢复 HTML 引用**（如果已修改）：
   打开 `gi/ach/index.html`，确保：
   ```html
   <script src="/javascripts/ach.js" type="text/javascript"></script>
   ```
   （而不是指向新脚本路径）

3. **清除 localStorage**（如果有新版本缓存导致冲突）：
   浏览器开发者工具 → Application → Local Storage → 清除

### 场景 B：只需恢复旧数据

1. **恢复数据文件**：
   ```bash
   copy legacy\ach\data\CH.js gi\CH\ach.js
   ```

### 场景 C：全量回滚（新数据+新逻辑全部撤回）

1. **恢复旧数据**：同场景 B
2. **恢复旧逻辑**：同场景 A
3. **删除新文件**（可选）：
   ```bash
   rmdir /s /q ach
   rmdir /s /q scripts
   ```

## 旧数据格式说明

旧数据使用 JS 全局变量，通过 `<script>` 标签直接加载：

```javascript
// gi/CH/ach.js（自动生成）
var _AchievementData = [{ "_id": 0, "Data": { "TotalNum": 1675, ... } }]
var _AchievementGroup = [{ "_id": 0, "Name": "天地万象", "Num": 890, "Reward": 5065 }, ...]
var _Achievement = [
  { "_id": 85006, "Group": 0, "Name": "...", "Desc": "...", "Ver": "6.0", "Hidden": true, "Reward": 5, "Total": 1 },
  ...
]
```

## 旧逻辑流程

1. `$(function(){...})` 页面加载后执行
2. 获取 `imgpre`、调用 `init_title`、渲染 `h3` 标题
3. 动态创建 `<script>` 加载 `/${lang3}/ach.js`
4. 加载完成后调用 `begin()`：
   - 提取版本列表 `verlist_include`
   - 渲染左侧分组表格（`.main-table`）
   - 点击分组时调用 `popAch()` 弹层显示明细
   - 弹层内使用 `achTable()` 渲染 `.weapon-table`
   - 版本下拉筛选
5. `$('body').addClass(bg_name)` 设置背景