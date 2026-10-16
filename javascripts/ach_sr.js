$(function () {

    var imgpre = $('#IMGPRE').val()

    var ttl = (lang == 'CH') ? '成就' : 'Achievements'
    init_title(ttl + ' ' + txt.PAGE_TITLE[lang])

    if (lang == 'EN') { $('body').css('font-family', "'Segoe UI', sans-serif") }
    else { $('body').css('font-family', "'Microsoft YaHei', sans-serif") }

    $('h3 .title').html(txt.Title[lang] + "<color style='font-size: 26px;'><br>" + txt.game_img[lang] + VER_SR + "</b></color>")
    $('h3 .subtitle').html(txt.Subtitle[lang]);
    $('h3 .lang').html(txt.Home_Lang)
    $('h3 .lang').hide()
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

    $('body').on('click', '._menu_', function () {
        popLinks(lang)
    })

    // ===== State =====
    var state = {
        manifest: null,
        groups: [],
        currentGroup: null,   // null = all groups
        currentVer: '',
        searchText: '',
        doneIds: []
    }

    var allData = {}   // cache: { groupId: [ach, ...] }
    var loadedGroups = {}  // track which groups have been loaded

    // ===== localStorage helpers =====
    function loadDone() {
        try {
            var stored = localStorage.getItem('ach:sr:done')
            state.doneIds = stored ? JSON.parse(stored) : []
        } catch (e) { state.doneIds = [] }
    }
    function saveDone() {
        localStorage.setItem('ach:sr:done', JSON.stringify(state.doneIds))
    }
    loadDone()

    // ===== URL hash helpers =====
    function parseHash() {
        var hash = window.location.hash.replace('#', '')
        if (!hash) return {}
        var params = {}
        hash.split('&').forEach(function (p) {
            var kv = p.split('=')
            if (kv[0]) params[decodeURIComponent(kv[0])] = (kv[1] ? decodeURIComponent(kv[1]) : '')
        })
        return params
    }

    function updateHash(groupId, ver) {
        var params = []
        if (groupId !== null && groupId !== undefined) params.push('group=' + encodeURIComponent(groupId))
        if (ver) params.push('ver=' + encodeURIComponent(ver))
        var newHash = params.join('&')
        if (window.location.hash !== '#' + newHash) {
            window.location.hash = newHash
        }
    }

    // ===== Load manifest =====
    var manifestUrl = '/sr/data/' + lang3 + '/ach.json'

    $.getJSON(manifestUrl, function (manifest) {
        state.manifest = manifest
        state.groups = manifest.groups

        var params = parseHash()
        var initialGroup = params.group !== undefined ? parseInt(params.group) : null
        if (isNaN(initialGroup)) initialGroup = null
        state.currentVer = params.ver || ''

        // Render everything in one call (summary + layout)
        renderAll(manifest, initialGroup)

        $('.ach-filter select').val(state.currentVer || (lang == 'CH' ? '全部' : 'All'))

        // Load initial group data and render
        loadAndRender(initialGroup, state.currentVer, '')

        $('body').addClass(bg_name)
    })

    // ===== Render: summary + layout =====
    function renderAll(manifest, selectedGroup) {
        $('container').render({
            div: [
                // Summary row
                {
                    h2: txt.AchNum[lang].replace("#", manifest.latestVersion) + "<color style='color:#ff0000;'>" + manifest.totalNum + "</color>"
                },
                {
                    h2: txt.AchNum[lang].replace("#", manifest.prevVersion) + "<color style='color:#ff0000;'>" + manifest.prevTotalNum + "</color>"
                },
                // Layout row
                {
                    class: 'ach-layout',
                    div: [
                        {
                            class: 'ach-sidebar',
                            div: buildSidebarItems(manifest, selectedGroup)
                        },
                        {
                            class: 'ach-main',
                            div: [
                                {
                                    class: 'ach-filter',
                                    div: buildFilterBar(manifest)
                                },
                                {
                                    class: 'ach-list',
                                    div: []
                                }
                            ]
                        }
                    ]
                }
            ],
            class: 'content'
        })
    }

    // ===== Build sidebar items =====
    function buildSidebarItems(manifest, selectedGroup) {
        var newNum = manifest.totalNum - manifest.prevTotalNum
        var items = []

        // "New achievements" entry — active only when selectedGroup === 'new'
        var newActive = (selectedGroup === 'new')
        items.push({
            div: [
                { p: txt.NewAch[lang] + ' ' + newNum, class: 'ach-sidebar-label' }
            ],
            class: 'ach-sidebar-item' + (newActive ? ' active' : ''),
            a: { 'data-group': 'new' }
        })

        // "All" entry — active when selectedGroup is null (meaning "all")
        var allActive = (selectedGroup === null || selectedGroup === 'all')
        items.push({
            div: [
                { p: txt.AllAch[lang] + ' ' + manifest.totalNum, class: 'ach-sidebar-label' }
            ],
            class: 'ach-sidebar-item' + (allActive ? ' active' : ''),
            a: { 'data-group': 'all' }
        })

        // Separator
        items.push({ class: 'ach-sidebar-sep', div: [] })

        // Per-group entries
        manifest.groups.forEach(function (g) {
            var gActive = (selectedGroup === g.id)
            items.push({
                div: [
                    {
                        img: imgpre + 'images/Achievement/' + g.icon,
                        class: 'ach-sidebar-icon'
                    },
                    {
                        span: g.name,
                        class: 'ach-sidebar-name'
                    },
                    {
                        span: g.num.toString(),
                        class: 'ach-sidebar-count'
                    }
                ],
                class: 'ach-sidebar-item' + (gActive ? ' active' : ''),
                a: { 'data-group': g.id }
            })
        })

        return items
    }

    // ===== Build filter bar =====
    function buildFilterBar(manifest) {
        // Options: "All" at top, then versions
        var allLabel = (lang == 'CH' ? '全部' : 'All')
        var verOptions = [allLabel].concat(manifest.versions)

        return [
            {
                input: '',
                class: 'ach-search',
                placeholder: (lang == 'CH') ? '搜索成就名称或描述…' : 'Search achievements…',
                style: {
                    'flex': '1',
                    'padding': '6px 10px',
                    'font-size': '14px',
                    'border': '1px solid #ccc',
                    'border-radius': '4px',
                    'margin-right': '10px'
                }
            },
            {
                select: '',
                class: 'ach-ver-select',
                options: verOptions,
                style: {
                    'padding': '6px 10px',
                    'font-size': '14px',
                    'border': '1px solid #ccc',
                    'border-radius': '4px',
                    'width': '90px'
                }
            }
        ]
    }

    // ===== Load group data and render =====
    function loadAndRender(groupId, ver, searchText) {
        var self = this
        if (!self._loading) self._loading = {}

        if (groupId === null || groupId === 'all' || groupId === 'new') {
            // Load all groups
            var allPromises = []
            state.groups.forEach(function (g) {
                if (!loadedGroups[g.id]) {
                    allPromises.push(loadSingleGroup(g.id))
                }
            })
            if (allPromises.length > 0) {
                $.when.apply($, allPromises).done(function () {
                    renderList(groupId, ver, searchText)
                })
            } else {
                renderList(groupId, ver, searchText)
            }
        } else {
            if (!loadedGroups[groupId]) {
                loadSingleGroup(groupId).done(function () {
                    renderList(groupId, ver, searchText)
                })
            } else {
                renderList(groupId, ver, searchText)
            }
        }
    }

    function loadSingleGroup(groupId) {
        var url = '/sr/data/' + lang3 + '/ach/' + groupId + '.json'
        return $.getJSON(url).done(function (data) {
            allData[groupId] = data
            loadedGroups[groupId] = true
        })
    }

    // ===== Render achievement list =====
    function renderList(groupId, ver, searchText) {
        var $list = $('.ach-list')
        $list.empty()

        var achievements = []
        var isNew = (groupId === null || groupId === 'all' || groupId === 'new')

        if (isNew) {
            // Collect from all groups
            state.groups.forEach(function (g) {
                if (allData[g.id]) {
                    achievements = achievements.concat(allData[g.id])
                }
            })
            if (groupId === 'new') {
                // Filter to latest version only
                var latestVer = state.manifest.latestVersion
                achievements = achievements.filter(function (a) { return a.ver === latestVer })
            }
        } else {
            achievements = allData[groupId] || []
        }

        // Version filter
        if (ver) {
            achievements = achievements.filter(function (a) { return a.ver === ver })
        }

        // Search filter
        if (searchText) {
            var q = searchText.toLowerCase()
            achievements = achievements.filter(function (a) {
                return a.name.toLowerCase().indexOf(q) !== -1 ||
                       a.desc.toLowerCase().indexOf(q) !== -1
            })
        }

        // Sort by id
        achievements.sort(function (a, b) { return a.id - b.id })

        if (achievements.length === 0) {
            $list.render({
                p: (lang == 'CH') ? '没有匹配的成就' : 'No matching achievements',
                style: { 'text-align': 'center', 'padding': '40px', 'color': '#999' }
            })
            return
        }

        // Build list items
        var items = []
        achievements.forEach(function (ach) {
            var isDone = state.doneIds.indexOf(ach.id) !== -1
            items.push({
                div: [
                    {
                        div: [
                            // Checkbox — type and data-id go in a:{}
                            {
                                input: '',
                                class: 'ach-checkbox',
                                a: { type: 'checkbox', 'data-id': ach.id }
                            },
                            // Name
                            {
                                span: ach.name,
                                class: 'ach-item-name'
                            },
                            // Reward
                            {
                                span: [
                                    { img: imgpre + 'images/Achievement/900001.png', class: 'jade' },
                                    ach.reward.toString() + (lang == 'CH' ? '星琼' : ' Stellar Jade')
                                ],
                                class: 'ach-item-reward'
                            },
                            // Version
                            {
                                span: ach.ver,
                                class: 'ach-item-ver'
                            }
                        ],
                        class: 'ach-item-top'
                    },
                    {
                        div: ach.desc,
                        class: 'ach-item-desc'
                    }
                ],
                class: 'ach-item' + (isDone ? ' done' : '')
            })
        })

        $list.render({ div: items, class: 'ach-items' })

        // Apply checked state after rendering (render plugin can't set checked via template)
        achievements.forEach(function (ach) {
            if (state.doneIds.indexOf(ach.id) !== -1) {
                $('.ach-checkbox[data-id="' + ach.id + '"]', $list).prop('checked', true)
            }
        })
    }

    // ===== Event handlers =====

    // Sidebar click
    $('body').on('click', '.ach-sidebar-item', function () {
        var groupId = $(this).attr('data-group')
        if (groupId === 'all') groupId = null
        else if (groupId === 'new') groupId = 'new'
        else groupId = parseInt(groupId)

        state.currentGroup = groupId

        $('.ach-sidebar-item').removeClass('active')
        $(this).addClass('active')

        updateHash(groupId, state.currentVer)
        loadAndRender(groupId, state.currentVer, state.searchText)
    })

    // Version select change
    $('body').on('change', '.ach-ver-select', function () {
        var val = $(this).val()
        // "All" / "全部" means no version filter
        if (val === 'All' || val === '全部') val = ''
        state.currentVer = val
        updateHash(state.currentGroup, state.currentVer)
        loadAndRender(state.currentGroup, state.currentVer, state.searchText)
    })

    // Search input
    $('body').on('input', '.ach-search', function () {
        state.searchText = $(this).val()
        loadAndRender(state.currentGroup, state.currentVer, state.searchText)
    })

    // Checkbox toggle
    $('body').on('change', '.ach-checkbox', function () {
        var id = parseInt($(this).attr('data-id'))
        var checked = $(this).prop('checked')

        if (checked) {
            if (state.doneIds.indexOf(id) === -1) {
                state.doneIds.push(id)
            }
        } else {
            var idx = state.doneIds.indexOf(id)
            if (idx !== -1) {
                state.doneIds.splice(idx, 1)
            }
        }
        saveDone()

        // Toggle done class on parent item
        if (checked) {
            $(this).closest('.ach-item').addClass('done')
        } else {
            $(this).closest('.ach-item').removeClass('done')
        }
    })

})