$(function () {

    var imgpre = $('#IMGPRE').val()
    var lazy = $('#NOLAZY').val() ? '' : 'lazy'

    init_title(txt.N_A[lang3] + ' ' + txt.PAGE_TITLE[lang])

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
    var starButton = null
    var showStar = false

    var has_2 = 1 // Secondary loading not implemented yet

    let script_computer = document.createElement('script')
    script_computer.src = '/sr/data/' + lang3 + '/AS.js'
    document.head.append(script_computer)
    script_computer.onload = begin

    function begin() {

        // 加载星启模式数据
        let script_star = document.createElement('script')
        script_star.src = '/sr/data/' + lang3 + '/AS_star.js'
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
                        p: txt.N_A[lang3],
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
                        ],
                        class: 'info_area'
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
                                    click: function() {
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
                                        class: 'u_s'
                                    }
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
                                style: { top: '0' }
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
                                        class: 'l_s'
                                    },
                                ],
                                class: 'l'
                            },
                            {
                                div: [
                                    {
                                        div: '',
                                        class: 'u u_h',
                                        style: {
                                            'width':'100%',
                                            'box-sizing': 'border-box',
                                            'border': 'none',
                                            'background-color': '#27363E',
                                            'color': '#eeeeee'
                                        }
                                    },
                                    {
                                        div: '',
                                        class: 'u u_b_b',
                                        style: {
                                            'width':'100%',
                                            'box-sizing': 'border-box',
                                            'border': 'none',
                                            'background-color': '#27363E',
                                            'color': '#eeeeee'
                                        }
                                    },
                                    {
                                        div: '',
                                        class: 'u u_b',
                                        style: {
                                            'width':'100%',
                                            'box-sizing': 'border-box',
                                            'border': 'none',
                                            'background-color': '#27363E',
                                            'color': '#eeeeee'
                                        }
                                    },
                                    {
                                        div: '',
                                        class: 'u u_g',
                                        when: lazy.length,
                                        style: {
                                            'width':'100%',
                                            'box-sizing': 'border-box',
                                            'border': 'none',
                                            'background-color': '#27363E',
                                            'color': '#eeeeee'
                                        }
                                    },
                                ],
                                class: 'u_b_c',
                                style: {
                                    display: 'flex',
                                    'flex-direction': 'column',
                                    'flex': '1',
                                    'min-width': '0',
                                    'margin': '6px 0px',
                                }
                            },
                            {
                                div: [
                                    {
                                        div: '',
                                        class: 'star star_h',
                                        style: {
                                            'width':'100%',
                                            'box-sizing': 'border-box',
                                            'border': 'none',
                                            'background-color': '#27363E',
                                            'color': '#eeeeee'
                                        }
                                    },
                                    {
                                        div: '',
                                        class: 'star star_s_b',
                                        style: {
                                            'width':'100%',
                                            'box-sizing': 'border-box',
                                            'border': 'none',
                                            'background-color': '#27363E',
                                            'color': '#eeeeee'
                                        }
                                    },
                                    {
                                        div: '',
                                        class: 'star star_s_c',
                                        style: {
                                            'width':'100%',
                                            'box-sizing': 'border-box',
                                            'border': 'none',
                                            'background-color': '#27363E',
                                            'color': '#eeeeee'
                                        }
                                    },
                                    {
                                        div: '',
                                        class: 'star star_s_g',
                                        when: lazy.length,
                                        style: {
                                            'width':'100%',
                                            'box-sizing': 'border-box',
                                            'border': 'none',
                                            'background-color': '#27363E',
                                            'color': '#eeeeee'
                                        }
                                    },
                                ],
                                class: 'star_b_c',
                                style: {
                                    display: 'flex',
                                    'flex-direction': 'column',
                                    'flex': '1',
                                    'min-width': '0'
                                }
                            },
                            {
                                div: [
                                    {
                                        div: '',
                                        class: 'l l_h',
                                        style: {
                                            'width':'100%',
                                            'box-sizing': 'border-box',
                                            'border': 'none',
                                            'background-color': '#27363E',
                                            'color': '#eeeeee'
                                        }
                                    },
                                    {
                                        div: '',
                                        class: 'l l_b_b',
                                        style: {
                                            'width':'100%',
                                            'box-sizing': 'border-box',
                                            'border': 'none',
                                            'background-color': '#27363E',
                                            'color': '#eeeeee'
                                        }
                                    },
                                    {
                                        div: '',
                                        class: 'l l_b',
                                        style: {
                                            'width':'100%',
                                            'box-sizing': 'border-box',
                                            'border': 'none',
                                            'background-color': '#27363E',
                                            'color': '#eeeeee'
                                        }
                                    },
                                    {
                                        div: '',
                                        class: 'l l_g',
                                        when: lazy.length,
                                        style: {
                                            'width':'100%',
                                            'box-sizing': 'border-box',
                                            'border': 'none',
                                            'background-color': '#27363E',
                                            'color': '#eeeeee'
                                        }
                                    },
                                ],
                                class: 'l_b_c',
                                style: {
                                    display: 'flex',
                                    'flex-direction': 'column',
                                    'flex': '1',
                                    'min-width': '0',
                                    'margin': '6px 0px',
                                }
                            },
                        ],
                        class: 'u_l',
                        when: (window.innerWidth <= 800)
                    },
                    {
                        div: [
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
                                                class: 'u_s'
                                            }
                                        ],
                                        class: 'u',
                                        style: {
                                            flex: '1',
                                            'min-width': '0',
                                            width: 'auto'
                                        }
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
                                        style: {
                                            flex: '1',
                                            'min-width': '0',
                                            width: 'auto',
                                            top: '0'
                                        }
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
                                                class: 'l_s'
                                            },
                                        ],
                                        class: 'l',
                                        style: {
                                            flex: '1',
                                            'min-width': '0',
                                            width: 'auto'
                                        }
                                    },
                                ],
                                class: 'u_l_w',
                                style: {
                                    display: 'flex',
                                    'justify-content': 'space-evenly'
                                }
                            },
                            {
                                div: [
                                    {
                                        div: [
                                            {
                                                div: '',
                                                class: 'u u_h',
                                                style: {
                                                    'box-sizing': 'border-box',
                                                    'border': 'none',
                                                    'background-color': '#27363E',
                                                    'color': '#eeeeee',
                                                    'width': '100%'
                                                }
                                            },
                                            {
                                                div: '',
                                                class: 'u u_b_b',
                                                style: {
                                                    'box-sizing': 'border-box',
                                                    'border': 'none',
                                                    'background-color': '#27363E',
                                                    'color': '#eeeeee',
                                                    'width': '100%'
                                                }
                                            },
                                            {
                                                div: '',
                                                class: 'u u_b',
                                                style: {
                                                    'box-sizing': 'border-box',
                                                    'border': 'none',
                                                    'background-color': '#27363E',
                                                    'color': '#eeeeee',
                                                    'width': '100%'
                                                }
                                            },
                                            {
                                                div: '',
                                                class: 'u u_g',
                                                when: lazy.length,
                                                style: {
                                                    'box-sizing': 'border-box',
                                                    'border': 'none',
                                                    'background-color': '#27363E',
                                                    'color': '#eeeeee',
                                                    'width': '100%'
                                                }
                                            },
                                        ],
                                        class: 'u_b_c',
                                        style: {
                                            display: 'flex',
                                            'flex-direction': 'column',
                                            'flex': '1',
                                            'min-width': '0',
                                            'margin': '6px 0px',
                                        }
                                    },
                                    {
                                        div: [
                                            {
                                                div: '',
                                                class: 'star star_h',
                                                style: {
                                                    'box-sizing': 'border-box',
                                                    'border': 'none',
                                                    'background-color': '#27363E',
                                                    'color': '#eeeeee',
                                                    'width': '100%'
                                                }
                                            },
                                            {
                                                div: '',
                                                class: 'star star_s_b',
                                                style: {
                                                    'box-sizing': 'border-box',
                                                    'border': 'none',
                                                    'background-color': '#27363E',
                                                    'color': '#eeeeee',
                                                    'width': '100%'
                                                }
                                            },
                                            {
                                                div: '',
                                                class: 'star star_s_c',
                                                style: {
                                                    'box-sizing': 'border-box',
                                                    'border': 'none',
                                                    'background-color': '#27363E',
                                                    'color': '#eeeeee',
                                                    'width': '100%'
                                                }
                                            },
                                            {
                                                div: '',
                                                class: 'star star_s_g',
                                                when: lazy.length,
                                                style: {
                                                    'box-sizing': 'border-box',
                                                    'border': 'none',
                                                    'background-color': '#27363E',
                                                    'color': '#eeeeee',
                                                    'width': '100%'
                                                }
                                            },
                                        ],
                                        class: 'star_b_c',
                                        style: {
                                            display: 'flex',
                                            'flex-direction': 'column',
                                            'flex': '1',
                                            'min-width': '0'
                                        }
                                    },
                                    {
                                        div: [
                                            {
                                                div: '',
                                                class: 'l l_h',
                                                style: {
                                                    'box-sizing': 'border-box',
                                                    'border': 'none',
                                                    'background-color': '#27363E',
                                                    'color': '#eeeeee',
                                                    'width': '100%'
                                                }
                                            },
                                            {
                                                div: '',
                                                class: 'l l_b_b',
                                                style: {
                                                    'box-sizing': 'border-box',
                                                    'border': 'none',
                                                    'background-color': '#27363E',
                                                    'color': '#eeeeee',
                                                    'width': '100%'
                                                }
                                            },
                                            {
                                                div: '',
                                                class: 'l l_b',
                                                style: {
                                                    'box-sizing': 'border-box',
                                                    'border': 'none',
                                                    'background-color': '#27363E',
                                                    'color': '#eeeeee',
                                                    'width': '100%'
                                                }
                                            },
                                            {
                                                div: '',
                                                class: 'l l_g',
                                                when: lazy.length,
                                                style: {
                                                    'box-sizing': 'border-box',
                                                    'border': 'none',
                                                    'background-color': '#27363E',
                                                    'color': '#eeeeee',
                                                    'width': '100%'
                                                }
                                            },
                                        ],
                                        class: 'l_b_c',
                                        style: {
                                            display: 'flex',
                                            'flex-direction': 'column',
                                            'flex': '1',
                                            'min-width': '0',
                                            'margin': '6px 0px',
                                        }
                                    },
                                ],
                                class: 'u_l_w',
                                style: {
                                    display: 'flex',
                                    'justify-content': 'space-evenly'
                                }
                            },
                        ],
                        class: 'u_l',
                        style: {
                            'flex-direction': 'column'
                        },
                        when: (window.innerWidth > 800)
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

        if (!lazy) {
            a_section_white()
            $("head").append('<style type="text/css"></style>');
            var newStyleElement = $("head").children(':last');
            newStyleElement.html('.info_area{color:white!important} .u_h,.u_b_b,.u_b,.l_h,.l_b_b,.l_b{color:white!important}');
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
        switch_title(_chaosschedule[mod(cur_index, max_index)].Name + ' ' + _chaosschedule[mod(cur_index, max_index)]._id)
        cur_schedule_ver = _chaosschedule[mod(cur_index, max_index)]._id
        $('.ver_text_name').html(_chaosschedule[mod(cur_index, max_index)].Name + ' ' + _chaosschedule[mod(cur_index, max_index)]._id)
        $('.ver_text_time').html(_chaosschedule[mod(cur_index, max_index)].Time)
        writeData()
    }

    function writeData() {
        cur_phase_data = _chaos[mod(cur_index, max_index)]
        cur_floor_data = lm(_chaos[mod(cur_index, max_index)].Floors, cur_floor)
        $('.dpc').html(txt.DPC_A[lang] + '<b><color style="color:#f29e38;">' + cur_floor_data.HPAS + '</color></b>')
        $('.f_text').html(cur_floor_data.Floor)
        var buff = _chaos[mod(cur_index, max_index)].Buff
        if (!buff) buff = cur_floor_data.Buff
        $('.buff_name').html(buff.Name + '<br>' + buff._id)
        $('.buff_desc').html(buff.Desc)
        if (buff.Extra && buff.Extra.length) {
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
        $('.u_s').empty().render({
            template: RES(cur_floor_data.Upper)
        })
        $('.l_m').empty()
        $('.l_m').render({
            template: Lineup(cur_floor_data.Lower)
        })
        $('.l_s').empty().render({
            template: RES(cur_floor_data.Lower)
        })
        
        // Star Mode 渲染 - 只在第12层显示（cur_floor=-1对应第12层）
        var isFloor12 = (cur_floor === -1);
        // 检查星启模式数据是否存在且当前版本有对应数据
        var star_data = typeof _AS_star !== 'undefined' && _AS_star ? _AS_star[cur_schedule_ver] : null;
        if (showStar && isFloor12 && star_data) {
            $('.star, .star_b_c').show();
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
            $('.star, .star_b_c').hide();
            $('.slider_switch').removeClass('slider_on');
        }
        $('.u_b').empty()
        $('.u_b').render([
            {
                p: txt.AS_Mechanics[lang3],
                style: {
                    'line-height': '1.7',
                    'margin': '0',
                    'font-weight': 'bold',
                },
                class: 'buff_name b1'
            },
            {
                p: txt.AS_Mechanics[lang3].replaceAll('＋', '－'),
                style: {
                    'line-height': '1.7',
                    'margin': '0',
                    'font-weight': 'bold',
                },
                class: 'buff_name b2'
            }
        ])
        uc_ee_list = []
        cur_phase_data.UC.forEach(function (w) {
            var v, show;
            if (typeof w === 'object') {
                v = w;
                show = `<b>${v._id} ${v.Name}</b><br>${v.Desc}`;
            } else {
                v = _mb[w];
                show = `<b>${w} ${v.Name}</b><br>${v.Desc}`;
                for (ee_id of v.EE) {
                    if (!uc_ee_list.includes(ee_id)) {
                        show += `<br><b>${_ee[ee_id].Name}</b><br>${_ee[ee_id].Desc}`;
                    }
                    uc_ee_list.push(ee_id);
                }
            }
            $('.u_b').render({
                p: show,
                style: {
                    'line-height': '1.7',
                    'margin-bottom': '0',
                }
            })
        })
        $('.u_b_b').empty().render([
            {
                p: txt.Choose_One[lang3],
                style: {
                    'line-height': '1.7',
                    'margin': '0',
                    'font-weight': 'bold',
                },
                class: 'buff_name b1'
            },
            {
                p: txt.Choose_One[lang3].replaceAll('＋', '－'),
                style: {
                    'line-height': '1.7',
                    'margin': '0',
                    'font-weight': 'bold',
                },
                class: 'buff_name b2'
            }
        ])
        cur_phase_data.UB.forEach(function (v) {
            $('.u_b_b').render({
                p: `<b>${v._id} ${v.Name}</b><br>${v.Desc}`,
                style: {
                    'line-height': '1.7',
                    'margin-bottom': '0',
                }
            })
        })
        $('.l_b').empty()
        $('.l_b').render([
            {
                p: txt.AS_Mechanics[lang3],
                style: {
                    'line-height': '1.7',
                    'margin': '0',
                    'font-weight': 'bold',
                },
                class: 'buff_name b1'
            },
            {
                p: txt.AS_Mechanics[lang3].replaceAll('＋', '－'),
                style: {
                    'line-height': '1.7',
                    'margin': '0',
                    'font-weight': 'bold',
                },
                class: 'buff_name b2'
            }
        ])
        lc_ee_list = []
        cur_phase_data.LC.forEach(function (w) {
            var v, show;
            if (typeof w === 'object') {
                v = w;
                show = `<b>${v._id} ${v.Name}</b><br>${v.Desc}`;
            } else {
                v = _mb[w];
                show = `<b>${w} ${v.Name}</b><br>${v.Desc}`;
                for (ee_id of v.EE) {
                    if (!lc_ee_list.includes(ee_id)) {
                        show += `<br><b>${_ee[ee_id].Name}</b><br>${_ee[ee_id].Desc}`;
                    }
                    lc_ee_list.push(ee_id);
                }
            }
            $('.l_b').render({
                p: show,
                style: {
                    'line-height': '1.7',
                    'margin-bottom': '0',
                }
            })
        })
        $('.l_b_b').empty().render([
            {
                p: txt.Choose_One[lang3],
                style: {
                    'line-height': '1.7',
                    'margin': '0',
                    'font-weight': 'bold',
                },
                class: 'buff_name b1'
            },
            {
                p: txt.Choose_One[lang3].replaceAll('＋', '－'),
                style: {
                    'line-height': '1.7',
                    'margin': '0',
                    'font-weight': 'bold',
                },
                class: 'buff_name b2'
            }
        ])
        cur_phase_data.LB.forEach(function (v) {
            $('.l_b_b').render({
                p: `<b>${v._id} ${v.Name}</b><br>${v.Desc}`,
                style: {
                    'line-height': '1.7',
                    'margin-bottom': '0',
                }
            })
        })

        // 星启模式：独立渲染星启模式的关卡效果和赛季效果数据
        $('.star_s_c').empty().render([
            {
                p: txt.AS_Mechanics[lang3],
                style: {
                    'line-height': '1.7',
                    'margin': '0',
                    'font-weight': 'bold',
                },
                class: 'buff_name b1'
            },
            {
                p: txt.AS_Mechanics[lang3].replaceAll('＋', '－'),
                style: {
                    'line-height': '1.7',
                    'margin': '0',
                    'font-weight': 'bold',
                    'font-size': '15px',
                },
                class: 'buff_name b2'
            }
        ])
        $('.star_s_b').empty().render([
            {
                p: txt.Choose_One[lang3],
                style: {
                    'line-height': '1.7',
                    'margin': '0',
                    'font-weight': 'bold',
                },
                class: 'buff_name b1'
            },
            {
                p: txt.Choose_One[lang3].replaceAll('＋', '－'),
                style: {
                    'line-height': '1.7',
                    'margin': '0',
                    'font-weight': 'bold',
                    'font-size': '15px',
                },
                class: 'buff_name b2'
            }
        ])
        $('.star_s_g').empty()
        if (showStar && isFloor12 && star_data) {
            // 星启模式 SC（推荐角色）
            if (star_data.SC && star_data.SC.length) {
                var star_sc_ee_list = []
                star_data.SC.forEach(function (w) {
                    var v, show;
                    if (typeof w === 'object') {
                        v = w;
                        show = `<b>${v._id} ${v.Name}</b><br>${v.Desc}`;
                    } else {
                        v = _mb[w];
                        show = `<b>${w} ${v.Name}</b><br>${v.Desc}`;
                        for (var ee_id of v.EE) {
                            if (!star_sc_ee_list.includes(ee_id)) {
                                show += `<br><b>${_ee[ee_id].Name}</b><br>${_ee[ee_id].Desc}`;
                            }
                            star_sc_ee_list.push(ee_id);
                        }
                    }
                    $('.star_s_c').render({
                        p: show,
                        style: {
                            'line-height': '1.7',
                            'margin-bottom': '0',
                        }
                    })
                })
            }
            // 星启模式 SB（关卡效果）
            if (star_data.SB && star_data.SB.length) {
                star_data.SB.forEach(function (v) {
                    $('.star_s_b').render({
                        p: `<b>${v._id} ${v.Name}</b><br>${v.Desc}`,
                        style: {
                            'line-height': '1.7',
                            'margin-bottom': '0',
                        }
                    })
                })
            }
            // 星启模式 SG（关卡阵容）
            if (star_data.SG && star_data.SG.length) {
                $('.star_s_g').render(Guide(star_data.SG))
            }
        }

        $('.u_g').empty().render(Guide(cur_phase_data.UG))
        $('.l_g').empty().render(Guide(cur_phase_data.LG))

        rotate()
        var floor_name = $('.f_text').html()

        $('.u_h').empty().render([
            {
                p: txt.HDGNotes[lang3],
                style: {
                    'line-height': '1.7',
                    'margin': '0',
                    'font-weight': 'bold',
                },
                class: 'buff_name b1'
            },
            {
                p: txt.HDGNotes[lang3].replaceAll('＋', '－'),
                style: {
                    'line-height': '1.7',
                    'margin': '0',
                    'font-weight': 'bold',
                },
                class: 'buff_name b2'
            }
        ])
        $('.l_h').empty().render([
            {
                p: txt.HDGNotes[lang3],
                style: {
                    'line-height': '1.7',
                    'margin': '0',
                    'font-weight': 'bold',
                },
                class: 'buff_name b1'
            },
            {
                p: txt.HDGNotes[lang3].replaceAll('＋', '－'),
                style: {
                    'line-height': '1.7',
                    'margin': '0',
                    'font-weight': 'bold',
                },
                class: 'buff_name b2'
            }
        ])

        generate_boss_guide('.u_h', cur_phase_data.UpperGuide)
        generate_boss_guide('.l_h', cur_phase_data.LowerGuide)
        $('.star_h').empty().render([
            {
                p: txt.HDGNotes[lang3],
                style: {
                    'line-height': '1.7',
                    'margin': '0',
                    'font-weight': 'bold',
                },
                class: 'buff_name b1'
            },
            {
                p: txt.HDGNotes[lang3].replaceAll('＋', '－'),
                style: {
                    'line-height': '1.7',
                    'margin': '0',
                    'font-weight': 'bold',
                    'font-size': '15px',
                },
                class: 'buff_name b2'
            }
        ])
        generate_boss_guide('.star_h', null)

        if (window.innerWidth <= 800) {
            $('.b1').siblings().hide()
        } else {
            $('.b1').hide()
        }
        
        myChart = echarts.init(document.getElementById('chart'))
        var option = {
            title: {
                text: txt.Chart_Title_AS[lang].replace('#', floor_name),
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
                trigger: 'axis'
            },
            grid: {
                left: '3%',
                right: '4%',
                top: '20%',
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
                    name: txt.Fiction_HP[lang],
                    type: 'line',
                    data: _chaoshp[floor_name].HP,
                    lineStyle: {
                        color: '#cc0000'
                    },
                    itemStyle: {
                        color: '#cc0000'
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

        console.log("FINISH")

    }

    function generate_boss_guide(p, i) {
        if (!i) {
            $(p).render([
                {
                    p: txt.Chart_Subtitle[lang],
                    //class: 'bossguide_p',
                    style: {
                        'text-align': 'center',
                        color: '#FFD780',
                        'margin-bottom': '9px',
                        'margin-top': '12px',
                    }
                },
                {
                    div: {
                        img: '/images/emote/Yunli/1.png'
                    },
                    class: 'yunli'
                },
                {
                    p: {
                        CH: '(๑>؂<๑)<br>被云璃吃掉了，嗷呜！<br>下次再来看看吧~',
                        EN: '(๑>؂<๑)<br>Oh no, Yunli ate this!<br>Come back again next time~'
                    }[lang],
                    style: {
                        'text-align': 'center',
                        'line-height': '2',
                    }
                }
            ])
            return
        }
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
                //class: 'bossguide_p',
                style: {
                    'line-height': '2',
                    'margin-bottom': '0',
                }
            })
        }
        $(p).render([
            {
                div: {
                    img: '/images/' + guide_data.Icon,
                    class: 'bossguide_img'
                },
                class: 'bossguide_img_w'
            },
            {
                p: guide_data.Name,
                //class: 'bossguide_p',
                style: {
                    'text-align': 'center',
                    'font-weight': 'bold',
                    'margin-bottom': '9px',
                    'margin-top': '12px',
                }
            },
            {
                p: txt.Chart_Subtitle[lang],
                //class: 'bossguide_p',
                style: {
                    'text-align': 'center',
                    color: '#FFD780',
                    'margin-bottom': '9px',
                    'margin-top': '12px',
                }
            },
        ].concat(lis))
    }

    function text_process(t) {
        return t.replaceAll(`#`, `</color>`).replaceAll(`@`, `<color style='color:#FFD780'>`)
    }

    $('body').on('click', '.u_b .buff_name, .l_b .buff_name', function () {
        $('.u_b p').toggle()
        $('.l_b p').toggle()
    })

    $('body').on('click', '.u_g .buff_name, .l_g .buff_name', function () {
        $('.u_g p').toggle()
        $('.l_g p').toggle()
    })

    $('body').on('click', '.u_b_b .buff_name, .l_b_b .buff_name', function () {
        $('.u_b_b p').toggle()
        $('.l_b_b p').toggle()
    })

    $('body').on('click', '.u_h .buff_name, .l_h .buff_name', function () {
        $('.u_h p').toggle()
        $('.l_h p').toggle()
        $('.u_h .yunli, .l_h .yunli').toggle()
        $('.u_h .bossguide_img_w, .l_h .bossguide_img_w').toggle()
    })

    $('body').on('click', '.star_s_c .buff_name', function () {
        $('.star_s_c p').toggle()
    })

    $('body').on('click', '.star_s_b .buff_name', function () {
        $('.star_s_b p').toggle()
    })

    $('body').on('click', '.star_s_g .buff_name', function () {
        $('.star_s_g p').toggle()
    })

    $('body').on('click', '.star_h .buff_name', function () {
        $('.star_h p').toggle()
        $('.star_h .yunli').toggle()
        $('.star_h .bossguide_img_w').toggle()
    })

    function Guide(phase_ids) {
        var infos = []
        phase_ids.forEach(function (id) {
            var info = ''
            if (typeof id === 'object') {
                info += '<b>' + id.Name + '</b><br>'
                info += id.Desc + '<br>'
                info += '<color style="color:#f29e38">' + (id.Answer || '') + '</color>'
            } else {
                info += '<b>' + _phaseinfos[id].Name + '</b><br>'
                info += _phaseinfos[id].Desc + '<br>'
                info += '<color style="color:#f29e38">' + _phaseinfos[id].Answer + '</color>'
                _phaseinfos[id].Skills.forEach(function (d) {
                    info += '<div style="height:0.8em;width:100%;margin:0"></div><color style="color:#FFE14B">' + d.Name + '</color>'
                    info += '<br>• ' + d.Text.join('<br>• ')
                })
            }
            infos.push(info)
        })
        return [
            {
                p: txt.AS_Guide[lang3],
                style: {
                    'line-height': '1.7',
                    'margin': '0',
                    'font-weight': 'bold',
                },
                class: 'buff_name b1'
            },
            {
                p: txt.AS_Guide[lang3].replaceAll('＋', '－'),
                style: {
                    'line-height': '1.7',
                    'margin': '0',
                    'font-weight': 'bold',
                },
                class: 'buff_name b2'
            },
            {
                p: infos.join('<br><br>'),
                style: {
                    'line-height': '1.7',
                    'margin-bottom': '0',
                }
            }
        ]
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

    function RES(L) {
        var max_id = 0
        var max_hp = 0
        L.forEach(function (l) {
            l.Monsters.forEach(function (m) {
                m.forEach(function (n) {
                    if (n.HP > max_hp) {
                        max_id = n.ID
                        max_hp = n.HP
                    }
                })
            })
        })
        if (_monster[max_id] && _monster[max_id]["9"]) {
            var reses = []
            for (const [p, q] of Object.entries(_monster[max_id]["9"])) {
                reses.push({
                    div: [
                        {
                            img: imgpre + `images/Element/${p}.png`,
                            class: 'statpageicon_2',
                            style: {
                                'top': '0'
                            }
                        },
                        {
                            span: (q * 100).toFixed(0) + '%'
                        }
                    ],
                    class: 'res_each'
                })
            }
            return [
                {
                    p: txt.AS_RES[lang],
                    style: {
                        'text-align': 'center',
                        'font-weight': 'bold',
                        //'margin': '10px 0'
                    }
                },
                {
                    div: reses,
                    class: 'res_wrapper'
                }
            ]
        }
    }

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
                    class: 'emote_block_'
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
                        'margin-bottom': '5px',
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

    function Wave(i, w, stage_lv, stage_hlg, stage_eg) {
        var monsters = []
        var affix0 = []
        w.forEach(function (t) {
            var me = _monster[t.ID] || { "2": "monsterfigure/None.png" }
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
                                    class: 'elem_as',
                                    data: me["2"],
                                    a: {
                                        loading: lazy
                                    }
                                },
                                class: 'monelem'
                            },
                            {
                                span: showstance(t.Stance) + (me["11"] ? ('×' + me["11"]) : ''),
                                class: 'monname_2',
                                style: {
                                    'margin-left': '5px',
                                    'position': 'relative',
                                    'bottom': '2px',
                                    'font-weight': 'bold'
                                }
                            },
                        ],
                        class: 'monbottom'
                    },
                    {
                        div: [
                            {
                                span: function () {
                                    var s = '<b><color style="color:#cc0000;">' + t.HP.toString() + '</color></b>'
                                    if (t.HPCount && t.HPCount > 1) {
                                        s += '<b>×' + t.HPCount + '</b>'
                                    }
                                    return s + (me["5"] ? ` <color style='color:#666;'>[${((stage_eg ? (stage_eg.HP ? stage_eg.HP : 1) : 1) * me["5"] * 100).toFixed(0)}%]</color>` : '')
                                },
                                class: 'monname_2',
                                when: t.HP
                            },
                            {
                                br: '',
                                when: t.HP && (t.SPD || me['13'])
                            },
                            {
                                span: '<b><color style="color:#2545ba;">' + t.SPD.toString() + '</color></b>' + (me["6"] ? ` <color style='color:#666;'>[${((stage_eg ? (stage_eg.SPD ? stage_eg.SPD : 1) : 1) * me["6"] * 100).toFixed(0)}%]</color>` : ''),
                                class: 'monname_2',
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
                        class: 'monright'
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
        var temp = {
            div: [
                {
                    p: (_monster[w[0].ID] || {})['4'] || '',
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
        //$('.buff').css('width', 'calc(100% - 60px)')
        //$('.target').toggle()
        $('.under2').hide()
        $('.chart_container').toggle()
        $('h3').toggle()
        $('.dl_button').toggle()
        $('.u_g').hide()
        $('.l_g').hide()
        $('.u_l').css('margin-bottom', '10px')
        $('.buff, .u_b, .u_b_b, .u_g, .l_b, .l_b_b, .l_g').css('color', 'white')
    })

    $('body').on('click', '.dl_button', function () {
        var toast = document.createElement('div')
        toast.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:rgba(0,0,0,0.8);color:#f29e38;padding:15px 32px;border-radius:8px;z-index:99999;font-size:15px'
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
        window.location.href = `/sr/yunli4`
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

})