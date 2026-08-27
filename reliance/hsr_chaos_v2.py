#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
混沌回忆处理 v2 — 基于EliteGroup自动计算怪物HP，无需手动输入HP倍率
在hsr_trans_chaos.py基础上改进，使用elitegroup的HPRatio替代手动hp_ratios输入

用法：python reliance/hsr_chaos_v2.py <maze_id> [version]
示例：
    python reliance/hsr_chaos_v2.py 1033
    python reliance/hsr_chaos_v2.py 1033 4.3.52
"""

import os
import sys
import json
import re
import requests
from typing import Dict, Any, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reliance.sync_elite import (
    load_level_curves as load_elite_curves,
    get_elite_group,
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

BASE_URL = "https://static.nanoka.cc/hsr"
LANGUAGE = "zh"
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "tempdata")
MONSTER_DB_PATH = os.path.join(PROJECT_ROOT, "sr", "data", "CH", "Monster.js")
CHAOS_JS_PATH = os.path.join(PROJECT_ROOT, "sr", "data", "CH", "Chaos_1.js")
CHAOS_STAR_PATH = os.path.join(PROJECT_ROOT, "sr", "data", "CH", "Chaos_star.js")
DEFAULT_VERSION = "4.3.52"

os.makedirs(OUTPUT_DIR, exist_ok=True)

FLOOR_LEVEL_MAP = {
    1: 68, 2: 70, 3: 73, 4: 75, 5: 78,
    6: 80, 7: 82, 8: 85, 9: 88, 10: 90, 11: 92, 12: 95,
}


def remove_trailing_commas(json_str: str) -> str:
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)
    return json_str


def download_maze_data(version: str, maze_id: str) -> Any:
    """下载迷宫数据（兼容列表和字典两种格式）"""
    url = f"{BASE_URL}/{version}/{LANGUAGE}/maze/{maze_id}.json"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"下载迷宫数据失败: {e}")
        return {}


def get_level_curve(curves: Dict[str, Any], hard_level_group: int, level: int) -> Dict[str, float]:
    """获取等级曲线数据（曲线索引 = 游戏等级 - 1，因为游戏没有0级）"""
    hlg = curves["hardlevelgroup"]
    hlg_str = str(hard_level_group)
    curve_level = level - 1
    lvl_str = str(curve_level)

    if hlg_str in hlg and lvl_str in hlg[hlg_str]:
        return hlg[hlg_str][lvl_str]

    if hlg_str in hlg:
        available = sorted([int(k) for k in hlg[hlg_str].keys()])
        if available:
            closest = min(available, key=lambda x: abs(x - curve_level))
            return hlg[hlg_str][str(closest)]

    return {"HP": 1, "ATK": 1, "DEF": 1, "SPD": 1, "Stance": 1}


_monster_api_cache: Dict[str, Optional[Dict[str, Any]]] = {}


def download_monster_data(monster_id: int, version: str) -> Optional[Dict[str, Any]]:
    """下载单个怪物数据（带内存缓存）"""
    mid_str = str(monster_id)
    cache_key = f"{mid_str}_{version}"
    if cache_key in _monster_api_cache:
        return _monster_api_cache[cache_key]

    local_file = os.path.join(OUTPUT_DIR, f"monster_{mid_str}_{version}.json")

    if os.path.exists(local_file):
        try:
            with open(local_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                _monster_api_cache[cache_key] = data
                return data
        except Exception:
            pass

    url = f"{BASE_URL}/{version}/{LANGUAGE}/monster/{mid_str}.json"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        try:
            with open(local_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        _monster_api_cache[cache_key] = data
        return data
    except Exception:
        _monster_api_cache[cache_key] = None
        return None


def get_monster_child(monster_data: Dict[str, Any], target_id: int) -> Optional[Dict[str, Any]]:
    """从怪物数据中找到匹配的子条目"""
    children = monster_data.get("child", [])
    for child in children:
        if child.get("id") == target_id:
            return child
    return children[0] if children else None


def get_hp_count(monster_data: Dict[str, Any]) -> float:
    """从怪物数据中获取HPCount累加所有阶段"""
    phase_list = monster_data.get("phase_list", [])
    if phase_list:
        return sum(p.get("phase_max_hp_ratio", 1.0) for p in phase_list)
    return monster_data.get("max_monster_phase", 1) or 1


def load_monster_base_stats() -> Dict[str, Dict[str, float]]:
    """从Monster.js加载怪物基础属性（含嵌套Child变体），提取HP/SPD/Stance/HPCount"""
    result = {}

    if not os.path.exists(MONSTER_DB_PATH):
        return result

    with open(MONSTER_DB_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    start = content.find('var _monster = {')
    end = content.find('var _monsterlist = [')
    if start == -1 or end == -1:
        return result

    js_obj = content[start + len('var _monster = '):end].strip()
    js_obj = js_obj.rstrip(';').strip()
    js_obj = remove_trailing_commas(js_obj)

    try:
        monster_data = json.loads(js_obj)
    except json.JSONDecodeError:
        return result

    for mid, mdata in monster_data.items():
        if isinstance(mdata, dict):
            stats = mdata.get("Stats", {})
            hp_count = mdata.get("HPCount", 1)
            if stats:
                result[mid] = {
                    "HP": stats.get("HP", 0),
                    "SPD": stats.get("SPD", 0),
                    "Stance": stats.get("Stance", 0),
                    "HPCount": hp_count if hp_count else 1
                }
            if "Child" in mdata:
                for child_id, child_data in mdata["Child"].items():
                    child_stats = child_data.get("Stats", {})
                    child_hp_count = child_data.get("HPCount", mdata.get("HPCount", 1))
                    if child_stats:
                        result[child_id] = {
                            "HP": child_stats.get("HP", 0),
                            "SPD": child_stats.get("SPD", 0),
                            "Stance": child_stats.get("Stance", 0),
                            "HPCount": child_hp_count if child_hp_count else 1
                        }
    return result


_monster_base_cache = None


def get_monster_base_stats() -> Dict[str, Dict[str, float]]:
    global _monster_base_cache
    if _monster_base_cache is None:
        _monster_base_cache = load_monster_base_stats()
    return _monster_base_cache


def calc_monster_stats(
    monster_id: int, level: int, hard_level_group: int,
    elite_group_id: int, curves: Dict[str, Any],
    version: str
) -> Optional[Dict[str, Any]]:
    """
    计算怪物在指定等级下的HP/SPD/Stance（与hsr_trans_as.py保持一致）

    回退优先级：
    1. Monster.js本地数据
    2. API精确匹配
    3. API父级ID回退
    """
    base_hp = None
    base_spd = None
    base_stance = None
    hp_count = 1

    # 优先级1: 本地Monster.js（含HPCount，不访问API）
    base_stats = get_monster_base_stats()
    key = str(monster_id)
    if key in base_stats:
        bs = base_stats[key]
        base_hp = bs["HP"]
        base_spd = bs["SPD"]
        base_stance = bs["Stance"]
        hp_count = bs.get("HPCount", 1)

    # 优先级2: API精确匹配（9位ID无直接API端点，跳过）
    if base_hp is None and len(str(monster_id)) != 9:
        monster_data = download_monster_data(monster_id, version)
        child = None
        if monster_data:
            child = get_monster_child(monster_data, monster_id)
        if monster_data and child:
            hp_base = monster_data.get("hp_base", 0) or 0
            speed_base = monster_data.get("speed_base", 0) or 0
            stance_base = monster_data.get("stance_base", 0) or 0
            hp_count = get_hp_count(monster_data)

            hp_mod = child.get("hp_modify_ratio", 1) or 1
            spd_mod = child.get("speed_modify_ratio", 1) or 1
            stance_mod = child.get("stance_modify_ratio", 1) or 1

            base_hp = (hp_base / 93.0) * hp_mod
            base_spd = speed_base * spd_mod
            base_stance = (stance_base / 30.0) * stance_mod

    # 优先级3: API父级ID回退
    if base_hp is None:
        str_id = str(monster_id)
        found_parent = False
        if len(str_id) == 9:
            trim_lengths = [2]
        else:
            trim_lengths = [1, 2, 3]
        for trim_len in trim_lengths:
            if len(str_id) > trim_len:
                parent_id = int(str_id[:-trim_len])
                parent_data = download_monster_data(parent_id, version)
                if parent_data:
                    child = get_monster_child(parent_data, monster_id)
                    if child:
                        hp_base = parent_data.get("hp_base", 0) or 0
                        speed_base = parent_data.get("speed_base", 0) or 0
                        stance_base = parent_data.get("stance_base", 0) or 0

                        hp_mod = child.get("hp_modify_ratio", 1) or 1
                        spd_mod = child.get("speed_modify_ratio", 1) or 1
                        stance_mod = child.get("stance_modify_ratio", 1) or 1

                        base_hp = (hp_base / 93.0) * hp_mod
                        base_spd = speed_base * spd_mod
                        base_stance = (stance_base / 30.0) * stance_mod
                        hp_count = get_hp_count(parent_data)
                        found_parent = True
                        break
        if not found_parent:
            print(f"警告：无法获取怪物 {monster_id} 的数据（本地和API中均未找到）")
            return {"ID": monster_id, "HP": 0, "SPD": 0, "Stance": 0}

    curve = get_level_curve(curves, hard_level_group, level)
    elite = get_elite_group(curves, elite_group_id, version=version)

    curve_hp = curve.get("HP", 1)
    curve_spd = curve.get("SPD", 1)
    curve_stance = curve.get("Stance", 1)
    hpratio = elite.get("HPRatio", 1)

    hp = round(base_hp * curve_hp * hpratio)
    spd = round(base_spd * curve_spd)
    stance = round(base_stance * curve_stance)

    return {
        "ID": monster_id,
        "HP": hp,
        "SPD": spd,
        "Stance": stance,
        "HPCount": hp_count
    }


def convert_floor_data_v2(
    floor: Dict[str, Any],
    floor_num: int,
    curves: Dict[str, Any],
    version: str = "4.3.52"
) -> Optional[Dict[str, Any]]:
    """
    转换单个楼层数据（v2：使用elitegroup的HPRatio + calc_monster_stats）
    """
    damage_type_map = {
        "Physical": "Phys", "Fire": "Fire", "Ice": "Ice",
        "Thunder": "Elec", "Wind": "Wind", "Quantum": "Quantum",
        "Imaginary": "Imaginary"
    }

    elem_upper = [damage_type_map.get(d, d) for d in floor.get("damage_type1", [])]
    elem_lower = [damage_type_map.get(d, d) for d in floor.get("damage_type2", [])]

    upper_event_raw = floor.get("event_id_list1", [])
    lower_event_raw = floor.get("event_id_list2", [])

    if not upper_event_raw or not lower_event_raw:
        print(f"  警告: 第{floor_num}层缺少event数据，跳过")
        return None

    upper_event = upper_event_raw[0]
    lower_event = lower_event_raw[0]

    if isinstance(upper_event, list):
        upper_event = upper_event[0] if upper_event else {}
    if isinstance(lower_event, list):
        lower_event = lower_event[0] if lower_event else {}

    if not isinstance(upper_event, dict) or not isinstance(lower_event, dict):
        print(f"  警告: 第{floor_num}层event数据格式异常，跳过")
        return None

    upper_level = upper_event.get("level", FLOOR_LEVEL_MAP.get(floor_num, 68))
    lower_level = lower_event.get("level", FLOOR_LEVEL_MAP.get(floor_num, 68))
    upper_hard_level_group = upper_event.get("hard_level_group", 3)
    lower_hard_level_group = lower_event.get("hard_level_group", 3)
    upper_elite_group = upper_event.get("elite_group", 0)
    lower_elite_group = lower_event.get("elite_group", 0)

    upper_elite = get_elite_group(curves, upper_elite_group, version=version) if upper_elite_group else {"HPRatio": 1.0}
    lower_elite = get_elite_group(curves, lower_elite_group, version=version) if lower_elite_group else {"HPRatio": 1.0}

    upper_hp_ratio = upper_elite.get("HPRatio", 1.0)
    lower_hp_ratio = lower_elite.get("HPRatio", 1.0)

    print(f"  第{floor_num}层 上: elite_group={upper_elite_group}, HPRatio={upper_hp_ratio}, 下: elite_group={lower_elite_group}, HPRatio={lower_hp_ratio}")

    def convert_stage_waves(event: Dict[str, Any], level: int, hard_level_group: int,
                            elite_group_id: int) -> List[List[Dict[str, Any]]]:
        """将event的monster_list转换为波次数据（与hsr_trans_as.py的convert_stage一致）"""
        monster_list = event.get("monster_list", [])
        if not monster_list:
            return []

        all_waves = []
        for wave in monster_list:
            if not isinstance(wave, dict):
                continue
            wave_monsters = []
            for key in sorted(wave.keys()):
                mid = wave[key]
                if isinstance(mid, int) and mid > 0:
                    stats = calc_monster_stats(mid, level, hard_level_group,
                                               elite_group_id, curves, version)
                    if stats:
                        wave_monsters.append(stats)
            if wave_monsters:
                all_waves.append(wave_monsters)
        return all_waves

    upper_waves = convert_stage_waves(upper_event, upper_level, upper_hard_level_group, upper_elite_group)
    lower_waves = convert_stage_waves(lower_event, lower_level, lower_hard_level_group, lower_elite_group)

    upper_monsters = []
    if upper_waves:
        upper_monsters.append({
            "_id": upper_event.get("stage_id", 0),
            "Level": upper_level,
            "HardLevelGroup": upper_hard_level_group,
            "EliteGroup": {
                "ID": upper_elite_group,
                "HP": upper_hp_ratio
            },
            "Monsters": upper_waves
        })

    lower_monsters = []
    if lower_waves:
        lower_monsters.append({
            "_id": lower_event.get("stage_id", 0),
            "Level": lower_level,
            "HardLevelGroup": lower_hard_level_group,
            "EliteGroup": {
                "ID": lower_elite_group,
                "HP": lower_hp_ratio
            },
            "Monsters": lower_waves
        })

    return {
        "Floor": floor_num,
        "ElemUpper": elem_upper,
        "ElemLower": elem_lower,
        "Upper": upper_monsters,
        "Lower": lower_monsters
    }


def generate_js_file(maze_id: str, converted_data: Dict[str, Any]) -> None:
    output_file = os.path.join(OUTPUT_DIR, f"Chaos_{maze_id}.js")
    json_str = json.dumps(converted_data, ensure_ascii=False, indent=4)

    lines = json_str.split('\n')
    adjusted_lines = []
    for i, line in enumerate(lines):
        adjusted_lines.append("    " + line)

    adjusted_json = '\n'.join(adjusted_lines)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("// Auto Generated by Chaos V2 (EliteGroup-based)\n\n")
        f.write("var _chaos = [\n")
        f.write(adjusted_json + "\n")
        f.write("]\n\n")
        f.write("// Schedule\n")
        f.write("var _chaosschedule = [\n")
        f.write(f"    {{\n")
        f.write(f'        "_id": {maze_id},\n')
        f.write(f'        "Name": "{converted_data["Name"]}",\n')
        f.write('        "Time": ""\n')
        f.write("    }\n")
        f.write("]\n\n")
        f.write("// HP Data\n")
        f.write("var _chaoshp = {}\n\n")
        f.write("// Dict\n")
        f.write(f'var _chaosdict = {{"{maze_id}": 0}}\n')

    print(f"成功生成JS文件: {output_file}")


def convert_chaos_star_data(
    star_floor: Dict[str, Any],
    curves: Dict[str, Any],
    version: str = "4.3.52"
) -> Optional[Dict[str, Any]]:
    """
    将Star层数据转换为Chaos_star.js格式（参照hsr_trans_as.py的generate_as_star_from_boss）

    Star层API格式：
    - damage_type: 元素类型列表（单列，非damage_type1/damage_type2）
    - event_id_list: 事件列表（单列，非event_id_list1/event_id_list2）
    """
    damage_type_map = {
        "Physical": "Phys", "Fire": "Fire", "Ice": "Ice",
        "Thunder": "Elec", "Wind": "Wind", "Quantum": "Quantum",
        "Imaginary": "Imaginary"
    }

    damage_types = star_floor.get("damage_type", [])
    elem_star = [damage_type_map.get(d, d) for d in damage_types]

    star_events = star_floor.get("event_id_list", [])
    if not star_events:
        print("警告：Star层没有event_id_list数据")
        return None

    event = star_events[0]
    if isinstance(event, list):
        event = event[0] if event else {}
    if not isinstance(event, dict):
        print("警告：Star层event数据格式异常")
        return None

    stage_id = event.get("stage_id", 0)
    stage_level = event.get("level", 95)
    hard_level_group = event.get("hard_level_group", 3)
    elite_group_id = event.get("elite_group", 0)
    monster_list = event.get("monster_list", [])

    elite = get_elite_group(curves, elite_group_id, version=version) if elite_group_id else {"HPRatio": 1.0, "AttackRatio": 1.1}

    star_monsters = []
    for wave in monster_list:
        if not isinstance(wave, dict):
            continue
        wave_monsters = []
        for key in sorted(wave.keys()):
            mid = wave[key]
            if isinstance(mid, int) and mid > 0:
                stats = calc_monster_stats(mid, stage_level, hard_level_group,
                                           elite_group_id, curves, version)
                if stats:
                    m = {
                        "ID": stats["ID"],
                        "HP": stats["HP"],
                        "SPD": stats["SPD"],
                        "Stance": stats["Stance"]
                    }
                    if stats.get("HPCount", 1) > 1:
                        m["HPCount"] = stats["HPCount"]
                    wave_monsters.append(m)
        if wave_monsters:
            star_monsters.append(wave_monsters)

    star_entry = {
        "_id": stage_id,
        "Level": stage_level,
        "HardLevelGroup": hard_level_group,
        "EliteGroup": {
            "ID": elite_group_id,
            "ATK": elite.get("AttackRatio", 1.1),
            "HP": elite.get("HPRatio", 1.0)
        },
        "Monsters": star_monsters
    }

    return {
        "ElemStar": elem_star,
        "Star": [star_entry]
    }


def generate_star_js_file(maze_id: str, star_data: Dict[str, Any]) -> str:
    """
    将Star数据合并到Chaos_star.js中（与AS_star.js的merge_star_to_as_star_js一致的模式）

    如果已存在该maze_id的条目，则跳过；否则追加到Chaos_star.js末尾
    """
    maze_id_str = str(maze_id)

    if os.path.exists(CHAOS_STAR_PATH):
        with open(CHAOS_STAR_PATH, 'r', encoding='utf-8') as f:
            content = f.read()

        if f'"{maze_id_str}"' in content:
            return f"Chaos_star条目 {maze_id_str} 已存在，跳过。如需更新请手动删除后重试"
    else:
        content = 'var _Chaos_star = {}'

    star_json = json.dumps(star_data, ensure_ascii=False, indent=4)
    star_lines = star_json.split('\n')
    star_block = '    "' + maze_id_str + '": ' + '\n'.join(star_lines)

    star_block = star_block.replace('\n', '\n    ')

    if content.strip().endswith('}'):
        content = content.rstrip()
        if content.endswith('}'):
            content = content[:-1].rstrip()
            if content.rstrip().endswith('{'):
                content = content.rstrip() + '\n' + star_block + '\n}'
            else:
                content = content.rstrip() + ',\n' + star_block + '\n}'

    with open(CHAOS_STAR_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"成功将Star数据合并到: {CHAOS_STAR_PATH}")
    return f"Star数据已写入 Chaos_star.js (maze_id={maze_id_str})"


def merge_chaos_to_chaos_js(converted_data: Dict[str, Any]) -> str:
    """
    将混沌回忆数据自动拼接到Chaos_1.js中（参照hsr_trans_as.py的merge_chaos_to_as_js）

    操作：
    1. 在_chaos数组最前面插入新条目
    2. 在_chaosschedule数组最前面插入schedule条目
    """
    chaos_id = converted_data.get("_id", 0)
    chaos_id_str = str(chaos_id)
    name = converted_data.get("Name", "未知")
    clean_name = re.sub(r'<[^>]*>', '', name).strip()

    if not os.path.exists(CHAOS_JS_PATH):
        return f"文件不存在: {CHAOS_JS_PATH}"

    with open(CHAOS_JS_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    if f'"_id": {chaos_id}' in content:
        return f"Chaos条目 {chaos_id} 已存在，无需拼接"

    # 1. 在 var _chaos = [ 之后插入 chaos 条目
    marker_chaos = 'var _chaos = ['
    idx_chaos = content.index(marker_chaos)
    insert_chaos = idx_chaos + len(marker_chaos)

    entry_json = json.dumps(converted_data, ensure_ascii=False, indent=4)
    entry_lines = entry_json.split('\n')
    entry_str = '\n'.join('    ' + line for line in entry_lines)
    content = content[:insert_chaos] + '\n' + entry_str + ',\n' + content[insert_chaos:]

    # 2. 在 var _chaosschedule = [ 之后插入 schedule 条目
    marker_sched = 'var _chaosschedule = ['
    idx_sched = content.index(marker_sched)
    insert_sched = idx_sched + len(marker_sched)
    sched_entry = (
        f'\n    {{\n'
        f'        "_id": {chaos_id},\n'
        f'        "Name": "{clean_name}",\n'
        f'        "Time": ""\n'
        f'    }},'
    )
    content = content[:insert_sched] + sched_entry + content[insert_sched:]

    with open(CHAOS_JS_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"成功将Chaos数据合并到: {CHAOS_JS_PATH}")
    return f"已自动拼接Chaos {chaos_id}（{clean_name}）到 Chaos_1.js"


def generate_chaos_v2(maze_id: str, version: str = DEFAULT_VERSION) -> str:
    """
    v2版本：基于EliteGroup自动计算HP，无需手动输入hp_ratios
    """
    print(f"[Chaos V2] 开始处理混沌回忆 {maze_id}...")

    curves = load_elite_curves()

    maze_data = download_maze_data(version, maze_id)
    if not maze_data:
        return "无法获取迷宫数据，退出"

    # 兼容新旧两种API格式
    if isinstance(maze_data, list):
        # 新格式：直接是楼层列表，每个元素自带group_name、desc、damage_type等
        if not maze_data:
            return "迷宫数据为空，退出"

        first = maze_data[0]
        group_name = first.get("group_name", first.get("name", "未知"))
        buff_desc = first.get("desc", "")
        buff_id = first.get("id", 0)

        # 过滤出普通楼层（有damage_type1/event_id_list1的）和星启层（有challenge_special的）
        regular_floors = [f for f in maze_data if "damage_type1" in f and "event_id_list1" in f]
        star_floors = [f for f in maze_data if "challenge_special" in f]

        levels = regular_floors
    else:
        # 旧格式：{config: {...}, level: [...]}
        config = maze_data.get("config", {})
        group_name = config.get("maze_group_name", config.get("name", "未知"))
        buff_id = config.get("map_buff_id", 0)
        buff_desc = config.get("map_buff_desc", "")
        levels = maze_data.get("level", [])

    floors = []
    for i in range(min(12, len(levels))):
        if i >= len(levels):
            break
        floor = levels[i]
        floor_num = i + 1
        floor_data = convert_floor_data_v2(
            floor, floor_num, curves,
            version=version
        )
        if floor_data is not None:
            floors.append(floor_data)

    converted_data = {
        "_id": int(maze_id),
        "Name": group_name,
        "Buff": {
            "_id": buff_id,
            "Name": "记忆紊流",
            "Desc": buff_desc
        },
        "Floors": floors
    }

    # 自动拼接到Chaos_1.js
    merge_result = merge_chaos_to_chaos_js(converted_data)
    print(merge_result)

    # 处理Star层（如有）
    star_msg = ""
    if isinstance(maze_data, list):
        star_floors = [f for f in maze_data if "challenge_special" in f]
        if star_floors:
            print(f"[Chaos V2] 检测到Star层数据，开始处理...")
            star_data = convert_chaos_star_data(star_floors[0], curves, version=version)
            if star_data:
                star_msg = generate_star_js_file(maze_id, star_data)
            else:
                star_msg = "Star层数据转换失败"

    return f"混沌回忆 {maze_id} ({group_name}) 处理完成！\n共 {len(floors)} 层" + (f"\n{star_msg}" if star_msg else "")


def main():
    if len(sys.argv) < 2:
        print("用法: python reliance/hsr_chaos_v2.py <maze_id> [version]")
        print("示例: python reliance/hsr_chaos_v2.py 1033")
        print("      python reliance/hsr_chaos_v2.py 1033 4.3.52")
        print("\nv2版本使用EliteGroup数据自动计算HP，无需手动输入倍率")
        sys.exit(1)

    maze_id = sys.argv[1]
    version = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_VERSION

    print(f"目标ID: {maze_id}")
    print(f"版本: {version}")
    print("模式: 自动EliteGroup HP计算")
    print()

    result = generate_chaos_v2(maze_id, version)
    print(result)


if __name__ == "__main__":
    main()