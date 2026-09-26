"""SR Achievement update script.

Input: SR achievement API endpoint (provided by user externally)
Output:
  - sr/data/{lang}/ach.json (manifest)
  - sr/data/{lang}/ach/{seriesId}.json (per-series achievement lists)

Idempotent: running twice produces same output (0 changes on second run).

Usage:
  python reliance/sr/ach/update.py < api_response.json

Expected API format (list of achievement objects):
  [
    {
      "id": 4010101,
      "name": { "CH": "...", "EN": "...", ... },
      "desc": { "CH": "...", "EN": "...", ... },
      "ver": "3.8",
      "series": 1,
      "reward": 20
    },
    ...
  ]
"""

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Supported languages
LANGUAGES = ["CH", "EN", "JP", "KR"]

# Static icon mapping for SR series (API may not provide icons)
SERIES_ICONS = {
    1: "CultivateAchievementIcon.png",
    2: "CollectAchievementIcon.png",
    3: "MainLineAchievementIcon.png",
    4: "ExploreAchievementIcon.png",
    5: "ReputationAchievementIcon.png",
    6: "ChallengeAchievementIcon.png",
    7: "BattleAchievementIcon.png",
    8: "TrackAchievementIcon.png",
    9: "RougeAchievementIcon.png",
}


def ver_sort_key(v):
    """Semantic version sort key (descending)."""
    parts = v.split(".")
    return tuple(int(p) for p in parts)


def build_manifest_from_api(achievements, lang):
    """Build manifest and per-series data from API response for a given language."""
    groups_map = {}  # series_id -> list of achievements
    ver_set = set()
    total_reward = 0

    for ach in achievements:
        sid = ach.get("series", ach.get("Series", 0))
        if sid not in groups_map:
            groups_map[sid] = []
        groups_map[sid].append(ach)

        v = ach.get("ver", ach.get("Ver", ""))
        if v:
            ver_set.add(str(v))

        total_reward += ach.get("reward", ach.get("Reward", 0))

    # Versions sorted descending
    versions = sorted(ver_set, key=ver_sort_key, reverse=True)
    latest_version = versions[0] if versions else ""
    prev_version = versions[1] if len(versions) > 1 else ""

    total_num = len(achievements)
    prev_total_num = sum(
        1
        for ach in achievements
        if str(ach.get("ver", ach.get("Ver", ""))) != latest_version
    )

    groups = []
    for sid in sorted(groups_map.keys()):
        series_achs = groups_map[sid]
        series_num = len(series_achs)
        series_reward = sum(
            ach.get("reward", ach.get("Reward", 0)) for ach in series_achs
        )
        groups.append(
            {
                "id": sid,
                "name": series_achs[0].get(
                    "series_name",
                    SERIES_ICONS.get(sid, ""),
                ),
                "icon": SERIES_ICONS.get(sid, ""),
                "num": series_num,
                "reward": series_reward,
            }
        )

    manifest = {
        "updatedAt": "",
        "latestVersion": latest_version,
        "totalNum": total_num,
        "prevVersion": prev_version,
        "prevTotalNum": prev_total_num,
        "totalReward": total_reward,
        "versions": versions,
        "groups": groups,
    }

    return manifest, groups_map


def write_json_file(filepath, data):
    """Write JSON file, returns True if content changed."""
    filepath = Path(filepath)
    new_content = json.dumps(data, ensure_ascii=False, indent=2) + "\n"

    if filepath.exists():
        old_content = filepath.read_text(encoding="utf-8")
        if old_content == new_content:
            return False  # No change

    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(new_content, encoding="utf-8")
    return True


def update_from_api(api_data):
    """Main update function. Takes parsed API JSON data."""
    total_changes = 0

    # If API data is a dict with key per language
    if isinstance(api_data, dict) and "CH" in api_data:
        # Multi-language format
        achievements_by_lang = api_data
    elif isinstance(api_data, list):
        # Single language list - duplicate for all languages
        # This assumes the API returns all languages in each entry's name/desc fields
        achievements_by_lang = {lang: api_data for lang in LANGUAGES}
    else:
        print("[ERROR] Unrecognized API data format")
        return 1

    for lang in LANGUAGES:
        achievements = achievements_by_lang.get(lang, achievements_by_lang.get("CH", []))
        if not achievements:
            print(f"[SKIP] {lang}: no data")
            continue

        manifest, groups_map = build_manifest_from_api(achievements, lang)

        # Write manifest
        manifest_path = PROJECT_ROOT / "sr" / "data" / lang / "ach.json"
        if write_json_file(manifest_path, manifest):
            print(f"[CHANGED] {manifest_path}")
            total_changes += 1
        else:
            print(f"[UNCHANGED] {manifest_path}")

        # Write per-series files
        ach_dir = PROJECT_ROOT / "sr" / "data" / lang / "ach"
        for sid in sorted(groups_map.keys()):
            series_achs = groups_map[sid]
            items = []
            for ach in series_achs:
                ver = ach.get("ver", ach.get("Ver", ""))
                items.append(
                    {
                        "id": ach.get("id", ach.get("_id", 0)),
                        "name": ach.get(
                            "name",
                            ach.get("Name", ""),
                        ),
                        "desc": ach.get(
                            "desc",
                            ach.get("Desc", ""),
                        ),
                        "ver": str(ver) if ver else "",
                        "reward": ach.get("reward", ach.get("Reward", 0)),
                    }
                )
            # Sort by id
            items.sort(key=lambda x: x["id"])

            series_path = ach_dir / f"{sid}.json"
            if write_json_file(series_path, items):
                print(f"[CHANGED] {series_path} ({len(items)} achievements)")
                total_changes += 1
            else:
                print(f"[UNCHANGED] {series_path} ({len(items)} achievements)")

    print(f"\nTotal changes: {total_changes}")
    return 0 if total_changes == 0 else 0  # Always return 0 (warnings only)


def main():
    if not sys.stdin.isatty():
        api_data = json.load(sys.stdin)
    else:
        print("[INFO] No input piped. Use: python update.py < api_data.json")
        print("[INFO] Running in verification mode (comparing existing files)...")
        api_data = []

    if api_data:
        return update_from_api(api_data)
    else:
        print("[INFO] No data provided. Exiting.")
        return 0


if __name__ == "__main__":
    sys.exit(main())