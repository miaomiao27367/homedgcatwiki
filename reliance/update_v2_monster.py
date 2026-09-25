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

# Ensure project root is on sys.path for shared module import
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from reliance.v2_build_utils import (
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
API_CACHE_DIR = os.path.join(PROJECT_ROOT, "reliance", "output", "api_cache")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "reliance", "output")

os.makedirs(API_CACHE_DIR, exist_ok=True)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (compatible; GI-V2-Update/1.0)"})
RETRY_COUNT = 3
RETRY_DELAY = 2


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
# MAIN
# ============================================================
def main():
    global API_VERSION, BASE_URL

    parser = argparse.ArgumentParser(description="Update single monster in V2_DATA")
    parser.add_argument("target_id", help="Local key (e.g. 101) or API child ID (8 digits)")
    parser.add_argument("--force", action="store_true", help="Skip API cache")
    parser.add_argument("--api-version", default=API_VERSION,
                        help=f"API version (default: {API_VERSION})")
    args = parser.parse_args()

    API_VERSION = args.api_version
    BASE_URL = f"https://static.nanoka.cc/gi/{API_VERSION}"
    no_cache = args.force

    # ---- Resolve target ID to local key ----
    target = args.target_id.strip()
    if target.isdigit() and len(target) == 8:
        # API child ID: derive parent and local key
        api_child_id = target
        local_key = api_child_id[1:-2].lstrip('0') or '0'
        print(f"  Child ID {api_child_id} -> local key {local_key}")
    else:
        local_key = target
        api_child_id = None

    print(f"=== Updating monster {local_key} ===\n")
    print(f"API Version: {API_VERSION}")

    # ---- Read existing V2_DATA ----
    print("Reading existing V2_DATA ...")
    v2_data = read_v2_data()
    if v2_data is None:
        return 1
    v2_data = normalize_v2_format(v2_data)

    # ---- Load local _Monsters ----
    print("Loading local _Monsters ...")
    local_monsters = load_local_monsters()
    if local_key not in local_monsters:
        print(f"  Error: Local key '{local_key}' not found in _Monsters.")
        return 1
    local_mon = local_monsters[local_key]
    print(f"  Monster: {local_mon.get('Name', local_key)}")

    # ---- Download API index (for parent ID lookup) ----
    print("Downloading API index ...")
    api_index = download_monster_index(API_VERSION, no_cache)
    print(f"  {len(api_index)} entries")

    api_parent_id = local_key_to_api_parent(local_key, api_index)
    if not api_parent_id:
        print("  Warning: No API parent found. Variants will be empty.")
        api_detail = {}
    else:
        print(f"  API parent: {api_parent_id}")
        api_detail = download_monster_detail(api_parent_id, API_VERSION, no_cache)
        if api_detail:
            print(f"  API children: {len(api_detail.get('child', {}))}")
        else:
            print("  Warning: API detail download failed.")
            api_detail = {}

    # ---- Build updated entries using shared module ----
    suffix_map = load_suffix_map()
    list_entry, variants = build_one_monster(local_key, local_mon, api_detail, suffix_map, api_index)

    # Update List entry in place
    v2_data["List"][local_key] = list_entry

    # Update Variants in place (preserve key ordering)
    # Remove old variants for this parent
    old_var_count = 0
    keys_to_remove = [cid for cid, vdata in v2_data.get("Variants", {}).items()
                      if str(vdata.get("ParentId")) == str(local_key)]
    for cid in keys_to_remove:
        del v2_data["Variants"][cid]
        old_var_count += 1

    # Add new variants (will be appended at the end, which matches full build order)
    for cid, vdata in variants.items():
        v2_data["Variants"][cid] = vdata

    print(f"\n  Removed {old_var_count} old variants, added {len(variants)} new variants")

    # ---- Write back ----
    write_v2_data(v2_data)
    print("  Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())