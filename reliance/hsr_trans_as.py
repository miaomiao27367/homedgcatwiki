#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动下载并转换AS数据脚本
功能：从API下载AS（末日幻影/Boss）数据，转换并拼接到AS.js的_chaos数组中
用法：python reliance/hsr_trans_as.py <boss_id> [version] [-f <local_file>]

示例：
    python reliance/hsr_trans_as.py 3018              # 转换遗忘冽风（boss_id=3018）
    python reliance/hsr_trans_as.py 3018 4.3.52       # 指定版本
    python reliance/hsr_trans_as.py 3018 -f 3018.json # 使用本地JSON文件
"""

import os
import sys
import json
import re
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional, Tuple

# 确保项目根目录在 sys.path 中，以便 import reliance.*
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reliance.sync_elite import load_level_curves, get_elite_group

BASE_URL = "https://static.nanoka.cc/hsr"
LANGUAGE = "zh"
OUTPUT_DIR = "./tempdata"
DEFAULT_VERSION = "4.3.52"

# True: 仅导出原始数据到 tempdata/，不拼接 JS。False: 正常拼接
testmod = False
#testmod = True

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
    """获取等级曲线数据（曲线索引 = 游戏等级 - 1）"""
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


def download_boss_data(boss_id: str, version: str) -> Optional[Dict[str, Any]]:
    """下载AS Boss数据"""
    local_file = os.path.join(OUTPUT_DIR, f"boss_{boss_id}_{version}.json")

    if os.path.exists(local_file):
        try:
            with open(local_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass

    url = f"{BASE_URL}/{version}/{LANGUAGE}/boss/{boss_id}.json"
    try:
        print(f"正在下载: {url}")
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        try:
            with open(local_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"已缓存到: {local_file}")
        except Exception:
            pass
        return data
    except Exception as e:
        print(f"下载Boss数据 boss/{boss_id} 失败: {e}")
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


def _is_monster_cached(monster_id: int, version: str) -> bool:
    mid_str = str(monster_id)
    local_file = os.path.join(OUTPUT_DIR, f"monster_{mid_str}_{version}.json")
    return os.path.exists(local_file)


def _collect_monster_ids_from_boss(boss_data: Dict[str, Any]) -> set:
    """从boss数据中收集所有怪物ID（含星启层）"""
    ids: set = set()
    for lv in boss_data.get("level", []):
        for field in ("event_id_list1", "event_id_list2", "event_id_list"):
            for evt in lv.get(field, []):
                for wave in evt.get("monster_list", []):
                    for v in wave.values():
                        if isinstance(v, int) and v > 0:
                            ids.add(v)
    return ids


def _collect_parent_ids(monster_ids: set) -> set:
    """为回退逻辑预收集父级ID（trim 1/2/3位）"""
    parents: set = set()
    for mid in monster_ids:
        s = str(mid)
        for trim_len in [1, 2, 3]:
            if len(s) > trim_len:
                parents.add(int(s[:-trim_len]))
    return parents


def prefetch_all_monsters(boss_data: Dict[str, Any], version: str,
                          max_workers: int = 8) -> None:
    """并行预下载所有怪物数据，大幅加速首次运行"""
    monster_ids = _collect_monster_ids_from_boss(boss_data)
    parent_ids = _collect_parent_ids(monster_ids)
    all_ids = monster_ids | parent_ids

    uncached = [mid for mid in all_ids if not _is_monster_cached(mid, version)]
    if not uncached:
        return

    print(f"并行预下载 {len(uncached)} 个怪物数据...")
    results = []

    def _download_one(mid):
        return download_monster_data(mid, version)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_download_one, mid): mid for mid in uncached}
        for future in as_completed(futures):
            mid = futures[future]
            try:
                data = future.result()
                results.append((mid, data is not None))
            except Exception:
                results.append((mid, False))

    ok = sum(1 for _, r in results if r)
    fail = len(results) - ok
    if fail:
        print(f"  {ok} 成功, {fail} 失败")
    else:
        print(f"  全部 {ok} 个下载完成")


def get_monster_child(monster_data: Dict[str, Any], target_id: int) -> Optional[Dict[str, Any]]:
    """从怪物数据中找到匹配的子条目"""
    children = monster_data.get("child", [])
    for child in children:
        if child.get("id") == target_id:
            return child
    return children[0] if children else None


def load_monster_base_stats() -> Dict[str, Dict[str, float]]:
    """从Monster.js加载怪物基础属性（含嵌套Child变体）"""
    result = {}

    js_path = "./sr/data/CH/Monster.js"
    if not os.path.exists(js_path):
        return result

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

    try:
        monster_data = json.loads(js_obj)
    except json.JSONDecodeError:
        return result

    for mid, mdata in monster_data.items():
        stats = mdata.get("Stats", {})
        if stats:
            result[mid] = {
                "HP": stats.get("HP", 0),
                "SPD": stats.get("SPD", 0),
                "Stance": stats.get("Stance", 0)
            }
        # 展开Child变体，Stats是倍率，需要乘本体值
        if isinstance(mdata, dict) and "Child" in mdata and stats:
            for child_id, child_data in mdata["Child"].items():
                child_stats = child_data.get("Stats", {})
                if child_stats:
                    result[child_id] = {
                        "HP": stats.get("HP", 0) * child_stats.get("HP", 1),
                        "SPD": stats.get("SPD", 0) * child_stats.get("SPD", 1),
                        "Stance": stats.get("Stance", 0) * child_stats.get("Stance", 1),
                    }
    return result


_monster_base_cache = None


def get_monster_base_stats() -> Dict[str, Dict[str, float]]:
    global _monster_base_cache
    if _monster_base_cache is None:
        _monster_base_cache = load_monster_base_stats()
    return _monster_base_cache


def get_hp_count(monster_data: Dict[str, Any]) -> float:
    """从怪物数据中获取HPCount累加所有阶段"""
    phase_list = monster_data.get("phase_list", [])
    if phase_list:
        return sum(p.get("phase_max_hp_ratio", 1.0) for p in phase_list)  # 累加所有阶段
    return monster_data.get("max_monster_phase", 1) or 1


def calc_monster_stats(monster_id: int, level: int, hard_level_group: int,
                       elite_group_id: int, curves: Dict[str, Any],
                       version: str) -> Optional[Dict[str, Any]]:
    """
    计算怪物在指定等级下的HP/SPD/Stance

    回退优先级：
    1. API精确匹配
    2. Monster_2.js / Monster_1.js 变体/基础数据
    3. API父级ID回退
    """
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
    else:
        # 回退: Monster_1.js / Monster_2.js
        base_stats = get_monster_base_stats()
        key = str(monster_id)
        if key in base_stats:
            bs = base_stats[key]
            base_hp = bs["HP"]
            base_spd = bs["SPD"]
            base_stance = bs["Stance"]
            # 尝试从父级API获取phase_max_hp_ratio
            hp_count = 1
            str_mid = str(monster_id)
            for trim_len in [1, 2, 3]:
                if len(str_mid) > trim_len:
                    parent_id = int(str_mid[:-trim_len])
                    parent_data = download_monster_data(parent_id, version)
                    if parent_data:
                        hp_count = get_hp_count(parent_data)
                        break
        else:
            # 回退: API父级ID回退
            str_id = str(monster_id)
            found_parent = False
            for trim_len in [1, 2, 3]:
                if len(str_id) > trim_len:
                    parent_id = int(str_id[:-trim_len])
                    parent_data = download_monster_data(parent_id, version)
                    if parent_data:
                        child = get_monster_child(parent_data, parent_id)
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
                print(f"警告：无法获取怪物 {monster_id} 的数据（API和Monster_1/2.js中均未找到）")
                return {"ID": monster_id, "HP": 0, "SPD": 0, "Stance": 0}

    curve = get_level_curve(curves, hard_level_group, level)
    elite = get_elite_group(curves, elite_group_id)

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


def convert_tag_to_buff(tag: Dict[str, Any]) -> Dict[str, Any]:
    """将API的tag格式转换为AS.js的Buff格式"""
    desc = tag.get("desc", "")
    params = tag.get("param", [])

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
        "Name": tag.get("name", ""),
        "Desc": desc
    }


def convert_stage(api_event: Dict[str, Any],
                  curves: Dict[str, Any], version: str) -> Optional[Dict[str, Any]]:
    """
    转换AS关卡数据（Upper或Lower）

    API的event结构直接包含elite_group、monster_list等字段，
    无需从外部传入infinite_list或elite_group_override
    """
    monster_list = api_event.get("monster_list", [])
    if not monster_list:
        return None

    level = api_event.get("level", 95)
    hard_level_group = api_event.get("hard_level_group", 3)
    elite_group_id = api_event.get("elite_group", 0)

    eg = curves["elitegroup"]
    eg_str = str(elite_group_id)
    elite = eg.get(eg_str, {"HPRatio": 1, "AttackRatio": 1.1})

    all_waves = []
    for wave in monster_list:
        wave_monsters = []
        for key in sorted(wave.keys()):
            mid = wave[key]
            if isinstance(mid, int) and mid > 0:
                stats = calc_monster_stats(mid, level, hard_level_group,
                                           elite_group_id, curves, version)
                wave_monsters.append(stats)
        if wave_monsters:
            all_waves.append(wave_monsters)

    if not all_waves:
        return None

    result = {
        "_id": api_event.get("stage_id", 0),
        "Level": level,
        "EliteGroup": {
            "ID": elite_group_id,
            "ATK": elite.get("AttackRatio", 1.1),
            "HP": elite.get("HPRatio", 1)
        },
        "Monsters": all_waves
    }

    return result


def convert_boss_to_chaos(boss_id: str, boss_data: Dict[str, Any],
                          version: str) -> Optional[Dict[str, Any]]:
    """将Boss API数据转换为_chaos条目格式"""
    curves = load_level_curves()

    chaos_id = int(boss_id)
    name = boss_data.get("name", "")

    level_list = boss_data.get("level", [])
    if not level_list:
        print("错误：未找到level数据")
        return None

    floors = []
    for idx, level_data in enumerate(level_list):
        floor_num = idx + 1

        upper_dmg = [ELEMENT_MAP.get(e, e) for e in level_data.get("damage_type1", [])]
        lower_dmg = [ELEMENT_MAP.get(e, e) for e in level_data.get("damage_type2", [])]

        upper_events = level_data.get("event_id_list1", [])
        lower_events = level_data.get("event_id_list2", [])

        upper_stages = []
        for evt in upper_events:
            stage = convert_stage(evt, curves, version)
            if stage:
                upper_stages.append(stage)

        lower_stages = []
        for evt in lower_events:
            stage = convert_stage(evt, curves, version)
            if stage:
                lower_stages.append(stage)

        hpas = 0
        for stage in upper_stages + lower_stages:
            for wave in stage.get("Monsters", []):
                for mon in wave:
                    hp = mon.get("HP", 0)
                    count = mon.get("HPCount", 1)
                    hpas += hp * count

        floor_entry = {
            "Floor": floor_num,
            "ElemUpper": upper_dmg,
            "ElemLower": lower_dmg,
            "HPAS": hpas,
            "Upper": upper_stages,
            "Lower": lower_stages
        }
        if not upper_stages and not lower_stages:
            continue
        floors.append(floor_entry)

    buff = None
    api_buff = boss_data.get("buff", {})
    if api_buff:
        desc = api_buff.get("desc", "")
        desc = desc.replace("<color=#f29e38ff>", "<color style='color:#f29e38;'>")
        desc = desc.replace("<unbreak>", "").replace("</unbreak>", "")

        params = api_buff.get("param", [])
        for i, p in enumerate(params):
            idx = i + 1
            m = re.search(r'#' + str(idx) + r'\[([^\]]*)\](%?)', desc)
            if m:
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
                        display = f"{val:.{decimals}f}"
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

        buff_id = api_buff.get("id", 0)
        if buff_id == 0 and level_list:
            first_upper_events = level_list[0].get("event_id_list1", [])
            if first_upper_events:
                for cfg in first_upper_events[0].get("stage_config_data", []):
                    if cfg.get("jdkamoanicm") == "_BindingMazeBuff":
                        buff_id = int(cfg.get("mojjbfbkbnc", 0))
                        break

        buff = {
            "_id": buff_id,
            "Name": api_buff.get("name", ""),
            "Desc": desc
        }

    ub = [convert_tag_to_buff(t) for t in boss_data.get("buff_list1", [])]
    lb = [convert_tag_to_buff(t) for t in boss_data.get("buff_list2", [])]

    # UC/LC/UG/LG 从最高楼层（非星启层）的 boss_monster_config 提取
    uc, lc, ug, lg = [], [], [], []
    if level_list:
        # 找最后一个有 boss_monster_config1 的楼层（跳过星启层）
        highest = None
        for lv in reversed(level_list):
            if lv.get("boss_monster_config1"):
                highest = lv
                break
        if highest:
            bmc1 = highest.get("boss_monster_config1", {})
            bmc2 = highest.get("boss_monster_config2", {})

            uc = [convert_tag_to_buff(t) for t in bmc1.get("tag_list", [])]
            lc = [convert_tag_to_buff(t) for t in bmc2.get("tag_list", [])]
            ug = [{"Name": p["name"], "Desc": p["desc"], "Answer": p.get("answer", "")}
                  for p in bmc1.get("phase_list", [])]
            lg = [{"Name": p["name"], "Desc": p["desc"], "Answer": p.get("answer", "")}
                  for p in bmc2.get("phase_list", [])]

    return {
        "_id": chaos_id,
        "Name": name,
        "Floors": floors,
        "Buff": buff,
        "UB": ub,
        "LB": lb,
        "UC": uc,
        "LC": lc,
        "UG": ug,
        "LG": lg
    }


def format_chaos_entry(entry: Dict[str, Any]) -> str:
    """将chaos条目格式化为可插入AS.js的JS代码字符串"""
    raw = json.dumps(entry, ensure_ascii=False, indent=4)
    lines = raw.split('\n')
    indented = '\n'.join('    ' + line for line in lines)
    return indented


def merge_chaos_to_as_js(boss_id: str, entry: Dict[str, Any], name: str,
                          begin_time: str = "", end_time: str = "") -> str:
    """将_chaos条目、_chaosschedule条目、_chaosdict条目拼接到AS.js"""
    as_js_path = "./sr/data/CH/AS.js"

    with open(as_js_path, 'r', encoding='utf-8') as f:
        content = f.read()

    chaos_id = int(boss_id)
    chaos_id_str = str(chaos_id)

    if f'"_id": {chaos_id}' in content:
        return f"AS条目 {chaos_id} 已存在，无需拼接"

    # 1. 在 var _chaos = [ 之后插入 chaos 条目
    marker_chaos = 'var _chaos = ['
    idx_chaos = content.index(marker_chaos)
    insert_chaos = idx_chaos + len(marker_chaos)
    entry_str = format_chaos_entry(entry)
    content = content[:insert_chaos] + '\n' + entry_str + ',\n' + content[insert_chaos:]

    # 2. 在 var _chaosschedule = [ 之后插入 schedule 条目
    marker_sched = 'var _chaosschedule = ['
    idx_sched = content.index(marker_sched)
    insert_sched = idx_sched + len(marker_sched)
    clean_name = re.sub(r'<[^>]*>', '', name).strip()
    time_str = ""
    if begin_time and end_time:
        time_str = f" {begin_time} - {end_time}"
    sched_entry = f'\n    {{\n        "_id": {chaos_id},\n        "Name": "{clean_name}",\n        "Time": "{time_str}"\n    }},'
    content = content[:insert_sched] + sched_entry + content[insert_sched:]

    # 3. 更新 _chaosdict（在对象开头插入新条目）
    marker_dict = 'var _chaosdict = {'
    idx_dict = content.index(marker_dict)
    insert_dict = idx_dict + len(marker_dict)
    dict_entry = f'\n    "{chaos_id_str}": 0,'
    content = content[:insert_dict] + dict_entry + content[insert_dict:]

    # 4. 更新 _chaosdict 中所有已有条目的索引（全部 +1）
    # 匹配 "XXXX": N 模式并递增
    def increment_dict_indices(match):
        key = match.group(1)
        val = int(match.group(2))
        return f'"{key}": {val + 1}'

    content = re.sub(r'"(\d+)": (\d+)', increment_dict_indices, content)

    # 5. 更新 _chaoshp 中每个楼层的HP数据和Index
    marker_hp = 'var _chaoshp = {'
    idx_hp = content.index(marker_hp)

    # 找到 _chaoshp 对象的结束位置（用于新增楼层时插入）
    hp_obj_start = content.index('{', idx_hp)
    depth_hp = 0
    hp_obj_end = hp_obj_start
    while hp_obj_end < len(content):
        ch = content[hp_obj_end]
        hp_obj_end += 1
        if ch == '{':
            depth_hp += 1
        elif ch == '}':
            depth_hp -= 1
            if depth_hp == 0:
                hp_obj_end -= 1
                break

    floors_in_boss = entry.get("Floors", [])

    for floor_data in floors_in_boss:
        floor_num = floor_data.get(" Floor", 1)
        hpas = floor_data.get("HPAS", 0)
        floor_str = str(floor_num)

        hp_section = content[idx_hp:hp_obj_end + 1]
        floor_pattern = f'"{floor_str}": {{'

        if floor_pattern not in hp_section:
            print(f"提示：_chaoshp中不存在楼层 {floor_str}，将创建")
            insert_before = hp_obj_end
            new_floor = (
                f',\n    "{floor_str}": {{\n'
                f'        "Name": [\n'
                f'            "{clean_name}"\n'
                f'        ],\n'
                f'        "HP": [\n'
                f'            {hpas}\n'
                f'        ],\n'
                f'        "Index": {{\n'
                f'            "{chaos_id_str}": 0\n'
                f'        }}\n'
                f'    }}'
            )
            content = content[:insert_before] + new_floor + content[insert_before:]
            delta = len(new_floor)
            hp_obj_end += delta
            continue

        floor_idx = hp_section.index(floor_pattern)
        floor_start = idx_hp + floor_idx

        index_marker = '"Index": {'
        index_start = content.index(index_marker, content.index(floor_pattern))
        index_brace = content.index('{', index_start)
        depth = 0
        i = index_brace
        while i < len(content):
            ch = content[i]
            i += 1
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    break
        index_block = content[index_brace:i]
        
        if f'"{chaos_id_str}"' in index_block:
            print(f"警告：怪物ID {chaos_id_str} 已存在于楼层 {floor_str} 的Index中，跳过")
            continue

        name_marker = f'"{floor_str}": {{\n        "Name": ['
        name_start = content.index(name_marker, floor_start)
        name_start = name_start + len(name_marker)
        name_end = content.index(']', name_start)
        name_insert = f',\n            "{clean_name}"'
        content = content[:name_end] + name_insert + content[name_end:]

        hp_marker = '"HP": ['
        hp_start = content.index(hp_marker, content.index(floor_pattern))
        hp_end = content.index(']', hp_start)
        hp_insert = f',\n            {hpas}'
        content = content[:hp_end] + hp_insert + content[hp_end:]

        index_end = content.index('}', index_brace)
        index_insert = f',\n                "{chaos_id_str}": '
        
        existing_indices = re.findall(r'"(\d+)": (\d+)', index_block)
        max_idx = max(int(v) for _, v in existing_indices) if existing_indices else -1
        new_idx = max_idx + 1
        
        content = content[:index_end] + index_insert + str(new_idx) + content[index_end:]

    # 写回文件
    with open(as_js_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return f"已自动拼接AS {chaos_id}（{clean_name}）到 AS.js"


def generate_as_star_from_boss(boss_id: str, boss_data: Dict[str, Any],
                                version: str) -> Optional[Dict[str, Any]]:
    """
    从Boss API数据生成AS_star模板数据

    AS_star.js中的Star难度数据是手动维护的，与普通楼层的怪物数据不同。
    此函数生成一个模板，包含：
    - ElemStar: 从API damage_type1转换的元素类型
    - Star: 从最高楼层（Floor 4）的星启event_id_list生成
    - SB: 从buff_list3（星启专属增益）提取
    - SC/SG: 从boss_monster_config（星启专属）提取

    生成的模板需要人工验证和调整，特别是：
    - Star阶段的怪物ID和属性可能与普通楼层不同
    - EliteGroup.ID可能是特殊值（如900）
    """
    levels = boss_data.get("level", [])
    if not levels:
        print(f"警告：Boss {boss_id} 没有楼层数据")
        return None

    # ElemStar: 从第一层的 damage_type1 转换
    lvl0 = levels[0]
    damage_types = lvl0.get("damage_type1", [])
    elem_star = [ELEMENT_MAP.get(dt, dt) for dt in damage_types if dt in ELEMENT_MAP]

    # Star: 从最高楼层的星启 event_id_list 生成模板
    # 星启层用 damage_type（无后缀），普通层用 damage_type1，两种情况都要纳入
    data_levels = [l for l in levels if l.get("damage_type1") is not None
                                     or l.get("damage_type") is not None]
    if not data_levels:
        print(f"警告：Boss {boss_id} 没有有效楼层数据")
        return None

    highest_lvl = data_levels[-1]

    # Star事件：优先取星启专属 event_id_list，fallback 到上半 event_id_list1
    star_events = highest_lvl.get("event_id_list", [])
    if not star_events:
        star_events = highest_lvl.get("event_id_list1", [])
        print(f"提示：Boss {boss_id} 没有星启event_id_list，使用event_id_list1")
    if not star_events:
        print(f"警告：Boss {boss_id} 最高楼层没有event数据")
        return None

    event = star_events[0]
    stage_id = event.get("stage_id", 0)
    stage_level = event.get("level", 90)
    elite_group_id = event.get("elite_group", 900)
    hard_level_group = event.get("hard_level_group", 0)
    monster_list = event.get("monster_list", [])

    # 加载等级曲线并转换怪物
    curves = load_level_curves()

    star_monsters = []
    for wave in monster_list:
        wave_monsters = []
        if isinstance(wave, dict):
            for _key, m_val in wave.items():
                m_id = int(m_val)
                stats = calc_monster_stats(m_id, stage_level,
                                           hard_level_group, elite_group_id,
                                           curves, version)
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
                else:
                    wave_monsters.append({
                        "ID": m_id, "HP": 0, "SPD": 0, "Stance": 0
                    })
        star_monsters.append(wave_monsters)

    star_entry = {
        "_id": stage_id,
        "Level": stage_level,
        "EliteGroup": {
            "ID": elite_group_id,
            "HP": 2.8
        },
        "Monsters": star_monsters
    }

    # SC/SG：优先取星启专属 boss_monster_config，fallback 到上半 boss_monster_config1
    sc, sg = [], []
    bmc_star = highest_lvl.get("boss_monster_config", {})
    if not bmc_star:
        bmc_star = highest_lvl.get("boss_monster_config1", {})
        print(f"提示：Boss {boss_id} 没有星启boss_monster_config，使用boss_monster_config1")
    if bmc_star:
        sc = [convert_tag_to_buff(t) for t in bmc_star.get("tag_list", [])]
        sg = [{"Name": p["name"], "Desc": p["desc"], "Answer": p.get("answer", "")}
              for p in bmc_star.get("phase_list", [])]

    # SB：优先取星启专属 buff_list3，fallback 到上半 buff_list1
    sb_buff_list = boss_data.get("buff_list3", [])
    if not sb_buff_list:
        sb_buff_list = boss_data.get("buff_list1", [])
        print(f"提示：Boss {boss_id} 没有星启buff_list3，使用buff_list1")

    return {
        "ElemStar": elem_star,
        "Star": [star_entry],
        "SB": [convert_tag_to_buff(t) for t in sb_buff_list],
        "SC": sc,
        "SG": sg
    }


def merge_star_to_as_star_js(boss_id: str, star_data: Dict[str, Any]) -> str:
    """
    将星难度数据合并到AS_star.js中

    Args:
        boss_id: Boss ID
        star_data: 包含 ElemStar 和 Star 字段的字典
    """
    as_star_path = "./sr/data/CH/AS_star.js"

    if not os.path.exists(as_star_path):
        return f"文件不存在: {as_star_path}"

    with open(as_star_path, 'r', encoding='utf-8') as f:
        content = f.read()

    boss_id_str = str(boss_id)

    if f'"{boss_id_str}": {{' in content:
        return f"AS_star条目 {boss_id_str} 已存在，跳过"

    # 在 var _AS_star = { 之后插入新条目
    marker = 'var _AS_star = {'
    idx = content.index(marker)
    insert_pos = idx + len(marker)

    # 格式化 elem_star
    elem = star_data.get("ElemStar", [])
    elem_lines = [f'"{e}"' for e in elem]
    elem_str = ',\n                '.join(elem_lines)

    # 格式化 star 条目
    star_entries = star_data.get("Star", [])
    star_str_parts = []
    for star_entry in star_entries:
        eg = star_entry.get("EliteGroup", {})
        eg_id = eg.get("ID", 0)
        eg_hp = eg.get("HP", 1)

        monsters = star_entry.get("Monsters", [])
        wave_strs = []
        for wave in monsters:
            mon_strs = []
            for m in wave:
                parts = [
                    f'"ID": {m.get("ID", 0)}',
                    f'"HP": {m.get("HP", 0)}'
                ]
                if m.get("HPCount", 1) > 1:
                    parts.append(f'"HPCount": {m["HPCount"]}')
                if m.get("SPD", 0) > 0:
                    parts.append(f'"SPD": {m["SPD"]}')
                if m.get("Stance", 0):
                    parts.append(f'"Stance": {m["Stance"]}')
                mon_strs.append('{' + ', '.join(parts) + '}')
            wave_strs.append('[' + ', '.join(mon_strs) + ']')

        star_str_parts.append(f'''        {{
            "_id": {star_entry.get("_id", 0)},
            "Level": {star_entry.get("Level", 90)},
            "EliteGroup": {{
                "ID": {eg_id},
                "HP": {eg_hp}
            }},
            "Monsters": [
                {',\n                '.join(wave_strs)}
            ]
        }}''')

    entry = f'''
    "{boss_id_str}": {{
        "ElemStar": [{elem_str}
        ],
        "Star": [
{",\n".join(star_str_parts)}
        ],
        "SB": {json.dumps(star_data.get("SB", []), ensure_ascii=False, indent=8)},
        "SC": {json.dumps(star_data.get("SC", []), ensure_ascii=False, indent=8)},
        "SG": {json.dumps(star_data.get("SG", []), ensure_ascii=False, indent=8)}
    }},'''

    content = content[:insert_pos] + entry + content[insert_pos:]

    with open(as_star_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return f"已自动拼接AS_star {boss_id_str} 到 AS_star.js"


def generate_as_data(boss_id: str, version: str = None,
                     local_file: str = None) -> str:
    """
    生成AS数据的主入口

    Args:
        boss_id: Boss ID（如 "3018" 对应遗忘冽风）
        version: 版本号（如 "4.3.52"），默认使用最新版本
        local_file: 本地JSON文件路径，如果指定则不下载API数据
    """
    if local_file:
        if not os.path.exists(local_file):
            return f"本地文件不存在: {local_file}"
        with open(local_file, 'r', encoding='utf-8') as f:
            boss_data = json.load(f)
        print(f"从本地文件加载: {local_file}")
    else:
        if version is None:
            version = DEFAULT_VERSION
        boss_data = download_boss_data(boss_id, version)

    if not boss_data:
        return f"下载Boss数据 boss/{boss_id} 失败"

    if version is None:
        version = DEFAULT_VERSION

    prefetch_all_monsters(boss_data, version)

    chaos_entry = convert_boss_to_chaos(boss_id, boss_data, version)
    if not chaos_entry:
        return f"转换Boss数据 boss/{boss_id} 失败"

    # 保存到tempdata
    output_file = os.path.join(OUTPUT_DIR, f"as_{boss_id}.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(chaos_entry, f, ensure_ascii=False, indent=2)

    if testmod:
        # 测试模式：额外导出 star 数据到 tempdata，不拼接 JS
        star_data = generate_as_star_from_boss(boss_id, boss_data, version)
        if star_data:
            star_file = os.path.join(OUTPUT_DIR, f"as_star_{boss_id}.json")
            with open(star_file, 'w', encoding='utf-8') as f:
                json.dump(star_data, f, ensure_ascii=False, indent=2)
            return f"AS {boss_id}（{boss_data.get('name', '')}）数据已导出到 tempdata/（测试模式，未拼接JS）\n  chaos -> {output_file}\n  star  -> {star_file}"
        return f"AS {boss_id}（{boss_data.get('name', '')}）数据已导出 -> {output_file}（测试模式，star数据生成失败）"

    # 正常模式：自动拼接到AS.js
    name = boss_data.get("name", "")
    begin_time = boss_data.get("begin_time", "")
    end_time = boss_data.get("end_time", "")
    merge_msg = merge_chaos_to_as_js(boss_id, chaos_entry, name,
                                      begin_time, end_time)

    # 自动生成并拼接到AS_star.js
    star_data = generate_as_star_from_boss(boss_id, boss_data, version)
    star_merge_msg = ""
    if star_data:
        star_merge_msg = merge_star_to_as_star_js(boss_id, star_data)

    result = f"AS {boss_id}（{name}）数据已生成 -> {output_file}"
    if merge_msg:
        result += "\n" + merge_msg
    if star_merge_msg:
        result += "\n" + star_merge_msg
    if star_data:
        result += "\n提示：AS_star模板数据已生成，请手动验证并调整ElemStar和Star中的怪物属性"
    return result


def main():
    if len(sys.argv) < 2:
        print("用法: python reliance/hsr_trans_as.py <boss_id> [version] [-f <local_file>]")
        print("示例: python reliance/hsr_trans_as.py 3018")
        print("      python reliance/hsr_trans_as.py 3018 4.3.52")
        print("      python reliance/hsr_trans_as.py 3018 -f 3018.json")
        sys.exit(1)

    boss_id = sys.argv[1]
    version = DEFAULT_VERSION
    local_file = None

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '-f' and i + 1 < len(sys.argv):
            local_file = sys.argv[i + 1]
            i += 2
        else:
            version = sys.argv[i]
            i += 1

    result = generate_as_data(boss_id, version, local_file)
    print(result)


if __name__ == "__main__":
    main()