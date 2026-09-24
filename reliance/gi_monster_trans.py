#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GI怪物数据从API更新程序
从 https://static.nanoka.cc/gi/{version}/monster.json 获取怪物索引
从 https://static.nanoka.cc/gi/{version}/zh/monster/{id}.json 获取怪物详情
转换并输出为本地 _Monsters 格式
"""

import os
import json
import time
import requests
import re
from typing import Optional, Dict, Any, List, Tuple

VERSION = "7.1.50"
BASE_URL = f"https://static.nanoka.cc/gi/{VERSION}"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "tempdata")

# 输出文件路径 (不修改原文件，输出到tempdata)
OUTPUT_MONSTERS_JS = os.path.join(OUTPUT_DIR, f"monsters_gi_{VERSION}.js")
OUTPUT_MONSTERS_JSON = os.path.join(OUTPUT_DIR, f"monsters_gi_{VERSION}.json")
OUTPUT_MAPPING_JSON = os.path.join(OUTPUT_DIR, f"monsters_mapping_{VERSION}.json")

os.makedirs(OUTPUT_DIR, exist_ok=True)

KNOWN_CHILD_SUFFIXES = [
    '_SimplifiedAI', '_AttackEnhance', '_Dark', '_Electro',
    '_Frozen', '_Thunder', '_Hydro', '_FromGoddess', '_SP',
    '_Sleep', '_Quest', '_Berserk', '_Slow', '_Pyro', '_Cryo',
    '_Anemo', '_Geo', '_Dendro', '_Elec', '_Water', '_Fire',
    '_Ice', '_Wind', '_Grass', '_Rock', '_Shield', '_Shielder',
    '_Wander', '_Dash', '_Ranged', '_Melee', '_Bomber',
]

# Session + Retry配置
SESSION = requests.Session()
SESSION.headers.update({'User-Agent': 'Mozilla/5.0 (compatible; GI-Monster-Trans/1.0)'})
RETRY_COUNT = 3
RETRY_DELAY = 2

# --- 元素映射 ---
SUB_HURT_TO_ELEMENT = {
    "fire": "Fire", "grass": "Grass", "water": "Water",
    "elec": "Elec", "wind": "Wind", "ice": "Ice",
    "rock": "Rock", "physical": "Phys",
}

# --- Grow Curve 映射 ---
GROW_CURVE_HP_MAP = {
    "GROW_CURVE_HP": 1,
    "GROW_CURVE_HP_S4": 2,     # 推测：更高的HP成长
    "GROW_CURVE_HP_S5": 2,     # 推测
    "GROW_CURVE_HP_2": 2,
    "GROW_CURVE_NONE": 0,
}

GROW_CURVE_ATK_MAP = {
    "GROW_CURVE_ATTACK": 3,
    "GROW_CURVE_ATTACK_2": 4,  # 更高的ATK成长
    "GROW_CURVE_ATTACK_S4": 4,
    "GROW_CURVE_ATTACK_S5": 4,
    "GROW_CURVE_NONE": 0,
}

# AUTOMATRON(机关)类型使用不同的曲线编号
GROW_CURVE_HP_MAP_AUTOMATRON = {
    "GROW_CURVE_HP": 1,
    "GROW_CURVE_HP_2": 7,
    "GROW_CURVE_HP_S4": 7,
    "GROW_CURVE_HP_S5": 20,
    "GROW_CURVE_NONE": 0,
}
GROW_CURVE_ATK_MAP_AUTOMATRON = {
    "GROW_CURVE_ATTACK": 3,
    "GROW_CURVE_ATTACK_2": 40,
    "GROW_CURVE_ATTACK_S4": 40,
    "GROW_CURVE_ATTACK_S5": 40,
    "GROW_CURVE_NONE": 0,
}

# codex → Color 推断映射（仅用于新条目）
CODEX_TO_COLOR = {
    "ELEMENTAL": None,   # 元素生命需结合sub_hurt判断
    "BOSS": None,        # BOSS大部分有对应Color
    "HILICHURL": "Phys",
    "HUMAN": "Phys",
    "ABYSS": "Dark",
    "BEAST": "Phys",
}


def get_icon_short_name(icon_full: str) -> str:
    """
    将API的完整icon名转为本地短名
    例如: UI_MonsterIcon_Slime_Grass_02 -> dslm
    这个映射需要手动维护，对于未知的返回None
    """
    return icon_full


def load_local_monsters() -> Dict[str, Any]:
    """加载本地 computer.js 中的 _Monsters 数据"""
    local_path = os.path.join(BASE_DIR, "gi", "CH", "computer.js")
    with open(local_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取 _Monsters 变量
    start = content.index('var _Monsters = {')
    eq = content.index('{', start)
    depth = 0
    i = eq
    while i < len(content):
        ch = content[i]
        i += 1
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                break
    
    js_block = content[eq:i]
    # JavaScript转JSON（处理末尾逗号等）
    js_block = re.sub(r',\s*(\}|\])', r'\1', js_block)
    try:
        return json.loads(js_block)
    except json.JSONDecodeError as e:
        print(f"Warning: Parse error at pos {e.pos}, trying to fix...")
        # 尝试更激进的修复
        js_block = re.sub(r',(\s*\n\s*)(\}|\])', r'\1\2', js_block)
        return json.loads(js_block)


def load_local_computer() -> Dict[str, Any]:
    """加载本地所有 computer.js 相关数据"""
    local_path = os.path.join(BASE_DIR, "gi", "CH", "computer.js")
    with open(local_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    result = {}
    
    # 提取 _Monsters
    try:
        start = content.index('var _Monsters = {')
        eq = content.index('{', start)
        depth = 0
        i = eq
        while i < len(content):
            ch = content[i]
            i += 1
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    break
        js_block = content[eq:i]
        js_block = re.sub(r',\s*(\}|\])', r'\1', js_block)
        result['_Monsters'] = json.loads(js_block)
    except Exception as e:
        print(f"Error loading _Monsters: {e}")
        result['_Monsters'] = {}
    
    # 提取 _MonsterCustomColorNameConfig
    try:
        start = content.index('var _MonsterCustomColorNameConfig = {')
        eq = content.index('{', start)
        depth = 0
        i = eq
        while i < len(content):
            ch = content[i]
            i += 1
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    break
        js_block = content[eq:i]
        js_block = re.sub(r',\s*(\}|\])', r'\1', js_block)
        result['_MonsterCustomColorNameConfig'] = json.loads(js_block)
    except Exception as e:
        print(f"Error loading _MonsterCustomColorNameConfig: {e}")
        result['_MonsterCustomColorNameConfig'] = {}
    
    return result


def api_id_to_local_key(api_id: str) -> str:
    """
    将API的8位ID转为本地key
    规则: 去掉首位的'2'和末两位后缀，去除前导零
    20010101 -> 101, 29010101 -> 90101
    """
    stripped = api_id[1:-2]  # 去掉首字母和末两位
    return stripped.lstrip('0') or '0'


def determine_color_from_sub_hurt(sub_hurt: Dict[str, float]) -> Optional[str]:
    """从sub_hurt推断怪物元素/颜色"""
    if not sub_hurt:
        return None
    # 寻找抗性最高（且 > 0.1）的元素
    max_res = 0.1
    max_elem = None
    for elem, res in sub_hurt.items():
        if res > max_res:
            max_res = res
            max_elem = elem
    if max_elem:
        return SUB_HURT_TO_ELEMENT.get(max_elem)
    return None


def infer_hp_curve(curves: List[Dict], codex: str = "") -> int:
    """从API growth curves映射为本地HPCurve值"""
    for c in curves:
        if 'HP' in c.get('type', ''):
            gc = c.get('grow_curve', '')
            if codex == 'AUTOMATRON':
                return GROW_CURVE_HP_MAP_AUTOMATRON.get(gc, 2)
            return GROW_CURVE_HP_MAP.get(gc, 1)
    return 1  # 默认


def infer_atk_curve(curves: List[Dict], codex: str = "") -> int:
    """从API growth curves映射为本地ATKCurve值"""
    for c in curves:
        if 'ATTACK' in c.get('type', ''):
            gc = c.get('grow_curve', '')
            if codex == 'AUTOMATRON':
                return GROW_CURVE_ATK_MAP_AUTOMATRON.get(gc, 4)
            return GROW_CURVE_ATK_MAP.get(gc, 3)
    return 3  # 默认


def convert_res_base(sub_hurt: Dict[str, float]) -> Dict[str, float]:
    """
    将API的sub_hurt转为本地RESBase格式
    sub_hurt中值为0.1的是默认值(10%全抗)，需要排除
    """
    result = {}
    for elem, value in sub_hurt.items():
        if value != 0.1:  # 排除默认10%全抗
            elem_name = SUB_HURT_TO_ELEMENT.get(elem, elem)
            result[elem_name] = value
    return result


def convert_immune(sub_hurt: Dict[str, float]) -> List[str]:
    """
    从sub_hurt中提取免疫类型（抗性 >= 1.0 或非常高）
    """
    immune = []
    for elem, value in sub_hurt.items():
        if value >= 1.0:
            elem_name = SUB_HURT_TO_ELEMENT.get(elem, elem)
            immune.append(elem_name)
    return immune


def _fetch_json(url: str, cache_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """带重试的JSON下载"""
    if cache_path and os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    for attempt in range(RETRY_COUNT):
        try:
            r = SESSION.get(url, timeout=30)
            r.raise_for_status()
            data = r.json()
            if cache_path:
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            return data
        except Exception as e:
            if attempt < RETRY_COUNT - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            print(f"  Error fetching {url}: {e}")
            return None


def download_monster_index(version: str) -> Dict[str, Any]:
    """下载怪物索引"""
    url = f"{BASE_URL}/monster.json"
    cache_path = os.path.join(OUTPUT_DIR, f"monster_index_{version}.json")
    print(f"Downloading monster index from {url}")
    data = _fetch_json(url, cache_path)
    return data if data else {}


def download_monster_detail(monster_id: str, version: str) -> Optional[Dict[str, Any]]:
    """下载单个怪物详情"""
    url = f"{BASE_URL}/zh/monster/{monster_id}.json"
    cache_path = os.path.join(OUTPUT_DIR, f"monster_detail_{monster_id}_{version}.json")
    return _fetch_json(url, cache_path)


def build_local_entry(
    api_parent_id: str,
    api_child_id: str,
    child_data: Dict[str, Any],
    parent_detail: Dict[str, Any],
    parent_index: Dict[str, Any],
    existing_local: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    根据API数据构建本地格式的怪物条目
    parent_index: monster.json中的条目（含codex字段）
    """
    local_key = api_id_to_local_key(api_child_id)
    codex = (parent_index.get('codex') or parent_detail.get('codex') or '').upper()
    
    entry = {
        "_id": int(local_key) if local_key.isdigit() else local_key,
    }
    
    # --- Name ---
    if existing_local and 'Name' in existing_local:
        entry['Name'] = existing_local['Name']
    else:
        # 优先使用detail中的name，其次使用index中的zh
        entry['Name'] = parent_detail.get('name') or parent_index.get('zh', '')
    
    # --- Title ---
    if existing_local and 'Title' in existing_local:
        entry['Title'] = existing_local['Title']
    else:
        title_parts = []
        if parent_detail.get('title'):
            title_parts.append(parent_detail['title'])
        if parent_detail.get('special_names'):
            title_parts.extend(parent_detail['special_names'])
        if title_parts:
            entry['Title'] = title_parts
    
    # --- Desc ---
    if existing_local and 'Desc' in existing_local:
        entry['Desc'] = existing_local['Desc']
    else:
        desc = parent_detail.get('desc') or parent_index.get('desc', '')
        if desc:
            entry['Desc'] = desc
    
    # --- Color ---
    sub_hurt = child_data.get('sub_hurt', {})
    if existing_local and 'Color' in existing_local:
        entry['Color'] = existing_local['Color']
    else:
        # 新条目: 尝试从sub_hurt推断，再从codex推断
        color = determine_color_from_sub_hurt(sub_hurt)
        if not color and codex in CODEX_TO_COLOR:
            color = CODEX_TO_COLOR[codex]
        if color:
            entry['Color'] = color
    
    # --- HP and ATK ---
    base = child_data.get('base', {})
    props = child_data.get('prop', [])
    
    if existing_local:
        if 'HP' in existing_local:
            entry['HP'] = existing_local['HP']
        if 'HPCurve' in existing_local:
            entry['HPCurve'] = existing_local['HPCurve']
        if 'ATK' in existing_local:
            entry['ATK'] = existing_local['ATK']
        if 'ATKCurve' in existing_local:
            entry['ATKCurve'] = existing_local['ATKCurve']
    else:
        # 新怪物：使用API的基础值
        if 'hp' in base:
            entry['HP'] = base['hp']
        if 'atk' in base:
            entry['ATK'] = base['atk']
        entry['HPCurve'] = infer_hp_curve(props, codex)
        entry['ATKCurve'] = infer_atk_curve(props, codex)
    
    # --- RESBase ---
    res_base = convert_res_base(sub_hurt)
    if res_base:
        entry['RESBase'] = res_base
    
    # --- Immune ---
    immune = convert_immune(sub_hurt)
    if immune:
        entry['Immune'] = immune
    
    # --- Icon ---
    if existing_local and 'Icon' in existing_local:
        entry['Icon'] = existing_local['Icon']
    else:
        icon = parent_index.get('icon', '')
        if icon:
            entry['Icon'] = [icon]
    
    # --- Csx ---
    if existing_local and 'Csx' in existing_local:
        entry['Csx'] = existing_local['Csx']
    
    # --- Tut ---
    if existing_local and 'Tut' in existing_local:
        entry['Tut'] = existing_local['Tut']
    
    # --- Tutorial ---
    if existing_local and 'Tutorial' in existing_local:
        entry['Tutorial'] = existing_local['Tutorial']
    
    return entry


def convert_all_monsters(
    version: str = VERSION,
    local_data: Optional[Dict[str, Any]] = None,
    limit: int = 0,
) -> Dict[str, Any]:
    """
    主函数：下载API数据并转换为本地格式
    limit: 限制处理数量，0=全部（用于测试）
    """
    if local_data is None:
        local_data = load_local_monsters()
    
    # 1. 下载索引
    index = download_monster_index(version)
    total_index = len(index)
    print(f"Monster index: {total_index} entries")
    
    # 构建本地ID -> 本地条目的映射，用于查找已有数据
    local_by_id = {}
    for key, entry in local_data.items():
        local_id = entry.get('_id', '')
        local_by_id[str(local_id)] = entry
        local_by_id[key] = entry  # 也按key索引
    
    # 2. 处理每个怪物
    new_monsters = {}
    mapping_log = []  # 记录API ID到本地key的映射
    
    api_ids = list(index.keys())
    if limit > 0:
        api_ids = api_ids[:limit]
    
    processed = 0
    skipped = 0
    total = len(api_ids)
    
    for i, api_id in enumerate(api_ids):
        index_entry = index[api_id]
        if (i + 1) % 50 == 0 or i == 0:
            print(f"  Processing {i + 1}/{total} ({processed} converted, {skipped} skipped)...")
        
        # 下载详情
        detail = download_monster_detail(api_id, version)
        if not detail:
            skipped += 1
            continue
        
        children = detail.get('child', {})
        if not children:
            skipped += 1
            continue
        
        # 过滤子变体：只取主变体（排除后缀变体）
        def is_base_child(cdata):
            mname = cdata.get('monster_name', '')
            for suffix in KNOWN_CHILD_SUFFIXES:
                if mname.endswith(suffix):
                    return False
            return True
        
        base_children = {cid: cdata for cid, cdata in children.items() if is_base_child(cdata)}
        if not base_children:
            base_children = children  # fallback: no base child found
        
        for child_id, child_data in base_children.items():
            local_key = api_id_to_local_key(child_id)
            
            # 避免重复key
            if local_key in new_monsters:
                continue
            
            # 查找已有条目
            existing = local_by_id.get(local_key) or local_by_id.get(child_id)
            
            # 构建新条目
            entry = build_local_entry(
                api_parent_id=api_id,
                api_child_id=child_id,
                child_data=child_data,
                parent_detail=detail,
                parent_index=index_entry,
                existing_local=existing,
            )
            
            new_monsters[local_key] = entry
            
            mapping_log.append({
                "api_parent_id": api_id,
                "api_child_id": child_id,
                "local_key": local_key,
                "name": entry.get('Name', ''),
                "is_new": existing is None,
                "icon_api": index_entry.get('icon', ''),
                "icon_local": entry.get('Icon', []),
                "color": entry.get('Color'),
            })
        
        processed += 1
    
    print(f"\n  Done: {total} processed, {processed} converted, {skipped} skipped")
    
    # 合并本地独有条目（不在API中的手动条目）
    local_only_count = 0
    for local_key, local_entry in local_data.items():
        if local_key not in new_monsters:
            new_monsters[local_key] = local_entry
            local_only_count += 1
    
    print(f"\nTotal entries converted: {len(new_monsters)}")
    new_count = sum(1 for m in mapping_log if m['is_new'])
    print(f"New entries (from API): {new_count}")
    print(f"Updated entries (from API): {len(mapping_log) - new_count}")
    print(f"Local-only entries (preserved): {local_only_count}")
    
    return new_monsters, mapping_log


def generate_js_output(monsters: Dict[str, Any], mapping_log: List[Dict]) -> str:
    """生成JS格式输出"""
    lines = []
    lines.append(f"// GI Monster Data - Generated from API version {VERSION}")
    lines.append(f"// Total entries: {len(monsters)}")
    lines.append("")
    lines.append("var _Monsters = {")
    
    sorted_keys = sorted(monsters.keys(), key=lambda k: int(k) if k.isdigit() else 0)
    
    for i, key in enumerate(sorted_keys):
        entry = monsters[key]
        comma = "," if i < len(sorted_keys) - 1 else ""
        lines.append(f"    \"{key}\": {json.dumps(entry, ensure_ascii=False)}{comma}")
    
    lines.append("};")
    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='GI Monster Data Converter from API')
    parser.add_argument('--limit', type=int, default=0, help='Limit processing to N monsters (0=all)')
    parser.add_argument('--version', type=str, default=VERSION, help=f'API version (default: {VERSION})')
    args = parser.parse_args()
    
    ver = args.version
    
    print(f"=== GI Monster Data Converter ===")
    print(f"API Version: {ver}")
    print(f"Output directory: {OUTPUT_DIR}")
    if args.limit > 0:
        print(f"Test mode: processing first {args.limit} entries only")
    print()
    
    # 加载本地数据（用于对比和保留手动数据）
    print("Loading local monster data...")
    local_data = load_local_monsters()
    print(f"  Local _Monsters entries: {len(local_data)}")
    
    # 执行转换
    new_monsters, mapping_log = convert_all_monsters(ver, local_data, limit=args.limit)
    
    # 更新输出路径（如果版本不同）
    output_js = OUTPUT_MONSTERS_JS.replace(VERSION, ver)
    output_json = OUTPUT_MONSTERS_JSON.replace(VERSION, ver)
    output_mapping = OUTPUT_MAPPING_JSON.replace(VERSION, ver)
    
    # 生成JS输出
    js_output = generate_js_output(new_monsters, mapping_log)
    with open(output_js, 'w', encoding='utf-8') as f:
        f.write(js_output)
    print(f"\nJS output saved to: {output_js}")
    
    # 生成JSON输出（便于查看和对比）
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(new_monsters, f, ensure_ascii=False, indent=2)
    print(f"JSON output saved to: {output_json}")
    
    # 生成映射日志
    with open(output_mapping, 'w', encoding='utf-8') as f:
        json.dump(mapping_log, f, ensure_ascii=False, indent=2)
    print(f"Mapping log saved to: {output_mapping}")
    
    # 统计
    new_count = sum(1 for m in mapping_log if m['is_new'])
    update_count = sum(1 for m in mapping_log if not m['is_new'])
    print(f"\n=== Summary ===")
    print(f"API monsters in index: {len(mapping_log)}")
    print(f"Previously existing: {update_count}")
    print(f"Newly added: {new_count}")
    print(f"Manual-curated data (Csx/Tut/Color/Icon) preserved for existing entries.")


if __name__ == '__main__':
    main()