#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动下载并转换AR数据脚本
功能：从API下载AR（峰值/末日幻影）数据，转换并拼接到AR.js的_maze对象中
用法：python reliance/hsr_trans_ar.py <peak_id> [version]

示例：
    python reliance/hsr_trans_ar.py 2              # 转换烈阳幻域（peak_id=2）
    python reliance/hsr_trans_ar.py 2 4.3.52       # 指定版本
"""

import os
import sys
import json
import re
import requests
from typing import Dict, Any, List, Optional, Tuple

# 确保项目根目录在 sys.path 中，以便 import reliance.*
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reliance.sync_elite import (
    load_level_curves,
    load_elite_group_data,
    get_elite_group,
    LEVEL_CURVES_PATH,
)

BASE_URL = "https://static.nanoka.cc/hsr"
LANGUAGE = "zh"
OUTPUT_DIR = "./tempdata"
DEFAULT_VERSION = "4.3.52"

ELEMENT_MAP = {
    "Physical": "Phys",
    "Fire": "Fire",
    "Ice": "Ice",
    "Thunder": "Elec",
    "Wind": "Wind",
    "Quantum": "Quantum",
    "Imaginary": "Imaginary"
}

os.makedirs(OUTPUT_DIR, exist_ok=True)


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


def download_peak_data(peak_id: str, version: str) -> Optional[Dict[str, Any]]:
    """下载AR峰值数据"""
    local_file = os.path.join(OUTPUT_DIR, f"peak_{peak_id}_{version}.json")

    if os.path.exists(local_file):
        try:
            with open(local_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass

    url = f"{BASE_URL}/{version}/{LANGUAGE}/peak/{peak_id}.json"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        try:
            with open(local_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        return data
    except Exception as e:
        print(f"下载AR数据 peak/{peak_id} 失败: {e}")
        return None


def download_monster_data(monster_id: int, version: str) -> Optional[Dict[str, Any]]:
    """下载单个怪物数据"""
    mid_str = str(monster_id)
    local_file = os.path.join(OUTPUT_DIR, f"monster_{mid_str}_{version}.json")

    if os.path.exists(local_file):
        try:
            with open(local_file, 'r', encoding='utf-8') as f:
                return json.load(f)
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
        return data
    except Exception:
        return None


def get_monster_child(monster_data: Dict[str, Any], target_id: int) -> Optional[Dict[str, Any]]:
    """从怪物数据中找到匹配的子条目"""
    children = monster_data.get("child", [])
    for child in children:
        if child.get("id") == target_id:
            return child
    return children[0] if children else None


def load_monster_base_stats() -> Dict[str, Dict[str, float]]:
    """从Monster.js加载怪物基础属性（作为API不可用时的fallback，含嵌套Child变体）"""
    import re

    result = {}

    js_path = "./sr/data/CH/Monster.js"
    with open(js_path, 'r', encoding='utf-8') as f:
        content = f.read()

    start = content.find('var _monster = {')
    end = content.find('var _monsterlist = [')
    if start == -1 or end == -1:
        return result

    js_obj = content[start + len('var _monster = '):end].strip()
    js_obj = js_obj.rstrip(';').strip()
    js_obj = re.sub(r',\s*}', '}', js_obj)
    js_obj = re.sub(r',\s*]', ']', js_obj)

    monster_data = json.loads(js_obj)

    for mid, mdata in monster_data.items():
        stats = mdata.get("Stats", {})
        if stats:
            result[mid] = {
                "HP": stats.get("HP", 0),
                "SPD": stats.get("SPD", 0),
                "Stance": stats.get("Stance", 0),
                "HPCount": mdata.get("HPCount", 1.0),
                "Multistage": mdata.get("Multistage", 1)
            }
        # 展开Child变体，Stats已是最终值，直接使用
        if isinstance(mdata, dict) and "Child" in mdata:
            for child_id, child_data in mdata["Child"].items():
                child_stats = child_data.get("Stats", {})
                if child_stats:
                    result[child_id] = {
                        "HP": child_stats.get("HP", 0),
                        "SPD": child_stats.get("SPD", 0),
                        "Stance": child_stats.get("Stance", 0),
                        "HPCount": mdata.get("HPCount", 1.0),
                        "Multistage": mdata.get("Multistage", 1)
                    }
    return result


# 缓存怪物基础数据
_monster_base_cache = None


def get_monster_base_stats() -> Dict[str, Dict[str, float]]:
    global _monster_base_cache
    if _monster_base_cache is None:
        _monster_base_cache = load_monster_base_stats()
    return _monster_base_cache


def calc_monster_stats(monster_id: int, level: int, hard_level_group: int,
                       elite_group_id: int, curves: Dict[str, Any],
                       version: str, use_infinite: bool = False) -> Optional[Dict[str, Any]]:
    """
    计算怪物在指定等级下的HP/SPD/Stance
    HP存储单阶段值，HPCount存储阶段数供前端显示×N标签
    SPD = round(base_spd × curve_spd + speed_modify_value)

    回退优先级：
    1. Monster.js本地数据
    2. API精确匹配
    3. API父级ID回退
    """
    base_hp = None
    base_spd = None
    base_stance = None
    hp_count = 1
    stance_count = 1
    spd_mod_val = 0
    stance_mod_val = 0

    # 优先级1: 本地Monster.js
    base_stats = get_monster_base_stats()
    key = str(monster_id)
    if key in base_stats:
        bs = base_stats[key]
        base_hp = bs["HP"]
        base_spd = bs["SPD"]
        base_stance = bs["Stance"]
        hp_count = bs.get("Multistage", 1)

    # 优先级2: API精确匹配（9位ID无直接API端点，跳过）
    if base_hp is None and len(str(monster_id)) != 9:
        monster_data = download_monster_data(monster_id, version)
        if monster_data:
            child = get_monster_child(monster_data, monster_id)
            if child:
                hp_base = monster_data.get("hp_base", 0) or 0
                speed_base = monster_data.get("speed_base", 0) or 0
                stance_base = monster_data.get("stance_base", 0) or 0

                hp_mod = child.get("hp_modify_ratio", 1) or 1
                spd_mod = child.get("speed_modify_ratio", 1) or 1
                stance_mod = child.get("stance_modify_ratio", 1) or 1
                spd_mod_val = child.get("speed_modify_value") or 0
                stance_mod_val = child.get("stance_modify_value") or 0

                base_hp = (hp_base / 93.0) * hp_mod
                base_spd = speed_base * spd_mod
                base_stance = (stance_base / 30.0) * stance_mod
                hp_count = monster_data.get("max_monster_phase", 1) or 1
                stance_count = monster_data.get("stance_count", 1) or 1

    # 优先级3: API父级ID回退（9位ID父级是前7位，跳过不必要的trim）
    if base_hp is None:
        str_id = str(monster_id)
        if len(str_id) == 9:
            trim_lengths = [2]  # 9位ID直接取前7位
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
                        spd_mod_val = child.get("speed_modify_value") or 0
                        stance_mod_val = child.get("stance_modify_value") or 0

                        base_hp = (hp_base / 93.0) * hp_mod
                        base_spd = speed_base * spd_mod
                        base_stance = (stance_base / 30.0) * stance_mod
                        hp_count = parent_data.get("max_monster_phase", 1) or 1
                        stance_count = parent_data.get("stance_count", 1) or 1
                        break

    if base_hp is None:
        print(f"警告：无法获取怪物 {monster_id} 的数据（本地和API中均未找到）")
        return {"ID": monster_id, "HP": 0, "SPD": 0, "Stance": 0, "HPCount": 1, "StanceCount": 1}

    curve = get_level_curve(curves, hard_level_group, level)
    elite = get_elite_group(curves, elite_group_id, use_infinite, version)

    curve_hp = curve.get("HP", 1)
    curve_spd = curve.get("SPD", 1)
    curve_stance = curve.get("Stance", 1)
    hpratio = elite.get("HPRatio", 1)

    hp = round(base_hp * curve_hp * hpratio)
    spd = round(base_spd * curve_spd + spd_mod_val)
    stance = round(base_stance * curve_stance)

    return {
        "ID": monster_id,
        "HP": hp,
        "SPD": spd,
        "Stance": stance,
        "HPCount": hp_count,
        "StanceCount": stance_count
    }


def convert_tag_to_buff(tag: Dict[str, Any]) -> Dict[str, Any]:
    """将API的tag格式转换为AR.js的Buff格式"""
    desc = tag.get("desc") or ""
    params = tag.get("param") or []

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

    return {
        "_id": tag.get("id", 0),
        "Name": tag.get("name") or "",
        "Desc": desc
    }


def convert_trial_stage(api_event: Dict[str, Any], infinite_list: Dict[str, Any],
                        curves: Dict[str, Any], version: str) -> Optional[Dict[str, Any]]:
    """
    转换试炼关卡数据

    优先使用 infinite_list 中每项的 monster_group_id_list（每项=一波）。
    infinite_list 为空时才回退到 monster_list。
    """
    level = api_event.get("level", 95)
    hard_level_group = api_event.get("hard_level_group", 3)

    # 按 infinite_wave_id 排序，确保波次顺序正确
    inf_entries = sorted(infinite_list.values(), key=lambda x: x.get("infinite_wave_id", 0)) \
        if infinite_list else []

    all_waves = []

    if inf_entries:
        # 使用 infinite_list 的 monster_group_id_list（每个条目 = 一波）
        stage_elite_group_id = 0
        for idx, inf in enumerate(inf_entries):
            inf_monsters = inf.get("monster_group_id_list", [])
            wave_elite_group_id = inf.get("elite_group", 0)
            wave_monsters = []

            if idx == 0:
                stage_elite_group_id = wave_elite_group_id

            for mid in inf_monsters:
                if isinstance(mid, int) and mid > 0:
                    stats = calc_monster_stats(mid, level, hard_level_group,
                                               wave_elite_group_id, curves, version,
                                               use_infinite=True)
                    wave_monsters.append(stats)
            if wave_monsters:
                all_waves.append(wave_monsters)
    else:
        # 回退：无 infinite_list 时使用 monster_list
        monster_list = api_event.get("monster_list", [])
        if not monster_list:
            return None
        stage_elite_group_id = 0
        for wave in monster_list:
            wave_monsters = []
            for key in sorted(wave.keys()):
                mid = wave[key]
                if isinstance(mid, int) and mid > 0:
                    stats = calc_monster_stats(mid, level, hard_level_group,
                                               0, curves, version)
                    wave_monsters.append(stats)
            if wave_monsters:
                all_waves.append(wave_monsters)

    if not all_waves:
        return None

    for wave in all_waves:
        for mon in wave:
            mon.pop("HPCount", None)

    elite = get_elite_group(curves, stage_elite_group_id, use_infinite=(len(inf_entries) > 0), version=version)

    result = {
        "_id": api_event.get("stage_id", 0),
        "Level": level,
        "HardLevelGroup": hard_level_group,
        "EliteGroup": {
            "ID": stage_elite_group_id,
            "ATK": elite.get("AttackRatio", 1.1),
            "HP": elite.get("HPRatio", 1)
        },
        "Monsters": all_waves
    }

    return result


def convert_peak_to_maze(peak_id: str, peak_data: Dict[str, Any],
                         version: str) -> Optional[Dict[str, Any]]:
    """将峰值API数据转换为_maze格式"""
    curves = load_level_curves()

    maze_id = f"4{str(peak_id).zfill(3)}"

    pre_levels = peak_data.get("pre_level", [])
    boss_level = peak_data.get("boss_level", {})
    boss_config = peak_data.get("boss_config", {})

    if len(pre_levels) < 3:
        print(f"错误：pre_level 不足3个，实际 {len(pre_levels)} 个")
        return None

    result = {}

    # 处理 pre_level[0] -> BuffA, ElemA, TrialA
    pl0 = pre_levels[0]
    result["BuffA"] = [convert_tag_to_buff(t) for t in pl0.get("tag_list", [])]
    result["ElemA"] = [ELEMENT_MAP.get(e, e) for e in pl0.get("damage_type", [])]
    if pl0.get("event_id_list"):
        result["TrialA"] = convert_trial_stage(
            pl0["event_id_list"][0], pl0.get("infinite_list", {}), curves, version
        )

    # 处理 pre_level[1] -> BuffB, ElemB, TrialB
    pl1 = pre_levels[1]
    result["BuffB"] = [convert_tag_to_buff(t) for t in pl1.get("tag_list", [])]
    result["ElemB"] = [ELEMENT_MAP.get(e, e) for e in pl1.get("damage_type", [])]
    if pl1.get("event_id_list"):
        result["TrialB"] = convert_trial_stage(
            pl1["event_id_list"][0], pl1.get("infinite_list", {}), curves, version
        )

    # 处理 pre_level[2] -> BuffC, ElemC, TrialC
    pl2 = pre_levels[2]
    result["BuffC"] = [convert_tag_to_buff(t) for t in pl2.get("tag_list", [])]
    result["ElemC"] = [ELEMENT_MAP.get(e, e) for e in pl2.get("damage_type", [])]
    if pl2.get("event_id_list"):
        result["TrialC"] = convert_trial_stage(
            pl2["event_id_list"][0], pl2.get("infinite_list", {}), curves, version
        )

    # 处理 boss_config -> FinalBuffs, FinalTagsHard, FinalHard
    result["FinalBuffs"] = [convert_tag_to_buff(t) for t in boss_config.get("buff_list", [])]
    result["FinalTagsHard"] = [convert_tag_to_buff(t) for t in boss_config.get("tag_list", [])]
    if boss_config.get("event_id_list"):
        result["FinalHard"] = convert_trial_stage(
            boss_config["event_id_list"][0], boss_config.get("infinite_list", {}), curves, version
        )

    # 处理 boss_level -> FinalTagsEasy, FinalEasy, ElemFinal
    result["FinalTagsEasy"] = [convert_tag_to_buff(t) for t in boss_level.get("tag_list", [])]
    if boss_level.get("event_id_list"):
        result["FinalEasy"] = convert_trial_stage(
            boss_level["event_id_list"][0], boss_level.get("infinite_list", {}), curves, version
        )
    result["ElemFinal"] = [ELEMENT_MAP.get(e, e) for e in boss_level.get("damage_type", [])]

    # 固定字段：所有AR条目共用
    result["TargetsTrial"] = [
        "不超过4轮战斗胜利",
        "不超过2轮战斗胜利",
        "没有角色无法战斗"
    ]
    result["TargetsFinal"] = [
        "不超过6轮战斗胜利",
        "不超过4轮战斗胜利",
        "不超过2轮战斗胜利"
    ]
    result["RewardLine"] = 1

    return {maze_id: result}


def format_maze_entry(maze_id: str, maze_data: Dict[str, Any]) -> str:
    """将maze_data格式化为可插入AR.js的JS代码字符串"""
    raw = json.dumps(maze_data, ensure_ascii=False, indent=4)
    lines = raw.split('\n')
    indented = '\n'.join('    ' + line for line in lines)
    return f'    "{maze_id}": {indented},\n'


def merge_maze_to_ar_js(maze_id: str, maze_data: Dict[str, Any], name: str = "") -> str:
    """将_maze条目和_schedule条目拼接到AR.js最前面"""
    ar_js_path = "./sr/data/CH/AR.js"

    with open(ar_js_path, 'r', encoding='utf-8') as f:
        content = f.read()

    if f'"{maze_id}":' in content:
        return f"AR条目 {maze_id} 已存在，无需拼接"

    # 1. 在 var _maze = { 之后插入 maze 数据
    marker_maze = 'var _maze = {'
    idx_maze = content.index(marker_maze)
    insert_maze = idx_maze + len(marker_maze)
    entry_maze = format_maze_entry(maze_id, maze_data)
    content = content[:insert_maze] + '\n' + entry_maze + content[insert_maze:]

    # 2. 在 var _schedule = [ 之后插入 schedule 条目
    marker_sched = 'var _schedule = ['
    idx_sched = content.index(marker_sched)
    insert_sched = idx_sched + len(marker_sched)

    clean_name = re.sub(r'<[^>]*>', '', name).strip()
    sched_entry = f'\n    {{\n        "_id": {maze_id},\n        "Name": "{clean_name}",\n        "Time": ""\n    }},'
    content = content[:insert_sched] + sched_entry + content[insert_sched:]

    with open(ar_js_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return f"已自动拼接AR {maze_id}（{clean_name}）到 AR.js"


def generate_ar_data(peak_id: str, version: str = None) -> str:
    """
    生成AR数据的主入口

    Args:
        peak_id: 峰值ID（如 "2" 对应烈阳幻域，maze_id=4002）
        version: 版本号（如 "4.3.52"），默认使用最新版本
    """
    if version is None:
        version = DEFAULT_VERSION

    peak_data = download_peak_data(peak_id, version)
    if not peak_data:
        return f"下载AR数据 peak/{peak_id} 失败"

    maze_entry = convert_peak_to_maze(peak_id, peak_data, version)
    if not maze_entry:
        return f"转换AR数据 peak/{peak_id} 失败"

    maze_id = list(maze_entry.keys())[0]
    maze_data = maze_entry[maze_id]

    # 保存到tempdata
    output_file = os.path.join(OUTPUT_DIR, f"ar_{maze_id}.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(maze_entry, f, ensure_ascii=False, indent=2)

    # 自动拼接到AR.js
    name = peak_data.get("name", "") or ""
    merge_msg = merge_maze_to_ar_js(maze_id, maze_data, name)
    result = f"AR {maze_id}（{name}）数据已生成 -> {output_file}"
    if merge_msg:
        result += "\n" + merge_msg
    return result


def main():
    if len(sys.argv) < 2:
        print("用法: python reliance/hsr_trans_ar.py <peak_id> [version]")
        print("示例: python reliance/hsr_trans_ar.py 2")
        print("      python reliance/hsr_trans_ar.py 2 4.3.52")
        sys.exit(1)

    peak_id = sys.argv[1]
    version = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_VERSION
    result = generate_ar_data(peak_id, version)
    print(result)


if __name__ == "__main__":
    main()