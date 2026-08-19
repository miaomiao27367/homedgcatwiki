import json
import os
import re
import requests

# ============================================================
#  配置区
# ============================================================

API_VERSION = "6.7.52"
CACHE_DIR = "tempdata"
OUTPUT_DIR = os.path.join(CACHE_DIR, "output")
WEAPON_DIR = "gi/CH/Weapon"
AVATAR_JS_PATH = "gi/CH/Weapon.js"

# ----------------------------------------------------------
#  武器类型映射: API -> 本地数字
# ----------------------------------------------------------
WEAPON_TYPE_MAPPING = {
    "WEAPON_SWORD_ONE_HAND": 1,
    "WEAPON_CLAYMORE": 2,
    "WEAPON_CATALYST": 3,
    "WEAPON_POLE": 4,
    "WEAPON_BOW": 5,
    "ITEM_TPS_WEAPON": 6,
}

# ----------------------------------------------------------
#  副属性映射: API fight_prop -> 本地
# ----------------------------------------------------------
CUSTOM_PROP_MAPPING = {
    "FIGHT_PROP_CRITICAL_HURT": "CD",
    "FIGHT_PROP_CRITICAL": "CR",
    "FIGHT_PROP_ATTACK_PERCENT": "ATK",
    "FIGHT_PROP_DEFENSE_PERCENT": "DEF",
    "FIGHT_PROP_HP_PERCENT": "HP",
    "FIGHT_PROP_ELEMENT_MASTERY": "EM",
    "FIGHT_PROP_CHARGE_EFFICIENCY": "ER",
    "FIGHT_PROP_PHYSICAL_ADD_HURT": "Phys",
}

# ============================================================
#  工具函数
# ============================================================

def download_and_cache(url, save_path):
    if os.path.exists(save_path):
        return True
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, timeout=30, headers=headers)
        response.raise_for_status()
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(response.text)
        return True
    except Exception as e:
        print(f"  [下载失败] {url}: {e}")
        return False


def escape_js_string(s):
    if not isinstance(s, str):
        return str(s)
    return s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '')


def process_color_tags(text):
    if not text:
        return ""
    text = text.replace('\\n', '<br>')
    text = re.sub(r'<color=#([A-Fa-f0-9]{6})([A-Fa-f0-9]{2})>',
                  r"<color style='color:#\1;'>", text)
    text = re.sub(r'<color=#([A-Fa-f0-9]{6})>',
                  r"<color style='color:#\1;'>", text)
    text = text.replace('</color>', '</color>')
    return text


def merge_refinement_descs(descs):
    """
    将多个精炼等级的独立描述合并为一个，数值部分用 / 分隔
    例如: "提升52点" + "提升65点" + "提升78点" → "提升52/65/78点"
    如果各等级描述结构不一致（如文本有差异），则回退到原逻辑用 / 拼接
    """
    if not descs:
        return ""
    if len(descs) == 1:
        return descs[0]

    # 匹配数字（可能被颜色标签包裹）：(<color...>)?数字(小数可选)(</color>)?
    num_pattern = re.compile(r'(<color[^>]*>)?(\d+\.?\d*)(</color>)?')

    # 解析每个描述，提取文本段和数字段
    all_segments = []
    for desc in descs:
        segments = []
        last_end = 0
        for m in num_pattern.finditer(desc):
            if m.start() > last_end:
                segments.append(('text', desc[last_end:m.start()]))
            segments.append(('num', m.group(1) or '', m.group(2), m.group(3) or ''))
            last_end = m.end()
        if last_end < len(desc):
            segments.append(('text', desc[last_end:]))
        all_segments.append(segments)

    # 验证所有描述的segment结构一致
    first = all_segments[0]
    for segs in all_segments[1:]:
        if len(segs) != len(first):
            return ' / '.join(descs)
        for i, (s1, s2) in enumerate(zip(first, segs)):
            if s1[0] != s2[0]:
                return ' / '.join(descs)
            if s1[0] == 'text' and s1[1] != s2[1]:
                return ' / '.join(descs)

    # 构建合并结果：文本不变，变化的数值用 / 合并
    result = []
    for i, seg in enumerate(first):
        if seg[0] == 'text':
            result.append(seg[1])
        else:
            nums = [s[i][2] for s in all_segments]
            if len(set(nums)) == 1:
                result.append(f"{seg[1]}{nums[0]}{seg[3]}")
            else:
                result.append(f"{seg[1]}{'/'.join(nums)}{seg[3]}")

    return ''.join(result)


# ============================================================
#  数据下载
# ============================================================

def download_weapon_data(weapon_id, version="6.7.52"):
    """
    下载武器数据
    :param weapon_id: 武器ID
    :param version: API版本号
    """
    base = f"https://static.nanoka.cc/gi/{version}/zh/weapon"
    story_base = "https://raw.githubusercontent.com/DimbreathBot/AnimeGameData/refs/heads/master/Readable/CHS"

    download_and_cache(
        f"{base}/{weapon_id}.json",
        os.path.join(CACHE_DIR, f"{version}-weapon-{weapon_id}-zh.json"))
    download_and_cache(
        f"{story_base}/Weapon{weapon_id}.txt",
        os.path.join(CACHE_DIR, f"weapon-story-{weapon_id}.txt"))


# ============================================================
#  _WeaponConfig 条目提取
# ============================================================

def extract_weapon_config(zh_file, weapon_id, ver_key="L"):
    """
    提取武器配置
    :param zh_file: JSON文件路径
    :param weapon_id: 武器ID
    :param ver_key: 版本键，如 "L", "M"
    """
    with open(zh_file, 'r', encoding='utf-8') as f:
        api = json.load(f)

    wid = str(weapon_id)

    # --- 基础字段 ---
    name = api.get('name', '???')
    desc = api.get('desc', '???')
    raw_type = api.get('weapon_type', '')
    weapon_type = WEAPON_TYPE_MAPPING.get(raw_type, 0)
    if weapon_type == 0 and raw_type:
        print(f"  [警告] 未知武器类型: {raw_type}，已映射为 0，请手动更新 WEAPON_TYPE_MAPPING")
    rank = api.get('rarity', 5)
    icon = api.get('icon', '')
    # 去掉图标名中的 C# 格式占位符 {0}
    icon = icon.replace("_{0}", "")

    # --- 武器属性 ---
    weapon_props = api.get('weapon_prop', [])
    sm = api.get('stats_modifier', {})
    ascension = api.get('ascension', {})

    stat = 0
    custom = ""
    custom_stat = 0
    for prop in weapon_props:
        ptype = prop.get('prop_type', '')
        base = prop.get('init_value', 0)
        if ptype == 'FIGHT_PROP_BASE_ATTACK':
            # 计算满级基础攻击力
            multiplier_key = 'atk'
            if multiplier_key in sm:
                lv90_mult = sm[multiplier_key].get('levels', {}).get('90', 1)
                if not lv90_mult:
                    lv90_mult = sm[multiplier_key].get('levels', {}).get('90', 1)
                stat = round(base * lv90_mult, 6)
            # 加上突破加成
            last_asc = ascension.get('6', {})
            asc_bonus = last_asc.get('fight_prop_base_attack', 0)
            stat = round(stat + asc_bonus, 6)
        else:
            # 副属性
            custom = CUSTOM_PROP_MAPPING.get(ptype, '')
            if not custom:
                custom = ptype.replace('FIGHT_PROP_', '')
                print(f"  [警告] 未知副属性类型: {ptype}，已映射为 {custom}，请手动更新 CUSTOM_PROP_MAPPING")
            pkey = ptype.lower()
            if pkey in sm:
                lv90_mult = sm[pkey].get('levels', {}).get('90', 1)
                if not lv90_mult:
                    lv90_mult = 1
                custom_stat = round(base * lv90_mult, 6)

    # --- 材料 ---
    materials = api.get('materials', {})
    asc_mat_id = None
    mat_ids = []
    
    # 尝试从 materials 字段获取
    if materials:
        try:
            last_asc_key = str(max(int(k) for k in materials.keys()))
            last_asc = materials.get(last_asc_key, {})
            for m in last_asc.get('mats', []):
                mid = m.get('id', 0)
                mrank = m.get('rank', 0)
                if mrank == 5:
                    asc_mat_id = mid
                elif mrank >= 3 and len(mat_ids) < 2:
                    mat_ids.append(mid)
        except Exception as e:
            print(f"  [警告] 解析材料数据失败: {e}")
    
    # 如果 materials 字段没有数据，尝试从其他字段获取
    if asc_mat_id is None:
        # 尝试从 weapon_prop 或其他字段获取
        weapon_prop = api.get('weapon_prop', {})
        if weapon_prop:
            # 有些API可能把材料信息放在其他地方
            pass
    
    # 如果还是没有，根据武器类型设置一个默认值（基于现有数据规律）
    if asc_mat_id is None:
        # 根据武器类型设置默认的 AscMatID
        # 114001-114080 是武器突破材料ID范围
        # 不同类型的武器可能对应不同的材料
        type_defaults = {
            1: 114008,  # 单手剑
            2: 114012,  # 双手剑
            3: 114016,  # 长柄武器
            4: 114028,  # 法器
            5: 114032,  # 弓
        }
        asc_mat_id = type_defaults.get(weapon_type, 114008)
        print(f"  [警告] 未从API获取到 AscMatID，已使用默认值 {asc_mat_id}")

    # --- 精炼 ---
    refinement = api.get('refinement', {})
    r1 = refinement.get('1', {})
    equip_affix_name = r1.get('name', '')
    equip_affix_id = int(f"1{wid}")

    # --- 故事 ---
    story = api.get('story', {})
    story_id = int(f"19{int(weapon_id) % 10000}") if story else 0
    story_count = 1 if story else 0

    # --- 版本 ---
    ver = ver_key

    return {
        "_id": wid,
        "Name": name,
        "Desc": desc,
        "Type": weapon_type,
        "Rank": rank,
        "Icons": icon,
        "Stat": stat,
        "Custom": custom,
        "CustomStat": custom_stat,
        "AscMatID": asc_mat_id,
        "MatIDs": mat_ids,
        "EquipAffixName": equip_affix_name,
        "EquipAffixID": equip_affix_id,
        "Extra": [],
        "Story": story_id,
        "StoryCount": story_count,
        "V": ver,
    }


def generate_weapon_config_json(entry):
    """生成 _WeaponConfig 条目的 JSON 字符串"""
    c = entry
    return f'''    "{c["_id"]}": {{
        "_id": "{c["_id"]}",
        "Name": "{c["Name"]}",
        "Desc": "{escape_js_string(c["Desc"])}",
        "Type": {c["Type"]},
        "Rank": {c["Rank"]},
        "Icons": "{c["Icons"]}",
        "Stat": {c["Stat"]},
        "Custom": "{c["Custom"]}",
        "CustomStat": {c["CustomStat"]},
        "AscMatID": {c["AscMatID"]},
        "MatIDs": [
            {c["MatIDs"][0] if len(c["MatIDs"]) > 0 else "null"},
            {c["MatIDs"][1] if len(c["MatIDs"]) > 1 else "null"}
        ],
        "EquipAffixName": "{c["EquipAffixName"]}",
        "EquipAffixID": {c["EquipAffixID"]},
        "Extra": [],
        "Story": {c["Story"]},
        "StoryCount": {c["StoryCount"]},
        "V": "{c["V"]}"
    }},'''


# ============================================================
#  _WeaponAffixPConfig_ + weapon_story_cache_ 提取
# ============================================================

def extract_weapon_affix_story(zh_file, weapon_id, story_file, ver_key="1"):
    """
    提取武器精炼和故事数据
    :param zh_file: JSON文件路径
    :param weapon_id: 武器ID
    :param story_file: 故事文件路径
    :param ver_key: 版本键，如 "L", "M", "1", "2"
    """
    with open(zh_file, 'r', encoding='utf-8') as f:
        api = json.load(f)

    equip_affix_id = int(f"1{weapon_id}")

    # --- 精炼数据 ---
    # API refinement 是精炼等级1-5，每个等级有独立描述
    # 但输出格式需要把所有精炼等级合并到一个版本条目中
    refinement = api.get('refinement', {})
    refined_descs = []
    for level in sorted(refinement.keys(), key=lambda x: int(x)):
        desc = refinement[level].get('desc', '')
        refined_descs.append(process_color_tags(desc))

    combined_desc = merge_refinement_descs(refined_descs)

    affix_config = {
        str(equip_affix_id): {
            "Ver": {
                ver_key: {
                    "Affix": [combined_desc]
                }
            }
        }
    }

    # --- 故事 ---
    story_cache = {}
    story_id = int(f"19{int(weapon_id) % 10000}")
    if os.path.exists(story_file):
        with open(story_file, 'r', encoding='utf-8') as f:
            story_text = f.read()
        story_cache[str(story_id)] = [story_text.replace('\n', '<br>')]
    else:
        print(f"  [警告] 故事文件不存在: {story_file}，使用默认空故事")
        # 如果获取不到故事文件，写入默认的空故事内容
        story_cache[str(story_id)] = ["暂无故事"]

    return affix_config, story_cache


def generate_weapon_js(weapon_id, affix_config, story_cache, output_file, merge_existing=False):
    """
    生成 Weapon/{id}.js 文件
    :param weapon_id: 武器ID
    :param affix_config: 精炼配置
    :param story_cache: 故事缓存
    :param output_file: 输出文件路径
    :param merge_existing: 是否合并到已存在的文件
    """
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # 如果需要合并，读取现有文件
    if merge_existing and os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 提取现有的 _WeaponAffixPConfig_
        affix_start = content.find('var _WeaponAffixPConfig_ = ')
        if affix_start >= 0:
            affix_end = content.find('\n\nvar weapon_story_cache_ = ')
            if affix_end > affix_start:
                affix_json_str = content[affix_start + len('var _WeaponAffixPConfig_ = '):affix_end]
                try:
                    existing_affix = json.loads(affix_json_str)
                    # 合并版本数据
                    equip_affix_id = str(int(f"1{weapon_id}"))
                    if equip_affix_id in existing_affix:
                        existing_affix[equip_affix_id]["Ver"].update(affix_config[equip_affix_id]["Ver"])
                    else:
                        existing_affix.update(affix_config)
                    affix_config = existing_affix
                except Exception as e:
                    print(f"  [警告] 合并精炼配置失败: {e}")
        
        # 提取现有的 weapon_story_cache_
        story_start = content.find('var weapon_story_cache_ = ')
        if story_start >= 0:
            story_end = content.find('\n', story_start + len('var weapon_story_cache_ = '))
            if story_end < 0:
                story_end = len(content)
            story_json_str = content[story_start + len('var weapon_story_cache_ = '):]
            try:
                existing_story = json.loads(story_json_str)
                # 合并故事数据（保留现有数据，如果新数据不为空则更新）
                if story_cache:
                    existing_story.update(story_cache)
                story_cache = existing_story
            except Exception as e:
                print(f"  [警告] 合并故事缓存失败: {e}")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('// Auto Generated\n\n')

        f.write('var _WeaponAffixPConfig_ = ')
        f.write(json.dumps(affix_config, indent=4, ensure_ascii=False))
        f.write('\n\n')

        f.write('var weapon_story_cache_ = ')
        f.write(json.dumps(story_cache, indent=4, ensure_ascii=False))
        f.write('\n')


# ============================================================
#  插入到 Weapon.js 的 _WeaponConfig
# ============================================================

def merge_to_avatar_js(entry):
    ws = AVATAR_JS_PATH
    if not os.path.exists(ws):
        print(f"  [警告] 未找到 {ws}，跳过自动拼接")
        return ""

    with open(ws, 'r', encoding='utf-8') as f:
        content = f.read()

    wid = entry["_id"]
    new_entry_str = generate_weapon_config_json(entry).rstrip('\n')

    # 定位 _WeaponConfig 对象头部
    marker = 'var _WeaponConfig = {'
    marker_pos = content.find(marker)
    if marker_pos < 0:
        return "错误：无法定位 _WeaponConfig"

    # 检查是否已存在相同ID的条目，存在则替换
    id_marker = f'"_id": "{wid}"'
    id_pos = content.find(id_marker)
    if id_pos >= 0:
        # 找到该条目在对象中的起始位置（向前找最近的 '"' 开头）
        block_start = content.rfind('\n    "', 0, id_pos)
        if block_start < 0 or block_start < marker_pos:
            return f"错误：无法定位武器 {wid} 的条目起始位置"

        # 找到该条目的结束位置（匹配 } 后跟 , 或 } ）
        brace_depth = 0
        block_end = id_pos
        in_block = False
        for i in range(block_start, len(content)):
            ch = content[i]
            if ch == '{':
                brace_depth += 1
                in_block = True
            elif ch == '}':
                brace_depth -= 1
                if in_block and brace_depth == 0:
                    # 找到闭合的 }，检查后面是否有逗号
                    if i + 1 < len(content) and content[i + 1] == ',':
                        block_end = i + 2
                    else:
                        block_end = i + 1
                    break

        new_content = content[:block_start] + '\n' + new_entry_str + '\n' + content[block_end:]
        with open(ws, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return f"武器 {wid} 条目已存在，已用新版本数据替换"

    # 不存在，插入到对象第一个元素之前（即 { 之后）
    head_pos = content.find('\n', marker_pos) + 1
    if head_pos <= 0:
        return "错误：无法定位 _WeaponConfig 对象头部"

    new_content = content[:head_pos] + new_entry_str + '\n' + content[head_pos:]

    with open(ws, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return f"已自动拼接武器 {wid} 到 {ws}"


# ============================================================
#  main 入口
# ============================================================

def main():
    import sys
    if len(sys.argv) < 2:
        print("用法: python gi_weapon_trans.py <weapon_id> [weapon_id ...]")
        sys.exit(1)

    weapon_ids = sys.argv[1:]

    for wid in weapon_ids:
        download_weapon_data(wid)

        zh_file = os.path.join(CACHE_DIR, f"{API_VERSION}-weapon-{wid}-zh.json")
        story_file = os.path.join(CACHE_DIR, f"weapon-story-{wid}.txt")

        if not os.path.exists(zh_file):
            print(f"  [跳过] 武器 {wid} 数据下载失败")
            continue

        entry = extract_weapon_config(zh_file, wid)
        affix_config, story_cache = extract_weapon_affix_story(zh_file, wid, story_file)

        output_js = os.path.join(WEAPON_DIR, f"{wid}.js")
        generate_weapon_js(wid, affix_config, story_cache, output_js)

        result = merge_to_avatar_js(entry)
        print(f"  {wid}: {entry['Name']} | {result}")

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        summary_path = os.path.join(OUTPUT_DIR, f"weapon_{wid}_summary.json")
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(entry, f, indent=2, ensure_ascii=False)

    print("完成")


def gi_weapon_update(weapon_id, version_map=None):
    """
    server.py 调用入口
    参数:
        weapon_id: 武器ID，如 "14522"
        version_map: 版本映射字典，如 {"L": "6.7.52", "M": "6.8.53"}，默认为 {"L": "6.7.52"}
    返回: (success: bool, message: str)
    """
    if version_map is None:
        version_map = {"L": "6.7.52"}

    wid = str(weapon_id)

    try:
        results = []
        output_js = os.path.join(WEAPON_DIR, f"{wid}.js")
        entries = []  # 收集所有版本的 entry，最后用最后一个版本插入 avatar.js

        for ver_key, api_ver in version_map.items():
            download_weapon_data(wid, api_ver)

            zh_file = os.path.join(CACHE_DIR, f"{api_ver}-weapon-{wid}-zh.json")
            story_file = os.path.join(CACHE_DIR, f"weapon-story-{wid}.txt")

            if not os.path.exists(zh_file):
                results.append(f"版本 {ver_key} ({api_ver}): 数据下载失败")
                continue

            entry = extract_weapon_config(zh_file, wid, ver_key)
            affix_config, story_cache = extract_weapon_affix_story(zh_file, wid, story_file, ver_key)
            entries.append(entry)

            results.append(f"版本 {ver_key} ({api_ver}): {entry['Name']}")

            # Weapon/{id}.js 合并多版本数据
            generate_weapon_js(wid, affix_config, story_cache, output_js, merge_existing=True)

            # 保存摘要
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            summary_path = os.path.join(OUTPUT_DIR, f"weapon_{wid}_{ver_key}_summary.json")
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(entry, f, indent=2, ensure_ascii=False)

        # avatar.js 只插入一份数据（使用最后一个版本，即最新版本）
        if entries:
            last_entry = entries[-1]
            merge_result = merge_to_avatar_js(last_entry)
            results.append(f"avatar.js: {merge_result}")
        else:
            results.append("所有版本数据下载失败，未插入 avatar.js")

        success = all("失败" not in r for r in results)
        message = "\n".join(results)
        return success, message

    except Exception as e:
        return False, f"武器 {wid} 处理异常: {str(e)}"


def get_weapon_icon_from_avatar(weapon_id):
    """
    从本地 Weapon.js 或 avatar.js 获取武器图标名称
    :param weapon_id: 武器ID
    :return: 图标名称（如 "UI_EquipIcon_Sword_Swanlake"）或空字符串
    """
    wid = str(weapon_id)

    def _search_icons(content, source_name):
        block_pattern = rf'"_id":\s*"{wid}"'
        block_match = re.search(block_pattern, content)
        if block_match:
            pos = block_match.start()
            icons_match = re.search(r'"Icons":\s*"([^"]+)"', content[pos:pos+2000])
            if icons_match:
                return icons_match.group(1)
        return None

    # 优先从 Weapon.js 查找（武器数据已独立到 Weapon.js）
    weapon_js_path = os.path.join(os.getcwd(), WEAPON_DIR + ".js")
    if os.path.exists(weapon_js_path):
        try:
            with open(weapon_js_path, 'r', encoding='utf-8') as f:
                content = f.read()
            icon = _search_icons(content, "Weapon.js")
            if icon:
                return icon
        except Exception as e:
            print(f"  [警告] 读取 Weapon.js 失败: {e}")

    # 回退到 avatar.js 查找
    avatar_js_path = os.path.join(os.getcwd(), AVATAR_JS_PATH)
    if os.path.exists(avatar_js_path):
        try:
            with open(avatar_js_path, 'r', encoding='utf-8') as f:
                content = f.read()
            icon = _search_icons(content, "avatar.js")
            if icon:
                return icon
        except Exception as e:
            print(f"  [警告] 读取 avatar.js 失败: {e}")

    print(f"  [警告] 武器 {wid} 未在 Weapon.js 或 avatar.js 中找到")
    return ""


def gi_weapon_img_sync(weapon_id, version="6.7.52"):
    """
    下载武器图片（从本地 Weapon.js 或 avatar.js 获取图标数据）
    参数:
        weapon_id: 武器ID，如 "14522"
        version: 保留参数（兼容旧调用）
    返回: (success: bool, message: str)
    """
    wid = str(weapon_id)

    try:
        # 从本地 Weapon.js / avatar.js 获取图标数据
        icon = get_weapon_icon_from_avatar(wid)
        if not icon:
            return False, f"武器 {wid} 未在本地 Weapon.js 或 avatar.js 中找到，请先更新武器数据"

        # 去掉图标名中的 C# 格式占位符 {0}
        icon = icon.replace("_{0}", "")

        from urllib.parse import urljoin
        IMG_SAVE_DIR = "homdgcat-res/Weapon"
        IMG_BASE_URL = "https://static.nanoka.cc/assets/gi"
        os.makedirs(IMG_SAVE_DIR, exist_ok=True)

        import shutil

        results = []
        normal_path = os.path.join(IMG_SAVE_DIR, f"{icon}.png")
        awaken_path = os.path.join(IMG_SAVE_DIR, f"{icon}_Awaken.png")

        # --- 下载突破前图片 ---
        normal_url = f"{IMG_BASE_URL}/{icon}.webp"
        if os.path.exists(normal_path):
            results.append(f"{icon}.png (缓存)")
        else:
            try:
                r = requests.get(normal_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
                r.raise_for_status()
                with open(normal_path, 'wb') as f:
                    f.write(r.content)
                results.append(f"{icon}.png (下载成功)")
            except Exception as e:
                results.append(f"{icon}.png (失败: {e})")

        # --- 下载突破后图片 ---
        awaken_url = f"{IMG_BASE_URL}/{icon}_Awaken.webp"
        if os.path.exists(awaken_path):
            results.append(f"{icon}_Awaken.png (缓存)")
        else:
            try:
                r = requests.get(awaken_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
                r.raise_for_status()
                with open(awaken_path, 'wb') as f:
                    f.write(r.content)
                results.append(f"{icon}_Awaken.png (下载成功)")
            except Exception:
                # 突破后资源不存在，将突破前图片复制为 _Awaken.png
                if os.path.exists(normal_path):
                    shutil.copy2(normal_path, awaken_path)
                    results.append(f"{icon}_Awaken.png (复用突破前)")
                else:
                    results.append(f"{icon}_Awaken.png (失败: 突破前图片也不存在)")

        return True, f"武器 {wid} 图片: " + ", ".join(results)

    except Exception as e:
        return False, f"武器 {wid} 图片下载异常: {str(e)}"


if __name__ == '__main__':
    main()