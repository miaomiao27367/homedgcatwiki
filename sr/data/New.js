// 从 _diff_avatar 和 _diff_weapon 自动生成最新角色/武器列表

// 元素和路径的映射
var ELEM_MAP = {
    'Fire': '火',
    'Ice': '冰',
    'Wind': '风',
    'Elec': '雷',
    'Quantum': '量子',
    'Imaginary': '虚数',
    'Physical': '物理'
};

var PATH_MAP = {
    'Destruction': '毁灭',
    'Preservation': '存护',
    'Harmony': '谐律',
    'Nihility': '虚无',
    'Hunt': '巡猎',
    'Erudition': '智识',
    'Remembrance': '记忆',
    'Elation': '欢愉'
};

// 自动生成 SR 最新角色和武器
var NEW_SR = [];

// 添加角色
for (const avatarId of (_diff_avatar || [])) {
    const avatar = _avatar.find(a => a._id == avatarId);
    if (avatar) {
        NEW_SR.push({
            "Name": {
                "CH": avatar.Name,
                "EN": avatar.Name,
                "JP": avatar.Name,
                "KR": avatar.Name
            },
            "Rarity": avatar.Rarity,
            "Link": `/sr/char#_${avatar._id}`,
            "Icon": `/images/avataricon/avatar/${avatar._id}.png`,
            "Elem": avatar.Element,
            "Type": avatar.Path
        });
    }
}

// 添加武器
for (const weaponId of (_diff_weapon || [])) {
    const weapon = _weapon.find(w => w._id == weaponId);
    if (weapon) {
        NEW_SR.push({
            "Name": {
                "CH": weapon.Name,
                "EN": weapon.Name,
                "JP": weapon.Name,
                "KR": weapon.Name
            },
            "Rarity": weapon.Rarity,
            "Link": `/sr/char#_${weapon._id}`,
            "Icon": `/images/lightconemediumicon/${weapon.Pic}`,
            "Type": weapon.Path
        });
    }
}

// GI部分保持手动维护（因为GI数据结构不同）
NEW_GI = [
    {
        "Name": {
            "CH": "法尔伽",
            "EN": "Varka",
            "JP": "ファルガ",
            "KR": "바르가"
        },
        "Rarity": 5,
        "Link": "/gi/char#_Varka",
        "Icon": "/homdgcat-res/Avatar/UI_AvatarIcon_Varka.png",
        "Elem": "Wind",
        "Type": "Skill_A_04"
    },
    {
        "Name": {
            "CH": "狼的武功歌",
            "EN": "Wolf's Martial Song",
            "JP": "狼の武功歌",
            "KR": "늑대의 무공가"
        },
        "Rarity": 5,
        "Link": "/gi/char#_12515",
        "Icon": "/homdgcat-res/Weapon/UI_EquipIcon_Claymore_EnsisAquilonis.png",
        "Type": "Skill_A_04"
    }
];//GI

var gi_ch = []
var sr_ch = []
var gi_en = []
var sr_en = []

for (const i of NEW_GI) {
    if (i.Elem) {
        gi_ch.push(i.Name.CH)
        gi_en.push(i.Name.EN)
    }
}
for (const i of NEW_SR) {
    if (i.Elem) {
        sr_ch.push(i.Name.CH)
        sr_en.push(i.Name.EN)
    }
}

document.querySelector('meta[name="description"]').setAttribute("content", `Genshin ${VER_GI.substring(0, 3)}: ${gi_en.join(', ')} | Star Rail ${VER_SR.substring(0, 3)}: ${sr_en.join(', ')} | 原神 ${VER_GI.substring(0, 3)}: ${gi_ch.join('、')} | 星穹铁道 ${VER_SR.substring(0, 3)}: ${sr_ch.join('、')}`);