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
    load_elite_group_data,
    get_elite_group,
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

BASE_URL = "https://static.nanoka.cc/hsr"
LANGUAGE = "zh"
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "tempdata")
MONSTER_DB_PATH = os.path.join(PROJECT_ROOT, "sr", "data", "CH", "Monster.js")
LEVEL_CURVES_PATH = os.path.join(PROJECT_ROOT, "sr", "data", "LevelCurves.js")
DEFAULT_VERSION = "4.3.52"

os.makedirs(OUTPUT_DIR, exist_ok=True)

FLOOR_LEVEL_MAP = {
    1: 68, 2: 70, 3: 73, 4: 75, 5: 78,
    6: 80, 7: 82, 8: 85, 9: 88, 10: 90, 11: 92, 12: 95,
}

CHAOS_HARD_LEVEL_GROUP = "3"


def remove_trailing_commas(json_str: str) -> str:
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)
    return json_str


def load_local_monster_db() -> Dict[str, Any]:
    monster_db = {}
    if not os.path.exists(MONSTER_DB_PATH):
        print(f"警告: 找不到 {MONSTER_DB_PATH}")
        return monster_db

    with open(MONSTER_DB_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    start = content.find('var _monster = {')
    end = content.find('var _monsterlist = [')
    if start == -1 or end == -1:
        print("警告: 无法解析 Monster.js")
        return monster_db

    json_str = content[start + len('var _monster = '):end].strip()
    json_str = json_str.rstrip(';').strip()
    json_str = remove_trailing_commas(json_str)

    try:
        data = json.loads(json_str)
        for key, value in data.items():
            monster_db[key] = value
            # 展开Child变体到顶层（兼容旧查询逻辑）
            if isinstance(value, dict) and "Child" in value:
                for child_id, child_data in value["Child"].items():
                    monster_db[child_id] = child_data
    except json.JSONDecodeError as e:
        print(f"警告: JSON解析失败: {e}")

    return monster_db


def load_level_curves() -> Dict[str, Any]:
    if not os.path.exists(LEVEL_CURVES_PATH):
        return {}

    with open(LEVEL_CURVES_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    start = content.find('var _hardlevelgroup = {')
    end = content.find('var _elitegroup')
    if start == -1 or end == -1:
        return {}

    curves_str = content[start + len('var _hardlevelgroup = '):end]
    curves_str = remove_trailing_commas(curves_str)

    try:
        data = json.loads(curves_str)
        return data.get("3", {})
    except json.JSONDecodeError:
        return {}


def download_maze_data(version: str, maze_id: str) -> Dict[str, Any]:
    url = f"{BASE_URL}/{version}/{LANGUAGE}/maze/{maze_id}.json"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"下载迷宫数据失败: {e}")
        return {}


def calculate_monster_hp(
    monster_id: int, monster_db: Dict[str, Any],
    level: int, level_curves: Dict[str, Any],
    hp_ratio: float
) -> float:
    monster_info = monster_db.get(str(monster_id), {})
    stats = monster_info.get("Stats", {})

    base_hp = stats.get("HP", 1.0)
    hp_growth = stats.get("HPGrowth", 0.0)
    hp_count = monster_info.get("HPCount", 1)

    level_str = str(level)
    hard_level_curve = level_curves.get(level_str, {})
    hp_curve = hard_level_curve.get("HP", 1.0)

    hp = (base_hp + hp_growth * (level - 1)) * hp_curve * hp_ratio / hp_count
    return round(hp, 2)


def calculate_monster_spd(
    monster_id: int, monster_db: Dict[str, Any],
    level: int, level_curves: Dict[str, Any]
) -> float:
    monster_info = monster_db.get(str(monster_id), {})
    stats = monster_info.get("Stats", {})

    base_spd = stats.get("SPD", 100)
    spd_growth = stats.get("SPDGrowth", 0.0)

    level_str = str(level)
    hard_level_curve = level_curves.get(level_str, {})
    spd_curve = hard_level_curve.get("SPD", 1.0)

    spd = (base_spd + spd_growth * (level - 1)) * spd_curve
    return round(spd, 2)


def convert_monster_data(
    monster_list: List[Dict[str, int]],
    monster_db: Dict[str, Any],
    level: int,
    level_curves: Dict[str, Any],
    hp_ratio: float
) -> List[List[Dict[str, Any]]]:
    converted = []
    for wave_idx, wave in enumerate(monster_list):
        wave_monsters = []
        for key in sorted(wave.keys()):
            monster_id = wave[key]
            monster_info_db = monster_db.get(str(monster_id), {})
            stats = monster_info_db.get("Stats", {})

            hp = calculate_monster_hp(monster_id, monster_db, level, level_curves, hp_ratio)
            spd = calculate_monster_spd(monster_id, monster_db, level, level_curves)
            stance = int(stats.get("Stance", 5))

            monster_data = {
                "ID": monster_id,
                "HP": hp,
                "SPD": spd,
                "Stance": stance
            }

            hp_count = monster_info_db.get("HPCount", 0)
            if hp_count > 1:
                monster_data["HPCount"] = hp_count

            wave_monsters.append(monster_data)
        converted.append(wave_monsters)
    return converted


def convert_floor_data_v2(
    floor: Dict[str, Any],
    floor_num: int,
    monster_db: Dict[str, Any],
    level_curves: Dict[str, Any],
    elite_curves: Dict[str, Any],
    use_infinite: bool = False,
    version: str = "4.3.52"
) -> Dict[str, Any]:
    """
    转换单个楼层数据（v2：使用elitegroup的HPRatio替代手动floor_hp_ratio）
    """
    damage_type_map = {
        "Physical": "Phys", "Fire": "Fire", "Ice": "Ice",
        "Thunder": "Elec", "Wind": "Wind", "Quantum": "Quantum",
        "Imaginary": "Imaginary"
    }

    elem_upper = [damage_type_map.get(d, d) for d in floor.get("damage_type1", [])]
    elem_lower = [damage_type_map.get(d, d) for d in floor.get("damage_type2", [])]

    upper_event = floor.get("event_id_list1", [{}])[0]
    lower_event = floor.get("event_id_list2", [{}])[0]

    upper_level = upper_event.get("level", FLOOR_LEVEL_MAP.get(floor_num, 68))
    lower_level = lower_event.get("level", FLOOR_LEVEL_MAP.get(floor_num, 68))
    upper_elite_group = upper_event.get("elite_group", 0)
    lower_elite_group = lower_event.get("elite_group", 0)

    # v2: 从elitegroup数据获取HPRatio
    upper_elite = get_elite_group(elite_curves, upper_elite_group, use_infinite, version) if upper_elite_group else {"HPRatio": 1.0}
    lower_elite = get_elite_group(elite_curves, lower_elite_group, use_infinite, version) if lower_elite_group else {"HPRatio": 1.0}

    upper_hp_ratio = upper_elite.get("HPRatio", 1.0)
    lower_hp_ratio = lower_elite.get("HPRatio", 1.0)

    print(f"  第{floor_num}层 上: elite_group={upper_elite_group}, HPRatio={upper_hp_ratio}, 下: elite_group={lower_elite_group}, HPRatio={lower_hp_ratio}")

    upper_monsters = []
    if upper_event:
        upper_monsters.append({
            "_id": upper_event.get("stage_id", 0),
            "Level": upper_level,
            "HardLevelGroup": 3,
            "EliteGroup": {
                "ID": upper_elite_group,
                "HP": upper_hp_ratio
            },
            "Monsters": convert_monster_data(
                upper_event.get("monster_list", []),
                monster_db, upper_level, level_curves, upper_hp_ratio
            )
        })

    lower_monsters = []
    if lower_event:
        lower_monsters.append({
            "_id": lower_event.get("stage_id", 0),
            "Level": lower_level,
            "HardLevelGroup": 3,
            "EliteGroup": {
                "ID": lower_elite_group,
                "HP": lower_hp_ratio
            },
            "Monsters": convert_monster_data(
                lower_event.get("monster_list", []),
                monster_db, lower_level, level_curves, lower_hp_ratio
            )
        })

    return {
        "Floor": floor_num,
        "Elem": [elem_upper, elem_lower],
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


def generate_chaos_v2(maze_id: str, version: str = DEFAULT_VERSION) -> str:
    """
    v2版本：基于EliteGroup自动计算HP，无需手动输入hp_ratios
    """
    print(f"[Chaos V2] 开始处理混沌回忆 {maze_id}...")

    monster_db = load_local_monster_db()
    level_curves = load_level_curves()
    elite_curves = load_elite_curves()

    maze_data = download_maze_data(version, maze_id)
    if not maze_data:
        return "无法获取迷宫数据，退出"

    # 提取配置信息
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
        floors.append(convert_floor_data_v2(
            floor, floor_num, monster_db, level_curves, elite_curves,
            version=version
        ))

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

    generate_js_file(maze_id, converted_data)

    return f"混沌回忆 {maze_id} ({group_name}) 处理完成！\n共 {len(floors)} 层"


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