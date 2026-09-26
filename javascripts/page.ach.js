$(function () {
    // ═══════════════════════════════════════════════════════════════
    // 头部初始化（照搬旧脚本第 1–30 行）
    // ═══════════════════════════════════════════════════════════════

    var imgpre = $('#IMGPRE').val()

    var ttl = (lang == 'CH') ? '成就' : 'Achievements'
    init_title(ttl + ' ' + computer_.MiscText.PAGE_TITLE[lang])

    $('.tls' + lang).css("color", "#df903b");
    $('h3 .title').html(computer_.MiscText.Title[lang] + "<color style='font-size: 26px;'><br>" + computer_.MiscText.game_img[lang] + VER_GI + "</b></color>");
    $('h3 .subtitle').html(computer_.MiscText.Subtitle[lang]);
    $('h3 .tlsub').html(computer_.MiscText.Translate_);
    $('h3 .tlsub').hide()
    $('h3 .links').render([
        {
            img: imgpre + 'images/menu.png',
            class: '_menu_'
        },
        {
            img: imgpre + 'images/translate.png',
            class: '_translate_'
        }
    ]);

    $("body").on("click", ".tlsub", function () {
        if (lang == 'CH') $("a[data-id='EN']").click()
        if (lang == 'EN') $("a[data-id='CN']").click()
    });

    // ═══════════════════════════════════════════════════════════════
    // 新成就页逻辑
    // ═══════════════════════════════════════════════════════════════

    var ACH_DATA_PATH = '/gi/CH/ach/ach.json'
    var GROUPS_PATH = '/gi/CH/ach/groups/'
    var STORAGE_KEY = 'ach:done'
    var primoIcon = imgpre + 'homdgcat-res/Csxylic/Primo.png'

    // ─── 状态 ────────────────────────────────────────────────────
    var state = {
        meta: null,                // ach.json 内容
        groups: {},                // groupId -> achievements[]
        selectedGroup: null,       // 当前选中的分组 id
        searchText: '',            // 搜索文本
        versionFilter: '',         // 版本过滤（空 = 全部）
        showHidden: true,          // 是否显示隐藏成就
        doneIds: new Set(),        // 已完成的成就 id 集合
        currentItems: null         // 当前加载的未过滤明细
    }

    // ─── 读取 localStorage 进度 ──────────────────────────────────
    function loadProgress() {
        try {
            var stored = localStorage.getItem(STORAGE_KEY)
            if (stored) {
                var arr = JSON.parse(stored)
                if (Array.isArray(arr)) {
                    state.doneIds = new Set(arr)
                }
            }
        } catch (e) {
            state.doneIds = new Set()
        }
    }

    function saveProgress() {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(state.doneIds)))
    }

    // ─── URL Hash 解析 ───────────────────────────────────────────
    function parseHash() {
        var hash = window.location.hash.replace('#', '')
        var params = {}
        hash.split('&').forEach(function (pair) {
            var parts = pair.split('=')
            if (parts[0]) params[parts[0]] = parts[1] || ''
        })
        return params
    }

    var _skipHashChange = false

    function updateHash() {
        var params = []
        if (state.selectedGroup !== null) params.push('group=' + state.selectedGroup)
        if (state.versionFilter) params.push('ver=' + state.versionFilter)
        if (state.searchText) params.push('search=' + encodeURIComponent(state.searchText))
        if (!state.showHidden) params.push('hide=0')
        var hash = params.join('&')
        var newHash = hash ? '#' + hash : ''
        if (window.location.hash !== newHash) {
            _skipHashChange = true
            window.location.hash = newHash
        }
    }

    // ─── 语义版本排序 ───────────────────────────────────────────
    function semverSortDesc(versions) {
        return versions.slice().sort(function (a, b) {
            var pa = a.split('.').map(Number)
            var pb = b.split('.').map(Number)
            for (var i = 0; i < Math.max(pa.length, pb.length); i++) {
                var na = pa[i] || 0
                var nb = pb[i] || 0
                if (na !== nb) return nb - na
            }
            return 0
        })
    }

    // ─── 渲染左侧分组列表 ───────────────────────────────────────
    function renderSidebar() {
        var $sidebar = $('#ach-sidebar')
        $sidebar.empty()

        if (!state.meta) return

        // "全部" 行
        var $allItem = $('<div class="ach-group-item' + (state.selectedGroup === null ? ' active' : '') + '" data-group="">').appendTo($sidebar)
        $('<span class="ach-group-name">').html(computer_.MiscText.Ach_All_Name[lang2]).appendTo($allItem)
        $('<span class="ach-group-num">').text(state.meta.totalNum).addClass('ach-num-highlight').appendTo($allItem)

        // 每个分组
        state.meta.groups.forEach(function (g) {
            var $item = $('<div class="ach-group-item' + (state.selectedGroup === g.id ? ' active' : '') + '" data-group="' + g.id + '">').appendTo($sidebar)
            $('<span class="ach-group-name">').text(g.name).appendTo($item)
            $('<span class="ach-group-num">').text(g.num).appendTo($item)
        })
    }

    // ─── 左侧分组点击事件（只绑定一次）──────────────────────────
    $(document).on('click', '#ach-sidebar .ach-group-item', function () {
        var gid = $(this).attr('data-group')
        state.selectedGroup = gid === '' ? null : parseInt(gid, 10)
        state.searchText = ''
        $('#ach-search-input').val('')
        updateHash()
        renderSidebar()
        loadCurrentGroup()
    })

    // ─── 加载分组明细 ───────────────────────────────────────────
    function reRenderFromCache() {
        if (state.currentItems) renderList(state.currentItems)
    }

    function loadCurrentGroup() {
        var $list = $('#ach-list')
        $list.html('<div class="ach-loading">' + (lang == 'CH' ? '加载中...' : 'Loading...') + '</div>')

        if (state.selectedGroup === null) {
            // "全部"：加载所有分组
            loadAllGroups()
            return
        }

        // 检查是否已缓存
        if (state.groups[state.selectedGroup]) {
            renderList(state.groups[state.selectedGroup])
            return
        }

        // fetch 加载
        $.getJSON(GROUPS_PATH + state.selectedGroup + '.json', function (data) {
            state.groups[state.selectedGroup] = data
            renderList(data)
        }).fail(function () {
            $list.html('<div class="ach-loading">' + (lang == 'CH' ? '加载失败' : 'Load Failed') + '</div>')
        })
    }

    function loadAllGroups() {
        var allItems = []
        var pending = state.meta.groups.length
        if (pending === 0) {
            renderList([])
            return
        }

        state.meta.groups.forEach(function (g) {
            if (state.groups[g.id]) {
                allItems = allItems.concat(state.groups[g.id])
                pending--
                if (pending === 0) renderList(allItems)
            } else {
                $.getJSON(GROUPS_PATH + g.id + '.json', function (data) {
                    state.groups[g.id] = data
                    allItems = allItems.concat(data)
                    pending--
                    if (pending === 0) renderList(allItems)
                }).fail(function () {
                    pending--
                    if (pending === 0) renderList(allItems)
                })
            }
        })
    }

    // ─── 渲染右侧列表 ───────────────────────────────────────────
    function renderList(items) {
        state.currentItems = items
        var $list = $('#ach-list')
        $list.empty()

        var filtered = filterItems(items)

        if (filtered.length === 0) {
            $list.html('<div class="ach-empty">' + (lang == 'CH' ? '没有匹配的成就' : 'No matching achievements') + '</div>')
            return
        }

        filtered.forEach(function (ach) {
            var $row = $('<div class="ach-row' + (state.doneIds.has(ach.id) ? ' ach-done' : '') + '">').appendTo($list)

            // 复选框
            var $cb = $('<input type="checkbox" class="ach-checkbox"' + (state.doneIds.has(ach.id) ? ' checked' : '') + '>')
                .appendTo($row)
                .on('change', function () {
                    if (this.checked) {
                        state.doneIds.add(ach.id)
                    } else {
                        state.doneIds.delete(ach.id)
                    }
                    saveProgress()
                    $row.toggleClass('ach-done', this.checked)
                })

            // 内容区
            var $info = $('<div class="ach-info">').appendTo($row)

            // 名称
            $('<div class="ach-name">').text(ach.name).appendTo($info)

            // 描述
            if (ach.desc) {
                $('<div class="ach-desc">').html(ach.desc).appendTo($info)
            }

            // 标签行
            var $tags = $('<div class="ach-tags">').appendTo($info)

            // 原石
            var $primo = $('<span class="ach-primo">').appendTo($tags)
            $('<img class="ach-primo-icon">').attr('src', primoIcon).appendTo($primo)
            $primo.append(' ' + ach.reward)

            // 版本
            if (ach.ver) {
                $('<span class="ach-ver-tag">').text(ach.ver).appendTo($tags)
            }

            // 总进度
            if (ach.total > 1) {
                $('<span class="ach-total-tag">').text('/' + ach.total).appendTo($tags)
            }

            // 隐藏标记
            if (ach.hidden) {
                $('<span class="ach-hidden-tag">').text(lang == 'CH' ? '隐藏' : 'Hidden').appendTo($tags)
            }
        })
    }

    // ─── 筛选逻辑 ───────────────────────────────────────────────
    function filterItems(items) {
        return items.filter(function (ach) {
            // 版本过滤
            if (state.versionFilter && ach.ver !== state.versionFilter) return false

            // 隐藏过滤
            if (!state.showHidden && ach.hidden) return false

            // 搜索：匹配 name 和 desc
            if (state.searchText) {
                var q = state.searchText.toLowerCase()
                var nameMatch = ach.name.toLowerCase().indexOf(q) !== -1
                var descMatch = ach.desc && ach.desc.toLowerCase().indexOf(q) !== -1
                if (!nameMatch && !descMatch) return false
            }

            return true
        })
    }

    // ─── 渲染过滤栏 ─────────────────────────────────────────────
    function renderFilters() {
        var $bar = $('#ach-filter-bar')
        $bar.empty()

        // 搜索框
        var $searchWrap = $('<div class="ach-filter-search">').appendTo($bar)
        $('<input id="ach-search-input" type="text" class="ach-search-input" placeholder="' + (lang == 'CH' ? '搜索成就...' : 'Search achievements...') + '">')
            .val(state.searchText)
            .appendTo($searchWrap)
            .on('input', function () {
                state.searchText = $(this).val()
                updateHash()
                reRenderFromCache()
            })

        // 版本下拉
        if (state.meta && state.meta.versions && state.meta.versions.length) {
            var $verWrap = $('<div class="ach-filter-ver">').appendTo($bar)
            var $verSelect = $('<select class="ach-ver-select">').appendTo($verWrap)

            var allLabel = lang == 'CH' ? '全部版本' : 'All Versions'
            $('<option value="">').text(allLabel).appendTo($verSelect)

            state.meta.versions.forEach(function (v) {
                var $opt = $('<option value="' + v + '"' + (state.versionFilter === v ? ' selected' : '') + '>').text(v)
                $verSelect.append($opt)
            })

            $verSelect.on('change', function () {
                state.versionFilter = $(this).val()
                updateHash()
                reRenderFromCache()
            })
        }

        // 隐藏开关
        var $hideWrap = $('<div class="ach-filter-hide">').appendTo($bar)
        var $hideLabel = $('<label class="ach-hide-label">').appendTo($hideWrap)
        $('<input type="checkbox" class="ach-hide-checkbox"' + (state.showHidden ? ' checked' : '') + '>')
            .appendTo($hideLabel)
            .on('change', function () {
                state.showHidden = this.checked
                updateHash()
                reRenderFromCache()
            })
        $hideLabel.append(' ' + (lang == 'CH' ? '显示隐藏' : 'Show Hidden'))
    }

    // ─── 更新右侧标题 ───────────────────────────────────────────
    function updateTitle() {
        var $title = $('#ach-list-title')
        if (state.selectedGroup === null) {
            $title.html(computer_.MiscText.Ach_All_Name[lang2])
            switch_title(computer_.MiscText.Ach_All_Name[lang2])
        } else if (state.meta) {
            var found = null
            state.meta.groups.forEach(function (g) {
                if (g.id === state.selectedGroup) found = g
            })
            if (found) {
                $title.text(found.name)
                switch_title(found.name)
            }
        }
    }

    // ─── 从 Hash 恢复状态 ───────────────────────────────────────
    function applyHash() {
        var params = parseHash()
        if (params.group !== undefined) {
            state.selectedGroup = params.group === '' ? null : parseInt(params.group, 10)
        }
        if (params.ver !== undefined) {
            state.versionFilter = params.ver
        }
        if (params.search !== undefined) {
            state.searchText = decodeURIComponent(params.search)
        }
        if (params.hide !== undefined) {
            state.showHidden = params.hide === '1'
        }
    }

    // ─── 监听 hashchange ────────────────────────────────────────
    $(window).on('hashchange', function () {
        if (_skipHashChange) {
            _skipHashChange = false
            return
        }
        applyHash()
        renderSidebar()
        renderFilters()
        updateTitle()
        loadCurrentGroup()
    })

    // ═══════════════════════════════════════════════════════════════
    // 初始化：获取数据后渲染
    // ═══════════════════════════════════════════════════════════════

    loadProgress()
    applyHash()

    // 检查 #ID 隐式传入（旧版兼容）
    var implicitId = $('#ID').val()
    if (implicitId && state.selectedGroup === null) {
        state.selectedGroup = parseInt(implicitId, 10)
    }

    $.getJSON(ACH_DATA_PATH, function (meta) {
        state.meta = meta

        // 组装容器结构
        var $container = $('container')

        // 如果已经有 .ach-layout 则不重复添加
        if ($container.find('.ach-layout').length === 0) {
            $container.append(
                '<div class="ach-layout">' +
                    '<div class="ach-sidebar" id="ach-sidebar"></div>' +
                    '<div class="ach-main">' +
                        '<div class="ach-filter-bar" id="ach-filter-bar"></div>' +
                        '<div class="ach-list-title" id="ach-list-title"></div>' +
                        '<div class="ach-list" id="ach-list"></div>' +
                    '</div>' +
                '</div>'
            )
        }

        renderFilters()
        renderSidebar()
        updateTitle()
        loadCurrentGroup()
    }).fail(function () {
        $('container').append('<div class="ach-loading" style="padding:40px;text-align:center;">' +
            (lang == 'CH' ? '数据加载失败，请刷新重试' : 'Failed to load data, please refresh') +
            '</div>')
    })

    // ═══════════════════════════════════════════════════════════════
    // 设置背景（照搬旧脚本）
    // ═══════════════════════════════════════════════════════════════
    $('body').addClass(bg_name)
})