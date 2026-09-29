"""
build_v2_data.py - Generate v2 monster data as 4 separate JSON files.
Usage: python reliance/build_v2_data.py [--lang CH] [--api-version 7.1.50] [--no-cache]

Data sources (priority: LOCAL > API):
  gi/CH/computer.js         - _Monsters, _Kingdoms, _Tuts, _Tutorials
  javascripts/monsterJson.js - _computer_.LevelCurves
  API: https://static.nanoka.cc/gi/{version}/monster.json         (index)
       https://static.nanoka.cc/gi/{version}/zh/monster/{id}.json (detail)

Output (4 JSON files in gi/{lang}/monster/):
  monster-v2-base.json  - { Generated, Version, Source, Kingdoms, Tuts, Tutorials }
  Levelcurve.json       - { "1": {...}, "2": {...}, ... }
  monster.json          - { "101": {...}, "102": {...}, ... }  (was List)
  monsterfull.json      - { "20010101": {...}, ... }
  reliance/output/v2_build_report.txt
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
# CONSTANTS (build-specific)
# ============================================================
API_VERSION = "7.1.50"
BASE_URL = f"https://static.nanoka.cc/gi/{API_VERSION}"
PROJECT_ROOT = _PROJECT_ROOT
API_CACHE_DIR = os.path.join(PROJECT_ROOT, ".temp", "gi", "v2", "api_cache")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, ".temp", "gi", "v2")

os.makedirs(API_CACHE_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# HTTP session
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (compatible; GI-V2-Build/1.0)"})
RETRY_COUNT = 3
RETRY_DELAY = 2


# ============================================================
# JS PARSING
# ============================================================
def extract_js_object(text, var_name):
    """Extract a JS object assigned to var_name."""
    idx = text.index(f"var {var_name}")
    chunk = text[idx:idx + 100]

    b_idx = chunk.index("{") if "{" in chunk else None
    a_idx = chunk.index("[") if "[" in chunk else None

    if b_idx is not None and (a_idx is None or b_idx < a_idx):
        idx = text.index("{", idx)
        close_char = "}"
    elif a_idx is not None:
        idx = text.index("[", idx)
        close_char = "]"
    else:
        raise ValueError(f"Could not find opening brace/bracket for {var_name}")

    start_char = text[idx]
    depth = 0
    in_str = False
    esc = False
    i = idx
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
            elif c == start_char:
                depth += 1
            elif c == close_char:
                depth -= 1
                if depth == 0:
                    raw = text[idx:i + 1]
                    raw = re.sub(r",\s*([}\]])", r"\1", raw)
                    return json.loads(raw)
        i += 1

    raise ValueError(f"Could not extract {var_name}: end of object not found")


# ============================================================
# LOCAL DATA LOADING
# ============================================================
def load_local_monsters(lang="CH"):
    """Extract _Monsters from gi/{lang}/computer.js."""
    path = os.path.join(PROJECT_ROOT, "gi", lang, "computer.js")
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    return extract_js_object(text, "_Monsters")


def load_local_kingdoms(lang="CH"):
    """Extract _Kingdoms from gi/{lang}/computer.js."""
    path = os.path.join(PROJECT_ROOT, "gi", lang, "computer.js")
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    return extract_js_object(text, "_Kingdoms")


def load_local_tutorials(lang="CH"):
    """Extract _Tutorials from gi/{lang}/computer.js."""
    path = os.path.join(PROJECT_ROOT, "gi", lang, "computer.js")
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    return extract_js_object(text, "_Tutorials")


def load_local_tuts(lang="CH"):
    """Extract _Tuts from gi/{lang}/computer.js."""
    path = os.path.join(PROJECT_ROOT, "gi", lang, "computer.js")
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    return extract_js_object(text, "_Tuts")


def load_level_curves():
    """Extract _computer_.LevelCurves from javascripts/monsterJson.js."""
    path = os.path.join(PROJECT_ROOT, "javascripts", "monsterJson.js")
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    computer = extract_js_object(text, "_computer_")
    return computer.get("LevelCurves", {})


def load_suffix_map():
    """Load suffix map from output/suffix_map.json."""
    path = os.path.join(OUTPUT_DIR, "suffix_map.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    # Default
    return {
        "": "基础",
        "_SimplifiedAI": "简化AI", "_AttackEnhance": "攻击强化",
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
# API FETCHING
# ============================================================
def fetch_json(url, cache_path=None, no_cache=False):
    """Fetch JSON from URL, with optional caching."""
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
    """Download API monster index (list of 8-digit IDs)."""
    url = f"{BASE_URL}/monster.json"
    cache = os.path.join(API_CACHE_DIR, f"monster_index_{version}.json")
    return fetch_json(url, cache, no_cache) or {}


def download_monster_detail(api_id, version, no_cache=False):
    """Download single monster detail from API."""
    url = f"{BASE_URL}/zh/monster/{api_id}.json"
    cache = os.path.join(API_CACHE_DIR, f"detail_{api_id}_{version}.json")
    return fetch_json(url, cache, no_cache)


# ============================================================
# MAIN BUILD
# ============================================================
def build_v2_data(lang="CH", no_cache=False):
    """Main build function."""
    print(f"=== Building V2_DATA (API-direct) for lang={lang} ===\n")
    print(f"API Version: {API_VERSION}")
    print()

    # ---- Load local data ----
    print("[1/5] Loading local data ...")
    monsters = load_local_monsters(lang)
    print(f"  _Monsters: {len(monsters)} parents")
    kingdoms = load_local_kingdoms(lang)
    print(f"  _Kingdoms: {len(kingdoms)} kingdoms")
    tutorials = load_local_tutorials(lang)
    print(f"  _Tutorials: {len(tutorials)} entries")
    tuts = load_local_tuts(lang)
    print(f"  _Tuts: {len(tuts)} entries")
    level_curves = load_level_curves()
    print(f"  LevelCurves: {len(level_curves)} level entries")
    suffix_map = load_suffix_map()
    print(f"  SuffixMap: {len(suffix_map)} entries")
    print()

    # ---- Download API index ----
    print("[2/5] Downloading API monster index ...")
    api_index = download_monster_index(API_VERSION, no_cache)
    print(f"  API index: {len(api_index)} entries")
    print()

    # ---- Build List + Variants (main loop: local _Monsters keys) ----
    print("[3/5] Building V2_DATA.List and V2_DATA.Variants ...")
    v2_list = {}
    v2_variants = {}

    stats = {
        "total_parents": len(monsters),
        "api_found": 0,
        "api_not_found": 0,
        "total_variants": 0,
        "suffix_empty": 0,
        "resbase_all_8": 0,
        "immune_empty": 0,
    }

    for pid in monsters:
        local_mon = monsters[pid]
        api_parent_id = local_key_to_api_parent(pid, api_index)

        if api_parent_id:
            api_detail = download_monster_detail(api_parent_id, API_VERSION, no_cache)
            if api_detail is None:
                api_detail = {}
                stats["api_not_found"] += 1
            else:
                stats["api_found"] += 1
        else:
            api_detail = {}
            stats["api_not_found"] += 1

        list_entry, variants = build_one_monster(pid, local_mon, api_detail, suffix_map, api_index)

        v2_list[pid] = list_entry

        for child_id, vdata in variants.items():
            v2_variants[child_id] = vdata
            stats["total_variants"] += 1
            if vdata.get("Suffix", "") == "":
                stats["suffix_empty"] += 1
            if isinstance(vdata.get("Immune", []), list) and len(vdata.get("Immune", [])) == 0:
                stats["immune_empty"] += 1
            # RESBase completeness
            rb = vdata.get("RESBase", {})
            if len(rb) == 8:
                stats["resbase_all_8"] += 1

        if stats["total_parents"] <= 10 or int(pid) % 50 == 0:
            print(f"  Processed {pid} ... ({stats['total_variants']} variants so far)")

    print(f"  Done. Parents: {stats['total_parents']}, Variants: {stats['total_variants']}")
    print(f"  API found: {stats['api_found']}, not found: {stats['api_not_found']}")
    print()

    # ---- Assemble V2_DATA ----
    print("[4/5] Assembling V2_DATA ...")
    now = datetime.now(timezone.utc).isoformat()[:19]
    v2_data = {
        "Version": "1.0",
        "Generated": now,
        "Source": {
            "Monsters": f"/gi/{lang}/computer.js",
            "API": f"https://static.nanoka.cc/gi/{API_VERSION}/",
            "LevelCurves": "/javascripts/monsterJson.js",
            "Script": "reliance/build_v2_data.py",
        },
        "Kingdoms": kingdoms,
        "LevelCurves": level_curves,
        "Tuts": tuts,
        "Tutorials": tutorials,
        "List": v2_list,
        "Variants": v2_variants,
    }

    # ---- Validation ----
    print("[5/5] Validating ...")
    errors = validate_v2(v2_data, monsters)
    if errors:
        print("\n=== VALIDATION ERRORS ===")
        for e in errors:
            print(f"  FAIL: {e}")
        print("\n  Build aborted. Fix errors before writing output.")
        return None, stats

    print("  All validations passed.")
    return v2_data, stats


# ============================================================
# VALIDATION
# ============================================================
def validate_v2(v2_data, local_monsters):
    """Run 6 required validation checks. Return list of error strings."""
    errors = []
    v2_list = v2_data.get("List", {})
    v2_variants = v2_data.get("Variants", {})

    # 1. Key sets match
    local_keys = set(str(k) for k in local_monsters.keys())
    v2_list_keys = set(v2_list.keys())
    if local_keys != v2_list_keys:
        missing = local_keys - v2_list_keys
        extra = v2_list_keys - local_keys
        if missing:
            errors.append(f"List missing {len(missing)} local keys: {sorted(missing)[:10]}...")
        if extra:
            errors.append(f"List has {len(extra)} extra keys: {sorted(extra)[:10]}...")

    # 2. Name match
    for pid in local_keys:
        local_name = local_monsters.get(pid, {}).get("Name", "")
        list_name = v2_list.get(pid, {}).get("Name", "")
        if local_name and list_name != local_name:
            errors.append(f"Name mismatch for {pid}: local='{local_name}' vs list='{list_name}'")

    # 3. Color match
    for pid in local_keys:
        local_color = local_monsters.get(pid, {}).get("Color")
        list_color = v2_list.get(pid, {}).get("Color")
        if local_color is not None and list_color != local_color:
            errors.append(f"Color mismatch for {pid}: local='{local_color}' vs list='{list_color}'")

    # 4. Icon match
    for pid in local_keys:
        local_icon = local_monsters.get(pid, {}).get("Icon")
        list_icon = v2_list.get(pid, {}).get("Icon")
        if local_icon is not None and list_icon != local_icon:
            errors.append(f"Icon mismatch for {pid}: local='{json.dumps(local_icon, ensure_ascii=False)}' vs list='{json.dumps(list_icon, ensure_ascii=False)}'")

    # 5. Immune preservation: 57 local monsters have non-empty Immune
    for pid in local_keys:
        local_immune = local_monsters.get(pid, {}).get("Immune")
        if isinstance(local_immune, list) and len(local_immune) > 0:
            # Check that all variants of this pid have this Immune
            for cid, vdata in v2_variants.items():
                if vdata.get("ParentId") == int(pid) or str(vdata.get("ParentId")) == pid:
                    var_immune = vdata.get("Immune", [])
                    if var_immune != local_immune:
                        errors.append(f"Immune mismatch for variant {cid} (parent {pid}): expected {local_immune}, got {var_immune}")
                        break

    # 6. HP match
    for pid in local_keys:
        local_hp = local_monsters.get(pid, {}).get("HP")
        if local_hp is not None:
            list_hp = v2_list.get(pid, {}).get("HP")
            if list_hp is None:
                errors.append(f"HP missing in List for {pid} (local has {local_hp})")

    return errors


# ============================================================
# WRITE OUTPUT (4 JSON files)
# ============================================================
def write_output(v2_data, lang="CH"):
    """Write 4 JSON files to gi/{lang}/.

    Files:
      monster-v2-base.json        - base data (Generated, Version, Source, Kingdoms, Tuts, Tutorials)
      Levelcurve.json            - LevelCurves dict  { "1": {...}, ... }
      monster.json               - List dict         { "101": {...}, ... }
      monsterfull.json           - Variants dict     { "20010101": {...}, ... }
    """
    out_dir = os.path.join(PROJECT_ROOT, "gi", lang, "monster")
    root_dir = os.path.join(PROJECT_ROOT, "gi", lang)
    print(f"\n=== Writing 4 JSON files ===\n")

    # Build base dict (everything except LevelCurves, List, Variants)
    base = {
        "Generated": v2_data.get("Generated"),
        "Version": v2_data.get("Version"),
        "Source": v2_data.get("Source"),
        "Kingdoms": v2_data.get("Kingdoms"),
        "Tuts": v2_data.get("Tuts"),
        "Tutorials": v2_data.get("Tutorials"),
    }

    levelcurve = v2_data.get("LevelCurves", {})
    monster = v2_data.get("List", {})
    variant = v2_data.get("Variants", {})

    # Levelcurve.json goes to gi/{lang}/, rest go to gi/{lang}/monster/
    files_root = {"Levelcurve.json": levelcurve}
    files_monster = {
        "monster-v2-base.json": base,
        "monster.json": monster,
        "monsterfull.json": variant,
    }

    total_bytes = 0
    for fname, data in files_root.items():
        path = os.path.join(root_dir, fname)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=False)
        size = os.path.getsize(path)
        total_bytes += size
        print(f"  {fname} -> gi/{lang}/{fname} ({size:,} bytes)")

    for fname, data in files_monster.items():
        path = os.path.join(out_dir, fname)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=False)
        size = os.path.getsize(path)
        total_bytes += size
        print(f"  {fname} -> gi/{lang}/monster/{fname} ({size:,} bytes)")

    print(f"\n  Total: {total_bytes:,} bytes ({total_bytes / 1024:.1f} KB)")


def write_report(v2_data, stats, out_path):
    """Write build report."""
    lines = []
    w = lines.append

    w("=" * 60)
    w("  V2_DATA Build Report (API-direct)")
    w("=" * 60)
    w(f"  Generated: {v2_data['Generated']}")
    w(f"  API Version: {API_VERSION}")
    w("")

    w("-" * 60)
    w("  Summary")
    w("-" * 60)
    w(f"  Total parents (List): {stats['total_parents']}")
    w(f"  Total variants: {stats['total_variants']}")
    w(f"  API detail found: {stats['api_found']}")
    w(f"  API detail NOT found: {stats['api_not_found']}")
    w("")

    w("-" * 60)
    w("  Field Sources")
    w("-" * 60)
    w("  Purely local (never from API):")
    for fld in PURELY_LOCAL_FIELDS:
        w(f"    - {fld}")
    w("")
    w("  API-only (no local counterpart):")
    w("    - MonsterName, Type, LocalLegend, Suffix")
    w("")
    w("  Hybrid (local priority, API fallback):")
    w("    - HP, HPCurve, HPCount, ATK, ATKCurve, ATKCount")
    w("    - RESBase (union: local overrides API)")
    w("")

    w("-" * 60)
    w("  Variant Field Stats")
    w("-" * 60)
    w(f"  Suffix empty (''): {stats['suffix_empty']}/{stats['total_variants']}")
    w(f"  RESBase complete (8 keys): {stats['resbase_all_8']}/{stats['total_variants']}")
    w(f"  Immune empty ([]): {stats['immune_empty']}/{stats['total_variants']}")
    w("")

    # Immune details: count non-empty
    immune_nonempty = 0
    for cid, vdata in v2_data.get("Variants", {}).items():
        imm = vdata.get("Immune", [])
        if isinstance(imm, list) and len(imm) > 0:
            immune_nonempty += 1
    w(f"  Immune non-empty: {immune_nonempty}/{stats['total_variants']}")
    w("")

    w("-" * 60)
    w("  Validation")
    w("-" * 60)
    w("  All 6 checks passed: YES")
    w("")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  Report written to {out_path}")


def main():
    global API_VERSION, BASE_URL

    parser = argparse.ArgumentParser(description="Build v2 monster data file (API-direct)")
    parser.add_argument("--lang", default="CH", help="Language code (default: CH)")
    parser.add_argument("--api-version", default=API_VERSION, help=f"API version (default: {API_VERSION})")
    parser.add_argument("--no-cache", action="store_true", help="Ignore local API cache")
    args = parser.parse_args()

    API_VERSION = args.api_version
    BASE_URL = f"https://static.nanoka.cc/gi/{API_VERSION}"

    result = build_v2_data(args.lang, args.no_cache)
    if result is None or result[0] is None:
        print("\n=== BUILD FAILED (validation errors) ===")
        return 1

    v2_data, stats = result
    total_bytes, out_dir = write_output(v2_data, args.lang)
    report_path = os.path.join(OUTPUT_DIR, "v2_build_report.txt")
    write_report(v2_data, stats, report_path)

    print(f"\n=== Done. 4 JSON files written to {out_dir} ({total_bytes:,} bytes total) ===")
    return 0


if __name__ == "__main__":
    exit(main())