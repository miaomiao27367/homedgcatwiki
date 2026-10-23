"""
v2_build_utils.py - Shared constants and functions for V2_DATA generation.
Used by both build_v2_data.py and update_v2_monster.py.

Contains:
  - Curve mapping tables
  - Normalization coefficients
  - Element key mapping
  - Field lists (PURELY_LOCAL_FIELDS, KNOWN_CHILD_SUFFIXES)
  - Helpers: get_local_val, expand_sub_hurt, compute_suffix
  - Curve mappers: map_hp_curve, map_atk_curve
  - Normalizers: normalize_hp, normalize_atk
  - ID mapping: api_id_to_local_key, local_key_to_api_parent
  - Core builder: build_one_monster (builds List + Variants for one parent)
"""

import os

# ============================================================
# CURVE MAPPING
# ============================================================
GROW_CURVE_HP_MAP = {
    "GROW_CURVE_HP": 1, "GROW_CURVE_HP_2": 2,
    "GROW_CURVE_HP_S4": 2, "GROW_CURVE_HP_S5": 2,
    "GROW_CURVE_NONE": 0,
}
GROW_CURVE_HP_MAP_AUTOMATRON = {
    "GROW_CURVE_HP": 1, "GROW_CURVE_HP_2": 7,
    "GROW_CURVE_HP_S4": 7, "GROW_CURVE_HP_S5": 20,
    "GROW_CURVE_NONE": 0,
}
GROW_CURVE_ATK_MAP = {
    "GROW_CURVE_ATTACK": 3, "GROW_CURVE_ATTACK_2": 4,
    "GROW_CURVE_ATTACK_S4": 4, "GROW_CURVE_ATTACK_S5": 4,
    "GROW_CURVE_NONE": 0,
}
GROW_CURVE_ATK_MAP_AUTOMATRON = {
    "GROW_CURVE_ATTACK": 3, "GROW_CURVE_ATTACK_2": 40,
    "GROW_CURVE_ATTACK_S4": 40, "GROW_CURVE_ATTACK_S5": 40,
    "GROW_CURVE_NONE": 0,
}

# ============================================================
# NORMALIZATION COEFFICIENTS
# ============================================================
HP_COEFFICIENTS = {0: 1.0, 1: 13.584, 2: 27.168, 7: 27.168, 20: 27.168}
ATK_COEFFICIENTS = {0: 1.0, 3: 12.56, 4: 12.56, 40: 12.56}

# ============================================================
# ELEMENT KEY MAPPING
# ============================================================
ELEMENT_MAP = {
    "physical": "Phys", "fire": "Fire", "water": "Water",
    "elec": "Elec", "wind": "Wind", "ice": "Ice",
    "rock": "Rock", "grass": "Grass",
}
ALL_ELEMENT_KEYS = ["Phys", "Fire", "Water", "Elec", "Ice", "Grass", "Wind", "Rock"]

# ============================================================
# KNOWN CHILD SUFFIXES (for stripping from monster_name)
# ============================================================
KNOWN_CHILD_SUFFIXES = [
    "_SimplifiedAI", "_AttackEnhance", "_Dark", "_Electro",
    "_Frozen", "_Thunder", "_Hydro", "_FromGoddess", "_SP",
    "_Sleep", "_Quest", "_Berserk", "_Slow", "_Pyro", "_Cryo",
    "_Anemo", "_Geo", "_Dendro", "_Elec", "_Water", "_Fire",
    "_Ice", "_Wind", "_Grass", "_Rock", "_Shield", "_Shielder",
    "_Wander", "_Dash", "_Ranged", "_Melee", "_Bomber",
]

# ============================================================
# FIELD LISTS
# ============================================================
PURELY_LOCAL_FIELDS = [
    "Name", "Title", "Desc", "Icon", "Color", "Csx", "Tut", "Tutorial",
    "UseCustomColorName", "RevertName", "Immune",
    "RESState", "RESModify", "MultiPlayerID",
    "ExtraSpiralAbyssCoeff", "NotAffectedBySpiralAbyss",
    "OnlyBaseImmune", "NoRESBase",
]

# Local-only fields also applied to variants
VARIANT_LOCAL_FIELDS = [
    "RESState", "RESModify", "MultiPlayerID",
    "ExtraSpiralAbyssCoeff", "NotAffectedBySpiralAbyss",
    "OnlyBaseImmune", "NoRESBase",
]

# ============================================================
# SUFFIX WHITELIST (only these Chinese-mapped suffixes are kept)
# ============================================================
SUFFIX_WHITELIST = {
    "简化AI", "攻击强化", "火", "冰", "雷", "水", "草", "风", "岩", "任务",
    "暗", "冻结", "护盾", "持盾", "游荡", "冲锋", "远程", "近战", "炸弹",
    "狂暴", "迟缓", "沉睡", "女神",
}


# ============================================================
# HELPERS
# ============================================================
def get_local_val(local_monster, field, default=None):
    """Get a value from local _Monsters, treating None/undefined as absent."""
    if local_monster is None:
        return default
    val = local_monster.get(field)
    if val is None:
        return default
    return val


def expand_sub_hurt(sub_hurt):
    """Expand API sub_hurt into full 8-element RESBase, filling missing with 0.1."""
    result = {}
    for api_key, local_key in ELEMENT_MAP.items():
        result[local_key] = sub_hurt.get(api_key, 0.1)
    return result


def compute_suffix(monster_name, parent_monster_name, suffix_map):
    """
    Compute suffix from child monster_name.
    Strip parent's monster_name prefix to get raw suffix.
    - If stripped is empty → ""
    - If stripped is in suffix_map (e.g. "_SimplifiedAI") → mapped name (e.g. "简化AI")
    - If stripped is unknown → keep raw suffix (e.g. "_Dark")
    """
    if not monster_name or not parent_monster_name:
        return ""

    # Exact match = base variant (01), no suffix
    if monster_name == parent_monster_name:
        return ""

    # Strip parent name prefix
    if monster_name.startswith(parent_monster_name):
        raw_suffix = monster_name[len(parent_monster_name):]
        if raw_suffix in suffix_map and raw_suffix != "":
            return suffix_map[raw_suffix]
        return raw_suffix

    # Fallback: monster_name doesn't start with parent name
    # Try stripping known child suffixes to find base
    base = monster_name
    for sfx in sorted(KNOWN_CHILD_SUFFIXES, key=lambda x: -len(x)):
        if base.endswith(sfx):
            base = base[:-len(sfx)]
    if base != monster_name:
        if base == parent_monster_name:
            return ""
        raw_suffix = monster_name[len(base):]
        if raw_suffix in suffix_map and raw_suffix != "":
            return suffix_map[raw_suffix]
        return raw_suffix

    # Last resort: try suffix_map keys on whole monster_name
    for sfx, name in sorted(suffix_map.items(), key=lambda x: -len(x[0])):
        if sfx and monster_name.endswith(sfx):
            return name

    return ""


def cleanup_suffix(raw_suffix):
    """P1: Apply suffix whitelist. Keep only recognized Chinese suffixes, discard others."""
    if raw_suffix == "":
        return ""
    if raw_suffix in SUFFIX_WHITELIST:
        return raw_suffix
    return ""


# ============================================================
# CURVE MAPPERS
# ============================================================
def map_hp_curve(prop_list, codex):
    """Map API grow_curve to local HPCurve number, based on codex."""
    gc = "GROW_CURVE_NONE"
    for p in prop_list:
        if "HP" in p.get("type", ""):
            gc = p.get("grow_curve", "GROW_CURVE_NONE")
            break
    if codex.upper() == "AUTOMATRON":
        return GROW_CURVE_HP_MAP_AUTOMATRON.get(gc, 2)
    return GROW_CURVE_HP_MAP.get(gc, 1)


def map_atk_curve(prop_list, codex):
    """Map API grow_curve to local ATKCurve number, based on codex."""
    gc = "GROW_CURVE_NONE"
    for p in prop_list:
        if "ATTACK" in p.get("type", ""):
            gc = p.get("grow_curve", "GROW_CURVE_NONE")
            break
    if codex.upper() == "AUTOMATRON":
        return GROW_CURVE_ATK_MAP_AUTOMATRON.get(gc, 4)
    return GROW_CURVE_ATK_MAP.get(gc, 3)


# ============================================================
# NORMALIZERS
# ============================================================
def normalize_hp(api_hp, curve):
    """Convert API absolute HP to normalized value."""
    if api_hp is None or api_hp == 0:
        return None
    coeff = HP_COEFFICIENTS.get(curve, 1.0)
    if coeff == 0:
        return None
    return round(api_hp / coeff, 6)


def normalize_atk(api_atk, curve):
    """Convert API absolute ATK to normalized value."""
    if api_atk is None or api_atk == 0:
        return None
    coeff = ATK_COEFFICIENTS.get(curve, 1.0)
    if coeff == 0:
        return None
    return round(api_atk / coeff, 6)


# ============================================================
# CHILD UTILITY
# ============================================================
def find_base_child(child_dict):
    """Find the '01' (base) variant in child_dict."""
    for cid in sorted(child_dict.keys()):
        if cid.endswith("01"):
            return cid, child_dict[cid]
    # Fallback: first child
    if child_dict:
        first = next(iter(child_dict.items()))
        return first
    return None, None


# ============================================================
# ID MAPPING
# ============================================================
def api_id_to_local_key(api_id):
    """8-digit API ID -> local _Monsters key. 20010101 -> '101'."""
    return api_id[1:-2].lstrip('0') or '0'


def local_key_to_api_parent(local_key, api_index):
    """Given a local key like '101', find the 8-digit API parent ID."""
    local_str = str(local_key)
    candidates = []
    for api_id_str in api_index:
        if not api_id_str.isdigit() or len(api_id_str) != 8:
            continue
        if api_id_to_local_key(api_id_str) == local_str:
            candidates.append(api_id_str)
    candidates.sort()
    return candidates[0] if candidates else None


# ============================================================
# CORE: BUILD ONE MONSTER (List + Variants)
# ============================================================
def build_one_monster(pid, local_monster, api_detail, suffix_map, api_index):
    """
    Build List entry and Variants entries for one parent monster.

    Returns: (list_entry, variants_dict)
      list_entry: dict for V2_DATA.List[pid]
      variants_dict: {child_id_str: variant_dict} for V2_DATA.Variants
    """
    variants_out = {}
    api_parent_id = local_key_to_api_parent(pid, api_index)

    # === Determine parent monster_name from API (for suffix stripping) ===
    api_children = api_detail.get("child", {}) if api_detail else {}
    parent_monster_name = ""
    base_child_id, base_child = find_base_child(api_children) if api_children else (None, None)
    if base_child:
        parent_monster_name = base_child.get("monster_name", "")

    # === Process each API child ===
    codex = api_detail.get("codex", "") if api_detail else ""

    for child_id_str, child_data in api_children.items():
        v_entry = {}

        # ---- _id, ParentId ----
        v_entry["_id"] = child_id_str
        v_entry["ParentId"] = int(pid) if pid.isdigit() else pid

        # ---- Suffix ----
        child_mname = child_data.get("monster_name", "")
        raw_suffix = compute_suffix(child_mname, parent_monster_name, suffix_map)
        v_entry["Suffix"] = cleanup_suffix(raw_suffix)

        # ---- MonsterName, Type, LocalLegend (API-only) ----
        v_entry["MonsterName"] = child_mname
        v_entry["Type"] = child_data.get("type") or "MONSTER_ORDINARY"
        v_entry["LocalLegend"] = bool(child_data.get("local_legend", False))

        # ---- HP / HPCurve (variants: API first, parent fallback) ----
        prop_list = child_data.get("prop", [])
        api_hp_curve = map_hp_curve(prop_list, codex)
        local_hpc = get_local_val(local_monster, "HPCurve")

        # Step 2: if parent curve is 7/20, force it
        if local_hpc in (7, 20):
            v_entry["HPCurve"] = local_hpc
        elif api_hp_curve == 0 and local_hpc is not None:
            # Step 3: API has no curve → fallback to parent
            v_entry["HPCurve"] = local_hpc
        else:
            v_entry["HPCurve"] = api_hp_curve

        # HP value: Step 1 API first, Step 3 parent fallback
        api_base = child_data.get("base", {})
        api_hp = api_base.get("hp")
        if api_hp is not None and api_hp > 0:
            v_entry["HP"] = normalize_hp(api_hp, v_entry["HPCurve"])
        else:
            v_entry["HP"] = get_local_val(local_monster, "HP")

        v_entry["HPCount"] = get_local_val(local_monster, "HPCount")

        # ---- ATK / ATKCurve (variants: API first, parent fallback) ----
        api_atk_curve = map_atk_curve(prop_list, codex)
        local_atc = get_local_val(local_monster, "ATKCurve")

        # Step 2: if parent curve is 40, force it
        if local_atc == 40:
            v_entry["ATKCurve"] = local_atc
        elif api_atk_curve == 0 and local_atc is not None:
            # Step 3: API has no curve → fallback to parent
            v_entry["ATKCurve"] = local_atc
        else:
            v_entry["ATKCurve"] = api_atk_curve

        # ATK value: Step 1 API first, Step 3 parent fallback
        api_atk = api_base.get("atk")
        if api_atk is not None and api_atk > 0:
            v_entry["ATK"] = normalize_atk(api_atk, v_entry["ATKCurve"])
        else:
            v_entry["ATK"] = get_local_val(local_monster, "ATK")

        v_entry["ATKCount"] = get_local_val(local_monster, "ATKCount")

        # RESBase: union of local parent RESBase + API sub_hurt ----
        local_resbase = get_local_val(local_monster, "RESBase", {})
        api_sub_hurt = child_data.get("sub_hurt", {})
        api_res_expanded = expand_sub_hurt(api_sub_hurt)

        resbase = {}
        for key in ALL_ELEMENT_KEYS:
            if local_resbase and key in local_resbase and local_resbase[key] is not None:
                resbase[key] = local_resbase[key]
            else:
                resbase[key] = api_res_expanded.get(key, 0.1)
        v_entry["RESBase"] = resbase

        # ---- Immune: from local only ----
        v_entry["Immune"] = get_local_val(local_monster, "Immune", [])

        # ---- Local-only fields ----
        for fld in VARIANT_LOCAL_FIELDS:
            v_entry[fld] = get_local_val(local_monster, fld)

        variants_out[child_id_str] = v_entry

    # === Build List entry (parent summary) ===
    list_entry = {}
    list_entry["_id"] = int(pid) if pid.isdigit() else pid

    for fld in PURELY_LOCAL_FIELDS:
        list_entry[fld] = get_local_val(local_monster, fld)

    # HP / HPCurve / HPCount / ATK / ATKCurve / ATKCount: API first, local fallback
    local_hp = get_local_val(local_monster, "HP")
    api_hp = None
    if base_child and base_child_id:
        api_hp = base_child.get("base", {}).get("hp")
    if api_hp is not None and api_hp > 0:
        api_hpc = map_hp_curve(base_child.get("prop", []), codex)
        list_entry["HP"] = normalize_hp(api_hp, api_hpc)
    else:
        list_entry["HP"] = local_hp

    local_hpc = get_local_val(local_monster, "HPCurve")
    if base_child:
        list_entry["HPCurve"] = map_hp_curve(base_child.get("prop", []), codex)
    else:
        list_entry["HPCurve"] = local_hpc

    local_hpcnt = get_local_val(local_monster, "HPCount")
    list_entry["HPCount"] = local_hpcnt

    local_atk = get_local_val(local_monster, "ATK")
    api_atk = None
    if base_child and base_child_id:
        api_atk = base_child.get("base", {}).get("atk")
    if api_atk is not None and api_atk > 0:
        api_atc = map_atk_curve(base_child.get("prop", []), codex)
        list_entry["ATK"] = normalize_atk(api_atk, api_atc)
    else:
        list_entry["ATK"] = local_atk

    local_atc = get_local_val(local_monster, "ATKCurve")
    if base_child:
        list_entry["ATKCurve"] = map_atk_curve(base_child.get("prop", []), codex)
    else:
        list_entry["ATKCurve"] = local_atc

    local_atkcnt = get_local_val(local_monster, "ATKCount")
    list_entry["ATKCount"] = local_atkcnt

    # RESBase: local first, API base child fallback
    local_resbase = get_local_val(local_monster, "RESBase")
    if local_resbase and isinstance(local_resbase, dict):
        list_entry["RESBase"] = dict(local_resbase)
    elif base_child:
        api_sub_hurt = base_child.get("sub_hurt", {})
        list_entry["RESBase"] = expand_sub_hurt(api_sub_hurt)
    else:
        list_entry["RESBase"] = {}

    # ParentId: from API mapping
    list_entry["ParentId"] = api_parent_id

    return list_entry, variants_out