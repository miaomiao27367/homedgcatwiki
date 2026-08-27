#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
虚构叙事处理 v2 — 基于EliteGroup自动计算怪物HP，无需手动HP补偿
在hsr_trans_fiction.py基础上改进，使用elitegroup数据替代hp_add_values手动输入

用法：python reliance/hsr_fiction_v2.py <story_id> [version]
示例：
    python reliance/hsr_fiction_v2.py 101
    python reliance/hsr_fiction_v2.py 101 4.3.52
"""

import os
import sys
import json
import requests
from typing import Dict, Any, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reliance.sync_elite import (
    load_level_curves as load_elite_curves,
    load_elite_group_data,
    get_elite_group,
    LEVEL_CURVES_PATH,
)

BASE_URL = "https://static.nanoka.cc/hsr"
LANGUAGE = "zh"
OUTPUT_DIR = "./tempdata"
DEFAULT_VERSION = "4.3.52"

MONSTER_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sr", "data", "CH", "Monster.js")
MONSTER_1_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tempdata", "Monster_1.json")
MONSTER_2_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tempdata", "Monster_2.json")

os.makedirs(OUTPUT_DIR, exist_ok=True)


def remove_trailing_commas(json_str: str) -> str:
    import re
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)
    return json_str


def load_local_monster_db() -> Dict[str, Any]:
    monster_db = {}
    if not os.path.exists(MONSTER_PATH):
        print(f"警告: 找不到 {MONSTER_PATH}")
        return monster_db

    with open(MONSTER_PATH, 'r', encoding='utf-8') as f:
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


def download_story_data(version: str, story_id: str) -> Dict[str, Any]:
    url = f"{BASE_URL}/{version}/{LANGUAGE}/story/{story_id}.json"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"下载数据失败: {e}")
        return {}


def get_monster_hp_multiplier(monster_db: Dict[str, Any], monster_id: str) -> tuple:
    monster_info = monster_db.get(monster_id)
    if monster_info and "Stats" in monster_info:
        hp = monster_info["Stats"].get("HP", 1.0)
        return (hp, True, monster_id)

    if len(monster_id) == 9 and monster_id.isdigit():
        base_id = monster_id[:-3]
        monster_info = monster_db.get(base_id)
        if monster_info and "Stats" in monster_info:
            hp = monster_info["Stats"].get("HP", 1.0)
            return (hp, True, base_id)
        return (0, False, base_id)

    return (1.0, False, "")


def get_monster_spd(monster_db: Dict[str, Any], monster_id: str) -> int:
    monster_info = monster_db.get(monster_id)
    if monster_info and "Stats" in monster_info:
        return int(monster_info["Stats"].get("SPD", 100))
    return 100


def get_monster_stance(monster_db: Dict[str, Any], monster_id: str) -> int:
    monster_info = monster_db.get(monster_id)
    if monster_info and "Stats" in monster_info:
        return int(monster_info["Stats"].get("Stance", 5))
    return 5


def parse_infinite_list_v2(infinite_list: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    解析infinite_list中的怪物数据（v2：同时提取elite_group）
    返回: 每波的怪物数据列表，包含monster_list和elite_group
    """
    waves = []
    wave_ids = sorted(infinite_list.keys())

    for wave_id in wave_ids:
        wave_data = infinite_list[wave_id]
        monster_list = wave_data.get("monster_group_id_list", [])

        unique_monsters = []
        seen = set()
        for monster_id in monster_list:
            if monster_id not in seen:
                seen.add(monster_id)
                unique_monsters.append(str(monster_id))

        if len(unique_monsters) == 4 and wave_id.endswith('1'):
            unique_monsters = unique_monsters[1:]

        # v2: 提取elite_group用于自动计算HP倍率
        elite_group = wave_data.get("elite_group", 0)

        waves.append({
            "monster_list": unique_monsters,
            "elite_group": elite_group
        })

    return waves


def convert_monster_data_v2(
    monster_waves: List[Dict[str, Any]],
    monster_db: Dict[str, Any],
    level_curves: Dict[str, Any],
    elite_curves: Dict[str, Any],
    level: int,
    use_infinite: bool = True,
    version: str = "4.3.52"
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    转换怪物数据（v2：使用elitegroup的HPRatio替代手动hp_add_values）
    """
    waves = []
    not_found_9digit_ids = []

    for wave_idx, wave_data in enumerate(monster_waves):
        monster_list = wave_data.get("monster_list", [])
        elite_group_id = wave_data.get("elite_group", 0)

        # v2: 从elitegroup获取HPRatio作为HP倍率
        hp_ratio = 1.0
        if elite_group_id:
            elite = get_elite_group(elite_curves, elite_group_id, use_infinite, version)
            hp_ratio = elite.get("HPRatio", 1.0)

        wave_monsters = []
        for idx, monster_id in enumerate(monster_list):
            num = 12 if idx == 0 else (11 if idx == 1 else 2)
            if len(monster_list) == 1:
                num = 1

            hp_multiplier, found, base_id = get_monster_hp_multiplier(monster_db, monster_id)
            if not found and len(monster_id) == 9:
                not_found_9digit_ids.append(monster_id)

            # v2: HP = 基础HP × elitegroup的HPRatio
            hp = hp_multiplier * hp_ratio

            spd = get_monster_spd(monster_db, monster_id)
            stance = get_monster_stance(monster_db, monster_id)

            wave_monsters.append({
                "ID": int(monster_id),
                "Num": num,
                "HP": hp,
                "SPD": spd,
                "Stance": stance
            })

        waves.append({"Monsters": wave_monsters})

    return waves, not_found_9digit_ids


def generate_fiction_v2(story_id: str, version: str = DEFAULT_VERSION) -> Tuple[str, List[str], Dict[str, Any]]:
    """
    生成虚构叙事数据（v2：基于EliteGroup自动计算HP）
    """
    print(f"[Fiction V2] 开始处理虚构叙事 {story_id}...")

    monster_db = load_local_monster_db()
    level_curves = load_elite_curves()

    story_data = download_story_data(version, story_id)
    if not story_data:
        return "无法获取虚构叙事数据，退出", [], {}

    group_name = story_data.get("name", "未知")
    levels = story_data.get("level", [])

    floors = []
    all_not_found_ids = []

    damage_type_map = {
        "Physical": "Phys", "Fire": "Fire", "Ice": "Ice",
        "Thunder": "Elec", "Wind": "Wind", "Quantum": "Quantum",
        "Imaginary": "Imaginary"
    }

    for i in range(min(4, len(levels))):
        if i >= len(levels):
            break
        floor = levels[i]
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
            upper_stage_id = upper_event.get("stage_id", floor_num * 100 + 1)
            upper_monster_waves = parse_infinite_list_v2(infinite_list1)
            upper_waves, not_found = convert_monster_data_v2(
                upper_monster_waves, monster_db, level_curves, level_curves, upper_level,
                version=version
            )
            all_not_found_ids.extend(not_found)
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
            lower_stage_id = lower_event.get("stage_id", floor_num * 100 + 2)
            lower_monster_waves = parse_infinite_list_v2(infinite_list2)
            lower_waves, not_found = convert_monster_data_v2(
                lower_monster_waves, monster_db, level_curves, level_curves, lower_level,
                version=version
            )
            all_not_found_ids.extend(not_found)
            if lower_waves:
                lower_monsters.append({
                    "_id": lower_stage_id,
                    "Level": lower_level,
                    "Waves": lower_waves
                })

        floors.append({
            "Floor": floor_num,
            "Elem": [elem_upper, elem_lower],
            "Upper": upper_monsters,
            "Lower": lower_monsters
        })

    converted_data = {
        "StoryID": story_id,
        "Name": group_name,
        "Floors": floors
    }

    # 输出到tempdata
    file_path = os.path.join(OUTPUT_DIR, f"fiction_{story_id}.json")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(converted_data, f, ensure_ascii=False, indent=2)

    result_msg = f"虚构叙事 {story_id} ({group_name}) 处理完成！\n"
    result_msg += f"楼层数: {len(floors)}\n"
    result_msg += f"输出文件: {file_path}\n"

    if all_not_found_ids:
        result_msg += f"\n未找到的怪物ID: {len(set(all_not_found_ids))}个"

    return result_msg, all_not_found_ids, converted_data


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

    result, not_found_ids, converted_data = generate_fiction_v2(story_id, version)
    print(result)

    if not_found_ids:
        print("\n" + "=" * 60)
        print("未能在Monster_1/2.json中找到的9位ID列表:")
        print("=" * 60)
        for monster_id in sorted(set(not_found_ids)):
            base_id = monster_id[:-3]
            print(f"  {monster_id} (原始: {base_id})")


if __name__ == "__main__":
    main()