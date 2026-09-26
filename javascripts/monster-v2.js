$(function () {

    var imgpre = $('#IMGPRE').val();
    var MONSTERID = $('#MONSTERID').val();

    // ============ 2. 页面头部 ============
    init_title(computer_.MiscText.PAGE_TITLE[lang]);
    $('h3 .title').html(computer_.MiscText.ComputerTitle[lang] + "<color style='font-size: 26px;'><br>" + computer_.MiscText.game_img[lang] + VER_GI + "</b></color>");
    $('h3 .subtitle').html(computer_.MiscText.Subtitle[lang]);
    $('h3 .tlsub').html(computer_.MiscText.Translate_);
    $('h3 .tlsub').hide();
    $('h3 .links').render([
        { img: imgpre + 'images/menu.png', class: '_menu_' },
        { img: imgpre + 'images/translate.png', class: '_translate_' }
    ]);

    // ============ 3. 加载数据 ============
    var script1 = document.createElement('script');
    script1.src = '/gi/' + lang3 + '/monster-v2-data.js';
    document.head.append(script1);
    script1.onload = begin;
    script1.onerror = function () {
        window.V2_DATA = { List: {}, Variants: {}, Kingdoms: [], LevelCurves: {}, Tuts: {}, Tutorials: {} };
        begin();
    };

    // ============ 4. 状态管理 ============
    var state = {
        search: '',
        kingdomId: null,
        selectedId: null,
        currentChildId: null,
        curKingdom: null,
        panelOpen: false,
        level: 100,
        resDecrease: 0,
        mul: 3.75,
        effHpCalc: null      // { hp, resDecrease } when active
    };

    var diffMonsters = [];
    var currentVer = (typeof VER_GI !== 'undefined') ? VER_GI : '6.3';

    function setState(patch) {
        Object.assign(state, patch);
    }

    // ============ 5. 纯函数：抗性→等效血量 ============
    function rescoeff(r) {
        if (r < 0) { return 1 - r / 2; }
        else if (r > 0.75) { return 1 / (4 * r + 1); }
        else { return 1 - r; }
    }

    function res(baseVal, redPct) {
        return rescoeff(0.1 - redPct) / rescoeff(baseVal - redPct);
    }

    // ============ 6. 主逻辑 ============};

    function begin() {
        $('body').addClass(bg_name);
        $('#monster_card_area_2').hide();

        fetch('/manifest.json')
            .then(function (r) { return r.json(); })
            .then(function (manifest) {
                if (manifest.gi && manifest.gi.diff && manifest.gi.diff.monster) {
                    diffMonsters = manifest.gi.diff.monster;
                }
                if (manifest.gi && manifest.gi.Current_Ver) {
                    currentVer = manifest.gi.Current_Ver;
                }
                _beginRender();
            })
            .catch(function () {
                _beginRender();
            });
    }

    function _beginRender() {
        initSearchBar();
        renderKingdoms();
        bindDetailPanelEvents();

        if (MONSTERID) {
            var kdm = findKingdomId(MONSTERID);
            if (kdm === -1) { selectKingdom(0); }
            else { var idx = kingdomIndexById(kdm); selectKingdom(idx >= 0 ? idx : 0); }
        } else { selectKingdom(0); }

        $(document).on('keydown', function (e) {
            if (e.key === 'Escape' && state.panelOpen) { closeDetailPanel(); }
        });
    }

    // ============ 7. 搜索栏 ============
    function initSearchBar() {
        var toolbar = document.createElement('div');
        toolbar.className = 'mv2-toolbar';
        var wrap = document.createElement('div');
        wrap.className = 'mv2-search-wrap';

        var input = document.createElement('input');
        input.type = 'text';
        input.className = 'mv2-search-input';
        input.placeholder = (lang === 'CH' ? '搜索怪物名或ID...' : 'Search name or ID...');

        var clearBtn = document.createElement('button');
        clearBtn.className = 'mv2-search-clear';
        clearBtn.textContent = '\u2715';

        wrap.appendChild(input);
        wrap.appendChild(clearBtn);

        var kingdomEl = $('.kingdom')[0];
        if (kingdomEl && kingdomEl.parentNode) {
            kingdomEl.parentNode.insertBefore(toolbar, kingdomEl.nextSibling);
        }
        toolbar.appendChild(wrap);

        var searchTimer = null;
        input.addEventListener('input', function () {
            var q = input.value.trim();
            clearBtn.classList.toggle('visible', q.length > 0);
            clearTimeout(searchTimer);
            searchTimer = setTimeout(function () { doSearch(q); }, 200);
        });

        clearBtn.addEventListener('click', function () {
            input.value = '';
            clearBtn.classList.remove('visible');
            doSearch('');
            var idx = state.kingdomId ? kingdomIndexById(state.kingdomId) : 0;
            selectKingdom(idx >= 0 ? idx : 0);
        });
    }

    function doSearch(query) {
        setState({ search: query });
        var area = $('#monster_card_area_1');
        area.empty();

        if (!query) {
            var idx = state.kingdomId ? kingdomIndexById(state.kingdomId) : 0;
            if (idx >= 0) { selectKingdom(idx); }
            return;
        }

        var qLower = query.toLowerCase();
        var results = [];
        for (var id in V2_DATA.List) {
            if (!V2_DATA.List.hasOwnProperty(id)) continue;
            var m = V2_DATA.List[id];
            if ((m.Name && m.Name.toLowerCase().indexOf(qLower) !== -1) || String(m._id).indexOf(query) !== -1) {
                results.push(m);
            }
            if (results.length >= 100) break;
        }

        if (results.length === 0) {
            var noResult = document.createElement('div');
            noResult.className = 'mv2-no-result';
            noResult.textContent = (lang === 'CH' ? '未找到相关怪物' : 'No monsters found');
            area.append(noResult);
            return;
        }

        var header = document.createElement('div');
        header.style.cssText = 'padding:6px 0;color:#999;font-size:13px';
        header.textContent = (lang === 'CH' ? '搜索结果: ' : 'Results: ') + results.length;
        area.append(header);

        var gridWrap = document.createElement('div');
        gridWrap.className = 'mv2-grid-wrap';
        results.forEach(function (m) { gridWrap.appendChild(buildCard(m)); });
        area.append(gridWrap);
    }

    // ============ 8. 分类按钮 ============
    function renderKingdoms() {
        var container = $('.kingdom');
        container.empty();
        V2_DATA.Kingdoms.forEach(function (kd) {
            var btn = document.createElement('kingdom');
            var link = document.createElement('a');
            link.setAttribute('data-id', kd.ID);
            link.className = 'kingdom_' + kd.ID;
            link.setAttribute('data-hd', (kd.ID === 19 || kd.ID === 21) ? '1' : '0');
            link.textContent = (kd.Name === '<b>6.3</b>') ? currentVer : kd.Name;
            link.addEventListener('click', function () {
                var kingdom = getKingdomById(kd.ID);
                if (!kingdom) return;
                selectKingdom(kingdomIndexById(kd.ID));
            });
            btn.appendChild(link);
            container.append(btn);
        });
    }

    function selectKingdom(idx) {
        var kingdom = V2_DATA.Kingdoms[idx];
        if (!kingdom) return;
        setState({ kingdomId: kingdom.ID, curKingdom: kingdom });
        $('.kingdom kingdom').removeClass('active');
        $('.kingdom_' + kingdom.ID).closest('kingdom').addClass('active');
        renderMonsters(kingdom);
    }

    // ============ 9. 怪物卡片 ============
    function renderMonsters(kingdom) {
        var area = $('#monster_card_area_1');
        area.empty();

        var kingdomName = (kingdom.Name === '<b>6.3</b>') ? currentVer : kingdom.Name;

        // 如果是版本占位分类，用 manifest.json diff.monster 动态渲染
        if (kingdom.Name === '<b>6.3</b>') {
            var diffMons = [];
            diffMonsters.forEach(function (mid) {
                var m = V2_DATA.List[mid];
                if (m) diffMons.push(m);
            });

            var header = document.createElement('div');
            header.style.cssText = 'padding:6px 0;color:#999;font-size:13px';
            header.textContent = kingdomName + ' (' + diffMons.length + ' ' + (lang === 'CH' ? '个怪物' : ' monsters') + ')';
            area.append(header);

            if (diffMons.length > 0) {
                var gridWrap = document.createElement('div');
                gridWrap.className = 'mv2-grid-wrap';
                diffMons.forEach(function (m) { gridWrap.appendChild(buildCard(m)); });
                area.append(gridWrap);
            }
            return;
        }

        var classes = [];
        for (var j in kingdom.Classes) { classes.push(kingdom.Classes[kingdom.Classes.length - j - 1]); }

        var totalCount = 0;
        classes.forEach(function (cls) { totalCount += cls.Monsters ? cls.Monsters.length : 0; });

        var header = document.createElement('div');
        header.style.cssText = 'padding:6px 0;color:#999;font-size:13px';
        var kingdomName = (kingdom.Name === '<b>6.3</b>') ? currentVer : kingdom.Name;
        header.textContent = kingdomName + ' (' + totalCount + ' ' + (lang === 'CH' ? '个怪物' : ' monsters') + ')';
        area.append(header);

        classes.forEach(function (cls) {
            if (!cls.Monsters || !cls.Monsters.length) return;
            if (cls.Name) {
                var clsName = document.createElement('div');
                clsName.className = 'mv2-class-name';
                clsName.textContent = cls.Name + ' (' + cls.Monsters.length + ')';
                area.append(clsName);
            }
            if (cls.Hidden) return;
            var gridWrap = document.createElement('div');
            gridWrap.className = 'mv2-grid-wrap';
            cls.Monsters.forEach(function (mid) {
                var monster = V2_DATA.List[mid];
                if (!monster) return;
                gridWrap.appendChild(buildCard(monster));
            });
            area.append(gridWrap);
        });
    }

    function buildCard(monster) {
        var card = document.createElement('div');
        card.className = 'mv2-card hover-shadow';
        card.setAttribute('data-id', monster._id);

        var chooseIcon = monster.Icon[Math.floor(Math.random() * monster.Icon.length)];
        var iconEl = document.createElement('img');
        iconEl.className = 'mv2-card-icon';
        iconEl.src = getIconUrl(chooseIcon);
        iconEl.loading = 'lazy';
        card.appendChild(iconEl);

        var nameEl = document.createElement('div');
        nameEl.className = 'mv2-card-name';
        nameEl.style.color = (computer_.TextColorConfig && monster.Color) ? computer_.TextColorConfig[monster.Color] : '#333';
        nameEl.textContent = monster.Name;
        card.appendChild(nameEl);

        var idEl = document.createElement('div');
        idEl.className = 'mv2-card-id';
        idEl.textContent = '#' + monster._id;
        card.appendChild(idEl);

        var hpEl = document.createElement('div');
        hpEl.className = 'mv2-card-hp';
        hpEl.textContent = formatHpQuick(monster);
        card.appendChild(hpEl);

        card.addEventListener('click', function () {
            openDetailPanel(this.getAttribute('data-id'));
        });

        return card;
    }

    // ============ 10. 详情面板 ============
    function bindDetailPanelEvents() {
        $('#mv2_detail_close').on('click', closeDetailPanel);
        $('#mv2_detail_back').on('click', closeDetailPanel);
        $('#mv2_detail_overlay').on('click', function (e) {
            if (e.target === this) closeDetailPanel();
        });
    }

    function openDetailPanel(parentId) {
        var parent = V2_DATA.List[parentId];
        if (!parent) return;

        setState({ selectedId: parentId, panelOpen: true, effHpCalc: null });

        var variants = getVariantsForParent(parentId);
        var defaultChildId = null;
        if (variants) {
            var ids = Object.keys(variants).sort();
            for (var i = 0; i < ids.length; i++) {
                if (variants[ids[i]].Suffix === '') { defaultChildId = ids[i]; break; }
            }
            if (defaultChildId === null && ids.length > 0) defaultChildId = ids[0];
        }
        setState({ currentChildId: defaultChildId });

        var data = getMonsterData(parentId, defaultChildId);
        renderDetailContent(data, parentId);

        $('#mv2_detail_overlay').addClass('open');
        $('#mv2_detail_modal').scrollTop(0);
    }

    function closeDetailPanel() {
        $('#mv2_detail_overlay').removeClass('open');
        setState({ selectedId: null, currentChildId: null, panelOpen: false, effHpCalc: null });
    }

    function renderDetailContent(data, parentId) {
        var content = $('#mv2_detail_content');
        content.empty();

        // 0. 等级/减抗计算栏
        renderCalcBar(data, content);

        // 1. 头部
        renderDetailHeader(data, content);

        // 2. 变种信息条
        if (state.currentChildId) { renderVariantInfoBar(data, content); }

        // 3. 数值区
        renderDetailStats(data, content);

        // 4. 抗性表
        renderDetailResistances(data, content);

        // 5. 教程/描述
        renderDetailTutorial(data, content);

        // 6. Csx
        if (data.Csx && data.Csx.length) { renderDetailCsx(data, content); }

        // 7. 变种区
        renderVariantsSection(parentId, content);
    }

    // ============ 11. 数据获取 ============
    function getMonsterData(pid, cid) {
        var list = V2_DATA.List[pid] || {};
        var variant = cid ? (V2_DATA.Variants[cid] || {}) : {};
        var merged = Object.assign({}, list, variant);
        return merged;
    }

    function getVariantsForParent(pid) {
        var out = {};
        var all = V2_DATA.Variants || {};
        for (var cid in all) {
            if (!all.hasOwnProperty(cid)) continue;
            if (String(all[cid].ParentId) === String(pid)) {
                out[cid] = all[cid];
            }
        }
        return Object.keys(out).length ? out : null;
    }

    function getIconUrl(icon) {
        if (!icon) return imgpre + 'homdgcat-res/monster/default.png';
        var folder = icon.indexOf('ItemIcon') !== -1 ? 'Mat' : 'monster';
        return imgpre + 'homdgcat-res/' + folder + '/' + icon + '.png';
    }

    // ============ 12. 计算栏（等级 + 减抗输入） ============
    function renderCalcBar(data, container) {
        var bar = document.createElement('div');
        bar.className = 'mv2-calc-bar';
        bar.id = 'mv2_calc_bar';

        // 等级
        var labelLv = document.createElement('label');
        labelLv.textContent = (lang === 'CH' ? '等级' : 'Level');
        bar.appendChild(labelLv);

        var lvInput = document.createElement('input');
        lvInput.type = 'number';
        lvInput.value = state.level;
        lvInput.min = 1;
        lvInput.max = 200;
        lvInput.id = 'mv2_level_input';
        lvInput.addEventListener('change', function () {
            setState({ level: parseInt(lvInput.value) || 100 });
            updateStatsDisplay();
            updateVariantsDisplay();
        });
        bar.appendChild(lvInput);

        // 倍率
        var labelMul = document.createElement('label');
        labelMul.textContent = (lang === 'CH' ? '倍率' : 'MUL');
        bar.appendChild(labelMul);

        var mulInput = document.createElement('input');
        mulInput.type = 'number';
        mulInput.value = state.mul;
        mulInput.min = 0.01;
        mulInput.max = 100;
        mulInput.step = 0.01;
        mulInput.id = 'mv2_mul_input';
        mulInput.addEventListener('change', function () {
            setState({ mul: parseFloat(mulInput.value) || 3.75 });
            updateStatsDisplay();
            updateVariantsDisplay();
        });
        bar.appendChild(mulInput);

        // 重置
        var resetBtn = document.createElement('button');
        resetBtn.className = 'mv2-calc-btn';
        resetBtn.textContent = (lang === 'CH' ? '重置' : 'Reset');
        resetBtn.addEventListener('click', function () {
            setState({ level: 100, resDecrease: 0, mul: 3.75, effHpCalc: null });
            lvInput.value = 100;
            mulInput.value = 3.75;
            updateStatsDisplay();
            updateVariantsDisplay();
            resetEffHp();
        });
        bar.appendChild(resetBtn);

        container.append(bar);
    }

    // ============ 13. HP/ATK 计算 ============
    function calcHpValue(data) {
        var level = state.level;
        var hp = data.HP || 0;
        var curve = data.HPCurve;

        var lc = V2_DATA.LevelCurves || null;
        var val = (lc && lc[level]) ? lc[level][curve] : undefined;
        var a = (val !== undefined) ? val : 1;

        return a * hp * state.mul;
    }

    function calcAtkValue(data) {
        var level = state.level;
        var atk = data.ATK || 0;
        var curve = data.ATKCurve;

        var lc = V2_DATA.LevelCurves || null;
        var val = (lc && lc[level]) ? lc[level][curve] : undefined;
        var a = (val !== undefined) ? val : 1;

        return a * atk * state.mul;
    }

    function calcStatValue(val, curve, level) {
        if (val === null || val === undefined) return null;
        var lc = V2_DATA.LevelCurves || null;
        var levelVal = (lc && lc[level]) ? lc[level][curve] : undefined;
        var a = (levelVal !== undefined) ? levelVal : 1;
        return (val || 0) * a * state.mul;
    }

    function formatHpAtk(v, level) {
        if (v.HP === null || v.HP === undefined) return (lang === 'CH' ? '友善生物' : 'Docile');
        var hp = calcStatValue(v.HP, v.HPCurve, level);
        var atk = calcStatValue(v.ATK, v.ATKCurve, level);
        var hpStr = Math.round(hp) + (v.HPCount ? '\u00D7' + v.HPCount : '');
        var atkStr = Math.round(atk) + (v.ATKCount ? '\u00D7' + v.ATKCount : '');
        return 'HP ' + hpStr + ' \u00B7 ATK ' + atkStr;
    }

    function formatStatValueFull(value, count) {
        if (value === undefined || value === null) return '-';
        var display = Math.round(value).toFixed(0);
        if (count) display += ' \u00D7' + count;
        return display;
    }

    function updateStatsDisplay() {
        var parentId = state.selectedId;
        var childId = state.currentChildId;
        if (!parentId) return;

        var data = getMonsterData(parentId, childId);
        var hpVal = calcHpValue(data);
        var atkVal = calcAtkValue(data);

        var statsSection = document.getElementById('mv2_stats_section');
        if (statsSection) {
            statsSection.innerHTML = '';
            var hpRow = createStatRow('HP', formatStatValueFull(hpVal, data.HPCount));
            var atkRow = createStatRow('ATK', formatStatValueFull(atkVal, data.ATKCount));
            statsSection.appendChild(hpRow);
            statsSection.appendChild(atkRow);
        }

        // 如果有效血量激活，重新计算
        if (state.effHpCalc) {
            computeEffHp(hpVal);
        }
    }

    function updateVariantsDisplay() {
        var cards = document.querySelectorAll('.mv2-variant-card');
        var parentId = state.selectedId;
        if (!parentId) return;
        var variants = getVariantsForParent(parentId);
        if (!variants) return;

        cards.forEach(function (card) {
            var childId = card.getAttribute('data-child-id');
            var v = variants[childId];
            if (!v) return;
            var statsSpan = card.querySelector('.mv2-variant-stats');
            if (statsSpan) {
                statsSpan.textContent = formatHpAtk(v, state.level);
            }
        });
    }

    // ============ 14. 等效血量 ============
    function renderEffHpBar(container) {
        var bar = document.createElement('div');
        bar.className = 'mv2-effhp-bar';
        bar.id = 'mv2_effhp_bar';

        var label = document.createElement('label');
        label.textContent = (lang === 'CH' ? '减抗 %' : 'RES ↓%');
        bar.appendChild(label);

        var input = document.createElement('input');
        input.type = 'number';
        input.value = state.resDecrease;
        input.min = 0;
        input.max = 200;
        input.id = 'mv2_effhp_input';
        bar.appendChild(input);

        var calcBtn = document.createElement('button');
        calcBtn.className = 'mv2-calc-btn';
        calcBtn.textContent = (lang === 'CH' ? '计算等效血量' : 'Calc Eff.HP');
        calcBtn.addEventListener('click', function () {
            var dec = parseInt(input.value) || 0;
            setState({ resDecrease: dec, effHpCalc: { hp: calcCurrentHp(), resDecrease: dec } });
            startEffHp();
        });
        bar.appendChild(calcBtn);

        var resetBtn = document.createElement('button');
        resetBtn.className = 'mv2-calc-btn';
        resetBtn.textContent = (lang === 'CH' ? '重置' : 'Reset');
        resetBtn.addEventListener('click', function () {
            input.value = 0;
            setState({ resDecrease: 0, effHpCalc: null });
            resetEffHp();
        });
        bar.appendChild(resetBtn);

        container.append(bar);
    }

    function calcCurrentHp() {
        var parentId = state.selectedId;
        var childId = state.currentChildId;
        if (!parentId) return 0;
        var data = getMonsterData(parentId, childId);
        return calcHpValue(data);
    }

    function startEffHp() {
        var resDecrease = state.effHpCalc ? state.effHpCalc.resDecrease : 0;
        var hp = state.effHpCalc ? state.effHpCalc.hp : 0;
        computeEffHp(hp, resDecrease);
    }

    function computeEffHp(hp, resDecrease) {
        if (!state.effHpCalc) return;
        if (hp === undefined) hp = state.effHpCalc.hp;
        if (resDecrease === undefined) resDecrease = state.effHpCalc.resDecrease;
        resDecrease = resDecrease || 0;

        var table = document.querySelector('#mv2_res_section .mv2-res-table');
        if (!table) return;

        table.classList.add('show-effhp');

        var parentId = state.selectedId;
        var childId = state.currentChildId;
        var data = getMonsterData(parentId, childId);
        var immune = data.Immune || [];
        var resBase = data.RESBase || {};

        var rows = table.querySelectorAll('tr');
        rows.forEach(function (row) {
            var resValTd = row.querySelector('.mv2-res-value, .mv2-res-immune');
            var effhpTd = row.querySelector('.mv2-res-effhp');
            if (!effhpTd) return;

            var elem = row.querySelector('.mv2-res-name');
            var elemName = elem ? elem.textContent : '';

            if (immune.indexOf(elemName) !== -1) {
                effhpTd.textContent = '免疫';
            } else {
                var baseVal = resBase[elemName] !== undefined ? resBase[elemName] : 0.1;
                var r = res(baseVal, resDecrease / 100);
                effhpTd.textContent = Math.round(hp * r).toFixed(0);
            }
        });
    }

    function resetEffHp() {
        var table = document.querySelector('#mv2_res_section .mv2-res-table');
        if (table) { table.classList.remove('show-effhp'); }
        setState({ effHpCalc: null });
    }

    // ============ 15. 详情页分块渲染 ============
    function renderDetailHeader(data, container) {
        var header = document.createElement('div');
        header.className = 'mv2-detail-header';

        var iconName = data.Icon ? data.Icon[Math.floor(Math.random() * data.Icon.length)] : '';
        var img = document.createElement('img');
        img.className = 'mv2-detail-icon';
        img.src = getIconUrl(iconName);
        header.appendChild(img);

        var info = document.createElement('div');
        info.className = 'mv2-detail-info';

        var nameEl = document.createElement('div');
        nameEl.className = 'mv2-detail-name';
        nameEl.style.color = (computer_.TextColorConfig && data.Color) ? computer_.TextColorConfig[data.Color] : '#333';
        nameEl.textContent = data.Name || '???';
        info.appendChild(nameEl);

        if (data.Title && data.Title.length) {
            data.Title.forEach(function (t) {
                if (t && t !== data.Name) {
                    var titleEl = document.createElement('div');
                    titleEl.className = 'mv2-detail-title';
                    titleEl.textContent = t;
                    info.appendChild(titleEl);
                }
            });
        }

        var badge = document.createElement('span');
        badge.className = 'mv2-detail-badge';
        badge.textContent = 'ID: ' + data._id;
        info.appendChild(badge);

        header.appendChild(info);
        container.append(header);
    }

    function updateVariantInfoBar(data) {
        var infoBar = document.getElementById('mv2_variant_info_bar');
        if (!infoBar) return;
        infoBar.innerHTML = '';
        var label = document.createElement('span');
        label.className = 'mv2-variant-label';
        label.textContent = (lang === 'CH' ? '当前变种' : 'Current Variant');
        infoBar.appendChild(label);
        infoBar.appendChild(document.createTextNode(': '));
        var nameSpan = document.createElement('span');
        var suffix = data.Suffix || '';
        nameSpan.textContent = data.Name + (suffix ? ' \u00B7 ' + suffix : '');
        infoBar.appendChild(nameSpan);
        infoBar.appendChild(document.createTextNode(' \u00B7 '));
        var idSpan = document.createElement('span');
        idSpan.textContent = 'ID ' + data._id;
        infoBar.appendChild(idSpan);
    }

    function renderVariantInfoBar(data, container) {
        var bar = document.createElement('div');
        bar.className = 'mv2-variant-info-bar';
        bar.id = 'mv2_variant_info_bar';
        container.append(bar);
        updateVariantInfoBar(data);
    }

    function renderDetailStats(data, container) {
        var section = document.createElement('div');
        section.id = 'mv2_stats_section';

        var hpVal = calcHpValue(data);
        var atkVal = calcAtkValue(data);

        section.appendChild(createStatRow('HP', formatStatValueFull(hpVal, data.HPCount)));
        section.appendChild(createStatRow('ATK', formatStatValueFull(atkVal, data.ATKCount)));

        container.append(section);
    }

    function createStatRow(labelText, valueHtml) {
        var row = document.createElement('div');
        row.className = 'mv2-stat-row';

        var label = document.createElement('span');
        label.className = 'mv2-stat-label';
        label.textContent = labelText;
        row.appendChild(label);

        var value = document.createElement('span');
        value.className = 'mv2-stat-value';
        value.innerHTML = valueHtml;
        row.appendChild(value);

        return row;
    }

    function renderDetailResistances(data, container) {
        var section = document.createElement('div');
        section.className = 'mv2-res-section';
        section.id = 'mv2_res_section';

        var head = document.createElement('div');
        head.className = 'a_section_head';
        head.textContent = computer_.MiscText.Computer_Result_RESBaseTitle ? computer_.MiscText.Computer_Result_RESBaseTitle[lang2] || '常态抗性' : '常态抗性';
        section.appendChild(head);

        var table = document.createElement('table');
        table.className = 'mv2-res-table';

        // 表头
        var thead = document.createElement('thead');
        var hr = document.createElement('tr');

        var thIcon = document.createElement('th');
        thIcon.style.width = '36px';
        hr.appendChild(thIcon);
        var thElem = document.createElement('th');
        hr.appendChild(thElem);

        var thVal = document.createElement('th');
        thVal.style.textAlign = 'right';
        thVal.textContent = (lang === 'CH' ? '抗性' : 'RES');
        hr.appendChild(thVal);

        var thEff = document.createElement('th');
        thEff.className = 'mv2-res-effhp';
        thEff.style.textAlign = 'right';
        thEff.textContent = (lang === 'CH' ? '等效HP' : 'Eff.HP');
        hr.appendChild(thEff);

        thead.appendChild(hr);
        table.appendChild(thead);

        // 表体
        var tbody = document.createElement('tbody');
        var resBase = data.RESBase || {};
        var immune = data.Immune || [];
        var elements = ['Phys', 'Fire', 'Water', 'Elec', 'Ice', 'Grass', 'Wind', 'Rock'];

        elements.forEach(function (elem) {
            var tr = document.createElement('tr');

            var tdIcon = document.createElement('td');
            tdIcon.className = 'mv2-res-icon-cell';
            var iconImg = document.createElement('img');
            iconImg.className = 'mv2-res-icon';
            iconImg.src = imgpre + 'homdgcat-res/UI/' + elem.replace('Phys', 'Physical') + '.png';
            tdIcon.appendChild(iconImg);
            tr.appendChild(tdIcon);

            var tdName = document.createElement('td');
            tdName.className = 'mv2-res-name';
            tdName.textContent = elem;
            tr.appendChild(tdName);

            var tdVal = document.createElement('td');
            if (immune.indexOf(elem) !== -1) {
                tdVal.className = 'mv2-res-immune';
                tdVal.textContent = computer_.MiscText.Computer_Result_Immune ? computer_.MiscText.Computer_Result_Immune[lang2] || '免疫' : '免疫';
            } else {
                tdVal.className = 'mv2-res-value';
                var val = resBase[elem] !== undefined ? resBase[elem] : 0.1;
                tdVal.textContent = (val * 100).toFixed(0) + '%';
            }
            tr.appendChild(tdVal);

            var tdEff = document.createElement('td');
            tdEff.className = 'mv2-res-effhp';
            tdEff.textContent = '-';
            tr.appendChild(tdEff);

            tbody.appendChild(tr);
        });

        table.appendChild(tbody);
        section.appendChild(table);

        // 等效血量操作栏
        renderEffHpBar(section);

        container.append(section);
    }

    function renderDetailTutorial(data, container) {
        var section = document.createElement('div');
        section.className = 'mv2-tutorial-section';
        section.id = 'mv2_tutorial_section';

        if (data.Tut && typeof V2_DATA.Tuts !== 'undefined' && V2_DATA.Tuts[data.Tut]) {
            V2_DATA.Tuts[data.Tut].forEach(function (e) {
                if (e.I) {
                    e.I.forEach(function (f) {
                        var img = document.createElement('img');
                        img.className = 'mv2-tutorial-img';
                        img.src = imgpre + 'images/Tutorial/' + f + '.png';
                        section.appendChild(img);
                    });
                }
            });
        }

        if (data.Desc) {
            var descEl = document.createElement('p');
            descEl.className = 'mv2-desc-text';
            descEl.innerHTML = data.Desc.replace(/#/g, '</color>').replace(/@/g, "<color style='color:#FFD780'>");
            section.appendChild(descEl);
        }

        if (data.Tutorial && typeof V2_DATA.Tutorials !== 'undefined' && V2_DATA.Tutorials[data.Tutorial]) {
            var tutText = V2_DATA.Tutorials[data.Tutorial];
            if (tutText) {
                var tutEl = document.createElement('p');
                tutEl.className = 'mv2-desc-text';
                tutEl.innerHTML = tutText.replace(/#/g, '</color>').replace(/@/g, "<color style='color:#FFD780'>");
                section.appendChild(tutEl);
            }
        }

        if (section.children.length > 0) { container.append(section); }
    }

    function renderDetailCsx(data, container) {
        var section = document.createElement('div');
        section.id = 'mv2_csx_section';
        var csxName = Array.isArray(data.Csx) ? data.Csx[0] : data.Csx;
        var btn = document.createElement('a');
        btn.className = 'mv2-csx-btn';
        btn.textContent = (lang === 'CH' ? '查看 3D 模型' : 'View 3D Model');
        btn.href = imgpre + 'EnemyChart/' + csxName + '.png';
        btn.target = '_blank';
        section.appendChild(btn);
        container.append(section);
    }

    // ============ 16. 变种区 ============
    function renderVariantsSection(parentId, container) {
        var variants = getVariantsForParent(parentId);
        if (!variants) return;

        var section = document.createElement('div');
        section.className = 'mv2-variants-section';
        section.id = 'mv2_variants_section';

        var head = document.createElement('div');
        head.className = 'a_section_head';
        head.textContent = (lang === 'CH' ? '变种' : 'Variants');
        section.appendChild(head);

        var list = document.createElement('div');
        list.className = 'mv2-variants-list';

        var sortedIds = Object.keys(variants).sort();
        sortedIds.forEach(function (childId) {
            var v = variants[childId];
            var card = document.createElement('div');
            card.className = 'mv2-variant-card hover-shadow';
            card.setAttribute('data-child-id', childId);
            if (String(state.currentChildId) === String(childId)) { card.classList.add('active'); }

            var nameSpan = document.createElement('span');
            nameSpan.className = 'mv2-variant-name';
            var vs = v.Suffix;
            nameSpan.textContent = (vs !== undefined && vs !== '') ? vs : (lang === 'CH' ? '基础' : 'Base');
            card.appendChild(nameSpan);

            var idSpan = document.createElement('span');
            idSpan.className = 'mv2-variant-id';
            idSpan.textContent = childId;
            card.appendChild(idSpan);

            var statsSpan = document.createElement('span');
            statsSpan.className = 'mv2-variant-stats';
            statsSpan.textContent = formatHpAtk(v, state.level);
            card.appendChild(statsSpan);

            // 抗性概要
            var resistEl = buildResistSummary(v);
            if (resistEl) { card.appendChild(resistEl); }

            card.addEventListener('click', function () {
                switchVariant(this.getAttribute('data-child-id'));
            });

            list.appendChild(card);
        });

        section.appendChild(list);
        container.append(section);
    }

    function buildResistSummary(variant) {
        var resBase = variant.RESBase || {};
        var immune = variant.Immune || [];
        var list = [];

        immune.forEach(function (e) {
            list.push({ elem: e, text: (lang === 'CH' ? '免疫' : 'Imm'), type: 'immune' });
        });

        var isImmune = {};
        immune.forEach(function (e) { isImmune[e] = true; });

        Object.keys(resBase).forEach(function (e) {
            if (isImmune[e]) return;
            var v = resBase[e];
            if (v === 0.1) return;
            var pct = Math.round(v * 100);
            var text = (pct > 0 ? '+' : '') + pct + '%';
            list.push({ elem: e, text: text, type: pct > 10 ? 'high' : (pct < 10 ? 'low' : 'default') });
        });

        if (list.length === 0) {
            var span = document.createElement('span');
            span.className = 'mv2-variant-resist';
            var badge = document.createElement('span');
            badge.className = 'mv2-res-badge res-default';
            badge.textContent = (lang === 'CH' ? '全 10%' : 'All 10%');
            span.appendChild(badge);
            return span;
        }

        var colorConfig = computer_.TextColorConfig || {};

        var wrap = document.createElement('span');
        wrap.className = 'mv2-variant-resist';

        list.forEach(function (item) {
            var badge = document.createElement('span');
            var classes = 'mv2-res-badge';
            if (item.type === 'immune') classes += ' res-immune';
            else if (item.type === 'high') classes += ' res-high';
            else if (item.type === 'low') classes += ' res-low';
            badge.className = classes;

            if (item.elem && colorConfig[item.elem]) {
                badge.style.color = colorConfig[item.elem];
            }

            badge.textContent = (item.elem ? (item.elem + ' ') : '') + item.text;
            wrap.appendChild(badge);
        });

        return wrap;
    }

    function switchVariant(childId) {
        var parentId = state.selectedId;
        if (!parentId) return;

        setState({ currentChildId: childId, effHpCalc: null });
        var data = getMonsterData(parentId, childId);

        updateVariantInfoBar(data);

        // 更新数值区
        updateStatsDisplay();

        // 更新抗性表
        var resSection = document.getElementById('mv2_res_section');
        if (resSection) {
            var resBase = data.RESBase || {};
            var immune = data.Immune || [];
            var elements = ['Phys', 'Fire', 'Water', 'Elec', 'Ice', 'Grass', 'Wind', 'Rock'];

            var rows = resSection.querySelectorAll('.mv2-res-table tbody tr');
            rows.forEach(function (tr, i) {
                var elem = elements[i];
                if (!elem) return;

                var tdVal = tr.querySelector('.mv2-res-value, .mv2-res-immune');
                if (!tdVal) return;

                if (immune.indexOf(elem) !== -1) {
                    tdVal.className = 'mv2-res-immune';
                    tdVal.textContent = computer_.MiscText.Computer_Result_Immune ? computer_.MiscText.Computer_Result_Immune[lang2] || '免疫' : '免疫';
                } else {
                    tdVal.className = 'mv2-res-value';
                    var val = resBase[elem] !== undefined ? resBase[elem] : 0.1;
                    tdVal.textContent = (val * 100).toFixed(0) + '%';
                }
            });

            // 重设等效血量
            resetEffHp();
        }

        // 更新变种卡片高亮
        var cards = document.querySelectorAll('.mv2-variant-card');
        cards.forEach(function (c) {
            c.classList.toggle('active', String(c.getAttribute('data-child-id')) === String(childId));
        });
    }

    // ============ 17. 辅助函数 ============
    function rnd(num) {
        var s = num.toFixed(5);
        while (s.length >= 2 && s.substring(s.length - 1) === '0') { s = s.substring(0, s.length - 1); }
        return s;
    }

    function formatHpQuick(monster) {
        var hp = monster.HP;
        var curve = monster.HPCurve;
        if (hp === null || hp === undefined) { return lang === 'CH' ? '友善生物' : 'Docile'; }
        if (curve === 1) { return 'HP ' + hp + ' 丘丘'; }
        if (curve === 10) { return 'HP ' + rnd(hp / 13.584) + ' 丘丘'; }
        if (curve === 2) { return 'HP ' + hp + ' 野伏'; }
        if (curve === 20) { return 'HP ' + rnd(hp / 27.168) + ' 野伏'; }
        if (curve === 7) { return 'HP ' + hp + ' 巡'; }
        return 'HP ' + hp + ' ?';
    }

    function getKingdomById(id) {
        for (var i = 0; i < V2_DATA.Kingdoms.length; i++) { if (V2_DATA.Kingdoms[i].ID === id) return V2_DATA.Kingdoms[i]; }
        return null;
    }

    function kingdomIndexById(id) {
        for (var i = 0; i < V2_DATA.Kingdoms.length; i++) { if (V2_DATA.Kingdoms[i].ID === id) return i; }
        return -1;
    }

    function findKingdomId(monsterId) {
        for (var k = 0; k < V2_DATA.Kingdoms.length; k++) {
            var classes = V2_DATA.Kingdoms[k].Classes;
            for (var c = 0; c < classes.length; c++) {
                var monsters = classes[c].Monsters;
                for (var m = 0; m < monsters.length; m++) {
                    if (monsters[m] == monsterId) return V2_DATA.Kingdoms[k].ID;
                }
            }
        }
        return -1;
    }
});