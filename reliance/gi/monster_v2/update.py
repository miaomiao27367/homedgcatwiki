"""
update_v2_monster.py - Single-ID update from API (API-direct).
Usage:
  python reliance/update_v2_monster.py 101              # by local key
  python reliance/update_v2_monster.py 20010101         # by API child ID
  python reliance/update_v2_monster.py 101 --force      # skip cache
  python reliance/update_v2_monster.py 101 --api-version 7.1.50
"""
import argparse
import json
import os
import re
import sys
import time
import requests
from datetime import datetime, timezone
from io import BytesIO
from PIL import Image

# Ensure project root is on sys.path for shared module import
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from reliance.gi.monster_v2.utils import (
    GROW_CURVE_HP_MAP, GROW_CURVE_HP_MAP_AUTOMATRON,
    GROW_CURVE_ATK_MAP, GROW_CURVE_ATK_MAP_AUTOMATRON,
    HP_COEFFICIENTS, ATK_COEFFICIENTS,
    ELEMENT_MAP, ALL_ELEMENT_KEYS,
    KNOWN_CHILD_SUFFIXES, PURELY_LOCAL_FIELDS, VARIANT_LOCAL_FIELDS,
    SUFFIX_WHITELIST,
    get_local_val, expand_sub_hurt, compute_suffix, cleanup_suffix,
    map_hp_curve, map_atk_curve,
    normalize_hp, normalize_atk,
    find_base_child,
    api_id_to_local_key, local_key_to_api_parent,
    build_one_monster,
)


# ============================================================
# CONSTANTS (update-specific)
# ============================================================
API_VERSION = "7.1.50"
BASE_URL = f"https://static.nanoka.cc/gi/{API_VERSION}"
PROJECT_ROOT = _PROJECT_ROOT
API_CACHE_DIR = os.path.join(PROJECT_ROOT, ".temp", "gi", "v2", "api_cache")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, ".temp", "gi", "v2")

os.makedirs(API_CACHE_DIR, exist_ok=True)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (compatible; GI-V2-Update/1.0)"})
RETRY_COUNT = 3
RETRY_DELAY = 2

# ============================================================
# CODEX → KINGDOM MAPPING (API → local)
# ============================================================
CODEX_TO_KINGDOM = {
    "ELEMENTAL": 0,
    "HILICHURL": 1,
    "ABYSS": 2,
    "FATUI": 3,
    "AUTOMATRON": 4,
    "HUMAN": 5,
    "BEAST": 6,
    "BOSS": 9,
    "ANIMAL": 13,
    "CRITTER": 6,
    "AVIARY": 6,
    "FISH": 6,
}

KINGDOM_NAMES = {
    0: "元素生命",
    1: "丘丘部族",
    2: "深渊",
    3: "愚人众",
    4: "自律机关",
    5: "其他人类势力",
    6: "异种魔兽",
    8: "幽境危战",
    9: "值得铭记的强敌",
    10: "地方传奇",
    11: "<b>6.3</b>",
    12: "历经百战",
    13: "友善生物",
}

CODEX_CLASS_NAMES = {
    "ELEMENTAL": "元素生命",
    "HILICHURL": "丘丘人",
    "ABYSS": "深渊魔物",
    "FATUI": "愚人众",
    "AUTOMATRON": "自律机关",
    "HUMAN": "人类势力",
    "BEAST": "异种魔兽",
    "BOSS": "首领敌人",
    "ANIMAL": "动物",
    "CRITTER": "走兽",
    "AVIARY": "飞禽",
    "FISH": "游鱼",
}

# ============================================================
# KINGDOM AUTO-ASSIGNMENT
# ============================================================


# ============================================================
# API FETCHING
# ============================================================
def fetch_json(url, cache_path=None, no_cache=False):
    if cache_path and not no_cache and os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    for attempt in range(RETRY_COUNT):
        try:
            r = SESSION.get(url, timeout=30)
            r.raise_for_status()
            data = r.json()
            if cache_path:
                os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            return data
        except Exception as e:
            if attempt < RETRY_COUNT - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            print(f"  Error fetching {url}: {e}")
            return None


def download_monster_index(version, no_cache=False):
    url = f"{BASE_URL}/monster.json"
    cache = os.path.join(API_CACHE_DIR, f"monster_index_{version}.json")
    return fetch_json(url, cache, no_cache) or {}


def download_monster_detail(api_id, version, no_cache=False):
    url = f"{BASE_URL}/zh/monster/{api_id}.json"
    cache = os.path.join(API_CACHE_DIR, f"detail_{api_id}_{version}.json")
    return fetch_json(url, cache, no_cache)


def load_suffix_map():
    path = os.path.join(OUTPUT_DIR, "suffix_map.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "": "基础", "_SimplifiedAI": "简化AI", "_AttackEnhance": "攻击强化",
        "_Dark": "暗", "_Electro": "雷", "_Frozen": "冻结",
        "_Thunder": "雷", "_Hydro": "水", "_Pyro": "火",
        "_Cryo": "冰", "_Anemo": "风", "_Geo": "岩",
        "_Dendro": "草", "_Elec": "雷", "_Water": "水",
        "_Fire": "火", "_Ice": "冰", "_Wind": "风",
        "_Grass": "草", "_Rock": "岩", "_Shield": "护盾",
        "_Shielder": "持盾", "_Wander": "游荡", "_Dash": "冲锋",
        "_Ranged": "远程", "_Melee": "近战", "_Bomber": "炸弹",
        "_SP": "SP", "_Quest": "任务", "_Berserk": "狂暴",
        "_Slow": "迟缓", "_Sleep": "沉睡", "_FromGoddess": "女神",
    }


# ============================================================
# V2_DATA FILE I/O
# ============================================================
def read_v2_data():
    """Read existing V2_DATA from gi/CH/monster-v2-data.js."""
    path = os.path.join(PROJECT_ROOT, "gi", "CH", "monster-v2-data.js")
    if not os.path.exists(path):
        print(f"  Error: {path} not found. Run build_v2_data.py first.")
        return None
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    idx = text.index("var V2_DATA = {")
    eq = text.index("{", idx)
    depth = 0
    in_str = False
    esc = False
    i = eq
    n = len(text)

    while i < n:
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "/" and i + 1 < n:
                nxt = text[i + 1]
                if nxt == "/":
                    i = text.index("\n", i) if "\n" in text[i:] else n
                    continue
                elif nxt == "*":
                    i = text.index("*/", i) if "*/" in text[i:] else n
                    i += 1
                    continue
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    raw = text[eq:i + 1]
                    raw = re.sub(r",\s*([}\]])", r"\1", raw)
                    return json.loads(raw)
        i += 1

    print("  Error: Could not parse V2_DATA from file.")
    return None


def normalize_v2_format(v2_data):
    """Convert old format (Monsters with nested Variants) to new format
    (List + Variants) if the old format is detected."""
    if "Monsters" in v2_data and "List" not in v2_data:
        print("  Detected old format (Monsters). Converting to new format (List + Variants) ...")
        new_list = {}
        new_variants = {}
        for pid, pdata in v2_data.pop("Monsters").items():
            nested_variants = pdata.pop("Variants", {})
            list_entry = dict(pdata)
            new_list[pid] = list_entry
            for cid, vdata in nested_variants.items():
                new_variants[cid] = vdata
        v2_data["List"] = new_list
        v2_data["Variants"] = new_variants
        print(f"  Converted: {len(new_list)} List entries, {len(new_variants)} Variants entries")
    return v2_data


def write_v2_data(v2_data):
    """Write V2_DATA back to gi/CH/monster-v2-data.js."""
    path = os.path.join(PROJECT_ROOT, "gi", "CH", "monster-v2-data.js")
    v2_data["Generated"] = datetime.now(timezone.utc).isoformat()[:19]

    header = f"""// Auto Generated by build_v2_data.py (API-direct edition)
// Source:
//   Monsters:   /gi/CH/computer.js
//   Kingdoms:   /gi/CH/computer.js
//   Tuts:       /gi/CH/computer.js
//   Tutorials:  /gi/CH/computer.js
//   LevelCurves: /javascripts/monsterJson.js
//   API Index:   https://static.nanoka.cc/gi/{API_VERSION}/monster.json
//   API Detail:  https://static.nanoka.cc/gi/{API_VERSION}/zh/monster/{{id}}.json
// API Version: {API_VERSION}
// Generated:   {v2_data['Generated']}
// Version:     {v2_data['Version']}

var V2_DATA = """
    json_str = json.dumps(v2_data, ensure_ascii=False, indent=2, sort_keys=True)

    with open(path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(json_str)
        f.write(";\n")

    file_size = os.path.getsize(path)
    print(f"  Written {path} ({file_size:,} bytes)")


def load_local_monsters():
    """Extract _Monsters from gi/CH/computer.js."""
    path = os.path.join(PROJECT_ROOT, "gi", "CH", "computer.js")
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    idx = text.index("var _Monsters = {")
    eq = text.index("{", idx)
    depth = 0
    in_str = False
    esc = False
    i = eq
    n = len(text)

    while i < n:
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "/" and i + 1 < n:
                nxt = text[i + 1]
                if nxt == "/":
                    i = text.index("\n", i) if "\n" in text[i:] else n
                    continue
                elif nxt == "*":
                    i = text.index("*/", i) if "*/" in text[i:] else n
                    i += 1
                    continue
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    raw = text[eq:i + 1]
                    raw = re.sub(r",\s*([}\]])", r"\1", raw)
                    return json.loads(raw)
        i += 1

    print("  Error: Could not extract _Monsters.")
    return {}


# ============================================================
# IMAGE CACHING
# ============================================================
def cache_monster_icons(icon_list, log_fn=None):
    """
    将怪物图标从 API CDN 下载并缓存到本地 homdgcat-res/monster/

    参数:
        icon_list: Icon 名字列表，如 ["UI_MonsterIcon_Chimera_CrocodileBoar"]
        log_fn:    日志函数
    返回:
        成功缓存的图片数量
    """
    if not icon_list:
        return 0

    icon_dir = os.path.join(_PROJECT_ROOT, "homdgcat-res", "monster")
    os.makedirs(icon_dir, exist_ok=True)
    cached = 0

    for icon_name in icon_list:
        if not icon_name:
            continue
        icon_path = os.path.join(icon_dir, f"{icon_name}.png")
        if os.path.exists(icon_path):
            continue  # 已有缓存

        webp_url = f"https://static.nanoka.cc/assets/gi/{icon_name}.webp"
        try:
            resp = requests.get(webp_url, headers={"User-Agent": "HomDGCat/1.0"}, timeout=30)
            if resp.status_code == 200:
                img = Image.open(BytesIO(resp.content))
                img.save(icon_path, "PNG")
                cached += 1
                if log_fn:
                    log_fn(f"  Cached icon: {icon_name}.png")
            else:
                if log_fn:
                    log_fn(f"  Icon not found (HTTP {resp.status_code}): {icon_name}")
        except Exception as e:
            if log_fn:
                log_fn(f"  Icon download failed: {icon_name} - {e}")

    return cached


# ============================================================
# KINGDOM AUTO-ASSIGNMENT
# ============================================================
def update_computer_js_kingdoms(new_kingdoms, log_fn=None):
    """Overwrite _Kingdoms in computer.js with modified array."""
    if log_fn is None:
        log_fn = print
    path = os.path.join(PROJECT_ROOT, "gi", "CH", "computer.js")
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    idx = text.index("var _Kingdoms = [")
    bracket = text.index("[", idx)
    depth = 0
    in_str = False
    esc = False
    i = bracket
    n = len(text)

    while i < n:
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "/" and i + 1 < n:
                nxt = text[i + 1]
                if nxt == "/":
                    i = text.index("\n", i) if "\n" in text[i:] else n
                    continue
                elif nxt == "*":
                    i = text.index("*/", i) if "*/" in text[i:] else n
                    i += 1
                    continue
            elif c == "[":
                depth += 1
            elif c == "]":
                depth -= 1
                if depth == 0:
                    kingdom_end = i
                    break
        i += 1
    else:
        log_fn("  Error: Could not find _Kingdoms array boundary in computer.js")
        return False

    new_json = json.dumps(new_kingdoms, ensure_ascii=False, indent=4)
    new_text = text[:bracket] + new_json + text[kingdom_end + 1:]
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_text)
    log_fn(f"  Updated computer.js _Kingdoms ({len(new_kingdoms)} kingdoms)")
    return True


def auto_assign_kingdom(v2_data, local_key, api_detail, log_fn=None):
    """Auto-assign monster to Kingdom based on API codex field.

    Updates both V2_DATA.Kingdoms (in-memory) and computer.js _Kingdoms (disk).
    """
    if log_fn is None:
        log_fn = print
    if not api_detail:
        return

    codex = api_detail.get("codex", "")
    if not codex:
        log_fn("  No codex in API detail, skipping Kingdom auto-assign")
        return

    kingdom_id = CODEX_TO_KINGDOM.get(codex.upper())
    if kingdom_id is None:
        log_fn(f"  Unknown codex '{codex}', skipping Kingdom auto-assign")
        return

    local_key_int = int(local_key)
    kingdom_name = KINGDOM_NAMES.get(kingdom_id, f"Kingdom {kingdom_id}")

    # Use API "title" as the sub-category Class name (not the local Title field)
    api_title = api_detail.get("title", "")
    class_name = api_title if api_title else CODEX_CLASS_NAMES.get(codex.upper(), codex)

    log_fn(f"  API title='{class_name}' -> Kingdom {kingdom_id} ({kingdom_name})")

    # --- Update V2_DATA.Kingdoms (in-memory) ---
    kingdoms = v2_data.get("Kingdoms", [])
    kingdom = None
    for k in kingdoms:
        if k.get("ID") == kingdom_id:
            kingdom = k
            break

    if kingdom is None:
        kingdom = {"ID": kingdom_id, "Name": kingdom_name, "Classes": []}
        kingdoms.append(kingdom)
        log_fn(f"  Created new Kingdom: {kingdom_name} (ID={kingdom_id})")

    classes = kingdom.get("Classes", [])
    target_class = None
    for cls in classes:
        if cls.get("Name") == class_name:
            target_class = cls
            break

    if target_class is None:
        target_class = {"ID": 0, "Name": class_name, "Monsters": []}
        classes.append(target_class)
        log_fn(f"  Created new Class: {class_name} in {kingdom_name}")

    monsters = target_class.get("Monsters", [])
    if local_key_int not in monsters:
        monsters.append(local_key_int)
        log_fn(f"  Auto-assigned {local_key} to Kingdom {kingdom_id} ({kingdom_name}) / Class {class_name}")
    else:
        log_fn(f"  {local_key} already in Kingdom {kingdom_id} ({kingdom_name})")

    # --- Update computer.js _Kingdoms (disk) ---
    update_computer_js_kingdoms(kingdoms, log_fn=log_fn)


# ============================================================
# WRAPPER FUNCTION (callable from server.py / tools UI)
# ============================================================
def update_single_monster(target_id, api_version=None, force=False):
    """
    单 ID 增量更新 —— 供 server.py 调用的包装函数。

    参数:
        target_id:  本地 key（如 "101"）或 API child ID（8位如 "20010101"）
        api_version: API 版本号（默认使用全局 API_VERSION）
        force:       是否跳过缓存重新下载

    返回:
        (success: bool, message: str, output: str)
    """
    global API_VERSION, BASE_URL

    if api_version:
        API_VERSION = api_version
        BASE_URL = f"https://static.nanoka.cc/gi/{API_VERSION}"

    output_lines = []
    def log(msg):
        print(msg)
        output_lines.append(msg)

    target = str(target_id).strip()
    if target.isdigit() and len(target) == 8:
        api_child_id = target
        local_key = api_child_id[1:-2].lstrip('0') or '0'
        log(f"  Child ID {api_child_id} -> local key {local_key}")
    else:
        local_key = target
        api_child_id = None

    log(f"=== Updating monster {local_key} ===")
    log(f"API Version: {API_VERSION}")

    log("Reading existing V2_DATA ...")
    v2_data = read_v2_data()
    if v2_data is None:
        return False, "V2_DATA 文件未找到，请先运行 build_v2_data.py", "\n".join(output_lines)
    v2_data = normalize_v2_format(v2_data)

    log("Loading local _Monsters ...")
    local_monsters = load_local_monsters()
    if local_key in local_monsters:
        local_mon = local_monsters[local_key]
        log(f"  Monster (local): {local_mon.get('Name', local_key)}")
    else:
        local_mon = None
        log(f"  Warning: local key '{local_key}' not in _Monsters, using API-only data")

    log("Downloading API index ...")
    api_index = download_monster_index(API_VERSION, force)
    log(f"  {len(api_index)} entries")

    api_parent_id = local_key_to_api_parent(local_key, api_index)
    if not api_parent_id:
        log("  Warning: No API parent found. Variants will be empty.")
        api_detail = {}
    else:
        log(f"  API parent: {api_parent_id}")
        api_detail = download_monster_detail(api_parent_id, API_VERSION, force)
        if api_detail:
            log(f"  API children: {len(api_detail.get('child', {}))}")
        else:
            log("  Warning: API detail download failed.")
            api_detail = {}

    suffix_map = load_suffix_map()
    list_entry, variants = build_one_monster(local_key, local_mon, api_detail, suffix_map, api_index)

    # ---- Enrich List entry from API (for API-only monsters lacking local _Monsters data) ----
    if local_mon is None and api_detail:
        enriched = []
        if not list_entry.get("Name"):
            list_entry["Name"] = api_detail.get("name", "")
            enriched.append("Name")
        if not list_entry.get("Title"):
            spec_names = api_detail.get("special_names", [])
            list_entry["Title"] = spec_names if isinstance(spec_names, list) else []
            if list_entry["Title"]:
                enriched.append(f"Title={list_entry['Title']}")
        if not list_entry.get("Desc"):
            list_entry["Desc"] = api_detail.get("desc", "")
            enriched.append("Desc")
        if not list_entry.get("Icon"):
            api_icon = api_detail.get("icon", "")
            list_entry["Icon"] = [api_icon] if api_icon else []
            enriched.append("Icon")
        if enriched:
            log(f"  Enriched from API: {', '.join(enriched)}")

    # ---- Auto-assign Kingdom based on API codex ----
    auto_assign_kingdom(v2_data, local_key, api_detail, log_fn=log)

    v2_data["List"][local_key] = list_entry

    keys_to_remove = [cid for cid, vdata in v2_data.get("Variants", {}).items()
                      if str(vdata.get("ParentId")) == str(local_key)]
    old_var_count = len(keys_to_remove)
    for cid in keys_to_remove:
        del v2_data["Variants"][cid]

    for cid, vdata in variants.items():
        v2_data["Variants"][cid] = vdata

    log(f"  Removed {old_var_count} old variants, added {len(variants)} new variants")

    write_v2_data(v2_data)

    # 缓存图标
    icon_list = list_entry.get("Icon", [])
    if icon_list:
        log("  Caching monster icons ...")
        n = cache_monster_icons(icon_list, log_fn=log)
        log(f"  Cached {n} icon(s)")
    else:
        log("  No icons to cache")

    log("  Done.")

    if local_mon:
        name = local_mon.get("Name", "?")
    else:
        name = list_entry.get("Name", local_key)
    return True, f"怪物 {local_key} ({name}) 更新成功", "\n".join(output_lines)


# ============================================================
# STANDALONE ICON CACHING (callable from server.py / tools UI)
# ============================================================
def cache_icons_for_monster(target_id, api_version=None, force=False):
    """
    独立图标缓存 —— 仅下载图标，不修改 V2_DATA。
    适用于：更新中断后补缓存、历史怪物图标补全。

    参数:
        target_id:  本地 key 或 API child ID
        api_version: API 版本号
        force:       是否跳过缓存重新下载
    返回:
        (success: bool, message: str, output: str)
    """
    global API_VERSION, BASE_URL

    if api_version:
        API_VERSION = api_version
        BASE_URL = f"https://static.nanoka.cc/gi/{API_VERSION}"

    output_lines = []
    def log(msg):
        print(msg)
        output_lines.append(msg)

    target = str(target_id).strip()
    if target.isdigit() and len(target) == 8:
        api_child_id = target
        local_key = api_child_id[1:-2].lstrip('0') or '0'
    else:
        local_key = target
        api_child_id = None

    log(f"=== Caching icons for {local_key} ===")

    # 尝试从 V2_DATA 获取 Icon
    v2_data = read_v2_data()
    if v2_data:
        v2_data = normalize_v2_format(v2_data)
        list_entry = v2_data.get("List", {}).get(local_key, {})
        icon_list = list_entry.get("Icon", [])
        if icon_list:
            log(f"  Found Icon in V2_DATA: {icon_list}")
            n = cache_monster_icons(icon_list, log_fn=log)
            log(f"  Cached {n} icon(s)")
            name = list_entry.get("Name", local_key)
            if n > 0:
                return True, f"图标缓存完成: {name} ({n} 个)", "\n".join(output_lines)
            else:
                return True, f"图标已存在，无需下载: {name}", "\n".join(output_lines)

    # V2_DATA 中没有，查询 API
    log("  Icon not in V2_DATA, querying API ...")
    api_index = download_monster_index(API_VERSION, force)
    api_parent_id = local_key_to_api_parent(local_key, api_index)
    if api_parent_id:
        api_detail = download_monster_detail(api_parent_id, API_VERSION, force)
        if api_detail:
            api_icon = api_detail.get("icon", "")
            if api_icon:
                n = cache_monster_icons([api_icon], log_fn=log)
                log(f"  Cached {n} icon(s) from API")
                if n > 0:
                    return True, f"图标缓存完成: {api_icon}", "\n".join(output_lines)
                else:
                    return True, f"图标已存在: {api_icon}", "\n".join(output_lines)

    log("  No icon found")
    return False, f"未找到图标: {local_key}", "\n".join(output_lines)


# ============================================================
# MAIN (CLI entry point)
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="Update single monster in V2_DATA")
    parser.add_argument("target_id", help="Local key (e.g. 101) or API child ID (8 digits)")
    parser.add_argument("--force", action="store_true", help="Skip API cache")
    parser.add_argument("--api-version", default=API_VERSION,
                        help=f"API version (default: {API_VERSION})")
    args = parser.parse_args()

    success, message, output = update_single_monster(
        args.target_id.strip(),
        api_version=args.api_version,
        force=args.force
    )
    print(message)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())