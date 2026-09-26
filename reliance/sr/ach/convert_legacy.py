"""Convert legacy Achievement.js to new JSON format.

Reads the old JS file and generates:
  - sr/data/{lang}/ach.json (manifest)
  - sr/data/{lang}/ach/{seriesId}.json (per-series achievement lists)

Usage:
  python reliance/sr/ach/convert_legacy.py
"""

import json
import os
import re
import sys
from pathlib import Path

# Project root (assumes script is at reliance/sr/ach/convert_legacy.py)
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Known languages for SR (only CH has Achievement.js currently)
LANGUAGES = ["CH"]


def parse_js_var(text: str, var_name: str):
    """Extract a JS variable value from text using bracket counting.
    Handles nested arrays and objects correctly."""
    # Find the variable assignment
    pattern = rf'var {var_name}\s*=\s*'
    m = re.search(pattern, text)
    if not m:
        return None
    
    start = m.end()
    if start >= len(text):
        return None
    
    first_char = text[start]
    if first_char == '[':
        close = ']'
    elif first_char == '{':
        close = '}'
    else:
        # Simple literal - read until end of line or ;
        end = start
        while end < len(text) and text[end] not in (';', '\n', '\r'):
            end += 1
        return text[start:end].strip()
    
    # Bracket counting
    depth = 0
    in_string = False
    string_char = None
    i = start
    while i < len(text):
        ch = text[i]
        if in_string:
            if ch == string_char and (i == 0 or text[i-1] != '\\'):
                in_string = False
        else:
            if ch in ('"', "'"):
                in_string = True
                string_char = ch
            elif ch == first_char:
                depth += 1
            elif ch == close:
                depth -= 1
                if depth == 0:
                    # Include optional semicolon
                    end = i + 1
                    while end < len(text) and text[end] in (' ', '\t', ';'):
                        end += 1
                    return text[start:end]
        i += 1
    
    return None


def clean_js_value(s: str):
    """Convert a JS value string to a Python object by cleaning JS-specific syntax.
    Replaces trailing commas, converts float-like versions to strings where needed."""
    # Remove trailing commas before closing brackets/braces
    s = re.sub(r',\s*(\]|\})', r'\1', s)
    # Parse as JSON
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    # Try replacing single quotes with double quotes
    s2 = s.replace("'", '"')
    try:
        return json.loads(s2)
    except json.JSONDecodeError:
        pass
    # Try handling hex numbers
    s3 = re.sub(r'0x[0-9a-fA-F]+', lambda m: str(int(m.group(0), 16)), s)
    try:
        return json.loads(s3)
    except json.JSONDecodeError:
        pass
    return None


def load_legacy_data(lang3: str):
    """Load legacy Achievement.js data for a given language."""
    js_path = PROJECT_ROOT / 'sr' / 'data' / lang3 / 'Achievement.js'
    if not js_path.exists():
        print(f"[WARN] Legacy data not found: {js_path}")
        return None
    
    text = js_path.read_text(encoding='utf-8')
    
    # Extract each variable
    data = {}
    for var_name in ['_achievementdata', '_achievementvers', '_achievement', '_option', '_achievementseries']:
        raw = parse_js_var(text, var_name)
        if raw is None:
            print(f"[ERROR] Could not find variable {var_name} in {js_path}")
            return None
        val = clean_js_value(raw)
        if val is None:
            print(f"[ERROR] Could not parse variable {var_name}")
            print(f"  Raw snippet: {raw[:200]}...")
            return None
        data[var_name] = val
    
    return data


def build_manifest(achievement, achievementseries, achievementvers):
    """Build the ach.json manifest from legacy data."""
    # Calculate versions from actual achievement data
    ver_set = set()
    for ach in achievement:
        v = ach.get('Ver')
        if v is not None and v != '':
            ver_set.add(str(v) if not isinstance(v, str) else v)
    
    # Semantic version sort (descending)
    def ver_key(v):
        parts = v.split('.')
        return tuple(int(p) for p in parts)
    
    versions = sorted(ver_set, key=ver_key, reverse=True)
    
    latest_version = versions[0] if versions else ''
    prev_version = versions[1] if len(versions) > 1 else ''
    
    total_num = len(achievement)
    prev_total_num = sum(1 for ach in achievement if str(ach.get('Ver', '')) != latest_version)
    total_reward = sum(ach.get('Reward', 0) for ach in achievement)
    
    # Build groups from achievementseries
    groups = []
    for series in achievementseries:
        sid = series['_id']
        series_achs = [ach for ach in achievement if ach.get('Series') == sid]
        groups.append({
            'id': sid,
            'name': series['Name'],
            'icon': series['Icon'],
            'num': len(series_achs),
            'reward': sum(ach.get('Reward', 0) for ach in series_achs)
        })
    
    manifest = {
        'updatedAt': '',  # Will be filled by update script
        'latestVersion': latest_version,
        'totalNum': total_num,
        'prevVersion': prev_version,
        'prevTotalNum': prev_total_num,
        'totalReward': total_reward,
        'versions': versions,
        'groups': groups
    }
    
    return manifest


def build_series_data(achievement, series_id):
    """Build per-series achievement list."""
    items = []
    for ach in achievement:
        if ach.get('Series') == series_id:
            ver = ach.get('Ver')
            items.append({
                'id': ach['_id'],
                'name': ach['Name'],
                'desc': ach['Desc'],
                'ver': str(ver) if not isinstance(ver, str) else ver,
                'reward': ach.get('Reward', 0)
            })
    # Sort by id
    items.sort(key=lambda x: x['id'])
    return items


def validate_achievement(achievement):
    """Validate achievement data integrity."""
    ids = [ach['_id'] for ach in achievement]
    if len(ids) != len(set(ids)):
        print("[WARN] Duplicate achievement IDs found!")
    
    # Verify Series values match expected range
    series_ids = set(ach.get('Series') for ach in achievement)
    print(f"  Series IDs in data: {sorted(series_ids)}")


def convert_language(lang3: str):
    """Convert legacy data for one language."""
    print(f"\n{'='*60}")
    print(f"Converting: sr/data/{lang3}/")
    print(f"{'='*60}")

    data = load_legacy_data(lang3)
    if data is None:
        return False

    achievement = data['_achievement']
    achievementseries = data['_achievementseries']
    achievementvers = data['_achievementvers']

    print(f"  Achievements loaded: {len(achievement)}")
    print(f"  Series loaded: {len(achievementseries)}")

    # Validate
    validate_achievement(achievement)

    # Verify series count
    if len(achievementseries) != 9:
        print(f"[WARN] Expected 9 series, found {len(achievementseries)}")

    # Verify icons
    for s in achievementseries:
        icon = s.get('Icon', '')
        if not icon:
            print(f"[WARN] Series {s['_id']} ({s['Name']}) has empty icon")
        else:
            icon_path = PROJECT_ROOT / 'images' / 'Achievement' / icon
            if not icon_path.exists():
                print(f"[WARN] Icon file not found: {icon_path}")

    # Build manifest
    manifest = build_manifest(achievement, achievementseries, achievementvers)

    # Verify manifest numbers match expected
    expected_total = sum(g['num'] for g in manifest['groups'])
    if expected_total != manifest['totalNum']:
        print(f"[ERROR] Group num sum ({expected_total}) != totalNum ({manifest['totalNum']})")
        return False

    print(f"  Manifest: totalNum={manifest['totalNum']}, "
          f"latestVersion={manifest['latestVersion']}, "
          f"prevTotalNum={manifest['prevTotalNum']}, "
          f"totalReward={manifest['totalReward']}")

    # Create output directories
    ach_dir = PROJECT_ROOT / 'sr' / 'data' / lang3 / 'ach'
    ach_dir.mkdir(parents=True, exist_ok=True)

    # Write manifest
    manifest_path = PROJECT_ROOT / 'sr' / 'data' / lang3 / 'ach.json'
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"  Wrote: {manifest_path}")

    # Write per-series files
    for series in achievementseries:
        sid = series['_id']
        series_data = build_series_data(achievement, sid)
        series_path = ach_dir / f'{sid}.json'
        with open(series_path, 'w', encoding='utf-8') as f:
            json.dump(series_data, f, ensure_ascii=False, indent=2)
        print(f"  Wrote: {series_path} ({len(series_data)} achievements)")

    return True


def main():
    print("Legacy Achievement.js to JSON Converter")
    print("=======================================")
    
    success = True
    for lang3 in LANGUAGES:
        if not convert_language(lang3):
            success = False
    
    if success:
        print(f"\n{'='*60}")
        print("All conversions completed successfully!")
        print(f"{'='*60}")
    else:
        print(f"\n{'='*60}")
        print("Some conversions failed. Check errors above.")
        print(f"{'='*60}")
        sys.exit(1)


if __name__ == '__main__':
    main()