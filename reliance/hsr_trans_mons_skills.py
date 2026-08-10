import os
import json
import re
import requests
from typing import Optional, Dict, Any

# 是否保存从网上下载的原始数据到本地缓存，True=保存，False=不保存（每次都重新下载）
SAVE_RAW_DATA = False

def download_monster_data(monster_id: str, version: str, language: str = "zh") -> Optional[Dict[str, Any]]:
    """
    从指定URL下载怪物数据

    Args:
        monster_id: 怪物ID
        version: 版本号，例如 "4.3.51"
        language: 语言

    Returns:
        下载的JSON数据，如果下载失败则返回None
    """
    # 定义testdata目录路径
    testdata_dir = "./tempdatamons"
    os.makedirs(testdata_dir, exist_ok=True)

    # 构建本地文件路径
    local_file = os.path.join(testdata_dir, f"{monster_id}_{version}.json")

    # 检查本地文件是否存在
    if SAVE_RAW_DATA and os.path.exists(local_file):
        try:
            with open(local_file, 'r', encoding='utf-8') as f:
                monster_data = json.load(f)
            return monster_data
        except Exception as e:
            print(f"读取本地缓存文件失败: {e}")
            # 读取失败，继续尝试下载

    # 从网络下载
    url = f"https://static.nanoka.cc/hsr/{version}/{language}/monster/{monster_id}.json"

    try:
        response = requests.get(url)
        response.raise_for_status()

        # 解析JSON数据
        monster_data = response.json()

        # 缓存到本地（由SAVE_RAW_DATA控制）
        if SAVE_RAW_DATA:
            try:
                with open(local_file, 'w', encoding='utf-8') as f:
                    json.dump(monster_data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"缓存数据到本地失败: {e}")
                # 缓存失败不影响返回数据

        return monster_data

    except requests.exceptions.RequestException as e:
        print(f"下载怪物 {monster_id} 的 {version} 版本数据失败: {e}")
        return None

def convert_monster_skill(monster_id: str, monster_data: Dict[str, Any], output_dir: str):
    """
    将怪物技能JSON数据转换为JS文件

    Args:
        monster_id: 怪物ID
        monster_data: 怪物JSON数据
        output_dir: 输出目录
    """
    testdata_dir = "./tempdatamons"
    os.makedirs(testdata_dir, exist_ok=True)
    if not monster_data:
        print(f"Error: 怪物 {monster_id} 的数据为空")
        return

    # 获取怪物ID
    resolved_id = monster_data.get('id') or monster_id

    # 获取第一个child的skill_list
    child = monster_data.get('child') or []
    if len(child) == 0:
        print(f"Error: No child found in data for monster {monster_id}")
        return

    skill_list = (child[0] or {}).get('skill_list') or []
    if not skill_list:
        print(f"Error: No skill_list found in data for monster {monster_id}")
        return

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 构建技能数据
    skills = {}
    ee_data = {}

    for skill in skill_list:
        if not skill:
            continue
        skill_id = skill.get('id')
        if skill_id is None:
            continue

        # 构建技能对象
        skill_obj = {
            "Key": "",  # 空着
            "Name": skill.get('skill_name') or "",
            "Desc": skill.get('skill_desc') or "",
            "P": " ".join(map(str, skill.get('phase_list') or [])),  # 列表转为空格隔开的字符串
            "SP": skill.get('sp_hit_base') or 0,
            "Elem": skill.get('damage_type') or "",
            "K": "",  # 空着
            "EE": []  # 先空着，后续填充
        }

        # 处理extra数据
        extra = skill.get('extra') or {}
        if extra:
            ee_ids = []
            for ee_id, ee_info in extra.items():
                if ee_info is None:
                    continue
                ee_ids.append(int(ee_id))
                ee_data[ee_id] = {
                    "N": ee_info.get('name') or "",
                    "D": ee_info.get('desc') or "",
                    "Param": ee_info.get('param') or []
                }
            skill_obj["EE"] = ee_ids

        skills[skill_id] = skill_obj

    # 生成技能JS文件
    skill_js_content = f"var _monsterskill_{resolved_id} = {json.dumps(skills, ensure_ascii=False, indent=2)};"
    skill_js_path = os.path.join(output_dir, f"{resolved_id}.js")

    with open(skill_js_path, 'w', encoding='utf-8') as f:
        f.write(skill_js_content)

    # 生成EE JS文件（如果有extra数据）
    if ee_data:
        ee_js_content = f"var _monstereffect_{resolved_id} = {json.dumps(ee_data, ensure_ascii=False, indent=2)};"
        ee_js_path = os.path.join(testdata_dir, f"{resolved_id}_ee.js")

        with open(ee_js_path, 'w', encoding='utf-8') as f:
            f.write(ee_js_content)


def convert_monster_basic_data(monster_id: str, monster_data: Dict[str, Any], output_dir: str):
    """
    将API原始怪物JSON转换为Monster.js嵌套格式
    - 7位ID的本体存储完整Stats
    - 9位ID的变体归入本体的Child，Stats存储为相对于本体的倍率

    Args:
        monster_id: 怪物ID
        monster_data: 怪物JSON数据
        output_dir: 输出目录
    """
    if not monster_data:
        print(f"Error: 怪物 {monster_id} 的数据为空")
        return

    STAT_KEYS = ["HP", "ATK", "DEF", "SPD", "Stance"]
    STAT_DIVISORS = {"HP": 93, "ATK": 1, "DEF": 210, "SPD": 1, "Stance": 30}

    # 元素名映射: API → local
    ELEM_MAP = {
        'Physical': 'Phys',
        'Fire': 'Fire',
        'Ice': 'Ice',
        'Thunder': 'Elec',
        'Wind': 'Wind',
        'Quantum': 'Quantum',
        'Imaginary': 'Imaginary'
    }

    def map_elem(e):
        return ELEM_MAP.get(e, e)

    def compute_stats(hp_base, attack_base, defence_base, speed_base, stance_base,
                      hp_mod=1.0, atk_mod=1.0, def_mod=1.0, spd_mod=1.0, stance_mod=1.0):
        return {
            "HP": round((hp_base * hp_mod) / STAT_DIVISORS["HP"], 4),
            "ATK": round((attack_base * atk_mod) / STAT_DIVISORS["ATK"], 4),
            "DEF": round((defence_base * def_mod) / STAT_DIVISORS["DEF"], 4),
            "SPD": round((speed_base * spd_mod) / STAT_DIVISORS["SPD"], 4),
            "Stance": round((stance_base * stance_mod) / STAT_DIVISORS["Stance"], 4),
        }

    def compute_ratio_stats(parent_stats, child_stats):
        if not parent_stats or not child_stats:
            return child_stats
        ratio = {}
        for key in STAT_KEYS:
            p_val = parent_stats.get(key, 1)
            c_val = child_stats.get(key, p_val)
            if p_val and p_val != 0:
                ratio[key] = round(c_val / p_val, 4)
            else:
                ratio[key] = 1.0
        return ratio

    # 图标路径
    image_path = monster_data.get('image_path') or ''
    icon = ''
    figure = ''
    m = re.search(r'Monster_(\d+)\.png$', image_path)
    if m:
        icon = f"mostericon/Monster_{m.group(1)}.png"
        figure = f"monsterfigure/Monster_{m.group(1)}.png"

    hp_base = monster_data.get('hp_base') or 0
    attack_base = monster_data.get('attack_base') or 0
    defence_base = monster_data.get('defence_base') or 0
    speed_base = monster_data.get('speed_base') or 0
    stance_base = monster_data.get('stance_base') or 0

    children = monster_data.get('child') or []
    if not children:
        print(f"Error: 怪物 {monster_id} 没有child数据")
        return

    # 区分本体和变体
    # 本体: 7位ID且hp_modify_ratio接近1（或第一个child）
    # 变体: 9位ID且hp_modify_ratio≠1
    base_child = None
    variants = []

    for child in children:
        if not child:
            continue
        child_id = child.get('id')
        if child_id is None:
            continue

        hp_mod = child.get('hp_modify_ratio') or 1
        is_default = abs(hp_mod - 1.0) < 0.001

        if is_default and base_child is None:
            base_child = child
        elif not is_default:
            variants.append(child)

    if base_child is None:
        base_child = children[0]

    base_id = base_child.get('id')
    if base_id is None:
        return

    base_id_str = str(base_id)

    # 构建RESBase
    res_base = {}
    for r in base_child.get('damage_type_resistance') or []:
        res_base[map_elem(r.get('damage_type', ''))] = r.get('value', 0)

    # 构建Weak
    weak = [map_elem(w) for w in base_child.get('stance_weak_list') or []]

    # 构建Skills
    skills = [s.get('id') for s in base_child.get('skill_list') or [] if s.get('id') is not None]

    hp_count = monster_data.get('hp_multiple_ratio')
    stance_count = monster_data.get('stance_break')

    base_entry = {
        "_id": base_id,
        "Name": monster_data.get('name') or '',
        "Desc": (monster_data.get('desc') or '').replace('\\n', '\n'),
        "Stats": compute_stats(
            hp_base, attack_base, defence_base, speed_base, stance_base,
            base_child.get('hp_modify_ratio') or 1,
            base_child.get('attack_modify_ratio') or 1,
            base_child.get('defence_modify_ratio') or 1,
            base_child.get('speed_modify_ratio') or 1,
            base_child.get('stance_modify_ratio') or 1,
        ),
        "Weak": weak,
        "RESBase": res_base,
        "StatusRESBase": monster_data.get('status_resistance_base') or 0,
        "DebuffRES": {},
        "Skills": skills,
        "Camp": monster_data.get('monster_camp_id') or 0,
        "Icon": icon,
        "Figure": figure,
    }
    if hp_count and hp_count > 1:
        base_entry["HPCount"] = hp_count
    if stance_count and stance_count > 1:
        base_entry["StanceCount"] = stance_count

    # 构建变体Child
    if variants:
        base_stats = base_entry["Stats"]
        base_entry["Child"] = {}
        for child in variants:
            child_id = child.get('id')
            if child_id is None:
                continue

            child_stats = compute_stats(
                hp_base, attack_base, defence_base, speed_base, stance_base,
                child.get('hp_modify_ratio') or 1,
                child.get('attack_modify_ratio') or 1,
                child.get('defence_modify_ratio') or 1,
                child.get('speed_modify_ratio') or 1,
                child.get('stance_modify_ratio') or 1,
            )

            child_res_base = {}
            for r in child.get('damage_type_resistance') or []:
                child_res_base[map_elem(r.get('damage_type', ''))] = r.get('value', 0)

            child_weak = [map_elem(w) for w in child.get('stance_weak_list') or []]
            child_skills = [s.get('id') for s in child.get('skill_list') or [] if s.get('id') is not None]

            child_entry = {
                "_id": child_id,
                "Name": base_entry["Name"],
                "Desc": base_entry["Desc"],
                "Stats": child_stats,
                "Weak": child_weak,
                "RESBase": child_res_base,
                "StatusRESBase": base_entry.get("StatusRESBase", 0),
                "DebuffRES": base_entry.get("DebuffRES", {}),
                "Skills": child_skills,
                "Camp": base_entry["Camp"],
                "Icon": base_entry["Icon"],
                "Figure": base_entry["Figure"],
            }
            base_entry["Child"][str(child_id)] = child_entry

    # 输出
    basic_entries = {base_id_str: base_entry}

    os.makedirs(output_dir, exist_ok=True)
    resolved_id = monster_data.get('id') or monster_id
    basic_js_content = f"var _monster_{resolved_id} = {json.dumps(basic_entries, ensure_ascii=False, indent=2)};"
    basic_js_path = os.path.join(output_dir, f"{resolved_id}_basic.js")

    with open(basic_js_path, 'w', encoding='utf-8') as f:
        f.write(basic_js_content)

    return basic_entries


def merge_basic_data_to_monster_js(basic_entries: Dict[str, Any]) -> str:
    """
    将新生成的基础数据增量合并到Monster.js的_monster和_monsterlist中

    策略：
    - 新本体（7位ID不存在）：完整插入（本体+Child变体）
    - 已有本体：只追加尚不存在的Child变体到已有本体的Child下
    """
    monster_js_path = "./sr/data/CH/Monster.js"

    with open(monster_js_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 定位 _monster 区域边界，避免搜索到 _status 和 _bossguide
    pattern_monster = '};\n\nvar _monsterlist = ['
    monster_end = content.find(pattern_monster)
    if monster_end == -1:
        return "错误：无法定位 _monster 对象结束位置"
    monster_section = content[:monster_end]

    new_bases = []
    children_to_add = {}  # {base_id: {child_id: child_entry, ...}}

    for base_id, entry in basic_entries.items():
        base_id_str = str(base_id)
        if f'"{base_id_str}":' not in monster_section:
            # 全新本体 → 整条插入
            new_bases.append(base_id_str)
        elif "Child" in entry:
            # 已有本体 → 只检查Child中是否有新变体
            for child_id, child_entry in entry["Child"].items():
                child_id_str = str(child_id)
                if f'"{child_id_str}":' not in monster_section:
                    children_to_add.setdefault(base_id_str, {})[child_id_str] = child_entry

    if not new_bases and not children_to_add:
        return "所有条目已存在，无需拼接"

    result_parts = []

    # 1. 插入全新本体（按ID数值排序）
    if new_bases:
        new_bases_sorted = sorted(new_bases, key=lambda x: int(x))
        new_entries = {cid: basic_entries[cid] for cid in new_bases_sorted}
        new_json = json.dumps(new_entries, ensure_ascii=False, indent=4)
        new_json = new_json[1:-1].strip()  # 去掉外层 {}
        new_json = '\n'.join('    ' + line for line in new_json.split('\n'))  # 补一级缩进

        # 在 _monster 闭合 }; 前插入新本体，逗号紧跟上一行末尾
        idx = content.find(pattern_monster)
        content = content[:idx].rstrip('\n') + ',\n' + new_json + '\n' + content[idx:]

        pattern_list = '];\n\nvar _status = {'
        if pattern_list not in content:
            return "错误：无法定位 _monsterlist 数组结束位置"
        new_id_lines = ',\n'.join(f'    {cid}' for cid in new_bases_sorted)
        idx2 = content.find(pattern_list)
        content = content[:idx2].rstrip('\n') + ',\n' + new_id_lines + '\n' + content[idx2:]

        result_parts.append(f"新增本体 {len(new_bases)} 个：{', '.join(new_bases)}")

    # 2. 为已有本体追加新Child变体
    if children_to_add:
        import re
        total_added = 0
        for base_id, child_dict in children_to_add.items():
            # 定位到本体的起始位置（仅在 _monster 区域内搜索）
            base_entry_pattern = re.compile(
                rf'"{re.escape(base_id)}":\s*\{{',
                re.DOTALL
            )
            m = base_entry_pattern.search(content, 0, monster_end)
            if not m:
                continue

            # 构建新变体JSON（4空格缩进 + 额外12空格偏移 = 3层嵌套）
            new_child_json = json.dumps(child_dict, ensure_ascii=False, indent=4)
            new_child_json = new_child_json[1:-1].strip()  # 去掉外层 {}
            new_child_json = '\n'.join('            ' + line for line in new_child_json.split('\n'))

            # 先定位本体条目的闭合 }（避免 child_pattern 误匹配到其他本体的 Child）
            brace_count = 1
            pos = m.end()
            while pos < len(content) and brace_count > 0:
                if content[pos] == '{':
                    brace_count += 1
                elif content[pos] == '}':
                    brace_count -= 1
                pos += 1
            base_close = pos - 1  # 本体条目闭合 } 的位置

            # 在本体条目范围内找 Child 块
            child_pattern = re.compile(r'"Child":\s*\{')
            child_m = child_pattern.search(content, m.start(), base_close)

            if child_m:
                # 已有Child块 → 在闭合 } 前追加
                child_open = child_m.end()
                brace_count = 1
                pos = child_open
                while pos < len(content) and brace_count > 0:
                    if content[pos] == '{':
                        brace_count += 1
                    elif content[pos] == '}':
                        brace_count -= 1
                    pos += 1
                child_close = pos - 1
                content = content[:child_close].rstrip() + ',\n' + new_child_json + '\n' + content[child_close:]
            else:
                # 没有Child块 → 在本体条目闭合 } 前插入Child块
                child_block = ',\n        "Child": {\n' + new_child_json + '\n        }'
                content = content[:base_close].rstrip() + child_block + '\n' + content[base_close:]

            total_added += len(child_dict)

        result_parts.append(f"追加变体 {total_added} 个")

    with open(monster_js_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return "；".join(result_parts)


def generate_monster_basic_data(monster_id: str, version: str = None) -> str:
    """
    生成怪物基础模块数据（_monster条目），供其他程序调用

    Args:
        monster_id: 怪物ID
        version: 完整版本号，例如 "4.3.51"
    """
    if monster_id is None or version is None:
        return "错误：必须传入 monster_id 和 version 参数"

    monster_data = download_monster_data(monster_id, version)

    if not monster_data:
        return f"下载怪物 {monster_id} 的数据失败"

    output_dir = "./tempdatamons"
    convert_monster_basic_data(monster_id, monster_data, output_dir)

    return f"怪物 {monster_id} 基础模块数据生成完成！"


def generate_monster_data(monster_id: str, version: str = None) -> str:
    """
    封装的生成怪物数据的函数，供其他程序调用

    Args:
        monster_id: 怪物ID
        version: 完整版本号，例如 "4.3.51"
    """

    # 参数检查：必须传入所有参数
    if monster_id is None or version is None:
        return "错误：必须传入 monster_id 和 version 参数"

    # 下载怪物数据
    monster_data = download_monster_data(monster_id, version)

    if not monster_data:
        return f"下载怪物 {monster_id} 的数据失败，退出程序"

    # 输出目录
    output_dir = "./sr/data/CH/skills"
    warning = ""

    # 检查技能文件是否已存在，若存在则生成到tempdatamons并返回警告
    resolved_id = monster_data.get('id') or monster_id
    expected_skill_path = os.path.join(output_dir, f"{resolved_id}.js")
    if os.path.exists(expected_skill_path):
        output_dir = "./tempdatamons"
        warning = f"【警告】怪物 {monster_id} 的技能文件 {resolved_id}.js 已存在于 {expected_skill_path}，新数据已生成到 {output_dir}，请手动比对后决定是否替换。"

    # 转换数据
    convert_monster_skill(monster_id, monster_data, output_dir)

    # 生成基础模块数据（_monster条目）
    basic_entries = convert_monster_basic_data(monster_id, monster_data, "./tempdatamons")

    # 自动拼接到Monster_1.js
    merge_msg = merge_basic_data_to_monster_js(basic_entries)

    result = f"怪物 {monster_id} 数据生成完成！"
    if merge_msg:
        result += "\n" + merge_msg
    if warning:
        return warning + "\n" + result
    return result


def merge_missing_ee_data() -> str:
    """
    读取所有 *_ee.js 文件，与 data/CH/MonsterSkill.js 中 _ee 对象的 key 比对，
    将 MonsterSkill.js 中没有的 eeid 数据合并到 EE.js，然后删除所有 *_ee.js
    """
    import glob, re

    ee_dir = "./tempdatamons"
    monster_skill_file = "./sr/data/CH/MonsterSkill.js"
    output_file = os.path.join(ee_dir, "EE.js")

    # 1. 读取所有 *_ee.js，收集 eeid -> effect 数据
    all_ee_data = {}
    ee_files = glob.glob(os.path.join(ee_dir, "*_ee.js"))
    if not ee_files:
        return "未找到任何 *_ee.js 文件，跳过合并"

    for ee_file in ee_files:
        try:
            with open(ee_file, 'r', encoding='utf-8') as f:
                content = f.read()
            start = content.find('{')
            end = content.rfind('}')
            if start >= 0 and end >= 0 and end > start:
                data = json.loads(content[start:end+1])
                for eeid, ee_info in data.items():
                    if str(eeid) not in all_ee_data:
                        all_ee_data[str(eeid)] = ee_info
        except Exception as e:
            print(f"读取 {ee_file} 失败: {e}")

    if not all_ee_data:
        return "所有 *_ee.js 中没有 effect 数据，跳过合并"

    # 2. 读取 MonsterSkill.js 的 _ee 对象 key
    known_eeids = set()
    if os.path.exists(monster_skill_file):
        try:
            with open(monster_skill_file, 'r', encoding='utf-8') as f:
                content = f.read()
            var_pos = content.find('var _ee =')
            if var_pos >= 0:
                json_start = content.find('{', var_pos)
                json_end = content.rfind('}')
                if json_start >= 0 and json_end >= 0 and json_end > json_start:
                    ee_chunk = content[json_start:json_end+1]
                    try:
                        ee_object = json.loads(ee_chunk)
                        for key in ee_object.keys():
                            known_eeids.add(str(key))
                    except json.JSONDecodeError:
                        # JSON 解析失败时用正则匹配 "数字": 形式的 key
                        key_matches = re.findall(r'"(\d+)"\s*:', ee_chunk)
                        for k in key_matches:
                            known_eeids.add(k)
        except Exception as e:
            print(f"读取 MonsterSkill.js 失败: {e}")
    else:
        print(f"警告: {monster_skill_file} 不存在，将输出所有 ee 数据")

    # 3. 找出 MonsterSkill.js 中不存在的 eeid
    missing_ee_data = {}
    for eeid, ee_info in all_ee_data.items():
        if eeid not in known_eeids:
            missing_ee_data[eeid] = ee_info

    # 4. 写入 EE.js 并删除临时文件
    ee_js_content = f"var _ee = {json.dumps(missing_ee_data, ensure_ascii=False, indent=2)};"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(ee_js_content)
    print(f"EE合并: MonsterSkill.js已有 {len(known_eeids)} 个，新增 {len(missing_ee_data)} 个 -> {output_file}")

    for ee_file in ee_files:
        try:
            os.remove(ee_file)
        except Exception as e:
            print(f"删除 {ee_file} 失败: {e}")

    return f"EE数据合并完成，共 {len(missing_ee_data)} 个新effect写入EE.js"


def main():
    """
    主函数（调试入口）
    """
    monster_list = ["8015030", "8015040", "8015050"]
    for monster_id in monster_list:
        generate_monster_data(monster_id, version="4.3.51")


if __name__ == "__main__":
    main()