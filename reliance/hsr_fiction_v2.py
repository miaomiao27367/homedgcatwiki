#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
虚构叙事处理 v2 — 使用calc_monster_stats统一计算怪物HP/SPD/Stance
与hsr_chaos_v2.py保持一致，基于EliteGroup+等级曲线，三级回退策略

用法：python reliance/hsr_fiction_v2.py <story_id> [version]
示例：
    python reliance/hsr_fiction_v2.py 101
    python reliance/hsr_fiction_v2.py 101 4.3.52
"""

import os
import sys
import re
import json
import requests
from typing import Dict, Any, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reliance.sync_elite import (
    load_level_curves as load_elite_curves,
    get_elite_group,
)

BASE_URL = "https://static.nanoka.cc/hsr"
LANGUAGE = "zh"
OUTPUT_DIR = "./tempdata"
DEFAULT_VERSION = "4.3.52"

MONSTER_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sr", "data", "CH", "Monster.js")
FICTION_1_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sr", "data", "CH", "Fiction_1.js")
FICTION_STAR_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sr", "data", "CH", "Fiction_star.js")

os.makedirs(OUTPUT_DIR, exist_ok=True)

_monster_api_cache: Dict[str, Optional[Dict[str, Any]]] = {}
_monster_base_cache: Optional[Dict[str, Dict[str, float]]] = None


def remove_trailing_commas(json_str: str) -> str:
    import re
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)
    return json_str


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
        response = requests.get(url, timeout=30)
        if response.status_code == 404:
            _monster_api_cache[cache_key] = None
            return None
        response.raise_for_status()
        data = response.json()
        _monster_api_cache[cache_key] = data

        try:
            with open(local_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        return data
    except Exception as e:
        print(f"  下载怪物 {mid_str} 失败: {e}")
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


def load_monster_base_stats() -> Dict[str, Dict[str, float]]:
    """从Monster.js加载怪物基础属性（含嵌套Child变体），提取HP/SPD/Stance/HPCount"""
    global _monster_base_cache
    if _monster_base_cache is not None:
        return _monster_base_cache

    result: Dict[str, Dict[str, float]] = {}

    if not os.path.exists(MONSTER_PATH):
        _monster_base_cache = result
        return result

    with open(MONSTER_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    start = content.find('var _monster = {')
    end = content.find('var _monsterlist = [')
    if start == -1 or end == -1:
        _monster_base_cache = result
        return result

    js_obj = content[start + len('var _monster = '):end].strip()
    js_obj = js_obj.rstrip(';').strip()
    js_obj = remove_trailing_commas(js_obj)

    try:
        monster_data = json.loads(js_obj)
    except json.JSONDecodeError:
        _monster_base_cache = result
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
    _monster_base_cache = result
    return result


def calc_monster_stats(
    monster_id: int, level: int, hard_level_group: int,
    elite_group_id: int, curves: Dict[str, Any],
    version: str, hp_multiplier: float = 1.0
) -> Optional[Dict[str, Any]]:
    """
    计算怪物在指定等级下的HP/SPD/Stance（与hsr_chaos_v2.py保持一致）

    回退优先级：
    1. Monster.js本地数据（含HPCount，不访问API）
    2. API精确匹配
    3. API父级ID回退
    """
    base_hp = None
    base_spd = None
    base_stance = None
    hp_count = 1

    # 优先级1: 本地Monster.js（含HPCount，不访问API）
    base_stats = load_monster_base_stats()
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

    hp = round(base_hp * curve_hp * hpratio * hp_multiplier)
    spd = round(base_spd * curve_spd)
    stance = round(base_stance * curve_stance)

    return {
        "ID": monster_id,
        "HP": hp,
        "SPD": spd,
        "Stance": stance,
        "HPCount": hp_count
    }


def download_story_data(version: str, story_id: str) -> Dict[str, Any]:
    url = f"{BASE_URL}/{version}/{LANGUAGE}/story/{story_id}.json"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"下载数据失败: {e}")
        return {}


def parse_infinite_list_v2(infinite_list: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    解析infinite_list中的怪物数据（v2：同时提取elite_group、keep_num、hp_add）
    返回: 每波的怪物数据列表，包含monster_list、monster_counts、elite_group、keep_num、hp_add
    """
    waves = []
    wave_ids = sorted(infinite_list.keys())

    for wave_id in wave_ids:
        wave_data = infinite_list[wave_id]
        raw_list = wave_data.get("monster_group_id_list", [])

        # 统计每个ID实际出现次数
        count_map = {}
        for mid in raw_list:
            count_map[mid] = count_map.get(mid, 0) + 1

        unique_monsters = []
        seen = set()
        for mid in raw_list:
            if mid not in seen:
                seen.add(mid)
                unique_monsters.append(str(mid))

        if len(unique_monsters) == 4 and wave_id.endswith('1'):
            removed = unique_monsters.pop(0)

        elite_group = wave_data.get("elite_group", 0)
        keep_num = wave_data.get("max_teammate_count", 5)
        hp_add = wave_data.get("param_list", [0, 1.0])[1]

        waves.append({
            "monster_list": unique_monsters,
            "monster_counts": count_map,
            "elite_group": elite_group,
            "keep_num": keep_num,
            "hp_add": hp_add,
        })

    return waves


def convert_monster_data_v2(
    monster_waves: List[Dict[str, Any]],
    curves: Dict[str, Any],
    hard_level_group: int,
    level: int,
    version: str = "4.3.52"
) -> List[Dict[str, Any]]:
    """
    转换怪物数据（v2：使用calc_monster_stats统一计算HP/SPD/Stance）
    输出格式匹配Fiction_2.js：每波含KeepNum/HPAdd/EliteGroup/Monsters
    """
    waves = []

    for wave_data in monster_waves:
        monster_list = wave_data.get("monster_list", [])
        monster_counts = wave_data.get("monster_counts", {})
        elite_group_id = wave_data.get("elite_group", 0)
        keep_num = wave_data.get("keep_num", 5)
        hp_add = wave_data.get("hp_add", 1.0)

        wave_monsters = []
        hp_multiplier = 1 + hp_add

        for monster_id in monster_list:
            mid = int(monster_id)
            num = monster_counts.get(mid, 1)
            stats = calc_monster_stats(mid, level, hard_level_group,
                                       elite_group_id, curves, version,
                                       hp_multiplier)
            if stats:
                m = {
                    "ID": stats["ID"],
                    "Num": num,
                    "HP": stats["HP"],
                    "SPD": stats["SPD"],
                    "Stance": stats["Stance"]
                }
                if stats.get("HPCount", 1) > 1:
                    m["HPCount"] = stats["HPCount"]
                wave_monsters.append(m)
            else:
                wave_monsters.append({
                    "ID": mid,
                    "Num": num,
                    "HP": 0,
                    "SPD": 0,
                    "Stance": 0
                })

        elite = get_elite_group(curves, elite_group_id, version=version)
        wave_entry = {
            "KeepNum": keep_num,
            "HPAdd": hp_add,
            "EliteGroup": {
                "ID": elite_group_id,
                "ATK": elite.get("AttackRatio", 0.5)
            },
            "Monsters": wave_monsters
        }
        waves.append(wave_entry)

    return waves


def merge_fiction_to_fiction_js(converted_data: Dict[str, Any]) -> str:
    """
    将虚构叙事数据自动拼接到Fiction_1.js中（参照hsr_chaos_v2.py的merge_chaos_to_chaos_js）

    操作：
    1. 在_fiction数组最前面插入新条目
    2. 在_fictionschedule数组最前面插入schedule条目
    """
    fiction_id = converted_data.get("_id", 0)
    fiction_id_str = str(fiction_id)
    name = converted_data.get("Name", "未知")
    clean_name = re.sub(r'<[^>]*>', '', name).strip()

    if not os.path.exists(FICTION_1_PATH):
        return f"文件不存在: {FICTION_1_PATH}"

    with open(FICTION_1_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    if f'"_id": {fiction_id}' in content:
        return f"Fiction条目 {fiction_id} 已存在，无需拼接"

    # 1. 在 var _fiction = [ 之后插入 fiction 条目
    marker_fiction = 'var _fiction = ['
    idx_fiction = content.index(marker_fiction)
    insert_fiction = idx_fiction + len(marker_fiction)

    entry_json = json.dumps(converted_data, ensure_ascii=False, indent=4)
    entry_lines = entry_json.split('\n')
    entry_str = '\n'.join('    ' + line for line in entry_lines)
    content = content[:insert_fiction] + '\n' + entry_str + ',\n' + content[insert_fiction:]

    # 2. 在 var _fictionschedule = [ 之后插入 schedule 条目
    marker_sched = 'var _fictionschedule = ['
    idx_sched = content.index(marker_sched)
    insert_sched = idx_sched + len(marker_sched)
    sched_entry = (
        f'\n    {{\n'
        f'        "_id": {fiction_id},\n'
        f'        "Name": "{clean_name}",\n'
        f'        "Time": ""\n'
        f'    }},'
    )
    content = content[:insert_sched] + sched_entry + content[insert_sched:]

    with open(FICTION_1_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"成功将Fiction数据合并到: {FICTION_1_PATH}")
    return f"已自动拼接Fiction {fiction_id}（{clean_name}）到 Fiction_1.js"


def convert_fiction_star_data(
    star_level: Dict[str, Any],
    curves: Dict[str, Any],
    version: str = "4.3.52"
) -> Optional[Dict[str, Any]]:
    """
    将虚构叙事Star层数据转换为Fiction_star.js格式

    Star层API格式：
    - damage_type: 元素类型列表（单列）
    - event_id_list: 事件列表（单列）
    - infinite_list: 无限波次数据（与普通层一致）
    """
    damage_type_map = {
        "Physical": "Phys", "Fire": "Fire", "Ice": "Ice",
        "Thunder": "Elec", "Wind": "Wind", "Quantum": "Quantum",
        "Imaginary": "Imaginary"
    }

    damage_types = star_level.get("damage_type", [])
    elem_star = [damage_type_map.get(d, d) for d in damage_types]

    star_events = star_level.get("event_id_list", [])
    if not star_events:
        print("警告：Star层没有event_id_list数据")
        return None

    event = star_events[0]
    stage_id = event.get("stage_id", 0)
    stage_level = event.get("level", 85)
    hard_level_group = event.get("hard_level_group", 3)

    infinite_list = star_level.get("infinite_list", {})
    star_monster_waves = parse_infinite_list_v2(infinite_list)
    star_waves = convert_monster_data_v2(
        star_monster_waves, curves, hard_level_group, stage_level,
        version=version
    )

    return {
        "ElemStar": elem_star,
        "Star": [
            {
                "_id": stage_id,
                "Level": stage_level,
                "Waves": star_waves
            }
        ]
    }


def merge_star_to_fiction_star_js(story_id: str, star_data: Dict[str, Any]) -> str:
    """
    将Star数据合并到Fiction_star.js中
    如果已存在该story_id的条目，则跳过；否则追加到Fiction_star.js末尾
    """
    story_id_str = str(story_id)

    if os.path.exists(FICTION_STAR_PATH):
        with open(FICTION_STAR_PATH, 'r', encoding='utf-8') as f:
            content = f.read()

        if f'"{story_id_str}"' in content:
            return f"Fiction_star条目 {story_id_str} 已存在，跳过"
    else:
        content = 'var _fiction_star = {}'

    star_json = json.dumps(star_data, ensure_ascii=False, indent=4)
    star_lines = star_json.split('\n')
    star_block = '    "' + story_id_str + '": ' + '\n'.join(star_lines)
    star_block = star_block.replace('\n', '\n    ')

    if content.strip().endswith('}'):
        content = content.rstrip()
        if content.endswith('}'):
            content = content[:-1].rstrip()
            if content.rstrip().endswith('{'):
                content = content.rstrip() + '\n' + star_block + '\n}'
            else:
                content = content.rstrip().rstrip(',') + ',\n' + star_block + '\n}'

    with open(FICTION_STAR_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"成功将Star数据合并到: {FICTION_STAR_PATH}")
    return f"Star数据已写入 Fiction_star.js (story_id={story_id_str})"


def replace_placeholders(desc: str, params: List) -> str:
    """替换API描述中的占位符（与hsr_trans_ar.py的convert_tag_to_buff一致）"""
    if not desc:
        return ""

    desc = desc.replace("<color=#f29e38ff>", "<color style='color:#f29e38;'>")
    desc = desc.replace("<unbreak>", "").replace("</unbreak>", "")

    for i, p in enumerate(params):
        idx = i + 1

        m = re.search(r'#' + str(idx) + r'\[([^\]]*)\](%?)', desc)
        if not m:
            continue

        fmt_spec = m.group(1)
        has_pct = m.group(2) == '%'
        full_match = m.group(0)

        if isinstance(p, (int, float)):
            if has_pct:
                val = p * 100
            else:
                val = p

            if fmt_spec.startswith('f'):
                decimals = int(fmt_spec[1:]) if len(fmt_spec) > 1 else 0
                if decimals == 1:
                    display = f"{val:.1f}"
                    if display.endswith('.0'):
                        display = display[:-2]
                else:
                    display = str(int(round(val)))
            elif fmt_spec == 'i':
                display = str(int(round(val)))
            else:
                display = str(int(round(val)))
        else:
            display = str(p)

        if has_pct:
            desc = desc.replace(full_match, f" {display}% ", 1)
        else:
            desc = desc.replace(full_match, f" {display} ", 1)

    desc = desc.strip()
    desc = re.sub(r'\s+', ' ', desc)
    return desc


def generate_fiction_v2(story_id: str, version: str = DEFAULT_VERSION) -> Tuple[str, List[str], Dict[str, Any]]:
    """
    生成虚构叙事数据（v2：使用calc_monster_stats统一计算HP/SPD/Stance）
    自动插入到Fiction_1.js和Fiction_star.js
    """
    print(f"[Fiction V2] 开始处理虚构叙事 {story_id}...")

    curves = load_elite_curves()

    story_data = download_story_data(version, story_id)
    if not story_data:
        return "无法获取虚构叙事数据，退出", [], {}

    group_name = story_data.get("name", "未知")
    levels = story_data.get("level", [])

    # 分离普通层和Star层
    regular_levels = [l for l in levels if "damage_type1" in l and "event_id_list1" in l]
    star_levels = [l for l in levels if "challenge_special" in l]

    floors = []

    damage_type_map = {
        "Physical": "Phys", "Fire": "Fire", "Ice": "Ice",
        "Thunder": "Elec", "Wind": "Wind", "Quantum": "Quantum",
        "Imaginary": "Imaginary"
    }

    for i, floor in enumerate(regular_levels[:4]):
        floor_num = i + 1

        elem_upper = [damage_type_map.get(d, d) for d in floor.get("damage_type1", [])]
        elem_lower = [damage_type_map.get(d, d) for d in floor.get("damage_type2", [])]

        upper_monsters = []
        lower_monsters = []

        # 上半部分
        infinite_list1 = floor.get("infinite_list1", {})
        upper_events = floor.get("event_id_list1", [])

        if upper_events and infinite_list1:
            upper_event = upper_events[0]
            upper_level = upper_event.get("level", 55)
            upper_hard_level = upper_event.get("hard_level_group", 3)
            upper_stage_id = upper_event.get("stage_id", floor_num * 100 + 1)
            upper_monster_waves = parse_infinite_list_v2(infinite_list1)
            upper_waves = convert_monster_data_v2(
                upper_monster_waves, curves, upper_hard_level, upper_level,
                version=version
            )
            if upper_waves:
                upper_monsters.append({
                    "_id": upper_stage_id,
                    "Level": upper_level,
                    "Waves": upper_waves
                })

        # 下半部分
        infinite_list2 = floor.get("infinite_list2", {})
        lower_events = floor.get("event_id_list2", [])

        if lower_events and infinite_list2:
            lower_event = lower_events[0]
            lower_level = lower_event.get("level", 55)
            lower_hard_level = lower_event.get("hard_level_group", 3)
            lower_stage_id = lower_event.get("stage_id", floor_num * 100 + 2)
            lower_monster_waves = parse_infinite_list_v2(infinite_list2)
            lower_waves = convert_monster_data_v2(
                lower_monster_waves, curves, lower_hard_level, lower_level,
                version=version
            )
            if lower_waves:
                lower_monsters.append({
                    "_id": lower_stage_id,
                    "Level": lower_level,
                    "Waves": lower_waves
                })

        floors.append({
            "Floor": floor_num,
            "ElemUpper": elem_upper,
            "ElemLower": elem_lower,
            "Upper": upper_monsters,
            "Lower": lower_monsters
        })

    converted_data = {
        "_id": int(story_id),
        "Name": group_name,
        "BST": 1,
        "Buffs": [
            {
                "_id": 0,
                "Name": b.get("name", ""),
                "Desc": replace_placeholders(b.get("desc", ""), b.get("param", [])),
                "SimpleDesc": ""
            }
            for b in story_data.get("option", [])
        ],
        "Blessing": [
            {
                "_id": 0,
                "Name": b.get("name", ""),
                "Desc": replace_placeholders(b.get("desc", ""), b.get("param", []))
            }
            for b in story_data.get("sub_option", [])
        ],
        "Floors": floors
    }

    # 输出到tempdata
    file_path = os.path.join(OUTPUT_DIR, f"fiction_{story_id}.json")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(converted_data, f, ensure_ascii=False, indent=2)

    # 自动拼接到Fiction_1.js
    merge_result = merge_fiction_to_fiction_js(converted_data)
    print(merge_result)

    # 处理Star层（如有）
    star_msg = ""
    if star_levels:
        print(f"[Fiction V2] 检测到Star层数据，开始处理...")
        star_data = convert_fiction_star_data(star_levels[0], curves, version=version)
        if star_data:
            star_msg = merge_star_to_fiction_star_js(story_id, star_data)
            print(star_msg)
        else:
            star_msg = "Star层数据转换失败"

    result_msg = f"虚构叙事 {story_id} ({group_name}) 处理完成！\n"
    result_msg += f"楼层数: {len(floors)}\n"
    result_msg += f"输出文件: {file_path}\n"
    if star_msg:
        result_msg += f"\n{star_msg}"

    return result_msg, [], converted_data


def main():
    if len(sys.argv) < 2:
        print("用法: python reliance/hsr_fiction_v2.py <story_id> [version]")
        print("示例: python reliance/hsr_fiction_v2.py 101")
        print("      python reliance/hsr_fiction_v2.py 101 4.3.52")
        sys.exit(1)

    story_id = sys.argv[1]
    version = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_VERSION

    print(f"目标ID: {story_id}")
    print(f"版本: {version}")
    print()

    result, _, converted_data = generate_fiction_v2(story_id, version)
    print(result)


if __name__ == "__main__":
    main()