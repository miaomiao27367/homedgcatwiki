// 改动汇总相关数据
var _changelog_relic = {
    "v1": [],
    "v2": [],
    "v3": [],
    "v4": [],
    "Live": []
}

var _changelog_avatar = {
    "1508": {},
    "1509": {},
    "1510": {},
    "23060": {},
    "23061": {},
    "23062": {},
}

var _changelog_veradd = {
    "v3": [
        {
            "Stance": [[6.0, ["Fire", "Elec", "Imaginary"]], [7.0, ["Fire", "Elec", "Imaginary"]]],
            "Name": "「齐响诗班」神主日",
            "_id": 3025016,
            "Icon": "mostericon/Monster_3025010.png"
        },
        {
            "HP": [10.0, 2.5],
            "Name": "「贼灵」巴特鲁斯",
            "_id": 4012052,
            "Icon": "mostericon/Monster_4012050.png"
        },
        {
            "HP": [2.5, 2.0],
            "Name": "金血忆灵 · 雉形",
            "_id": 406201001,
            "Icon": "mostericon/Monster_4062010.png"
        }
    ],
    "v4": [
        {
            "HP": [15.0, 21.0],
            "Name": "惊梦剧团的甜猿泰山",
            "_id": 300302013,
            "Icon": "mostericon/Monster_3003020.png"
        },
        {
            "HP": [60.0, 80.0],
            "Name": "月夜天马",
            "_id": 402302005,
            "Icon": "mostericon/Monster_4023020.png"
        }
    ],
    "Live": [
        {"SPD": [130.0, 125.0], "Name": "巨剑守护 · 陷坚挫锐的先锋将", "_id": 4013014, "Icon": "mostericon/Monster_4013010.png"},
        {"SPD": [130.0, 125.0], "Name": "巨剑守护 · 陷坚挫锐的先锋将", "_id": 401301401, "Icon": "mostericon/Monster_4013010.png"},
        {"HP": [60.0, 70.0], "Name": "狮震八方 · 皎阳似火的飞翼兽", "_id": 4023011, "Icon": "mostericon/Monster_4023010.png"},
        {"HP": [130.0, 150.0], "Name": "狮震八方 · 皎阳似火的飞翼兽", "_id": 402301101, "Icon": "mostericon/Monster_4023010.png"},
        {"HP": [3.6, 2.88], "Name": "扑大哥", "_id": 800205102, "Icon": "mostericon/Monster_8002050.png"},
        {"HP": [3.6, 2.88], "Name": "扑大哥", "_id": 800205103, "Icon": "mostericon/Monster_8002050.png"},
        {"HP": [3.6, 2.88], "Name": "扑老二", "_id": 800205202, "Icon": "mostericon/Monster_8002050.png"},
        {"HP": [3.6, 2.88], "Name": "扑老二", "_id": 800205203, "Icon": "mostericon/Monster_8002050.png"},
        {"HP": [3.6, 2.88], "Name": "扑三弟", "_id": 800205303, "Icon": "mostericon/Monster_8002050.png"},
        {"HP": [3.6, 2.88], "Name": "扑三弟", "_id": 800205304, "Icon": "mostericon/Monster_8002050.png"},
        {"HP": [3.6, 2.88], "Name": "序列扑满", "_id": 800205801, "Icon": "mostericon/Monster_8002050.png"},
        {"HP": [3.6, 2.88], "Name": "序列扑满", "_id": 800205802, "Icon": "mostericon/Monster_8002050.png"},
        {"HP": [166.5, 133.0], "Name": "序列扑满（巨大）", "_id": 800210901, "Icon": "mostericon/Monster_8002050.png"},
        {"HP": [166.5, 133.0], "Name": "序列扑满（巨大）", "_id": 800210902, "Icon": "mostericon/Monster_8002050.png"}
    ]
}

var cl_vers = __SR_CONFIG__.VS
var cl_select = (function() {
    var s = {};
    for (var i = 0; i < cl_vers.length - 1; i++) {
        s[cl_vers[i] + " - " + cl_vers[i + 1]] = i + 1;
    }
    return s;
})()
var _diff_avatar = __SR_CONFIG__.diff.avatar
var _diff_weapon = __SR_CONFIG__.diff.weapon