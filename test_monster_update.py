"""
批量测试 update_single_monster - 验证 6 个新版本怪物
验证：每个更新成功 / 数据完好 / 旧数据不受影响 / 最终一致
"""
import json
import os
import shutil
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from reliance.update_v2_monster import update_single_monster

DATA_PATH = os.path.join(PROJECT_ROOT, "gi", "CH", "monster-v2-data.js")
BACKUP_PATH = DATA_PATH + ".backup"

TARGET_IDS = ["20090101", "25134601", "26310701", "26310801", "28021004", "28021603"]

# ---- 1. 备份 ----
print("=" * 65)
print("阶段1: 备份原数据")
print("=" * 65)
shutil.copy2(DATA_PATH, BACKUP_PATH)
print(f"  备份完成: {BACKUP_PATH}")
print()

# 读取原始数据
with open(DATA_PATH, "r", encoding="utf-8") as f:
    raw = f.read()
idx = raw.index("var V2_DATA = ")
json_start = raw.index("{", idx)
json_str = raw[json_start:].rstrip(";\n\r ")
base_data = json.loads(json_str)

base_list_keys = set(base_data.get("List", {}).keys())
base_variants_keys = set(base_data.get("Variants", {}).keys())
base_list_count = len(base_list_keys)
base_variants_count = len(base_variants_keys)
base_kingdoms = json.dumps(base_data.get("Kingdoms", []), sort_keys=True, ensure_ascii=False)
base_levelcurves = json.dumps(base_data.get("LevelCurves", {}), sort_keys=True, ensure_ascii=False)

print(f"  基准 List: {base_list_count}   Variants: {base_variants_count}")
print()

# ---- 2. 逐个更新 ----
results = {}
all_added_list = set()
all_added_variants = set()

for tid in TARGET_IDS:
    print("=" * 65)
    print(f"阶段2: 更新 {tid} ({TARGET_IDS.index(tid) + 1}/{len(TARGET_IDS)})")
    print("=" * 65)

    # 记录当前状态
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        raw = f.read()
    idx = raw.index("var V2_DATA = ")
    json_str = raw[raw.index("{", idx):].rstrip(";\n\r ")
    pre = json.loads(json_str)
    pre_list = set(pre.get("List", {}).keys())
    pre_variants = set(pre.get("Variants", {}).keys())

    success, message, output = update_single_monster(tid, force=True)

    # 记录更新后状态
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        raw = f.read()
    idx = raw.index("var V2_DATA = ")
    json_str = raw[raw.index("{", idx):].rstrip(";\n\r ")
    post = json.loads(json_str)
    post_list = set(post.get("List", {}).keys())
    post_variants = set(post.get("Variants", {}).keys())

    added_l = post_list - pre_list
    added_v = post_variants - pre_variants
    removed_l = pre_list - post_list
    removed_v = pre_variants - post_variants

    all_added_list |= added_l
    all_added_variants |= added_v

    results[tid] = {
        "success": success,
        "message": message,
        "added_list": added_l,
        "added_variants": added_v,
        "removed_list": removed_l,
        "removed_variants": removed_v,
    }

    status = "OK" if success else "FAIL"
    print(f"  [{status}] {message}")
    if added_l:
        for lk in sorted(added_l):
            e = post["List"][lk]
            print(f"         List +{lk}: {e.get('Name', '?')}  Icon={e.get('Icon', '?')}")
    if added_v:
        print(f"         Variants +{len(added_v)} 条")
    if removed_l:
        print(f"         [WARN] List 丢失: {removed_l}")
    if removed_v:
        print(f"         [WARN] Variants 丢失: {removed_v}")
    print()

# ---- 3. 最终完整性验证 ----
print("=" * 65)
print("阶段3: 最终完整性验证")
print("=" * 65)

with open(DATA_PATH, "r", encoding="utf-8") as f:
    raw = f.read()
idx = raw.index("var V2_DATA = ")
json_str = raw[raw.index("{", idx):].rstrip(";\n\r ")
final_data = json.loads(json_str)

final_list_keys = set(final_data.get("List", {}).keys())
final_variants_keys = set(final_data.get("Variants", {}).keys())

all_pass = True

# 3a. 无旧数据丢失
lost_list = base_list_keys - final_list_keys
lost_variants = base_variants_keys - final_variants_keys
if lost_list:
    print(f"  [FAIL] 旧 List 丢失 {len(lost_list)}: {sorted(lost_list)[:10]}")
    all_pass = False
else:
    print(f"  [OK]   旧 List 无丢失 ({base_list_count} -> {len(final_list_keys)})")

if lost_variants:
    print(f"  [FAIL] 旧 Variants 丢失 {len(lost_variants)}: {sorted(lost_variants)[:10]}")
    all_pass = False
else:
    print(f"  [OK]   旧 Variants 无丢失 ({base_variants_count} -> {len(final_variants_keys)})")

# 3b. 旧数据无意外修改
changed_list = 0
for key in base_list_keys & final_list_keys:
    if base_data["List"][key] != final_data["List"][key]:
        changed_list += 1
print(f"  {'[OK]' if changed_list == 0 else '[WARN]'}   旧 List 变更 {changed_list} 条" + (" (无)" if changed_list == 0 else ""))

changed_variants = 0
for key in base_variants_keys & final_variants_keys:
    if base_data["Variants"][key] != final_data["Variants"][key]:
        changed_variants += 1
print(f"  {'[OK]' if changed_variants == 0 else '[WARN]'}   旧 Variants 变更 {changed_variants} 条" + (" (无)" if changed_variants == 0 else ""))

# 3c. Kingdoms / LevelCurves 不变
final_kingdoms = json.dumps(final_data.get("Kingdoms", []), sort_keys=True, ensure_ascii=False)
final_levelcurves = json.dumps(final_data.get("LevelCurves", {}), sort_keys=True, ensure_ascii=False)
if final_kingdoms == base_kingdoms:
    print(f"  [OK]   Kingdoms 不变")
else:
    print(f"  [WARN] Kingdoms 被修改!")
    all_pass = False
if final_levelcurves == base_levelcurves:
    print(f"  [OK]   LevelCurves 不变")
else:
    print(f"  [WARN] LevelCurves 被修改!")
    all_pass = False

# 3d. 所有目标 ID 都在 List 中
print()
for tid in TARGET_IDS:
    r = results[tid]
    in_list = any(tid in k or str(k).endswith(tid[-5:]) for k in final_list_keys)
    status = "OK" if r["success"] else "FAIL"
    print(f"  [{status}] {tid:>12}  success={r['success']:5}  in_List={in_list}  +{len(r['added_variants'])}v")

# 3e. 新增条目字段完整性
print()
print("--- 新增 List 条目字段检查 ---")
required_fields = ["Name", "Icon", "_id", "Title"]
for lk in sorted(all_added_list, key=str):
    e = final_data["List"][lk]
    missing = [f for f in required_fields if not e.get(f)]
    hp_ok = e.get("HP") is not None
    atk_ok = e.get("ATK") is not None
    extra = "" if hp_ok and atk_ok else " (HP/ATK null - animal/object)"
    if missing:
        print(f"  [WARN] {lk}: 缺失字段 {missing}")
        all_pass = False
    else:
        print(f"  [OK]   {lk}: {e.get('Name', '?')}  HP={e.get('HP')}  ATK={e.get('ATK')}{extra}")

# 3f. 新增 Variants 字段完整性
print()
print("--- 新增 Variants 条目字段检查 ---")
variant_req = ["_id", "ParentId", "MonsterName", "HPCurve", "ATKCurve"]
bad_variants = 0
for vk in sorted(all_added_variants, key=str):
    v = final_data["Variants"][vk]
    missing = [f for f in variant_req if v.get(f) is None]
    hp_ok = v.get("HP") is not None
    atk_ok = v.get("ATK") is not None
    if missing or not hp_ok or not atk_ok:
        bad_variants += 1
        if bad_variants <= 5:
            print(f"  [WARN] {vk}: MonsterName={v.get('MonsterName')} HP={v.get('HP')} ATK={v.get('ATK')} Curves=({v.get('HPCurve')},{v.get('ATKCurve')})")
if bad_variants == 0:
    print(f"  [OK]   所有新增 Variants 字段完整 ({len(all_added_variants)} 条)")
else:
    print(f"  [WARN] {bad_variants}/{len(all_added_variants)} Variants 字段不完整")

print()
print("=" * 65)
print("总结")
print("=" * 65)
total_success = sum(1 for r in results.values() if r["success"])
print(f"  更新成功: {total_success}/{len(TARGET_IDS)}")
print(f"  List 增长: {base_list_count} -> {len(final_list_keys)} (+{len(final_list_keys) - base_list_count})")
print(f"  Variants 增长: {base_variants_count} -> {len(final_variants_keys)} (+{len(final_variants_keys) - base_variants_count})")
if all_pass and total_success == len(TARGET_IDS):
    print(f"  结论: [PASS] 所有更新成功，数据完整，旧数据无影响")
else:
    print(f"  结论: [CHECK] 存在问题，请检查上方输出")

print()
print(f"  备份文件: {BACKUP_PATH}")
print("  回滚命令: copy gi\\CH\\monster-v2-data.js.backup gi\\CH\\monster-v2-data.js")