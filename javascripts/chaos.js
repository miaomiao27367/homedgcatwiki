$(function () {

    var imgpre = $('#IMGPRE').val()
    var lazy = $('#NOLAZY').val() ? '' : 'lazy'

    init_title(txt.N_C[lang3] + ' ' + txt.PAGE_TITLE[lang])

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

    var EG = 1
    var HLG = 1
    var DEF = 2000
    var LV = 95
    //refreshStats()
    var IS_DMG = 1
    var cm = {}
    var HIDE_SHOW = 0
    var multistage_mode = 0
    var starButton = null
    var showStar = false

    var has_2 = 0

    // 先加载 Monster.js 完整数据，再加载 Chaos_1.js，最后从完整数据构建 _monster
    var _monster_full = {}

    let script_m1 = document.createElement('script')
    script_m1.src = '/sr/data/' + lang3 + '/Monster.js'
    document.head.append(script_m1)

    script_m1.onload = function () {
        // 展开 Child 变体到 _monster_full 顶层
        var baseKeys = Object.keys(_monster)
        for (var i = 0; i < baseKeys.length; i++) {
            var base = _monster[baseKeys[i]]
            _monster_full[baseKeys[i]] = base
            if (base && base.Child) {
                var childKeys = Object.keys(base.Child)
                for (var j = 0; j < childKeys.length; j++) {
                    var childId = childKeys[j]
                    var child = base.Child[childId]
                    var childCopy = Object.assign({}, child)
                    if (base.Stats && child.Stats) {
                        childCopy.Stats = {}
                        for (var k in base.Stats) {
                            childCopy.Stats[k] = Math.round(base.Stats[k] * (child.Stats[k] || 1) * 10000) / 10000
                        }
                    }
                    _monster_full[childId] = childCopy
                }
            }
        }

        // 从完整数据构建精简版 _monster
        var newMonster = {}
        for (var key in _monster_full) {
            var m = _monster_full[key]
            newMonster[key] = {
                    "1": m.Figure || ("monsterfigure/Monster_" + key + ".png"),
                    "2": m.Weak || [],
                    "3": m.HPCount || 1,
                    "4": m.Name || "",
                    "11": m.StanceCount || 0,
                    "12": m.Multistage || 0,
                    "13": m.Multistage_list || []
                }
        }
        _monster = newMonster

        begin()
    }

    function begin() {

        let script_computer = document.createElement('script')
        script_computer.src = '/sr/data/' + lang3 + '/Chaos_1.js'
        document.head.append(script_computer)
        script_computer.onload = function () {

            let script_computer_2 = document.createElement('script')
            script_computer_2.src = '/sr/data/' + lang3 + '/Chaos_2.js'
            document.head.append(script_computer_2)
            script_computer_2.onload = function () {
                has_2 = 1
                _chaos = _chaos.concat(_chaos_2)
            }

            // 加载星启模式数据
            let script_star = document.createElement('script')
            script_star.src = '/sr/data/' + lang3 + '/Chaos_star.js'
            document.head.append(script_star)

            max_index = _chaosschedule.length
            cur_index = _chaos.findIndex(function(c) { return c._id == $('#CID').val() })
            if (cur_index < 0) cur_index = 0

            cur_floor = $('#FID').val() ? (parseInt($('#FID').val()) - 1) : -1
            cur_floor_data = 0

            $('container').render({
                template: {
                    div: [
                        {
                            p: txt.N_C[lang3],
                            style: {
                                'text-align': 'center',
                                'font-weight': 'bold',
                                'font-size': '1.6em',
                                'margin-bottom': '-10px',
                                'margin-top': '15px',
                            }
                        },
                        {
                            div: [
                                {
                                    div: '◁',
                                    class: 'v_l'
                                },
                                {
                                    div: [
                                        {
                                            p: '',
                                            class: 'ver_text_name'
                                        },
                                        {
                                            p: '',
                                            class: 'ver_text_time'
                                        }
                                    ],
                                    class: 'ver_text hover-shadow'
                                },
                                {
                                    div: {
                                        p: '▷'
                                    },
                                    class: 'v_r'
                                }
                            ],
                            class: 'ver'
                        },
                        {
                            div: [
                                {
                                    div: [
                                        {
                                            span: ((lang == 'CH') ? '下载图片' : 'Download'),
                                        }
                                    ],
                                    class: 'level_ dl_button hover-shadow',
                                },
                                {
                                    div: [
                                        {
                                            div: {
                                                img: '/images/emote/Yunli/1.png',
                                            },
                                            class: 'perf_img'
                                        },
                                        {
                                            span: ((lang == 'CH') ? '云璃成绩' : 'Yunli Performance'),
                                        }
                                    ],
                                    class: 'level_ yunli_button hover-shadow',
                                },
                            ],
                            class: 'button_w'
                        },
                        {
                            div: [
                                {
                                    div: '◁',
                                    class: 'f_l'
                                },
                                {
                                    div: '',
                                    class: 'f_text'
                                },
                                {
                                    div: '▷',
                                    class: 'f_r'
                                }
                            ],
                            class: 'floor_select'
                        },
                        {
                            div: [
                                {
                                    div: [
                                        {
                                            p: '',
                                            class: 'buff_name'
                                        },
                                        {
                                            p: '',
                                            class: 'buff_desc'
                                        },
                                        {
                                            p: '',
                                            class: 'dpc'
                                        },
                                    ],
                                    class: 'buff'
                                },
                                {
                                    div: [
                                        {
                                            p: '',
                                            class: 'target_c'
                                        },
                                        {
                                            div: '',
                                            class: 'target_t'
                                        },
                                    ],
                                    class: 'target',
                                    when: 0,
                                },
                            ],
                            class: 'info_area'
                        },
                        {
                            div: [
                                {
                                    div: [
                                        {
                                            div: '',
                                            class: 'u_r'
                                        },
                                        {
                                            div: '',
                                            class: 'u_m'
                                        },
                                        {
                                            div: '',
                                            class: 'u_g',
                                            when: window.innerWidth <= 800
                                        },
                                    ],
                                    class: 'u'
                                },
                                {
                                    div: [
                                        {
                                            div: '',
                                            class: 'star_r'
                                        },
                                        {
                                            div: '',
                                            class: 'star_m'
                                        },
                                    ],
                                    class: 'star',
                                },
                                {
                                    div: [
                                        {
                                            div: '',
                                            class: 'l_r'
                                        },
                                        {
                                            div: '',
                                            class: 'l_m'
                                        },
                                        {
                                            div: '',
                                            class: 'l_g',
                                            when: window.innerWidth <= 800
                                        },
                                    ],
                                    class: 'l'
                                },
                            ],
                            class: 'u_l'
                        },
                        {
                            div: [
                                {
                                    div: '',
                                    class: 'u_g'
                                },
                                {
                                    div: '',
                                    class: 'star_g'
                                },
                                {
                                    div: '',
                                    class: 'l_g'
                                }
                            ],
                            class: 'u_l_g',
                            when: window.innerWidth > 800
                        },
                        {
                            div: [
                                {
                                    span: (lang == 'CH') ? '星启模式' : 'Star Mode',
                                    class: 'slider_label'
                                },
                                {
                                    div: [
                                        {
                                            div: '',
                                            class: 'slider_thumb'
                                        }
                                    ],
                                    class: 'slider_switch',
                                    event: {
                                        click: function () {
                                            showStar = !showStar;
                                            writeData();  // 调用 writeData() 重新渲染
                                        }
                                    }
                                },
                            ],
                            class: 'star_button hover-shadow'
                        },
                        {
                            div: [
                                {
                                    span: ((lang == 'CH') ? '多阶段血量' : 'Multistage HP'),
                                    style: {
                                        'margin-right': '8px',
                                        'font-size': '0.85em',
                                        'align-self': 'center'
                                    }
                                },
                                {
                                    div: [
                                        {
                                            div: '',
                                            class: 'slider_thumb'
                                        }
                                    ],
                                    class: 'slider_switch ms_switch',
                                    event: {
                                        click: function () {
                                            multistage_mode = 1 - multistage_mode
                                            if (multistage_mode) {
                                                $(this).addClass('slider_on')
                                            } else {
                                                $(this).removeClass('slider_on')
                                            }
                                            writeData()
                                        }
                                    }
                                },
                            ],
                            class: 'star_button hover-shadow',
                            style: {
                                'display': 'flex',
                                'align-items': 'center'
                            }
                        },
                        {
                            div: {
                                div: '',
                                id: 'chart',
                            },
                            class: 'chart_container'
                        },
                    ],
                    class: 'content'
                }
            })

            writeVer()

            $('body').addClass(bg_name)
            starButton = $('.star_button')[0]

            // 滑块样式已移至 chaos.css

            if (!lazy) {
                a_section_white()
                $("head").append('<style type="text/css"></style>');
                var newStyleElement = $("head").children(':last');
                newStyleElement.html('.info_area{color:white!important}');
            }

        }

        $('body').on('click', '.ver_text', function () {
            var pop = poplayer({
                header: '',
                width: '95%',
                template: [
                    {
                        div: function (k) {
                            _chaosschedule.forEach(function (t, i) {
                                if (t.Time != ' - ') return
                                $(k.container).render({
                                    p: '<b>' + t.Name + '</b><br>' + t.Time,
                                    class: 'ver_text hover-shadow',
                                    style: {
                                        width: '250px',
                                        'padding-left': '10px',
                                        'padding-right': '10px',
                                        'text-align': 'center',
                                        'line-height': '1.7'
                                    },
                                    event: {
                                        click: function () {
                                            pop.close()
                                            cur_index = i
                                            writeVer()
                                        }
                                    }
                                })
                            })
                        },
                        style: {
                            display: 'flex',
                            'flex-wrap': 'wrap',
                            'justify-content': 'space-evenly'
                        }
                    },
                    {
                        div: function (k) {
                            _chaosschedule.forEach(function (t, i) {
                                if (t.Time == ' - ') return
                                $(k.container).render({
                                    p: '<b>' + t.Name + '</b><br>' + t.Time,
                                    class: 'ver_text hover-shadow',
                                    style: {
                                        width: '250px',
                                        'padding-left': '10px',
                                        'padding-right': '10px',
                                        'text-align': 'center',
                                        'line-height': '1.7'
                                    },
                                    event: {
                                        click: function () {
                                            pop.close()
                                            cur_index = i
                                            writeVer()
                                        }
                                    }
                                })
                            })
                        },
                        style: {
                            display: 'flex',
                            'flex-wrap': 'wrap',
                            'justify-content': 'space-evenly'
                        }
                    }
                ]
            })
        })

        function writeVer() {
            if (mod(cur_index, max_index) < 4) {
                writeVerAfter()
            } else {
                if (has_2) {
                    writeVerAfter()
                    return
                }
                $('.lt').show()
                var ou = setInterval(function () {
                    if (has_2) {
                        $('.lt').hide()
                        writeVerAfter()
                        clearInterval(ou)
                    }
                }, 200)
            }
        }

        function writeVerAfter() {
            switch_title(_chaosschedule[mod(cur_index, max_index)].Name)
            cur_schedule_ver = _chaosschedule[mod(cur_index, max_index)]._id
            $('.ver_text_name').html(_chaosschedule[mod(cur_index, max_index)].Name)
            $('.ver_text_time').html(_chaosschedule[mod(cur_index, max_index)].Time)
            writeData()
        }

        function writeData() {
            cur_floor_data = lm(_chaos[mod(cur_index, max_index)].Floors, cur_floor)
            $('.dpc').html(txt.DPC_S[lang] + '<b><color style="color:#f29e38;">' + cur_floor_data.HPSingle + '</color></b>' + '<br>' + txt.DPC_M[lang] + '<b><color style="color:#f29e38;">' + cur_floor_data.HPMulti + '</color></b>')
            $('.f_text').html(cur_floor_data.Floor)
            var buff = _chaos[mod(cur_index, max_index)].Buff
            if (!buff) buff = cur_floor_data.Buff
            if (buff) {
                $('.info_area').show()
                $('.buff_name').html(buff.Name + '<br>' + buff._id)
                $('.buff_desc').html(buff.Desc)
            } else {
                $('.info_area').hide()
            }
            if (buff && buff.Extra && buff.Extra.length) {
                buff.Extra.forEach(function (t) {
                    var affix = ""
                    if (t.DMG) {
                        var this_lv = cur_floor_data.Upper[0].Level
                        var this_hlg = cur_floor_data.Upper[0].HardLevelGroup ? cur_floor_data.Upper[0].HardLevelGroup : "1"
                        affix = '<b>' + Math.floor(t.DMG * _enviro[this_hlg][this_lv]) + '</b>'
                        if (t.Color) {
                            affix = `<color style='color:#${elemcolor[t.Color]}'>` + affix + '</color>'
                        }
                    }
                    $('.buff_desc').render({
                        p: '- ' + t.Name + ' ' + affix,
                        style: {
                            margin: '0'
                        }
                    })
                })
            }
            $('.target_c').html(txt.Cycle[lang] + cur_floor_data.TurnNum)
            $('.target_t').empty().render({
                template: {
                    p: [
                        {
                            img: imgpre + 'images/Misc/Star.png',
                            class: 'star'
                        }, function (d) {
                            return d.data
                        }
                    ],
                    style: {
                        'line-height': '28px'
                    }
                },
                data: cur_floor_data.Targets
            })
            var _lv = cur_floor_data.Upper[0].Level
            $('.u_r').empty().render({
                template: [
                    {
                        div: [
                            {
                                p: txt.Recommended[0][lang] + ' Lv' + _lv
                            },
                            {
                                img: function (k) {
                                    return imgpre + 'images/Element/' + k.data + '.png'
                                },
                                class: 'elem_',
                                data: cur_floor_data.ElemUpper,
                                a: {
                                    loading: lazy
                                }
                            },
                            {
                                p: (lang == 'CH') ? '玩家自创阵容' : 'Fan-Made Lineup',
                                when: !(cur_floor_data.ElemUpper && cur_floor_data.ElemUpper.length),
                                style: {
                                    'font-size': '1.2em',
                                    color: '#cc0000',
                                }
                            },
                            {
                                p: txt.Chart_Subtitle[lang],
                                style: {
                                    'font-size': '0.75em',
                                    color: '#0066FF',
                                }
                            },
                        ]
                    }
                ]
            })
            $('.l_r').empty().render({
                template: [
                    {
                        div: [
                            {
                                p: txt.Recommended[1][lang] + ' Lv' + _lv
                            },
                            {
                                img: function (k) {
                                    return imgpre + 'images/Element/' + k.data + '.png'
                                },
                                class: 'elem_',
                                data: cur_floor_data.ElemLower,
                                a: {
                                    loading: lazy
                                }
                            },
                            {
                                p: (lang == 'CH') ? '玩家自创阵容' : 'Fan-Made Lineup',
                                when: !(cur_floor_data.ElemLower && cur_floor_data.ElemLower.length),
                                style: {
                                    'font-size': '1.2em',
                                    color: '#cc0000',
                                }
                            },
                            {
                                p: txt.Chart_Subtitle[lang],
                                style: {
                                    'font-size': '0.75em',
                                    color: '#0066FF',
                                }
                            },
                        ]
                    }
                ]
            })
            $('.u_m').empty()
            $('.u_m').render({
                template: Lineup(cur_floor_data.Upper)
            })
            $('.l_m').empty()
            $('.l_m').render({
                template: Lineup(cur_floor_data.Lower)
            })

            // Star Mode 渲染 - 只在第12层显示（cur_floor=-1对应第12层）
            var isFloor12 = (cur_floor === -1);
            // 检查星启模式数据是否存在且当前版本有对应数据
            var star_data = typeof _Chaos_star !== 'undefined' && _Chaos_star ? _Chaos_star[cur_schedule_ver] : null;
            if (showStar && isFloor12 && star_data) {
                $('.star').show();
                $('.star_g').show();
                $('.slider_switch').addClass('slider_on');

                // 获取星启模式数据
                var star_level = star_data.Star[0].Level;

                // 渲染星启模式右侧信息
                $('.star_r').empty().render({
                    template: [
                        {
                            div: [
                                {
                                    p: (lang == 'CH') ? '星启模式' : 'Star Mode' + ' Lv' + star_level
                                },
                                {
                                    img: function (k) {
                                        return imgpre + 'images/Element/' + k.data + '.png'
                                    },
                                    class: 'elem_',
                                    data: star_data.ElemStar,
                                    a: {
                                        loading: lazy
                                    }
                                },
                                {
                                    p: txt.Chart_Subtitle[lang],
                                    style: {
                                        'font-size': '0.75em',
                                        color: '#0066FF',
                                    }
                                },
                            ]
                        }
                    ]
                })

                // 渲染星启模式怪物阵容
                $('.star_m').empty()
                $('.star_m').render({
                    template: Lineup(star_data.Star)
                })
            } else {
                $('.star').hide();
                $('.star_g').hide();
                $('.slider_switch').removeClass('slider_on');
            }

            rotate()
            var floor_name = $('.f_text').html()

            myChart = echarts.init(document.getElementById('chart'))
            var option = {
                title: {
                    text: txt.Chart_Title_MoC[lang].replace('#', floor_name),
                    subtext: txt.Chart_Subtitle[lang],
                    left: 'center',
                    textStyle: {
                        color: '#000'
                    },
                    subtextStyle: {
                        color: '#2545ba'
                    },
                    top: '8%'
                },
                tooltip: {
                    trigger: 'axis',
                },
                legend: {
                    data: [txt.DPC_S[lang], txt.DPC_M[lang]],
                    top: '20%'
                },
                grid: {
                    left: '3%',
                    right: '4%',
                    top: '26%',
                    containLabel: true
                },
                toolbox: {
                    feature: {
                        saveAsImage: {}
                    },
                    right: '75%',
                    top: '10%'
                },
                xAxis: {
                    type: 'category',
                    boundaryGap: true,
                    data: _chaoshp[floor_name].Name,
                    axisLabel: {
                        color: '#000',
                        padding: [5, 0],
                    }
                },
                yAxis: {
                    type: 'value'
                },
                series: [
                    {
                        name: txt.DPC_S[lang],
                        type: 'line',
                        data: _chaoshp[floor_name].Single,
                        lineStyle: {
                            color: '#cc0000'
                        },
                        itemStyle: {
                            color: '#cc0000'
                        },
                    },
                    {
                        name: txt.DPC_M[lang],
                        type: 'line',
                        data: _chaoshp[floor_name].Multi,
                        lineStyle: {
                            color: '#2545ba'
                        },
                        itemStyle: {
                            color: '#2545ba'
                        },
                    }
                ]
            }
            if ($("#NOLAZY").val()) option.tooltip.show = false
            myChart.setOption(option)

            myChart.dispatchAction({
                type: 'showTip',
                dataIndex: _chaoshp[$('.f_text').html()].Index[_chaosschedule[mod(cur_index, max_index)]._id],
                seriesIndex: 1,
            })

            if (cur_floor_data.Manual) {
                $('.dl_button').hide()
            } else {
                $('.dl_button').show()
            }

            var show_u = cur_floor_data.UpperGuide && cur_floor_data.UpperGuide.length
            var show_l = cur_floor_data.LowerGuide && cur_floor_data.LowerGuide.length
            $('.u_g').empty()
            $('.l_g').empty()
            if (show_u) {
                generate_boss_guide('.u_g', cur_floor_data.UpperGuide)
            }
            if (show_l) {
                generate_boss_guide('.l_g', cur_floor_data.LowerGuide)
            }

            console.log("FINISH")

        }

        function generate_boss_guide(p, d) {
            d.forEach(function (i) {
                var guide_data = _bossguide[i]
                var lis = []
                var s = []
                for (const item of guide_data.Notes) {
                    if (item.Title) {
                        s = ['<b>@' + item.Title + '#</b>']
                    } else {
                        s = []
                    }
                    for (const desc of item.DescList) {
                        s.push(desc)
                    }
                    lis.push({
                        p: text_process(s.join('<br>')),
                        class: 'bossguide_p'
                    })
                }
                $(p).render({
                    div: {
                        div: [
                            {
                                p: {
                                    CH: '妮可少女的研究',
                                    EN: `HomDGCat's Notes`
                                }[lang],
                                class: 'bossguide_p_b',
                                style: {
                                    'text-align': 'center',
                                    'font-weight': 'bold',
                                }
                            },
                            {
                                div: {
                                    img: '/images/' + guide_data.Icon,
                                    class: 'bossguide_img'
                                },
                                class: 'bossguide_img_w'
                            },
                            {
                                p: guide_data.Name,
                                class: 'bossguide_p_b',
                                style: {
                                    'text-align': 'center',
                                    'font-weight': 'bold',
                                }
                            },
                            {
                                p: txt.Chart_Subtitle[lang],
                                class: 'bossguide_p',
                                style: {
                                    'text-align': 'center',
                                    color: '#FFD780',
                                    'margin-bottom': '10px'
                                }
                            },
                        ].concat(lis),
                        class: 'a_section_content'
                    },
                    class: 'a_section'
                })
            })
        }

        function text_process(t) {
            return t.replaceAll(`#`, `</color>`).replaceAll(`@`, `<color style='color:#FFD780'>`)
        }

        $('body').on('click', '.v_r', function () {
            cur_index -= 1
            writeVer()
        })

        $('body').on('click', '.v_l', function () {
            cur_index += 1
            writeVer()
        })

        $('body').on('click', '.f_r', function () {
            cur_floor += 1
            writeData()
        })

        $('body').on('click', '.f_l', function () {
            cur_floor -= 1
            writeData()
        })

        $('body').on('mouseleave', '#chart', function () {
            myChart.dispatchAction({
                type: 'showTip',
                dataIndex: _chaoshp[$('.f_text').html()].Index[_chaosschedule[mod(cur_index, max_index)]._id],
                seriesIndex: 1,
            })
        })

        function Lineup(L) {
            var out = []
            L.forEach(function (l) {
                out.push(Stage(l))
            })
            return out
        }

        function Stage(l) {
            var waves = []
            l.Monsters.forEach(function (w, i) {
                waves.push(Wave(i, w, l.Level, l.HardLevelGroup, l.EliteGroup))
            })
            var temp = {
                div: [
                    {
                        div: [
                            {
                                div: '',
                                class: 'emote_'
                            },
                        ],
                        class: 'emote_block_',
                    },
                    {
                        p: function (d) {
                            var show = []
                            var start = ''
                            if (l._id) start = '<color style="color:#2545ba">' + l._id + '</color><br>'
                            if (l.EliteGroup) show.push('HP <color style="color:#cc0000">' + ((l.EliteGroup.HP || 1) * 100).toFixed(0) + '%</color>')
                            if (l.EliteGroup && l.EliteGroup.ATK && l.EliteGroup.ATK != 1) show.push('ATK <color style="color:#cc0000">' + (l.EliteGroup.ATK * 100).toFixed(0) + '%</color>')
                            return start + show.join(' | ')
                        },
                        class: '',
                        style: {
                            'text-align': 'center',
                            'font-weight': 'bold',
                            'font-size': '0.9em',
                            'margin-top': '-5px',
                            'margin-bottom': '15px',
                            'line-height': '1.9'
                        }
                    },
                    {
                        div: waves,
                        class: 'stage_waves'
                    }
                ],
                class: 'stage'
            }
            return temp
        }

        function getMonsterData(id) {
            if (_monster[id]) return _monster[id]
            if (_monster_full[id]) {
                var m = _monster_full[id]
                var p = m
                if (String(id).length > 7) {
                    var sid = String(id)
                    for (var t = 1; t <= 3; t++) {
                        if (sid.length <= t) break
                        var bid = sid.substring(0, sid.length - t)
                        if (_monster_full[bid]) { p = _monster_full[bid]; break }
                    }
                }
                return {
                    "1": m.Figure || ("monsterfigure/Monster_" + id + ".png"),
                    "2": m.Weak || [],
                    "3": p.HPCount || 1,
                    "4": m.Name || "",
                    "11": p.StanceCount || 0,
                    "12": p.Multistage || 0,
                    "13": p.Multistage_list || []
                }
            }
            var strId = String(id)
            for (var trim = 1; trim <= 3; trim++) {
                if (strId.length <= trim) break
                var baseId = strId.substring(0, strId.length - trim)
                if (_monster_full[baseId]) {
                    var m = _monster_full[baseId]
                    return {
                        "1": m.Figure || ("monsterfigure/Monster_" + baseId + ".png"),
                        "2": m.Weak || [],
                        "3": m.HPCount || 1,
                        "4": m.Name || "",
                        "11": m.StanceCount || 0,
                        "12": m.Multistage || 0,
                        "13": m.Multistage_list || []
                    }
                }
            }
            return {"1": "monsterfigure/None.png", "2": [], "3": 1, "4": "", "11": 0, "12": 0, "13": []}
        }

        function Wave(i, w, stage_lv, stage_hlg, stage_eg) {
            var monsters = []
            var affix0 = []
            w.forEach(function (t) {
                var me = getMonsterData(t.ID)
                monsters.push({
                    span: [
                        {
                            div: [
                                {
                                    img: imgpre + 'images/' + me["1"],
                                    class: 'monicon hasimg',
                                    event: {
                                        load: function (d) {
                                            $(d.sender).siblings('.monnameload').hide()
                                        },
                                        error: function (d) {
                                            $(d.sender).css("opacity", "0")
                                            $(d.sender).removeClass('hasimg')
                                            $(d.sender).siblings('.hasimgname').removeClass('hasimgname')
                                            $(d.sender).parent().addClass('monicon')
                                        },
                                    },
                                    a: {
                                        loading: lazy
                                    }
                                },
                                {
                                    div: {
                                        p: me["4"]
                                    },
                                    class: 'monnameload hasimgname'
                                },
                            ],
                            class: 'monleft'
                        },
                        {
                            div: [
                                {
                                    span: {
                                        img: function (k) {
                                            return imgpre + 'images/Element/' + k.data + '.png'
                                        },
                                        class: 'elem',
                                        data: me["2"],
                                        a: {
                                            loading: lazy
                                        }
                                    },
                                    class: 'monelem'
                                },
                                {
                                    span: showstance(t.Stance) + (me["11"] ? ('×' + me["11"]) : ''),
                                    class: 'monname',
                                    style: {
                                        'margin-left': '5px',
                                        'position': 'relative',
                                        'bottom': '2px',
                                        'font-weight': 'bold'
                                    }
                                },
                            ],
                            class: 'monbottom',
                            when: t.Stance
                        },
                        {
                            div: [
                                {
                                    span: function () {
                                        var s = '<b><color style="color:#cc0000;">' + t.HP.toString() + '</color></b>'
                                        var has_multistage = me["12"] && me["12"] > 1
                                        var has_hpcount = me["3"] && me["3"] > 1
                                        if (multistage_mode === 0) {
                                            if (has_hpcount) {
                                                s += '<b>×' + me["3"] + '</b>'
                                            } else if (has_multistage) {
                                                var sum = 0
                                                for (var pi = 0; pi < me["13"].length; pi++) {
                                                    sum += me["13"][pi]
                                                }
                                                s += '<b>×' + sum + '</b>'
                                            }
                                        } else {
                                            if (has_multistage) {
                                                var phases = []
                                                for (var pi = 0; pi < me["13"].length; pi++) {
                                                    phases.push('P' + (pi + 1) + ':×' + me["13"][pi])
                                                }
                                                s += ' <span style="color:#f29e38;font-size:0.85em;">' + phases.join(' ') + '</span>'
                                            } else if (has_hpcount) {
                                                s += '<b>×' + me["3"] + '</b>'
                                            }
                                        }
                                        if (me["5"]) s += ` <color style='color:#666;'>[${((stage_eg ? (stage_eg.HP ? stage_eg.HP : 1) : 1) * me["5"] * 100).toFixed(0)}%]</color>`
                                        if (t.HPShow) s += ` <color style='color:#666;'>[${(t.HPShow * 100).toFixed(0)}%]</color>`
                                        return s
                                    },
                                    class: 'monname',
                                    when: t.HP
                                },
                                {
                                    br: '',
                                    when: t.HP && (t.SPD || me['13'])
                                },
                                {
                                    span: function () {
                                        s = '<b><color style="color:#2545ba;">' + t.SPD.toString() + '</color></b>'
                                        if (me["6"]) s += ` <color style='color:#666;'>[${((stage_eg ? (stage_eg.SPD ? stage_eg.SPD : 1) : 1) * me["6"] * 100).toFixed(0)}%]</color>`
                                        if (t.SPDShow) s += ` <color style='color:#666;'>[${(t.SPDShow * 100).toFixed(0)}%]</color>`
                                        return s
                                    },
                                    class: 'monname',
                                    when: t.SPD
                                },
                                {
                                    br: '',
                                    when: t.SPD && me['13']
                                },
                                {
                                    span: function () {
                                        if (me['13'] < 100) {
                                            return {
                                                CH: '行动提前',
                                                EN: 'Advance'
                                            }[lang] + ' <b><color style="color:#cc0000;">' + (100 - me['13']).toString() + '%</color></b>'
                                        } else {
                                            return {
                                                CH: '行动延后',
                                                EN: 'Delay'
                                            }[lang] + ' <b><color style="color:#cc0000;">' + (me['13'] - 100).toString() + '%</color></b>'
                                        }
                                    },
                                    when: me['13'],
                                    class: 'monname'
                                }
                            ],
                            class: 'monright',
                            style: {
                                'margin-top': t.Stance ? '' : '0px'
                            }
                        },
                    ],
                    class: 'monster_card hover-shadow',
                    a: {
                        'data-id': t.ID,
                        'data-lv': stage_lv,
                        'data-hl': stage_hlg ? stage_hlg : 1,
                        'data-eg': stage_eg ? stage_eg.ID : 1
                    }
                })
                if (_affix[t.ID]) {
                    affix0.push(_affix[t.ID].replaceAll("#", "</color>").replaceAll("@", "<color style='color:#cc0000;'>"))
                }
            })
            var wave_title = txt.Wave[i][lang]
            if ((lang == 'CH') && w.length == 1) wave_title = `<color style='font-weight:bold'>` + getMonsterData(w[0].ID)['4'] + '</color>'
            var temp = {
                div: [
                    {
                        p: wave_title,
                        class: 'wave_name'
                    },
                    {
                        div: monsters,
                        class: 'wave_monsters'
                    },
                    {
                        p: `[[.]]`,
                        style: {
                            'text-align': 'center',
                            'font-size': '0.8em',
                            'font-weight': 'bold'
                        },
                        data: affix0,
                        when: affix0.length,
                    }
                ],
                class: 'wave_wrap'
            }
            return temp
        }

        $('body').on('mouseenter', '.monster_card', function () {
            $(this).find('.hasimgname').show()
            $(this).find('.hasimg').css("opacity", "0.2")
        })

        $('body').on('mouseleave', '.monster_card', function () {
            $(this).find('.hasimgname').hide()
            $(this).find('.hasimg').css("opacity", "1")
        })

        $('body').on('click', '.monster_card', function () {
            window.open(`/sr/monster?lang=${lang3}&id=${$(this).attr('data-id')}&lv=${$(this).attr('data-lv')}&hlg=${$(this).attr('data-hl')}&eg=${$(this).attr('data-eg')}&def=1000`)
        })

        $('body').on('dblclick', '.title', function () {
            $('.under').toggle()
            $('.chart_container').toggle()
            $('h3').toggle()
            $('.dl_button').hide()
            $('.buff').css('color', 'white')
        })

        $('body').on('click', '.dl_button', function () {
            var toast = document.createElement('div')
            toast.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:rgba(0,0,0,0.8);color:#f29e38;padding:16px 32px;border-radius:8px;z-index:99999;font-size:16px'
            toast.textContent = '生成中...'
            document.body.appendChild(toast)

            function doCapture() {
                var el = document.querySelector('container')
                var w = el.scrollWidth
                var h = el.scrollHeight
                html2canvas(el, {
                    backgroundColor: '#1a1a2e',
                    scale: 2,
                    useCORS: true,
                    logging: false,
                    width: w,
                    height: h,
                    windowWidth: w,
                    windowHeight: h
                }).then(function (canvas) {
                    var a = document.createElement('a')
                    a.download = cur_schedule_ver + '.png'
                    a.href = canvas.toDataURL('image/png')
                    a.click()
                    toast.remove()
                }).catch(function (err) {
                    console.error('生成失败:', err)
                    alert('生成失败，请重试')
                    toast.remove()
                })
            }

            if (window.html2canvas) {
                doCapture()
            } else {
                var s = document.createElement('script')
                s.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js'
                s.onload = doCapture
                s.onerror = function () {
                    toast.remove()
                    alert('加载失败，请检查网络')
                }
                document.head.appendChild(s)
            }
        })

        $('body').on('click', '.yunli_button', function () {
            window.location.href = `/sr/yunli2`
        })

        $('body').on('click', '.emote_block_', rotate)

        function rotate() {
            var keq_emotes = ['1', '2', '3']
            $('.emote_').each(function () {
                var this_emote = keq_emotes[Math.floor(Math.random() * keq_emotes.length)]
                $(this).empty().render({
                    img: `/images/emote/Yunli/${this_emote}.png`
                })
            })
        }
    }
})