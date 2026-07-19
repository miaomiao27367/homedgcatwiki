$(function () {

    var imgpre = $('#IMGPRE').val()
    var lazy = $('#NOLAZY').val() ? '' : 'lazy'
    var dev_only = 0

    _NAME = {
        CH: '异相仲裁',
        EN: 'Anomaly Arbitration',
        JP: '異相の仲裁',
        KR: '이상 중재',
    }

    _Cycle_Trial = {
        CH: '骑士轮数：',
        EN: 'Knight Cycles: ',
    }

    _Cycle_Final = {
        CH: '王棋轮数：',
        EN: 'Checkmate Cycles: ',
    }

    init_title(_NAME[lang3] + ' ' + txt.PAGE_TITLE[lang])

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

    // 先加载 Monster_1/2 完整数据，再加载 AR.js（_maze + _schedule），最后从完整数据构建 _monster
    var _monster_full = {}

    let script_m1 = document.createElement('script')
    script_m1.src = '/sr/data/' + lang3 + '/Monster_1.js'
    document.head.append(script_m1)

    script_m1.onload = function () {
        _monster_full = _monster

        let script_m2 = document.createElement('script')
        script_m2.src = '/sr/data/' + lang3 + '/Monster_2.js'
        document.head.append(script_m2)

        script_m2.onload = function () {
            if (typeof _monster_2 !== 'undefined') {
                for (var key in _monster_2) {
                    if (!_monster_full[key]) {
                        _monster_full[key] = _monster_2[key]
                    }
                }
            }

            let script_ar = document.createElement('script')
            script_ar.src = '/sr/data/' + lang3 + '/AR.js'
            document.head.append(script_ar)

            script_ar.onload = function () {
                // AR.js 不再包含 _monster，从 Monster_1/2 完整数据构建
                var newMonster = {}
                for (var key in _monster_full) {
                    var m = _monster_full[key]
                    newMonster[key] = {
                        "1": m.Name || "",
                        "2": m.Figure || ("monsterfigure/Monster_" + key + ".png"),
                        "3": m.Weak || []
                    }
                }
                _monster = newMonster
                begin()
            }
        }
    }

    function begin() {

        console.log(window.innerWidth)
        max_index = _schedule.length

        // 构建_dict映射，将CID映射到索引
        var _dict = {}
        for (var i = 0; i < _schedule.length; i++) {
            _dict[_schedule[i]._id] = i
        }

        cur_index = _dict[$('#CID').val()]
        if (!cur_index) cur_index = 0

        if (!lazy || !dev_only) {
            $('container').render({
                template: {
                    div: [
                        {
                            p: _NAME[lang3],
                            style: {
                                'text-align': 'center',
                                'font-weight': 'bold',
                                'font-size': '1.6em',
                                'margin-bottom': '-10px',
                                'margin-top': '15px',
                            }
                        },
                        {
                            p: {
                                CH: '这是一个测试页面',
                                EN: 'This is a test page'
                            }[lang],
                            style: {
                                'text-align': 'center',
                                'font-weight': 'bold',
                                'font-size': '1.6em',
                                'margin-bottom': '10px',
                                'margin-top': '35px',
                                'color': 'red'
                            },
                            when: dev_only
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
                                    div: '',
                                    class: 'buff reward_1'
                                },
                                {
                                    div: [
                                        {
                                            p: '',
                                            class: 'target_c target_c_1'
                                        },
                                        {
                                            div: '',
                                            class: 'target_t target_t_1'
                                        },
                                    ],
                                    class: 'target',
                                },
                            ],
                            class: 'info_area'
                        },
                        {
                            div: [
                                {
                                    div: '',
                                    class: 'smallbuff a_b_0'
                                },
                                {
                                    div: '',
                                    class: 'smallbuff a_b_1'
                                },
                                {
                                    div: '',
                                    class: 'smallbuff a_b_2'
                                },
                            ],
                            class: 'a_b u_b smallbuff_wrap',
                        },
                        {
                            div: [
                                {
                                    div: [
                                        {
                                            div: [
                                                {
                                                    div: '',
                                                    class: 'a_r u_r'
                                                },
                                                {
                                                    div: '',
                                                    class: 'a_m u_m'
                                                },
                                            ],
                                            class: 'u'
                                        },
                                    ],
                                    class: 'u_l',
                                },
                                {
                                    div: [
                                        {
                                            div: [
                                                {
                                                    div: '',
                                                    class: 'b_r u_r'
                                                },
                                                {
                                                    div: '',
                                                    class: 'b_m u_m'
                                                },
                                            ],
                                            class: 'u'
                                        },
                                    ],
                                    class: 'u_l',
                                },
                                {
                                    div: [
                                        {
                                            div: [
                                                {
                                                    div: '',
                                                    class: 'c_r u_r'
                                                },
                                                {
                                                    div: '',
                                                    class: 'c_m u_m'
                                                },
                                            ],
                                            class: 'u'
                                        },
                                    ],
                                    class: 'u_l',
                                },
                            ],
                            class: 'u_l_wrapper'
                        },
                        {
                            div: [
                                {
                                    div: '',
                                    class: 'buff reward_2'
                                },
                                {
                                    div: [
                                        {
                                            p: '',
                                            class: 'target_c target_c_2'
                                        },
                                        {
                                            div: '',
                                            class: 'target_t target_t_2'
                                        },
                                    ],
                                    class: 'target',
                                },
                            ],
                            class: 'info_area'
                        },
                        {
                            div: '',
                            class: 'd_b u_b smallbuff_wrap'
                        },
                        {
                            div: [
                                {
                                    div: '',
                                    class: 'smallbuff_half d_e_3'
                                },
                                {
                                    div: '',
                                    class: 'smallbuff_half d_e_4'
                                },
                            ],
                            class: 'a_b u_b smallbuff_wrap',
                            when: window.innerWidth > 900
                        },
                        {
                            div: [
                                {
                                    div: [
                                        {
                                            div: [
                                                {
                                                    div: '',
                                                    class: 'd_r u_r'
                                                },
                                                {
                                                    div: '',
                                                    class: 'd_m u_m'
                                                },
                                            ],
                                            class: 'u'
                                        },
                                    ],
                                    class: 'u_l'
                                },
                                {
                                    div: [
                                        {
                                            div: [
                                                {
                                                    div: '',
                                                    class: 'e_r u_r'
                                                },
                                                {
                                                    div: '',
                                                    class: 'e_m u_m'
                                                },
                                            ],
                                            class: 'u'
                                        },
                                    ],
                                    class: 'u_l',
                                },
                            ],
                            class: 'u_l_wrapper',
                            when: window.innerWidth > 900
                        },
                        {
                            div: [
                                {
                                    div: '',
                                    class: 'smallbuff_half d_e_3'
                                },
                            ],
                            class: 'a_b u_b smallbuff_wrap',
                            when: window.innerWidth <= 900
                        },
                        {
                            div: [
                                {
                                    div: [
                                        {
                                            div: [
                                                {
                                                    div: '',
                                                    class: 'd_r u_r'
                                                },
                                                {
                                                    div: '',
                                                    class: 'd_m u_m'
                                                },
                                            ],
                                            class: 'u'
                                        },
                                    ],
                                    class: 'u_l'
                                },
                            ],
                            class: 'u_l_wrapper',
                            when: window.innerWidth <= 900
                        },
                        {
                            div: [
                                {
                                    div: '',
                                    class: 'smallbuff_half d_e_4'
                                },
                            ],
                            class: 'a_b u_b smallbuff_wrap',
                            when: window.innerWidth <= 900
                        },
                        {
                            div: [
                                {
                                    div: [
                                        {
                                            div: [
                                                {
                                                    div: '',
                                                    class: 'e_r u_r'
                                                },
                                                {
                                                    div: '',
                                                    class: 'e_m u_m'
                                                },
                                            ],
                                            class: 'u'
                                        },
                                    ],
                                    class: 'u_l'
                                },
                            ],
                            class: 'u_l_wrapper',
                            when: window.innerWidth <= 900
                        },
                        {
                            div: '',
                            class: 'u_g'
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
        }

        $('body').addClass(bg_name)

        if (!lazy) {
            a_section_white()
            $("head").append('<style type="text/css"></style>');
            var newStyleElement = $("head").children(':last');
            newStyleElement.html('.info_area{color:white!important}');
        }

    }

    function writeVer() {
        writeVerAfter()
    }

    function reward(id) {

        for (const i of [2, 3]) {
            var element = {
                2: '.reward_1', 
                3: '.reward_2'
            }[i]
            $(element).empty()
            var text = {
                2: {
                    CH: '骑士奖励',
                    EN: 'Knight Rewards'
                }[lang],
                3: {
                    CH: '王棋奖励',
                    EN: 'Checkmate Rewards'
                }[lang]
            }[i]
            $(element).render({
                p: text,
                width: '100%',
                class: 'reward_text'
            })
            _rewardline[id].forEach(function (t) {
                if (t.Type != i) return
                var reward_items = []
                t.Reward.forEach(function (s) {
                    reward_items.push({
                        div: [
                            {
                                img: `/images/itemicon/${s.Icon}.png`,
                                class: 'reward_img'
                            },
                            {
                                p: s.Count.toString(),
                                class: 'reward_count'
                            }
                        ],
                        class: 'reward_block'
                    })
                })
                $(element).render({
                    div: [
                        {
                            p: t.Count.toString(),
                            class: 'reward_stars'
                        },
                        {
                            div: reward_items,
                            class: 'reward_items'
                        }
                    ]
                })
            })
        }

    }

    function writeVerAfter() {
        switch_title(_schedule[mod(cur_index, max_index)].Name)
        cur_schedule_ver = _schedule[mod(cur_index, max_index)]._id
        cur_floor_data = _maze[cur_schedule_ver]
        $('.ver_text_name').html(_schedule[mod(cur_index, max_index)].Name)
        $('.ver_text_time').html(_schedule[mod(cur_index, max_index)].Time)
        writeData()
    }

    function writeData() {
        
        $('.target_c_1').html(_Cycle_Trial[lang] + '7')
        $('.target_c_2').html(_Cycle_Final[lang] + `7 / <color style='color:#FF8877'> 3 </color>`)
        $('.target_t_1').empty().render({
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
            data: cur_floor_data.TargetsTrial
        })
        $('.target_t_2').empty().render({
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
            data: cur_floor_data.TargetsFinal
        })

        for (const z of [0, 1, 2, 3, 4]) {
            var key = [
                'TrialA',
                'TrialB',
                'TrialC',
                'FinalEasy',
                'FinalHard',
            ][z]
            var buff_key = [
                'BuffA',
                'BuffB',
                'BuffC',
                'FinalBuffs',
                'FinalBuffs',
            ][z]
            var tag_key = [
                '',
                '',
                '',
                'FinalTagsEasy',
                'FinalTagsHard',
            ][z]
            var elem_key = [
                'ElemA',
                'ElemB',
                'ElemC',
                'ElemFinal',
                'ElemFinal',
            ][z]
            var letter = [
                'a',
                'b',
                'c',
                'd',
                'e'
            ][z]
            var show_text = [
                (lang == 'CH') ? '普通总血量' : 'Knight I',
                (lang == 'CH') ? '骑士二' : 'Knight II',
                (lang == 'CH') ? '骑士三' : 'Knight III',
                (lang == 'CH') ? '将杀王棋' : 'Checkmate',
                (lang == 'CH') ? '将杀王棋•绝境' : 'Checkmate: Zugzwang',
            ][z]
            $(`.${letter}_r`).empty().render({
                template: [
                    {
                        div: [
                            {
                                p: show_text + ' Lv' + cur_floor_data[key].Level
                            },
                            {
                                img: function (k) {
                                    return imgpre + 'images/Element/' + k.data + '.png'
                                },
                                class: 'elem_',
                                data: cur_floor_data[elem_key],
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
            $(`.${letter}_m`).empty().render({
                template: Stage(cur_floor_data[key], letter)
            })
            if (z < 3) {
                var need_desc = [
                    {
                        p: show_text,
                        class: 'smallbuff_name'
                    }
                ]
                for (const buff_data of cur_floor_data[buff_key]) {
                    need_desc.push({
                        p: `<b>${buff_data._id} ${buff_data.Name}</b><br>${buff_data.Desc}`,
                        class: 'smallbuff_desc'
                    })
                }
                $(`.a_b_${z}`).empty().render(need_desc)
            } else {
                $(`.${letter}_b`).empty()
                for (const b of cur_floor_data[buff_key]) {
                    $(`.${letter}_b`).render({
                        template: {
                            div: [
                                {
                                    p: b.Name + '<br>' + b._id,
                                    class: 'smallbuff_name'
                                },
                                {
                                    p: b.Desc,
                                    class: 'smallbuff_desc'
                                },
                            ],
                            class: 'smallbuff'
                        }
                    })
                }
                var need_desc = [
                    {
                        p: show_text,
                        class: 'smallbuff_name'
                    }
                ]
                for (const buff_data of cur_floor_data[tag_key]) {
                    need_desc.push({
                        p: `<b>${buff_data._id} ${buff_data.Name}</b><br>${buff_data.Desc}`,
                        class: 'smallbuff_desc'
                    })
                }
                $(`.d_e_${z}`).empty().render(need_desc)
            }
        }

        $('.u_g').empty()
        generate_boss_guide('.u_g', cur_floor_data.BossGuides)

        reward(cur_floor_data.RewardLine)

        rotate()

        // 渲染总血量演化图表
        renderHpChart()

        console.log("FINISH")

    }

    function renderHpChart() {
        // 从_schedule中获取版本名称，按id升序排列（id越高越右边）
        var versionNames = [];
        // 先按_id升序排序_schedule
        var sortedSchedule = _schedule.slice().sort(function(a, b) {
            return a._id - b._id;
        });
        for (var i = 0; i < sortedSchedule.length; i++) {
            if (sortedSchedule[i].Time != ' - ') {
                versionNames.push(sortedSchedule[i].Name);
            }
        }
        
        // 获取当前版本在图表中的索引
        var currentIndex = _arbitrationhp.Index[cur_schedule_ver];
        if (currentIndex === undefined) currentIndex = 0;
        
        myChart = echarts.init(document.getElementById('chart'))
        var option = {
            title: {
                text: (lang == 'CH') ? '异象仲裁每期总血量演化' : 'Anomaly Arbitration HP Evolution',
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
                data: [
                    (lang == 'CH') ? '普通总血量' : 'Knight I',
                    (lang == 'CH') ? '骑士二' : 'Knight II',
                    (lang == 'CH') ? '骑士三' : 'Knight III',
                    (lang == 'CH') ? '将杀王棋' : 'Checkmate',
                    (lang == 'CH') ? '将杀王棋·绝境' : 'Checkmate: Zugzwang'
                ],
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
                data: versionNames,
                axisLabel: {
                    color: '#000',
                    padding: [5, 0],
                }
            },
            yAxis: {
                type: 'value',
                axisLabel: {
                    formatter: function(value) {
                        if (value >= 10000) {
                            return (value / 10000).toFixed(1) + '万';
                        }
                        return value;
                    }
                }
            },
            series: (function() {
                // 定义所有折线配置
                var allSeries = [
                    {
                        name: (lang == 'CH') ? '普通总血量' : 'Knight I',
                        key: 'TrialA',
                        color: '#cc0000'
                    },
                    {
                        name: (lang == 'CH') ? '骑士二' : 'Knight II',
                        key: 'TrialB',
                        color: '#2545ba'
                    },
                    {
                        name: (lang == 'CH') ? '骑士三' : 'Knight III',
                        key: 'TrialC',
                        color: '#f29e38'
                    },
                    {
                        name: (lang == 'CH') ? '将杀王棋' : 'Checkmate',
                        key: 'FinalEasy',
                        color: '#00cc00'
                    },
                    {
                        name: (lang == 'CH') ? '将杀王棋·绝境' : 'Checkmate: Zugzwang',
                        key: 'FinalHard',
                        color: '#9900cc'
                    }
                ];
                
                // 过滤出有有效数据的折线
                var validSeries = [];
                for (var i = 0; i < allSeries.length; i++) {
                    var data = _arbitrationhp[allSeries[i].key];
                    // 检查数据是否存在且非空，并且不全是0
                    if (data && data.length > 0 && data.some(function(val) { return val > 0; })) {
                        validSeries.push({
                            name: allSeries[i].name,
                            type: 'line',
                            data: data,
                            lineStyle: {
                                color: allSeries[i].color
                            },
                            itemStyle: {
                                color: allSeries[i].color
                            }
                        });
                    }
                }
                return validSeries;
            })()
        }
        if ($("#NOLAZY").val()) option.tooltip.show = false
        myChart.setOption(option)

        // 高亮当前版本数据
        myChart.dispatchAction({
            type: 'showTip',
            dataIndex: currentIndex,
            seriesIndex: 0,
        })
    }

    $('body').on('mouseleave', '#chart', function () {
        var currentIndex = _arbitrationhp.Index[cur_schedule_ver];
        if (currentIndex === undefined) currentIndex = 0;
        myChart.dispatchAction({
            type: 'showTip',
            dataIndex: currentIndex,
            seriesIndex: 0,
        })
    })

    function Stage(l, letter) {
        var waves = []
        l.Monsters.forEach(function (w, i) {
            waves.push(Wave(i, w, l.Level, l.HardLevelGroup, l.EliteGroup, letter))
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
        var strId = String(id)
        for (var trim = 1; trim <= 3; trim++) {
            if (strId.length <= trim) break
            var baseId = strId.substring(0, strId.length - trim)
            if (_monster_full[baseId]) {
                var m = _monster_full[baseId]
                return {
                    "1": m.Name || "",
                    "2": m.Figure || ("monsterfigure/Monster_" + baseId + ".png"),
                    "3": m.Weak || []
                }
            }
        }
        return { "1": "", "2": "monsterfigure/None.png", "3": [] }
    }

    function Wave(i, w, stage_lv, stage_hlg, stage_eg, letter) {
        var monsters = []
        var monicon = ''
        if (['a', 'b', 'c'].includes(letter)) {
            monicon = 'monicon_1'
        } else {
            monicon = 'monicon_2'
        }
        w.forEach(function (t) {
            var me = getMonsterData(t.ID)
            monsters.push({
                span: [
                    {
                        div: [
                            {
                                img: '/images/' + me["2"],
                                class: `${monicon} hasimg`,
                                event: {
                                    load: function (d) {
                                        $(d.sender).siblings('.monnameload').hide()
                                    },
                                    error: function (d) {
                                        $(d.sender).css("opacity", "0")
                                        $(d.sender).removeClass('hasimg')
                                        $(d.sender).siblings('.hasimgname').removeClass('hasimgname')
                                        $(d.sender).parent().addClass(monicon)
                                    },
                                },
                                a: {
                                    loading: lazy
                                }
                            },
                            {
                                div: {
                                    p: me["1"]
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
                                    data: me["3"],
                                    a: {
                                        loading: lazy
                                    }
                                },
                                class: 'monelem'
                            },
                            {
                                span: showstance(t.Stance) + (t.StanceCount && t.StanceCount > 1 ? ('×' + t.StanceCount) : ''),
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
                                    if (t.HPCount && t.HPCount > 1) {
                                        s += '<b>×' + t.HPCount + '</b>'
                                    }
                                    return s
                                },
                                class: 'monname',
                                when: t.HP
                            },
                            {
                                br: '',
                                when: t.HP && (t.SPD || me["6"])
                            },
                            {
                                span: function () {
                                    s = '<b><color style="color:#2545ba;">' + t.SPD.toString() + '</color></b>'
                                    return s
                                },
                                class: 'monname',
                                when: t.SPD
                            },
                            {
                                br: '',
                                when: t.SPD && me["6"]
                            },
                            {
                                span: function () {
                                    if (me["6"] < 100) {
                                        return {
                                            CH: '行动提前',
                                            EN: 'Advance'
                                        }[lang] + ' <b><color style="color:#cc0000;">' + (100 - me["6"]).toString() + '%</color></b>'
                                    } else {
                                        return {
                                            CH: '行动延后',
                                            EN: 'Delay'
                                        }[lang] + ' <b><color style="color:#cc0000;">' + (me["6"] - 100).toString() + '%</color></b>'
                                    }
                                },
                                when: me["6"],
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
        })
        var wave_title = txt.Wave[i][lang]
        if ((lang == 'CH') && w.length == 1) wave_title = `<color style='font-weight:bold'>` +  getMonsterData(w[0].ID)['1'] + '</color>'
        var wave_wrap_data = [
            {
                p: wave_title,
                class: 'wave_name'
            }
        ]
        var monsters_split = (window.innerWidth <= 600) ? list_split(monsters, 100) : list_split(monsters, 5)
        for (const d_ of monsters_split) {
            wave_wrap_data.push({
                div: d_,
                class: 'wave_monsters'
            })
        }
        var temp = {
            div: wave_wrap_data,
            class: 'wave_wrap'
        }
        return temp
    }

    function list_split(data_list, split_num) {
        var temp = []
        var out = []
        for (const i in data_list) {
            if ((i > 0) && (i % split_num == 0)) {
                out.push(temp)
                temp = []
            }
            temp.push(data_list[i])
        }
        out.push(temp)
        return out
    }

    function hide(n) {
        //return n
        return n.replaceAll("0", "█").replaceAll("1", "█").replaceAll("2", "█").replaceAll("3", "█").replaceAll("4", "█").replaceAll("5", "█").replaceAll("6", "█").replaceAll("7", "█").replaceAll("8", "█").replaceAll("9", "█")
    }

    function generate_boss_guide(p, d) {
        if (!d) return
        if (!d.length) return
        if (d.length == 1) split_index = 1
        if (d.length == 2) split_index = 2
        if (d.length >= 3) split_index = 3
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
                class: `a_section a_section_split_${split_index}`
            })
        })
    }

    $('body').on('click', '.ver_text', function () {
        var pop = poplayer({
            header: '',
            width: '95%',
            template: [
                {
                    div: function (k) {
                        _schedule.forEach(function (t, i) {
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
                        _schedule.forEach(function (t, i) {
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

    $('body').on('click', '.emote_block_', rotate)

    $('body').on('click', '.yunli_button', function () {
        window.location.href = `/sr/yunli5`
    })

    function rotate() {
        var keq_emotes = ['1', '2', '3']
        $('.emote_').each(function () {
            var this_emote = keq_emotes[Math.floor(Math.random() * keq_emotes.length)]
            $(this).empty().render({
                img: `/images/emote/Yunli/${this_emote}.png`
            })
        })
    }
})