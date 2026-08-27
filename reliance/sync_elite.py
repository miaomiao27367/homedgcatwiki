#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
精英组数据同步与加载模块
- 从API下载 EliteGroup.json / InfiniteEliteGroup.json
- 自动将缺失条目缓存到本地 LevelCurves.js
- 供 hsr_trans_ar.py / hsr_trans_as.py 共用
"""

import os
import json
import requests
from typing import Any, Dict, Tuple

BASE_URL = "https://static.nanoka.cc/hsr"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tempdata")
LEVEL_CURVES_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sr", "data", "LevelCurves.js")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- 模块级缓存 ---
_elite_group_cache: Dict[str, Dict[str, float]] | None = None
_infinite_elite_group_cache: Dict[str, Dict[str, float]] | None = None


def sync_elite_to_local(api_data: list, var_name: str, api_name: str) -> None:
    """将API中缺失的精英组条目自动补充到本地 LevelCurves.js 的指定变量中"""
    with open(LEVEL_CURVES_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # 解析本地已有的变量
    local_ids: set[int] = set()
    try:
        start = content.index(f'var {var_name}')
        eq = content.index('=', start)
        brace = content.index('{', eq)
        depth = 0
        i = brace
        while i < len(content):
            ch = content[i]
            i += 1
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    break
        local_data = json.loads(content[brace:i])
        local_ids = set(int(k) for k in local_data.keys())
        end_pos = i
    except ValueError:
        # 变量不存在，找到 _elitegroup 的结束位置
        start = content.index('var _elitegroup')
        eq = content.index('=', start)
        brace = content.index('{', eq)
        depth = 0
        i = brace
        while i < len(content):
            ch = content[i]
            i += 1
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    break
        end_pos = i

    missing = []
    for entry in api_data:
        eg_id = entry.get("EliteGroup")
        if eg_id is not None and eg_id not in local_ids:
            missing.append(entry)

    if not missing:
        return

    if not local_ids:
        new_lines = ["", f"var {var_name} = {{"]
        for idx, entry in enumerate(missing):
            eg_id = entry["EliteGroup"]
            comma = "," if idx < len(missing) - 1 else ""
            new_lines.append(f'    "{eg_id}": {{')
            new_lines.append(f'        "EliteGroup": {eg_id},')
            new_lines.append(f'        "AttackRatio": {entry["AttackRatio"]},')
            new_lines.append(f'        "DefenceRatio": {entry["DefenceRatio"]},')
            new_lines.append(f'        "HPRatio": {entry["HPRatio"]},')
            new_lines.append(f'        "SpeedRatio": {entry["SpeedRatio"]},')
            new_lines.append(f'        "StanceRatio": {entry["StanceRatio"]}')
            new_lines.append(f'    }}{comma}')
        new_lines.append("};")
        insert_text = "\n".join(new_lines)
        insert_pos = end_pos
    else:
        insert_text = ""
        for entry in missing:
            eg_id = entry["EliteGroup"]
            insert_text += ",\n"
            insert_text += f'    "{eg_id}": {{\n'
            insert_text += f'        "EliteGroup": {eg_id},\n'
            insert_text += f'        "AttackRatio": {entry["AttackRatio"]},\n'
            insert_text += f'        "DefenceRatio": {entry["DefenceRatio"]},\n'
            insert_text += f'        "HPRatio": {entry["HPRatio"]},\n'
            insert_text += f'        "SpeedRatio": {entry["SpeedRatio"]},\n'
            insert_text += f'        "StanceRatio": {entry["StanceRatio"]}\n'
            insert_text += "    }"
        insert_pos = end_pos - 1

    content = content[:insert_pos] + insert_text + content[insert_pos:]

    with open(LEVEL_CURVES_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"  [自动缓存] {api_name}: 已将 {len(missing)} 条缺失条目补充到 LevelCurves.js ({var_name})")


def load_elite_group_data() -> Tuple[Dict[str, Dict[str, float]], Dict[str, Dict[str, float]]]:
    """从API下载 EliteGroup.json 和 InfiniteEliteGroup.json，构建查找表"""
    global _elite_group_cache, _infinite_elite_group_cache

    if _elite_group_cache is not None and _infinite_elite_group_cache is not None:
        return _elite_group_cache, _infinite_elite_group_cache

    _elite_group_cache = {}
    _infinite_elite_group_cache = {}

    for api_name, cache_dict in [
        ("EliteGroup", _elite_group_cache),
        ("InfiniteEliteGroup", _infinite_elite_group_cache)
    ]:
        local_file = os.path.join(OUTPUT_DIR, f"{api_name}.json")
        if os.path.exists(local_file):
            try:
                with open(local_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                data = None
        else:
            data = None

        if data is None:
            url = f"{BASE_URL}/4.3.52/{api_name}.json"
            try:
                response = requests.get(url)
                response.raise_for_status()
                data = response.json()
                try:
                    with open(local_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False)
                except Exception:
                    pass
            except Exception:
                continue

        for entry in data:
            eg_id = entry.get("EliteGroup")
            if eg_id is not None:
                cache_dict[str(eg_id)] = {
                    "HPRatio": entry.get("HPRatio", 1),
                    "AttackRatio": entry.get("AttackRatio", 1),
                    "DefenceRatio": entry.get("DefenceRatio", 1),
                    "SpeedRatio": entry.get("SpeedRatio", 1),
                    "StanceRatio": entry.get("StanceRatio", 1)
                }

        # 下载后自动同步到本地 LevelCurves.js
        var_name = "_elitegroup" if api_name == "EliteGroup" else "_infiniteelitegroup"
        try:
            sync_elite_to_local(data, var_name, api_name)
        except Exception:
            pass

    return _elite_group_cache, _infinite_elite_group_cache


def load_level_curves() -> Dict[str, Any]:
    """加载 LevelCurves.js 中的 _hardlevelgroup、_elitegroup 和 _infiniteelitegroup 数据"""
    with open(LEVEL_CURVES_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # 解析 _hardlevelgroup
    start = content.index('var _hardlevelgroup')
    eq = content.index('=', start)
    brace = content.index('{', eq)
    depth = 0
    i = brace
    while i < len(content):
        ch = content[i]
        i += 1
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                break
    hardlevelgroup = json.loads(content[brace:i])

    # 解析 _elitegroup
    start2 = content.index('var _elitegroup')
    eq2 = content.index('=', start2)
    brace2 = content.index('{', eq2)
    depth = 0
    i = brace2
    while i < len(content):
        ch = content[i]
        i += 1
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                break
    elitegroup = json.loads(content[brace2:i])

    # 解析 _infiniteelitegroup（如果存在）
    infiniteelitegroup = {}
    try:
        start3 = content.index('var _infiniteelitegroup')
        eq3 = content.index('=', start3)
        brace3 = content.index('{', eq3)
        depth = 0
        i = brace3
        while i < len(content):
            ch = content[i]
            i += 1
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    break
        infiniteelitegroup = json.loads(content[brace3:i])
    except ValueError:
        pass

    return {
        "hardlevelgroup": hardlevelgroup,
        "elitegroup": elitegroup,
        "infiniteelitegroup": infiniteelitegroup
    }


def get_elite_group(curves: Dict[str, Any], elite_group_id: int,
                    use_infinite: bool = False) -> Dict[str, float]:
    """
    获取精英组数据
    查找优先级：API缓存 → 本地 _infiniteelitegroup → 本地 _elitegroup
    """
    eg_str = str(elite_group_id)

    elite_cache, infinite_cache = load_elite_group_data()

    if use_infinite and eg_str in infinite_cache:
        return infinite_cache[eg_str]
    if not use_infinite and eg_str in elite_cache:
        return elite_cache[eg_str]

    if use_infinite and eg_str in elite_cache:
        return elite_cache[eg_str]
    if not use_infinite and eg_str in infinite_cache:
        return infinite_cache[eg_str]

    if use_infinite and eg_str in curves.get("infiniteelitegroup", {}):
        return curves["infiniteelitegroup"][eg_str]

    eg = curves["elitegroup"]
    if eg_str in eg:
        return eg[eg_str]

    return {"HPRatio": 1, "AttackRatio": 1.1}