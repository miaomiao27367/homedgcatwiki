# 成就页重构 — 阶段 1：勘查报告

> ⚠️ **本文件已过时（STALE）**
>
> 此文档为阶段 1 的勘查/规划报告，仅作历史参考，**不再代表当前实现**。
> 当前实际实现已偏离本文档内容：
> - 新脚本实际存放于 `javascripts/ach_gi.js` 与 `javascripts/ach_sr.js`（而非文中建议的 `gi/ach/page.ach.js`）。
> - 新数据格式为 `/gi/{lang3}/ach/ach.json` + `/gi/{lang3}/ach/groups/{id}.json`（GI）、`/sr/data/{lang3}/ach.json` + `/sr/data/{lang3}/ach/{id}.json`（SR），而非文中 `1.8` 描述的旧 `.ach.js`。
> - 实现细节与待办事项以 `docs/ach-todo.md`（TODO 文档）为准。

## 1. 公共框架接入点

### 1.1 页面入口 `gi/ach/index.html`

```
路径: C:\Users\Lenovo\Desktop\homdgcatwiki\homdgcatwiki\gi\ach\index.html
```

加载顺序（内容区可改部分为粗体）：

| 资源 | 路径 | 可否改动 |
|------|------|---------|
| jQuery | `/plugins/jquery.js` | 否（公共） |
| jquerysession | `/plugins/jquerysession.js` | 否（公共） |
| thin.js（弹层+render） | `/plugins/thin.js` | 否（公共） |
| ver.js（VER_GI, create_toolbar） | `/javascripts/ver.js` | 否（公共） |
| thin.css | `/stylesheets/thin.css` | 否（公共） |
| style_.css | `/stylesheets/style_.css` | 否（公共） |
| ach.css | `/stylesheets/ach.css` | **成就专用 CSS（可改/可新增）** |
| computerJson.js（computer_, init_title, lang3, bg_name） | `/javascripts/computerJson.js` | 否（公共） |
| **ach.js（成就逻辑）** | `/javascripts/ach.js` | **成就专用 JS（可替换）** |
| **数据文件** | `/gi/${lang3}/ach.js`（动态载入） | **成就数据（可替换/归档）** |

### 1.2 `init_title` 定义位置

**`computerJson.js:2773`** 和 **`txt.js:1524`**（两处定义相同）：

```javascript
function init_title(ttl) {
    document.title = ttl
    init_title_save = ttl
}
```

### 1.3 `switch_title` 定义位置

**`computerJson.js:2778`** 和 **`txt.js:1529`**（两处定义相同）：

```javascript
function switch_title(new_add) {
    document.title = new_add + ' ' + init_title_save
}
```

### 1.4 `poplayer` 定义位置

**`plugins/thin.js:1092`**：

```javascript
function poplayer(p) {
    // 创建 popmask → popdialog → popheader + closeicon + popbody
    // 支持 p.header, p.width, p.template, p.data, p.render, p.class, p.height, p.onclose
    // 使用 $(popcontainer).render(...) 渲染内容
}
```

### 1.5 `$(...).render` 定义位置

**`plugins/thin.js`**（jQuery 插件 `$.fn.extend`）。这是一个模板渲染引擎：
- 支持 `{data: [...], template: {...}}` 格式
- 支持 `[[field]]` 占位符
- 支持函数式模板

### 1.6 `computer_.MiscText` 成就相关字段

全部定义在 **`computerJson.js`**：

| 字段 | 行号 | 用途 |
|------|------|------|
| `PAGE_TITLE` | L32 | 页面标题后缀 |
| `Title` | L44 | 头部 Logo |
| `Subtitle` | L55 | 头部副标题 |
| `Translate_` | L67 | 语言切换链接 |
| `game_img` | L14 | 游戏图标+版本号前缀 |
| `Ach_Total` | L1177 | "总成就数" 文案 |
| `Ach_Table_Header` | L1182 | 分组表头 ["合辑","数量","原石"] |
| `Ach_All_Name` | L1199 | "全部成就" |
| `Ach_Extra` | L1204 | 弹层头部后缀 |
| `Ach_Inner_Header` | L1209 | 明细表头 ["奖励","成就","版本","总进度","隐藏"] |

### 1.7 变量取值

| 变量 | 来源 | 典型值 |
|------|------|--------|
| `imgpre` | `$('#IMGPRE').val()` → HTML `<input id="IMGPRE" value="/">` | `"/"` |
| `lang3` | `computerJson.js:2248` 先从 `#LANG` 取，再读 cookie | `"CH"` 或 `"EN"` 等 |
| `lang2` | `= lang3`，若非 CH/EN/RU 则强制 `"EN"` | `"CH"` 或 `"EN"` |
| `lang` | `= lang2`，RU 时降级为 `"EN"` | `"CH"` 或 `"EN"` |
| `bg_name` | `computerJson.js:2799` / `txt.js:1550`，默认 `'bg'`，`#NOLAZY` 时 `'bg_2'` | `'bg'` 或 `'bg_2'` |
| `VER_GI` | `ver.js` 从 `/manifest.json` 读取 | `"6.3"` |

### 1.8 数据文件

- **当前路径**：`/gi/${lang3}/ach.js`（脚本内部动态创建 `<script>` 加载）
- **CN 数据**：`/gi/CH/ach.js`（17167 行，含 `_AchievementData`、`_AchievementGroup`、`_Achievement` 三个全局变量）
- **EN 数据**：`/gi/EN/ach.js` **不存在**（只有 CH 版本）

> **注意**：`gi/` 下只有 `CH/` 目录，没有 `EN/`、`JP/`、`KR/` 等。意味着其他语言会 404 降级，但页面仍在工作（数据为空）。

---

## 2. 主题色使用情况

### 2.1 `#df903b`（强调色/选中态）

| 位置 | 用途 |
|------|------|
| `style_.css:672` | `.a_section` 类 |
| `style_.css:682` | 其他强调元素 |
| `style.css:58,82,92` | 通用强调色 |
| `monster-v2.css` | 多处边框/背景/文字（选中态） |
| `home.css:46,50` | 首页强调 |
| `ach.js:7` | `.tls` 语言标签着色 |
| `computerJson.js` | `Page` 文案中的颜色 |

### 2.2 `#FF0000`（数字强调）

在旧 `ach.js` 中用于总成就数字。其他页面用于数值强调。

### 2.3 `homdgcat-res/Csxylic/Primo.png`（原石图标）

仅出现在 **`javascripts/ach.js:244`**：

```javascript
img: imgpre + 'homdgcat-res/Csxylic/Primo.png'
```

---

## 3. 头部初始化（旧脚本第 1–30 行——必须逐行照搬）

```javascript
// L1: 获取 imgpre
var imgpre = $('#IMGPRE').val()

// L2-3: 设置页面标题
var ttl = (lang == 'CH') ? '成就' : 'Achievements'
init_title(ttl + ' ' + computer_.MiscText.PAGE_TITLE[lang])

// L4: 语言标签着色
$('.tls' + lang).css("color", "#df903b");

// L5-9: h3 内容渲染
$('h3 .title').html(computer_.MiscText.Title[lang] + "<color style='font-size: 26px;'><br>" + computer_.MiscText.game_img[lang] + VER_GI + "</b></color>");
$('h3 .subtitle').html(computer_.MiscText.Subtitle[lang]);
$('h3 .tlsub').html(computer_.MiscText.Translate_);
$('h3 .tlsub').hide()
$('h3 .links').render([
    { img: imgpre + 'images/menu.png', class: '_menu_' },
    { img: imgpre + 'images/translate.png', class: '_translate_' }
]);

// L10-14: 语言切换
$("body").on("click", ".tlsub", function () {
    if (lang == 'CH') $("a[data-id='EN']").click()
    if (lang == 'EN') $("a[data-id='CN']").click()
});

// 数据加载（通过动态创建 script 标签）
let script_computer = document.createElement('script')
script_computer.src = '/gi/' + lang3 + '/ach.js'
document.head.append(script_computer)
script_computer.onload = begin

// 在 begin() 末尾：
$('body').addClass(bg_name)
```

---

## 4. 新脚本路径建议

| 建议路径 | 说明 |
|---------|------|
| `javascripts/ach.js` | **不推荐** — 这是旧逻辑路径，直接覆盖无法回滚 |
| `javascripts/page.ach.js` | 可行 — 放在公共 JS 目录，与旧文件区分 |
| `gi/ach/page.ach.js` | **推荐** — 成就页专用，与数据目录同级，语义清晰 |

**选型决定**：使用 `gi/ach/page.ach.js`。理由：
- 与页面文件 `gi/ach/index.html` 同目录
- 与数据目录 `gi/ach/` 将来要放的数据同级
- 不和公共 `javascripts/` 混在一起

**HTML 需要修改**：将 `<script src="/javascripts/ach.js">` 改为 `<script src="/gi/ach/page.ach.js">`。

### 公共框架是否自动加载新脚本？

**否**。需要手动修改 `gi/ach/index.html` 中的 `<script>` src 指向。

---

## 5. 旧 CSS 注意事项

旧 `stylesheets/ach.css` 包含：

| 规则 | 用途 | 新设计是否保留 |
|------|------|-------------|
| `.ach-ver select` | 版本下拉样式 | 需要保留类似功能 |
| `.content` | 内容区背景 | 保留白色背景 |
| `popdialog / popheader / popbody` | 弹层样式 | **废弃**（不再弹层） |
| `.main-table` | 旧表格 | **废弃** |
| `.weapon-table / .weapon-head` | 旧明细表格 | **废弃** |
| `.jade` | 原石图标 | 需要保留类似样式 |
| `rotateX(180deg)` | 滚动反转 | **废弃** |

建议新建 `ach/ach.css` 或覆盖 `/stylesheets/ach.css`。

---

## 6. 关键发现

1. **数据只有 CH 版本**：`gi/CH/ach.js` 存在，`gi/EN/` 目录不存在。旧脚本动态加载 `${lang3}/ach.js` 在其他语言下会 404。
2. **`lang2` vs `lang` 区别**：`lang2` 保留原始语言代码（CH/EN/RU），`lang` 会把 RU 降级为 EN。文案索引用 `lang2`（例如 `Ach_Total[lang2]`）。
3. **旧脚本用弹层展示明细**：新设计改为右侧面板，需要完全重写交互逻辑。
4. **数据总量**：`_AchievementData[0].Data.TotalNum = 1675`，`TotalPrimo = 12830`，`_Achievement` 数组含数百条记录。
5. **分组 ID 范围**：0 ~ 66（非连续），共约 45 个分组。