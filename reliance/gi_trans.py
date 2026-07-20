import json
import os
import requests
import re

# ============================================================
#  配置区
# ============================================================

SCRIPT_VERSION = "3.1"
API_VERSION = "6.7.52"

CACHE_DIR = "tempdata"
OUTPUT_DIR = os.path.join(CACHE_DIR, "output")
AVATAR_DIR = "gi/CH/Avatar"
AVATAR_JS_PATH = "gi/CH/avatar.js"

# 版本列表在运行时由用户输入，不再硬编码

# ----------------------------------------------------------
#  元素映射: API -> 本地
# ----------------------------------------------------------
ELEMENT_MAPPING = {
    "Anemo": "Wind", "Hydro": "Water", "Geo": "Rock",
    "Pyro": "Fire", "Electro": "Elec", "Dendro": "Grass", "Cryo": "Ice",
}

# ----------------------------------------------------------
#  武器映射: API -> 本地
# ----------------------------------------------------------
WEAPON_MAPPING = {
    "WEAPON_SWORD_ONE_HAND": "Sword", "WEAPON_CLAYMORE": "Claymore",
    "WEAPON_POLE": "Pole", "WEAPON_CATALYST": "Catalyst", "WEAPON_BOW": "Bow",
}

# ----------------------------------------------------------
#  国家/地区映射: API region -> 本地
# ----------------------------------------------------------
NATION_MAPPING = {
    "ASSOC_TYPE_LIYUE": "Liyue", "ASSOC_TYPE_MONDSTADT": "Mondstadt",
    "ASSOC_TYPE_INAZUMA": "Inazuma", "ASSOC_TYPE_SUMERU": "Sumeru",
    "ASSOC_TYPE_FONTAINE": "Fontaine", "ASSOC_TYPE_NATLAN": "Natlan",
    "ASSOC_TYPE_SNEZHNAYA": "Snezhnaya", "ASSOC_TYPE_CHENYU_VALE": "Chenyu Vale",
    "ASSOC_TYPE_OTHER": "???",
}

# ----------------------------------------------------------
#  稀有度映射: API -> 本地
# ----------------------------------------------------------
RARITY_MAPPING = {
    "QUALITY_ORANGE": 5, "QUALITY_PURPLE": 4,
    "QUALITY_BLUE": 3, "QUALITY_GREEN": 2,
}

# ----------------------------------------------------------
#  突破属性映射: API fight_prop -> 本地
# ----------------------------------------------------------
CUSTOM_PROMOTE_MAPPING = {
    "fight_prop_critical_hurt": "CD", "fight_prop_critical": "CR",
    "fight_prop_heal_add": "Heal", "fight_prop_elemental_mastery": "EM",
    "fight_prop_charge_efficiency": "ER", "fight_prop_physical_add": "Phys",
    "fight_prop_fire_add": "Fire", "fight_prop_water_add": "Water",
    "fight_prop_grass_add": "Grass", "fight_prop_elec_add": "Elec",
    "fight_prop_ice_add": "Ice", "fight_prop_wind_add": "Wind",
    "fight_prop_rock_add": "Rock",
}

# ----------------------------------------------------------
#  成长曲线映射: API grow_curve -> 本地Curve值
#  注: 此映射可能不完整，需人工验证
# ----------------------------------------------------------
GROW_CURVE_MAPPING = {
    "GROW_CURVE_HP_S4": 104, "GROW_CURVE_ATTACK_S4": 204,
    "GROW_CURVE_HP_S5": 105, "GROW_CURVE_ATTACK_S5": 205,
}

# ============================================================
#  API自动填充 / 需手动填写 对照表
# ============================================================
#  avatar.js:
#    [API] _name, _id, Name, Desc, Title, Constellation, Nation, Belong
#    [API] Grade, Weapon, Element, Birthday, Icon
#    [API] CommonMatt, TalentMat, TalentMatt, SpecialityMat, AscMat, WeekMat
#    [API] CustomPromote, Curve (prop_grow_curves映射), ShowStats, ShowStats2
#    [API] Version (API前两位+0.1), Fetter, _CV (CH/EN/JP/KR)
#    [手动] Type (角色性别类型 Girl/Boy/Lady/Male)
#    [手动] Nation (新阵营需手动加映射)
#
#  {id}_1.js:
#    [API] Ver: 每个版本键独立的 BattleSkills/PassiveSkills/Constellations/HyperLinks
#    [API] _AvatarMats_: Promotion, A, E, Q
#    [API] _AvatarDataConfig_: BallList (从energy数据预填)
#    [API] _AvatarAttackConfig_: AttackList (从attack数据预填)
#    [手动] _AvatarDataConfig_: EndureList/WindZoneList/OtherDataList
#    [手动] _AvatarAttackConfig_: 格式可能需微调
#    [手动] BattleSkills[].Num/Lock: 已填默认值(1/2/3, 5.0)，请验证
#    [手动] PassiveSkills[].Buff, Constellations[].Buff
#
#  {id}_2.js:
#    [API] _AvatarFetterConfig_: StoryList, VoiceList
#    [API] _AvatarCostumeConfig_: Costumes, Dish (ID/JD/Name/Desc/Icon), Namecard
#    [手动] Dish.Eff (料理效果文本), Dish.Recipe (料理配方材料)
#    [手动] Dish.JD: API返回recipe ID而非基础料理ID，可能需修正
#    [手动] acs_cache_: 时装描述缓存
# ============================================================

# ============================================================
#  工具函数
# ============================================================

def download_and_cache(url, save_path):
    if os.path.exists(save_path):
        print(f"  [缓存] {save_path}")
        return True
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    try:
        print(f"  [下载] {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(response.text)
        return True
    except Exception as e:
        print(f"  [失败] {e}")
        return False


def escape_js_string(s):
    if not isinstance(s, str):
        return str(s)
    return s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '')


def process_color_tags(text):
    if not text:
        return ""
    text = text.replace('\\n', '<br>')
    text = re.sub(r'<color=#([A-Fa-f0-9]{2})([A-Fa-f0-9]{6})>',
                  r"<color style='color:#\2;'>", text)
    text = text.replace('</color>', '</color>')
    return text


def remove_link_tags(text):
    text = re.sub(r'\{LINK#N\d+\}', '', text)
    text = re.sub(r'\{/LINK\}', '', text)
    return text


def resolve_param_refs(text, skill_param_map):
    if not text or not skill_param_map:
        return text
    def replacer(m):
        skill_id = m.group(1)
        idx_str = m.group(2)
        idx = int(idx_str) - 1
        if skill_id in skill_param_map and idx >= 0 and idx < len(skill_param_map[skill_id]):
            val = skill_param_map[skill_id][idx]
            if isinstance(val, float) and val == int(val):
                return str(int(val))
            return str(val)
        return m.group(0)
    return re.sub(r'\{PARAM#P(\d+)\|(\d+)S1\}', replacer, text)


def format_param_value(value, format_spec):
    if 'P' in format_spec:
        return f"{value * 100:.4f}%"
    elif 'F1' in format_spec or 'F2' in format_spec:
        return f"{value:.4f}"
    elif 'I' in format_spec:
        return str(int(value))
    return str(value)


# ============================================================
#  数据下载
# ============================================================

def download_all_data(character_id, versions_dict):
    for ver_key, api_ver in versions_dict.items():
        download_and_cache(
            f"https://static.nanoka.cc/gi/{api_ver}/zh/hyperlink.json",
            os.path.join(CACHE_DIR, f"{api_ver}-hyperlink.json"))
        download_and_cache(
            f"https://static.nanoka.cc/gi/{api_ver}/zh/character/{character_id}.json",
            os.path.join(CACHE_DIR, f"{api_ver}-{character_id}-zh.json"))
        download_and_cache(
            f"https://static.nanoka.cc/gi/{api_ver}/en/character/{character_id}.json",
            os.path.join(CACHE_DIR, f"{api_ver}-{character_id}-en.json"))
    return character_id


# ============================================================
#  avatar.js 角色基本信息提取
# ============================================================

def extract_character_info(zh_file, en_file, short_id):
    with open(zh_file, 'r', encoding='utf-8') as f:
        zh = json.load(f)
    with open(en_file, 'r', encoding='utf-8') as f:
        en = json.load(f)

    ci = zh.get('chara_info', {})
    sm = zh.get('stats_modifier', {})

    # --- 基础属性 ---
    base_hp = zh.get('base_hp', 0)
    base_atk = zh.get('base_atk', 0)
    base_def = zh.get('base_def', 0)

    asc_data = sm.get('ascension', [])
    asc_bonus = asc_data[-1] if asc_data else {}

    # --- CustomPromote ---
    custom_promote = "CD"
    custom_stat_value = 0
    base_stat_keys = ['fight_prop_base_hp', 'fight_prop_base_attack', 'fight_prop_base_defense']
    for key, value in asc_bonus.items():
        if key not in base_stat_keys and key.startswith('fight_prop_'):
            custom_stat_value = value
            custom_promote = CUSTOM_PROMOTE_MAPPING.get(key, "CD")
            break

    # --- LV90 / LV100 属性 ---
    hp_90 = round(base_hp * sm.get('hp', {}).get('90', 1) + asc_bonus.get('fight_prop_base_hp', 0))
    atk_90 = round(base_atk * sm.get('atk', {}).get('90', 1) + asc_bonus.get('fight_prop_base_attack', 0))
    def_90 = round(base_def * sm.get('def', {}).get('90', 1) + asc_bonus.get('fight_prop_base_defense', 0))
    hp_100 = round(base_hp * sm.get('hp', {}).get('100', 1) + asc_bonus.get('fight_prop_base_hp', 0))
    atk_100 = round(base_atk * sm.get('atk', {}).get('100', 1) + asc_bonus.get('fight_prop_base_attack', 0))
    def_100 = round(base_def * sm.get('def', {}).get('100', 1) + asc_bonus.get('fight_prop_base_defense', 0))

    # --- 曲线类型 ---
    curve = None
    prop_curves = sm.get('prop_grow_curves', [])
    if prop_curves:
        for pc in prop_curves:
            if pc.get('type') == 'FIGHT_PROP_BASE_HP':
                curve = GROW_CURVE_MAPPING.get(pc.get('grow_curve', ''))
                break

    # --- 材料 ---
    mats = zh.get('materials', {})
    asc = mats.get('ascensions', [])
    tal = mats.get('talents', [])

    CommonMatt = TalentMatt = SpecialityMat = AscMat = WeekMat = None
    TalentMat = 1

    if asc:
        last_mats = asc[-1].get('mats', [])
        if len(last_mats) > 3: CommonMatt = last_mats[3].get('id')
        if len(last_mats) > 2: SpecialityMat = last_mats[2].get('id')
        if len(last_mats) > 1: AscMat = last_mats[1].get('id')

    if tal:
        last_grp = tal[-1]
        if last_grp:
            last_tm = last_grp[-1].get('mats', [])
            if len(last_tm) > 0: TalentMatt = last_tm[0].get('id')
            if len(last_tm) > 2: WeekMat = last_tm[2].get('id')
            if TalentMatt is not None:
                TalentMat = ((TalentMatt - 104303) // 3) % 3 + 1

    # 武器
    weapon_raw = zh.get('weapon', '')
    weapon = WEAPON_MAPPING.get(weapon_raw, weapon_raw.replace('WEAPON_', '').capitalize())
    if weapon == "Sword_one_hand": weapon = "Sword"

    # 元素
    element_raw = zh.get('element', '')
    element = ELEMENT_MAPPING.get(element_raw.capitalize(), element_raw.capitalize())

    # 国家/归属
    nation = NATION_MAPPING.get(ci.get('region', ''), ci.get('region', '???'))
    belong = ci.get('native', '???')

    # 稀有度
    grade = RARITY_MAPPING.get(zh.get('rarity', ''), 5)

    # 声优
    va = ci.get('va', {})
    cv = {
        "_CH": va.get('chinese', '？？？'),
        "_EN": va.get('english', '？？？'),
        "_JP": va.get('japanese', '？？？'),
        "_KR": va.get('korean', '？？？'),
    }

    # 生日
    birth = ci.get('birth', [1, 1])
    birthday = f"{birth[0]}/{birth[1]}"

    version_parts = API_VERSION.split('.')
    char_version = f"{version_parts[0]}.{int(version_parts[1]) + 1}"

    return {
        "_name": en.get('name', ''),
        "_id": int(short_id),
        "Name": zh.get('name', ''),
        "Desc": zh.get('desc', ''),
        "Title": ci.get('title', ''),
        "Constellation": ci.get('constellation', ''),
        "Nation": nation,
        "Belong": belong,
        "Grade": grade,
        "Type": "???",
        "Weapon": weapon,
        "Element": element,
        "Birthday": birthday,
        "Icon": zh.get('icon', ''),
        "CommonMatt": CommonMatt,
        "TalentMat": TalentMat,
        "TalentMatt": TalentMatt,
        "SpecialityMat": SpecialityMat,
        "AscMat": AscMat,
        "WeekMat": WeekMat,
        "CustomPromote": custom_promote,
        "Curve": curve,
        "ShowStats": {
            "HP": hp_90, "ATK": atk_90, "DEF": def_90,
            "Custom": custom_stat_value
        },
        "ShowStats2": {
            "HP": hp_100, "ATK": atk_100, "DEF": def_100,
            "Custom": custom_stat_value
        },
        "Version": char_version,
        "Fetter": int(short_id),
        "_CV": cv,
    }


# ============================================================
#  avatar.js 生成
# ============================================================

def generate_avatar_js(info, output_file):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    c = info
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('// Auto Generated\n\n')
        f.write('var __AvatarInfoConfig = [\n')
        f.write('    {\n')
        f.write(f'        "_name": "{c["_name"]}",\n')
        f.write(f'        "_id": {c["_id"]},\n')
        for key in ["Name", "Desc", "Title", "Constellation", "Nation", "Belong"]:
            f.write(f'        "{key}": "{escape_js_string(c[key])}",\n')
        f.write(f'        "Grade": {c["Grade"]},\n')
        f.write(f'        "Type": "{c["Type"]}",\n')
        f.write(f'        "Weapon": "{c["Weapon"]}",\n')
        f.write(f'        "Element": "{c["Element"]}",\n')
        f.write(f'        "Birthday": "{c["Birthday"]}",\n')
        f.write(f'        "Icon": "{c["Icon"]}",\n')
        for m in ["CommonMatt", "TalentMat", "TalentMatt", "SpecialityMat", "AscMat", "WeekMat"]:
            val = c[m]
            f.write(f'        "{m}": {val if val is not None else "null"},\n')
        f.write(f'        "CustomPromote": "{c["CustomPromote"]}",\n')
        f.write(f'        "Curve": {c["Curve"] if c["Curve"] is not None else "null"},\n')
        for stats_key in ["ShowStats", "ShowStats2"]:
            s = c[stats_key]
            f.write(f'        "{stats_key}": {{\n')
            f.write(f'            "HP": {s["HP"]},\n')
            f.write(f'            "ATK": {s["ATK"]},\n')
            f.write(f'            "DEF": {s["DEF"]},\n')
            f.write(f'            "Custom": {s["Custom"]}\n')
            f.write('        },\n')
        f.write(f'        "Version": "{c["Version"]}",\n')
        f.write(f'        "Fetter": {c["Fetter"]},\n')
        f.write('        "_CV": {\n')
        for lang in ["_CH", "_EN", "_JP", "_KR"]:
            f.write(f'            "{lang}": "{c["_CV"][lang]}"')
            f.write(',\n' if lang != "_KR" else '\n')
        f.write('        }\n')
        f.write('    }\n')
        f.write(']')


def generate_avatar_entry_json(info):
    """生成单个avatar条目的JSON字符串（用于拼接）"""
    c = info
    lines = []
    lines.append('    {')
    lines.append(f'        "_name": "{escape_js_string(c["_name"])}",')
    lines.append(f'        "_id": {c["_id"]},')
    for key in ["Name", "Desc", "Title", "Constellation", "Nation", "Belong"]:
        lines.append(f'        "{key}": "{escape_js_string(c[key])}",')
    lines.append(f'        "Grade": {c["Grade"]},')
    lines.append(f'        "Type": "{c["Type"]}",')
    lines.append(f'        "Weapon": "{c["Weapon"]}",')
    lines.append(f'        "Element": "{c["Element"]}",')
    lines.append(f'        "Birthday": "{c["Birthday"]}",')
    lines.append(f'        "Icon": "{c["Icon"]}",')
    for m in ["CommonMatt", "TalentMat", "TalentMatt", "SpecialityMat", "AscMat", "WeekMat"]:
        val = c[m]
        lines.append(f'        "{m}": {val if val is not None else "null"},')
    lines.append(f'        "CustomPromote": "{c["CustomPromote"]}",')
    lines.append(f'        "Curve": {c["Curve"] if c["Curve"] is not None else "null"},')
    for stats_key in ["ShowStats", "ShowStats2"]:
        s = c[stats_key]
        lines.append(f'        "{stats_key}": {{')
        lines.append(f'            "HP": {s["HP"]},')
        lines.append(f'            "ATK": {s["ATK"]},')
        lines.append(f'            "DEF": {s["DEF"]},')
        lines.append(f'            "Custom": {s["Custom"]}')
        lines.append('        },')
    lines.append(f'        "Version": "{c["Version"]}",')
    lines.append(f'        "Fetter": {c["Fetter"]},')
    lines.append('        "_CV": {')
    for i, lang in enumerate(["_CH", "_EN", "_JP", "_KR"]):
        suffix = ',' if lang != "_KR" else ''
        lines.append(f'            "{lang}": "{c["_CV"][lang]}"{suffix}')
    lines.append('        }')
    lines.append('    },')

    return '\n'.join(lines)


def merge_to_avatar_js(character_id, char_info):
    """
    将生成的角色条目自动插入到 gi/CH/avatar.js 的 __AvatarInfoConfig 中。
    以刻晴条目中的 "Test": "test value" 为定位标记，插入到刻晴后面。
    """
    avatar_js = AVATAR_JS_PATH
    if not os.path.exists(avatar_js):
        print(f"  [警告] 未找到 {avatar_js}，跳过自动拼接")
        return ""

    with open(avatar_js, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查是否已存在
    avatar_id = char_info["_id"]
    if f'"_id": {avatar_id},' in content or f'"_id": {avatar_id}\n' in content:
        dup_path = os.path.join(OUTPUT_DIR, f"{avatar_id}_duplicate.js")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        new_entry = generate_avatar_entry_json(char_info)
        with open(dup_path, 'w', encoding='utf-8') as f:
            f.write('var __AvatarInfoConfig = [\n')
            f.write(new_entry)
            f.write('\n]')
        return f"角色 {avatar_id} 条目已存在，新数据已输出到 {dup_path} 请人工比对保留哪个"

    # 定位标记: "Test": "test value"
    marker = '"Test": "test value"'
    marker_pos = content.find(marker)
    if marker_pos < 0:
        return "错误：无法定位 'Test': 'test value' 标记"

    # 从标记位置往后找，找到闭合该条目的 },\n    {
    after_marker = content[marker_pos:]
    close_idx = after_marker.find('},\n    {')
    if close_idx < 0:
        # 尝试另一种格式
        close_idx = after_marker.find('}\n    ]')
        if close_idx < 0:
            return "错误：无法定位刻晴条目结束位置"

    # 生成新条目
    new_entry = generate_avatar_entry_json(char_info)

    # 拼接: 在刻晴条目 }, 之后插入
    insert_pos = marker_pos + close_idx + 2  # 跳过 },
    new_content = content[:insert_pos] + '\n' + new_entry + content[insert_pos:]

    with open(avatar_js, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return f"已自动拼接角色 {avatar_id} 到 {avatar_js}（刻晴下方）"


# ============================================================
#  技能信息提取 -> _AvatarSkillPConfig_
# ============================================================

def extract_skills(zh_file, api_version):
    with open(zh_file, 'r', encoding='utf-8') as f:
        zh = json.load(f)

    skills = zh.get('skills', [])
    passives = zh.get('passives', [])
    constellations = zh.get('constellations', [])
    all_desc = []

    # --- 战斗技能 ---
    battle_skills = []
    for idx, skill in enumerate(skills):
        desc = skill.get('desc', '')
        all_desc.append(desc)
        desc_text = process_color_tags(remove_link_tags(desc))

        promote = skill.get('promote', {})
        levels = sorted(promote.keys(), key=lambda x: int(x))
        desc_list = promote.get('0', {}).get('desc', [])
        icon = promote.get('0', {}).get('icon', '')

        param_descs = []
        for desc_item in desc_list:
            if not desc_item:
                continue
            parts = desc_item.split('|')
            label = parts[0].strip()
            template = parts[1] if len(parts) > 1 else ''

            pd = {"Desc": label, "ParamLevelList": []}
            for level in levels:
                plist = promote.get(level, {}).get('param', [])
                pv = template
                for m in re.findall(r'\{param(\d+)(:[^}]*)?\}', template):
                    pi = int(m[0]) - 1
                    if pi < len(plist):
                        pv = pv.replace(
                            f"{{param{m[0]}{m[1]}}}",
                            format_param_value(plist[pi], m[1] if m[1] else ''))
                pd["ParamLevelList"].append(pv)
            param_descs.append(pd)

        battle_skills.append({
            "Name": skill.get('name', ''),
            "Desc": desc_text,
            "Num": idx + 1,
            "Lock": 5.0,
            "Icon": icon,
            "ParamDesc": param_descs,
        })

    # --- 被动技能 ---
    passive_skills = []
    for p in passives:
        desc = p.get('desc', '')
        all_desc.append(desc)
        passive_skills.append({
            "Name": p.get('name', ''),
            "Desc": process_color_tags(remove_link_tags(desc)),
            "Icon": p.get('icon', ''),
        })

    # --- 命之座 ---
    const_list = []
    for i, cst in enumerate(constellations):
        desc = cst.get('desc', '')
        all_desc.append(desc)
        const_list.append({
            "Level": i + 1,
            "Name": cst.get('name', ''),
            "Desc": process_color_tags(remove_link_tags(desc)),
            "Icon": cst.get('icon', ''),
        })

    # --- HyperLinks ---
    skill_param_map = {}
    for s in skills:
        sid = str(s.get('id', ''))
        if sid:
            skill_param_map[sid] = s.get('param_list', [])
    for p in passives:
        pid = str(p.get('id', ''))
        if pid:
            skill_param_map[pid] = p.get('param_list', [])
    for c in constellations:
        cid = str(c.get('id', ''))
        if cid:
            skill_param_map[cid] = c.get('param_list', [])
    hyperlinks = extract_hyperlinks(all_desc, api_version, skill_param_map)

    return {
        "BattleSkills": battle_skills,
        "PassiveSkills": passive_skills,
        "Constellations": const_list,
        "HyperLinks": hyperlinks,
    }


def extract_hyperlinks(desc_list, api_version, skill_param_map=None):
    hyperlink_file = os.path.join(CACHE_DIR, f"{api_version}-hyperlink.json")
    if not os.path.exists(hyperlink_file):
        print(f"  [警告] 未找到 {hyperlink_file}")
        return []

    with open(hyperlink_file, 'r', encoding='utf-8') as f:
        hl_data = json.load(f)

    link_ids = set()
    for desc in desc_list:
        for m in re.findall(r'\{LINK#N(\d+)\}', desc):
            link_ids.add(m)

    print(f"  提取到 {len(link_ids)} 个术语链接")
    hyperlinks = []
    for lid in link_ids:
        if lid in hl_data:
            term = hl_data[lid]
            desc = term.get('desc', '')
            desc = resolve_param_refs(desc, skill_param_map)
            hyperlinks.append({
                "Name": term.get('name', ''),
                "Desc": process_color_tags(desc),
            })
    return hyperlinks


# ============================================================
#  材料提取 -> _AvatarMats_
# ============================================================

def extract_materials(zh_file):
    with open(zh_file, 'r', encoding='utf-8') as f:
        zh = json.load(f)

    mats = zh.get('materials', {})

    promotion = []
    for i, asc in enumerate(mats.get('ascensions', [])):
        if i == 0:
            promotion.append({})
        d = {"202": asc.get('cost', 0)}
        for m in asc.get('mats', []):
            d[str(m.get('id', 0))] = m.get('count', 0)
        promotion.append(d)

    avatar_mats = {"Promotion": promotion}
    talent_keys = ["A", "E", "Q"]
    for i, talent_group in enumerate(mats.get('talents', [])):
        if i < len(talent_keys):
            talent_list = []
            for talent in talent_group:
                d = {"202": talent.get('cost', 0)}
                for m in talent.get('mats', []):
                    d[str(m.get('id', 0))] = m.get('count', 0)
                talent_list.append(d)
            avatar_mats[talent_keys[i]] = talent_list

    return avatar_mats


# ============================================================
#  攻击配置提取 -> _AvatarAttackConfig_ (API提供部分数据)
# ============================================================

def extract_attack_config(zh_file):
    with open(zh_file, 'r', encoding='utf-8') as f:
        zh = json.load(f)

    attack_list = zh.get('attack', [])
    if not attack_list:
        return {}

    config = {"AttackList": []}
    for atk in attack_list:
        icd = atk.get('icd', {})
        poise = atk.get('poise', {})
        entry = {
            "Skill": atk.get('name', ''),
            "Shape": {"Type": "Default", "Size": [0]},
            "AtkTag": icd.get('tag', ''),
            "AttTag": "",
            "AttGrp": icd.get('group', ''),
            "Element": ELEMENT_MAPPING.get(atk.get('element', ''), atk.get('element', 'None')),
            "GU": atk.get('gauge', 0),
            "Poise": poise.get('value', 0),
            "ForceType": 0,
            "Force": [0, 0],
            "Blunt": False,
            "Arkhe": 0,
            "HTime": 0,
            "HScale": 0,
            "BeHalt": False,
            "CanInfuse": False,
            "StrikeType": atk.get('strike_type', 'Default'),
            "AttackType": atk.get('attack_type', 'Default'),
        }
        config["AttackList"].append(entry)
    return config


# ============================================================
#  粒子数据提取 -> _AvatarDataConfig_ (API提供部分数据)
# ============================================================

def extract_data_config(zh_file):
    with open(zh_file, 'r', encoding='utf-8') as f:
        zh = json.load(f)

    energy = zh.get('energy', [])
    if not energy:
        return {"BallList": [], "EndureList": [], "WindZoneList": [], "OtherDataList": []}

    ball_list = []
    for e in energy:
        drop_array = []
        if e.get('chance', 0) > 0:
            drop_array.append({"Num": e.get('per_drop', 1), "Chance": e.get('chance', 100) / 100})
        ball_list.append({
            "When": f"{e.get('skill', '')} ({e.get('kind', '')})",
            "CD": e.get('cd', 0),
            "DropArray": drop_array,
        })

    return {
        "BallList": ball_list,
        "EndureList": [],
        "WindZoneList": [],
        "OtherDataList": [],
    }


# ============================================================
#  _1.js 生成
# ============================================================

def generate_1_js(short_id, versions, materials, data_config, attack_config, output_file):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    cid = str(short_id)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('// Auto Generated\n\n')

        # _AvatarDataConfig_
        f.write('var _AvatarDataConfig_ = {\n')
        f.write(f'    "{cid}": {{\n')
        f.write(f'        "BallList": {json.dumps(data_config.get("BallList", []), ensure_ascii=False)},\n')
        f.write(f'        "EndureList": {json.dumps(data_config.get("EndureList", []), ensure_ascii=False)},\n')
        f.write(f'        "WindZoneList": {json.dumps(data_config.get("WindZoneList", []), ensure_ascii=False)},\n')
        f.write(f'        "OtherDataList": {json.dumps(data_config.get("OtherDataList", []), ensure_ascii=False)}\n')
        f.write('    }\n')
        f.write('}\n\n')

        # _AvatarMats_
        f.write('var _AvatarMats_ = {\n')
        f.write(f'    "{cid}": {{\n')
        f.write('        "Promotion": [\n')
        for mat in materials["Promotion"]:
            f.write('            {\n')
            for k, v in mat.items():
                f.write(f'                "{k}": {v},\n')
            f.write('            },\n')
        f.write('        ],\n')
        for tk in ["A", "E", "Q"]:
            if tk in materials:
                f.write(f'        "{tk}": [\n')
                for mat in materials[tk]:
                    f.write('            {\n')
                    for k, v in mat.items():
                        f.write(f'                "{k}": {v},\n')
                    f.write('            },\n')
                f.write('        ],\n')
        f.write('    }\n')
        f.write('}\n\n')

        # _AvatarSkillPConfig_
        f.write('var _AvatarSkillPConfig_ = {\n')
        f.write(f'    "{cid}": {{\n')
        f.write('        "Ver": {\n')
        for version, data in versions.items():
            f.write(f'            "{version}": {{\n')

            f.write('                "BattleSkills": [\n')
            for skill in data["BattleSkills"]:
                f.write('                    {\n')
                f.write(f'                        "Name": "{escape_js_string(skill["Name"])}",\n')
                f.write(f'                        "Desc": "{escape_js_string(skill["Desc"])}",\n')
                f.write(f'                        "Num": {skill["Num"]},\n')
                f.write(f'                        "Lock": {skill["Lock"]},\n')
                f.write(f'                        "Icon": "{skill["Icon"]}",\n')
                f.write('                        "ParamDesc": [\n')
                for param in skill["ParamDesc"]:
                    f.write('                            {\n')
                    f.write(f'                                "Desc": "{escape_js_string(param["Desc"])}",\n')
                    f.write('                                "ParamLevelList": [\n')
                    for val in param["ParamLevelList"]:
                        f.write(f'                                    "{val}",\n')
                    f.write('                                ]\n')
                    f.write('                            },\n')
                f.write('                        ]\n')
                f.write('                    },\n')
            f.write('                ],\n')

            f.write('                "PassiveSkills": [\n')
            for ps in data["PassiveSkills"]:
                f.write('                    {\n')
                f.write(f'                        "Name": "{escape_js_string(ps["Name"])}",\n')
                f.write(f'                        "Desc": "{escape_js_string(ps["Desc"])}",\n')
                f.write(f'                        "Icon": "{ps["Icon"]}"\n')
                f.write('                    },\n')
            f.write('                ],\n')

            f.write('                "Constellations": [\n')
            for cst in data["Constellations"]:
                f.write('                    {\n')
                f.write(f'                        "Level": {cst["Level"]},\n')
                f.write(f'                        "Name": "{escape_js_string(cst["Name"])}",\n')
                f.write(f'                        "Desc": "{escape_js_string(cst["Desc"])}",\n')
                f.write(f'                        "Icon": "{cst["Icon"]}"\n')
                f.write('                    },\n')
            f.write('                ],\n')

            if data.get("HyperLinks"):
                f.write('                "HyperLinks": [\n')
                for hl in data["HyperLinks"]:
                    f.write('                    {\n')
                    f.write(f'                        "Name": "{escape_js_string(hl["Name"])}",\n')
                    f.write(f'                        "Desc": "{escape_js_string(hl["Desc"])}"\n')
                    f.write('                    },\n')
                f.write('                ]\n')
            else:
                f.write('                "HyperLinks": []\n')

            f.write('            },\n')
        f.write('        }\n')
        f.write('    }\n')
        f.write('}\n\n')

        # _AvatarAttackConfig_
        f.write('var _AvatarAttackConfig_ = {\n')
        f.write(f'    "{cid}": ')
        if attack_config:
            f.write(json.dumps(attack_config, ensure_ascii=False, indent=4).replace('\n', '\n    '))
        else:
            f.write('{}')
        f.write('\n')
        f.write('}\n')


# ============================================================
#  _2.js 提取 (故事/语音/服装/料理/名片)
# ============================================================

def extract_character_2(zh_file):
    with open(zh_file, 'r', encoding='utf-8') as f:
        zh = json.load(f)

    ci = zh.get('chara_info', {})

    # --- 故事 ---
    story_list = []
    for story in ci.get('stories', []):
        story_list.append({
            "Title": story.get('title', '？？？'),
            "Content": story.get('text', '？？？').replace('\\n', '<br>'),
            "Tips": story.get('unlock', []),
        })

    # --- 语音 ---
    voice_list = []
    for quote in ci.get('quotes', []):
        voice_list.append({
            "Title": quote.get('title', '？？？'),
            "Content": quote.get('text', '？？？').replace('\\n', '<br>'),
            "Tips": quote.get('unlocked', []),
        })

    # --- 服装 ---
    costume_list = []
    for costume in ci.get('costume', []):
        costume_list.append({
            "ID": costume.get('id', 0),
            "Name": costume.get('name', '？？？'),
            "Desc": costume.get('desc', '？？？'),
            "Icon": costume.get('icon', ''),
            "Quality": costume.get('quality', 0),
        })

    # --- 特色料理 ---
    sf = ci.get('special_food', {})
    dish = {
        "ID": sf.get('id', 0),
        "JD": sf.get('recipe', 0),
        "Name": f"<b>{sf.get('name', '？？？')}</b>",
        "Eff": "【需要手动填写】",
        "Desc": sf.get('desc', '？？？'),
        "Recipe": {},
        "Icon": sf.get('icon', ''),
    }

    # --- 名片 ---
    nc = ci.get('namecard', {})
    namecard = {
        "Name": f"<b>{nc.get('name', '？？？')}</b>",
        "Desc": nc.get('desc', '？？？'),
        "Pic": nc.get('icon', ''),
    }

    # --- 游迹（绘想游迹/trace_effect）---
    trace_effects = ci.get('trace_effect', [])

    return {
        "StoryList": story_list,
        "VoiceList": voice_list,
        "Costumes": costume_list,
        "Dish": dish,
        "Namecard": namecard,
        "TraceEffects": trace_effects,
    }


def generate_2_js(short_id, data, output_file):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    cid = str(short_id)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('// Auto Generated\n\n')

        # _AvatarFetterConfig_
        f.write('var _AvatarFetterConfig_ = {\n')
        f.write(f'    "{cid}": {{\n')

        f.write('        "StoryList": [\n')
        for story in data["StoryList"]:
            f.write('            {\n')
            f.write(f'                "Title": "{escape_js_string(story["Title"])}",\n')
            f.write(f'                "Content": "{escape_js_string(story["Content"])}",\n')
            f.write('                "Tips": [\n')
            for tip in story["Tips"]:
                f.write(f'                    "{escape_js_string(tip)}",\n')
            f.write('                ]\n')
            f.write('            },\n')
        f.write('        ],\n')

        f.write('        "VoiceList": [\n')
        for voice in data["VoiceList"]:
            f.write('            {\n')
            f.write(f'                "Title": "{escape_js_string(voice["Title"])}",\n')
            f.write(f'                "Content": "{escape_js_string(voice["Content"])}",\n')
            f.write('                "Tips": [\n')
            for tip in voice["Tips"]:
                f.write(f'                    "{escape_js_string(tip)}",\n')
            f.write('                ]\n')
            f.write('            },\n')
        f.write('        ]\n')
        f.write('    }\n')
        f.write('}\n\n')

        # _AvatarCostumeConfig_
        f.write('var _AvatarCostumeConfig_ = {\n')
        f.write(f'    "{cid}": {{\n')
        f.write('        "Costumes": [\n')
        for costume in data["Costumes"]:
            f.write('            {\n')
            f.write(f'                "ID": {costume["ID"]},\n')
            f.write(f'                "Name": "{escape_js_string(costume["Name"])}",\n')
            f.write(f'                "Desc": "{escape_js_string(costume["Desc"])}",\n')
            f.write(f'                "Icon": "{costume["Icon"]}",\n')
            f.write(f'                "Quality": {costume["Quality"]}\n')
            f.write('            },\n')
        f.write('        ],\n')
        f.write('        "Dish": {\n')
        f.write(f'            "ID": {data["Dish"]["ID"]},\n')
        f.write(f'            "JD": {data["Dish"]["JD"]},\n')
        f.write(f'            "Name": "{escape_js_string(data["Dish"]["Name"])}",\n')
        f.write(f'            "Eff": "{escape_js_string(data["Dish"]["Eff"])}",\n')
        f.write(f'            "Desc": "{escape_js_string(data["Dish"]["Desc"])}",\n')
        f.write('            "Recipe": {\n')
        for item_id, count in data["Dish"]["Recipe"].items():
            f.write(f'                "{item_id}": {count},\n')
        f.write('            },\n')
        f.write(f'            "Icon": "{data["Dish"]["Icon"]}"\n')
        f.write('        },\n')
        f.write('        "Namecard": {\n')
        f.write(f'            "Name": "{escape_js_string(data["Namecard"]["Name"])}",\n')
        f.write(f'            "Desc": "{escape_js_string(data["Namecard"]["Desc"])}",\n')
        f.write(f'            "Pic": "{data["Namecard"]["Pic"]}"\n')
        f.write('        }\n')
        f.write('    }\n')
        f.write('}\n\n')

        # acs_cache_
        f.write('var acs_cache_ = {}\n')


# ============================================================
#  主函数
# ============================================================

def main():
    print(f"=" * 60)
    print(f"  transitgi.py v{SCRIPT_VERSION} | 默认API v{API_VERSION}")
    print(f"  缓存目录: {CACHE_DIR}/")
    print(f"=" * 60)

    character_id = input("\n请输入角色ID（例如：10000003）: ").strip()
    if not character_id:
        print("未输入角色ID，退出。")
        return

    short_id = str(int(character_id[5:]))
    print(f"角色ID: {character_id} (短ID: {short_id})")

    # 版本配置输入
    print(f"\n版本配置: 格式为 键:API版本号, 多个用逗号分隔")
    print(f"例: L:{API_VERSION}  或  L:{API_VERSION}, M:6.8.53")
    version_input = input(f"请输入版本配置 (默认 L:{API_VERSION}): ").strip()
    if not version_input:
        versions_dict = {"L": API_VERSION}
    else:
        versions_dict = {}
        for pair in version_input.split(','):
            pair = pair.strip()
            if ':' in pair:
                key, ver = pair.split(':', 1)
                versions_dict[key.strip()] = ver.strip()
            else:
                print(f"  [警告] 跳过无效格式: {pair}")

    if not versions_dict:
        print("错误: 未指定任何版本配置。")
        return

    first_ver_key = list(versions_dict.keys())[0]
    first_api_ver = versions_dict[first_ver_key]
    print(f"版本配置: {versions_dict}")

    # [1] 下载数据（缓存优先）
    print("\n[1/5] 下载数据...")
    download_all_data(character_id, versions_dict)

    zh_file = os.path.join(CACHE_DIR, f"{first_api_ver}-{character_id}-zh.json")
    en_file = os.path.join(CACHE_DIR, f"{first_api_ver}-{character_id}-en.json")

    if not (os.path.exists(zh_file) and os.path.exists(en_file)):
        print("错误: 未找到数据文件，请检查角色ID是否正确。")
        return

    # [2] avatar条目 -> 自动拼接
    print("\n[2/5] 提取角色基本信息 -> avatar条目...")
    char_info = extract_character_info(zh_file, en_file, short_id)
    ava_out = os.path.join(OUTPUT_DIR, f"{short_id}.js")
    generate_avatar_js(char_info, ava_out)
    print(f"  生成: {ava_out}")
    merge_msg = merge_to_avatar_js(character_id, char_info)
    if merge_msg:
        print(f"  {merge_msg}")

    # [3] 技能（每个版本）+ 材料 + DataConfig + AttackConfig -> _1.js
    print("\n[3/5] 提取技能/材料/攻击配置...")
    versions_data = {}
    for ver_key, api_ver in versions_dict.items():
        print(f"  版本 [{ver_key}] API v{api_ver} ...")
        zh_file_ver = os.path.join(CACHE_DIR, f"{api_ver}-{character_id}-zh.json")
        if not os.path.exists(zh_file_ver):
            print(f"    [警告] 未找到 {zh_file_ver}，跳过")
            continue
        versions_data[ver_key] = extract_skills(zh_file_ver, api_ver)

    materials = extract_materials(zh_file)
    data_config = extract_data_config(zh_file)
    attack_config = extract_attack_config(zh_file)
    js1_out = os.path.join(AVATAR_DIR, f"{short_id}_1.js")
    generate_1_js(short_id, versions_data, materials, data_config, attack_config, js1_out)
    print(f"  生成: {js1_out}")

    # [4] 故事/语音/服装/料理/名片 -> _2.js
    print("\n[4/5] 提取故事/语音/服装/料理/名片...")
    char2_data = extract_character_2(zh_file)
    js2_out = os.path.join(AVATAR_DIR, f"{short_id}_2.js")
    generate_2_js(short_id, char2_data, js2_out)
    print(f"  生成: {js2_out}")

    # [5] 完成
    print("\n[5/5] 生成完毕！")
    print(f"  输出: {AVATAR_DIR}/{short_id}_1.js | {AVATAR_DIR}/{short_id}_2.js")
    print(f"  Avatar条目: 已自动拼接至 {AVATAR_JS_PATH}")
    print(f"  版本: {', '.join(versions_dict.keys())} ({len(versions_dict)}个)")
    print("  需要手动填写的字段请查看脚本顶部注释。")


if __name__ == "__main__":
    main()


def gi_character_update(character_id, versions_dict):
    """
    封装函数，供 server.py 调用。
    参数:
        character_id: 完整角色ID，如 "10000003"
        versions_dict: 版本映射，如 {"L": "6.7.52", "M": "6.8.53"}
    返回:
        (success, message) 元组
    """
    try:
        short_id = str(int(character_id[5:]))
        print(f"角色ID: {character_id} (短ID: {short_id})")

        if not versions_dict:
            versions_dict = {"L": API_VERSION}

        first_ver_key = list(versions_dict.keys())[0]
        first_api_ver = versions_dict[first_ver_key]
        print(f"版本配置: {versions_dict}")

        # [1] 下载数据
        print("[1/5] 下载数据...")
        download_all_data(character_id, versions_dict)

        zh_file = os.path.join(CACHE_DIR, f"{first_api_ver}-{character_id}-zh.json")
        en_file = os.path.join(CACHE_DIR, f"{first_api_ver}-{character_id}-en.json")

        if not (os.path.exists(zh_file) and os.path.exists(en_file)):
            return (False, f"未找到数据文件，请检查角色ID {character_id} 是否正确")

        # [2] avatar条目 -> 自动拼接
        print("[2/5] 提取角色基本信息 -> avatar条目...")
        char_info = extract_character_info(zh_file, en_file, short_id)
        ava_out = os.path.join(OUTPUT_DIR, f"{short_id}.js")
        generate_avatar_js(char_info, ava_out)
        merge_msg = merge_to_avatar_js(character_id, char_info)
        if merge_msg:
            print(f"  {merge_msg}")

        # [3] 技能/材料/攻击配置
        print("[3/5] 提取技能/材料/攻击配置...")
        versions_data = {}
        for ver_key, api_ver in versions_dict.items():
            print(f"  版本 [{ver_key}] API v{api_ver} ...")
            zh_file_ver = os.path.join(CACHE_DIR, f"{api_ver}-{character_id}-zh.json")
            if not os.path.exists(zh_file_ver):
                print(f"    [警告] 未找到 {zh_file_ver}，跳过")
                continue
            versions_data[ver_key] = extract_skills(zh_file_ver, api_ver)

        materials = extract_materials(zh_file)
        data_config = extract_data_config(zh_file)
        attack_config = extract_attack_config(zh_file)
        js1_out = os.path.join(AVATAR_DIR, f"{short_id}_1.js")
        generate_1_js(short_id, versions_data, materials, data_config, attack_config, js1_out)

        # [4] 故事/语音/服装/料理/名片
        print("[4/5] 提取故事/语音/服装/料理/名片...")
        char2_data = extract_character_2(zh_file)
        js2_out = os.path.join(AVATAR_DIR, f"{short_id}_2.js")
        generate_2_js(short_id, char2_data, js2_out)

        print(f"[5/5] 生成完毕！{AVATAR_DIR}/{short_id}_1.js | {AVATAR_DIR}/{short_id}_2.js")
        return (True, f"角色 {character_id} 更新成功")

    except Exception as e:
        return (False, f"角色 {character_id} 处理失败: {str(e)}")