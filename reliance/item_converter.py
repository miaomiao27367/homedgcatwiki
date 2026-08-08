#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
item_converter.py - 根据API数据补全/转换本地Item.js
=====================================================
用法:
  python item_converter.py                  # 补全missing_ids.txt中的所有ID
  python item_converter.py --all            # 包含"..."占位名
  python item_converter.py 110281 110282    # 补全指定ID
  python item_converter.py --dry            # 仅预览，不写入文件

数据来源:
  item_all.json: https://static.nanoka.cc/hsr/{ver}/{lang}/item_all.json
  (完整字段: Desc/Story/Src/Icon/Pic)
  item.json:      https://static.nanoka.cc/hsr/{ver}/{lang}/item.json
  (精简字段: 仅基础信息)

映射关系:
  API字段                  本地字段    转换方式
  ──────────────────────────────────────────────────
  id                       _id         直接
  item_name                Name        直接
  item_desc                Desc        直接
  item_bg_desc             Story       \n -> <br>
  item_icon_path           Icon        取文件名
  item_figure_icon_path    Pic         取文件名
  item_comefrom[].desc     Src         拼接
  purpose_type             Type        查PURPOSE_TYPE_MAP
  rarity                   Rarity      查RARITY_MAP

  RARITY_MAP:        Normal->1  NotNormal->2  Rare->3  VeryRare->4  SuperRare->5
  PURPOSE_TYPE_MAP:  1~7->3(培养素材)  8,9,11,12,13->1(货币)  10->7(消耗品)
                     14->10(贵重物)  16->5(任务道具)  17->4(合成素材)
                     19->11(配方)  21->12(读物)
"""

import json
import os
import sys
import re
import io
import requests
from pathlib import Path
from PIL import Image
from typing import Dict, Any, Optional, List, Tuple

# ============================================================
#  配置区
# ============================================================

API_VERSION = "4.4.54"
LANG = "zh"
API_URL = f"https://static.nanoka.cc/hsr/{API_VERSION}/{LANG}/item_all.json"
CACHE_DIR = "tempdata"
LOCAL_ITEM_PATH = "sr/data/CH/Item.js"
MISSING_IDS_PATH = r"missing_ids.txt"
BACKUP_PATH = r"Item.js.bak"

# ----------------------------------------------------------
#  Rarity映射: API -> 本地Rarity数值
#  ⚠️ Normal=灰底1星, NotNormal=绿底2星
# ----------------------------------------------------------
RARITY_MAP = {
    "Normal": 1,
    "NotNormal": 2,
    "Rare": 3,
    "VeryRare": 4,
    "SuperRare": 5,
}

# ----------------------------------------------------------
#  purpose_type -> Type 映射
# ----------------------------------------------------------
PURPOSE_TYPE_MAP = {
    # 1~7: 培养素材
    1: 3, 2: 3, 3: 3, 4: 3, 5: 3, 6: 3, 7: 3,
    # 8,9,11,12,13: 货币
    8: 1, 9: 1, 11: 1, 12: 1, 13: 1,
    # 10: 消耗品
    10: 7,
    # 14: 贵重物
    14: 10,
    # 16: 任务道具
    16: 5,
    # 17: 合成素材
    17: 4,
    # 19: 配方
    19: 11,
    # 21: 读物
    21: 12,
}

# ----------------------------------------------------------
#  Type编号 -> 显示名称
# ----------------------------------------------------------
TYPE_NAMES = {
    1: "货币", 2: "头像", 3: "培养素材", 4: "合成素材",
    5: "任务道具", 6: "礼包", 7: "消耗品", 8: "宠物",
    9: "对话框", 10: "贵重物", 11: "配方", 12: "读物", 13: "其他",
}

# 确保缓存目录存在
os.makedirs(CACHE_DIR, exist_ok=True)


# ============================================================
#  数据加载
# ============================================================

def load_api_data() -> Dict[str, Any]:
    """从API下载item_all.json，优先使用本地缓存"""
    cache_file = os.path.join(CACHE_DIR, f"item_all_{API_VERSION}_{LANG}.json")

    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"从缓存加载API数据: {len(data)}条")
        return data

    print(f"正在下载: {API_URL}")
    try:
        resp = requests.get(API_URL, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"下载成功并缓存: {len(data)}条")
        return data
    except Exception as e:
        print(f"下载失败: {e}")
        sys.exit(1)


def load_local_items() -> Tuple[Dict, str]:
    """读取本地Item.js，返回(数据字典, 原始文件内容)"""
    with open(LOCAL_ITEM_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    m = re.search(r"var _item = (\{[\s\S]*?\});\s*\n", content)
    if not m:
        raise ValueError("无法解析Item.js中的_item变量")
    local = eval(m.group(1))
    return local, content


def read_missing_ids(filepath: str = MISSING_IDS_PATH) -> List[str]:
    """从missing_ids.txt读取ID列表"""
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        ids = re.findall(r"\d+", f.read())
    return ids


# ============================================================
#  数据转换
# ============================================================

def guess_version(item_id: str, local_items: Dict) -> str:
    """根据附近已存在道具的Ver推断版本号"""
    target_prefix = item_id[:3]
    candidates = []
    for lid, item in local_items.items():
        if str(lid)[:3] == target_prefix and item.get("Ver") and item["Ver"] != "1.x":
            candidates.append((abs(int(lid) - int(item_id)), item["Ver"]))
    if candidates:
        candidates.sort()
        return candidates[0][1]
    return "4.0"


def convert_item(api_item: Dict, local_items: Dict) -> Optional[Dict]:
    """将单条API数据转换为本地Item.js格式"""
    item_id = str(api_item.get("id", ""))

    # 提取Icon/Pic文件名
    icon_path = api_item.get("item_icon_path", "")
    figure_path = api_item.get("item_figure_icon_path", "")
    icon = Path(icon_path).name if icon_path else ""
    pic = Path(figure_path).name if figure_path else icon

    # 处理Story换行
    story = api_item.get("item_bg_desc", "")
    if story:
        story = story.replace("\\n", "<br>").replace("\n", "<br>")

    # 处理来源
    comefrom = api_item.get("item_comefrom", [])
    if comefrom:
        src = ", ".join(c.get("desc", "") for c in comefrom if c.get("desc"))
    else:
        src = ""

    # 确定Type
    purpose = api_item.get("purpose_type", 0)
    item_type = PURPOSE_TYPE_MAP.get(purpose, 13)

    # 确定Rarity
    rarity_str = api_item.get("rarity", "Normal")
    rarity = RARITY_MAP.get(rarity_str, 1)

    return {
        "_id": int(item_id),
        "Type": item_type,
        "Rarity": rarity,
        "Name": api_item.get("item_name", ""),
        "Desc": api_item.get("item_desc", ""),
        "Story": story,
        "Icon": icon,
        "Pic": pic or icon,
        "Src": src,
        "Ver": guess_version(item_id, local_items),
    }


# ============================================================
#  输出生成
# ============================================================

def format_item_entry(item: Dict) -> str:
    """格式化为Item.js中的单条记录"""
    return (
        f'    "{item["_id"]}": {{\n'
        f'        "_id": {item["_id"]},\n'
        f'        "Type": {item["Type"]},\n'
        f'        "Rarity": {item["Rarity"]},\n'
        f'        "Name": {json.dumps(item["Name"], ensure_ascii=False)},\n'
        f'        "Desc": {json.dumps(item["Desc"], ensure_ascii=False)},\n'
        f'        "Story": {json.dumps(item["Story"], ensure_ascii=False)},\n'
        f'        "Icon": {json.dumps(item["Icon"], ensure_ascii=False)},\n'
        f'        "Pic": {json.dumps(item["Pic"], ensure_ascii=False)},\n'
        f'        "Src": {json.dumps(item["Src"], ensure_ascii=False)},\n'
        f'        "Ver": {json.dumps(item["Ver"], ensure_ascii=False)}\n'
        f'    }}'
    )


def insert_into_item_js(content: str, entries: List[str]) -> str:
    """将新条目插入到Item.js的最后一个}之前"""
    last_brace = content.rfind("}")
    return content[:last_brace] + ",\n" + ",\n".join(entries) + "\n" + content[last_brace:]


# ============================================================
#  主流程
# ============================================================

def main():
    args = sys.argv[1:]
    is_dry = "--dry" in args
    include_dots = "--all" in args
    target_ids = [a for a in args if not a.startswith("--") and a.isdigit()]

    # 解析 --ver 参数
    ver = "4.0"
    for i, a in enumerate(args):
        if a == "--ver" and i + 1 < len(args):
            ver = args[i + 1]
            break

    # 如果没有指定ID，从missing_ids.txt读取
    if not target_ids:
        target_ids = read_missing_ids()
        if not target_ids:
            print("未找到missing_ids.txt，也没有指定ID")
            print("用法: python item_converter.py [ID...] [--all] [--dry]")
            sys.exit(1)

    print(f"{'='*50}")
    print(f"item_converter.py")
    print(f"目标ID: {len(target_ids)}个")
    print(f"{'='*50}")

    # 加载数据
    api_data = load_api_data()
    local_items, local_content = load_local_items()

    # 转换
    new_items = []
    skipped = []

    for tid in target_ids:
        if tid in local_items:
            skipped.append((tid, "本地已存在"))
            continue

        if tid not in api_data:
            skipped.append((tid, "API中未找到"))
            continue

        api_item = api_data[tid]
        name = api_item.get("item_name", "")

        if name == "..." and not include_dots:
            skipped.append((tid, f"占位名(...)，用--all强制包含"))
            continue

        item = convert_item(api_item, local_items)
        if item is None:
            skipped.append((tid, "转换失败"))
            continue

        item["Ver"] = ver  # 使用手动输入的Ver

        new_items.append(item)

    # 按类型分组统计
    by_type = {}
    for item in new_items:
        tn = TYPE_NAMES.get(item["Type"], f"Type{item['Type']}")
        by_type.setdefault(tn, []).append(item)

    print(f"\n新增: {len(new_items)} | 跳过: {len(skipped)}")
    if include_dots:
        print("(包含...占位名)")
    print()

    if by_type:
        print("按类型分布:")
        for tn, items in sorted(by_type.items()):
            print(f"  {tn}: {len(items)}个")

    # 预览
    if new_items:
        print(f"\n--- 预览 (前10个) ---")
        for item in new_items[:10]:
            tn = TYPE_NAMES.get(item["Type"], f"Type{item['Type']}")
            print(f"  [{item['_id']}] {item['Name']} | {tn} | R{item['Rarity']} | {item['Ver']}")
        if len(new_items) > 10:
            print(f"  ... 还有{len(new_items) - 10}个")

    if skipped:
        print(f"\n--- 跳过 ({len(skipped)}) ---")
        for tid, reason in skipped:
            print(f"  {tid}: {reason}")

    if is_dry:
        print("\n[dry模式] 未写入文件")
        return

    if not new_items:
        print("\n无新道具需要添加")
        return

    # 生成条目并插入
    entries = [format_item_entry(item) for item in new_items]
    new_content = insert_into_item_js(local_content, entries)

    # 备份
    with open(BACKUP_PATH, "w", encoding="utf-8") as f:
        f.write(local_content)
    print(f"\n已备份: {BACKUP_PATH}")

    # 写入
    with open(LOCAL_ITEM_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"已写入: {LOCAL_ITEM_PATH} (+{len(new_items)}个)")

    # 验证
    try:
        with open(LOCAL_ITEM_PATH, "r", encoding="utf-8") as f:
            verify = f.read()
        m = re.search(r"var _item = (\{[\s\S]*?\});\s*\n", verify)
        if m:
            eval(m.group(1))
            print("语法验证: OK")
    except Exception as e:
        print(f"语法验证: FAILED - {e}")


# ============================================================
#  generate_avatar_items - 生成简化版道具数据（仅Name+Icon）
#  用于Avatar.js等只需要名称和图标的场景
# ============================================================

def generate_avatar_items(
    ids: List[int],
    api_version: str = API_VERSION,
    lang: str = LANG,
    img_save_dir: str = "images/itemicon",
    output_file: str = None,
) -> Dict[str, Dict[str, str]]:
    """
    根据ID列表生成 {id: {Name, Icon}} 格式的简化数据，并下载图标

    Args:
        ids: 物品ID列表
        api_version: API版本号
        lang: 语言 (zh/en)
        img_save_dir: 图标保存目录
        output_file: 输出的JS文件路径

    Returns:
        {"ID": {"Name": "...", "Icon": "itemicon/ID.png"}, ...}
    """
    url = f"https://static.nanoka.cc/hsr/{api_version}/{lang}/item_all.json"
    print(f"正在拉取: {url}")

    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    item_all = resp.json()
    print(f"已加载 {len(item_all)} 条")

    Path(img_save_dir).mkdir(parents=True, exist_ok=True)
    img_url_template = "https://static.nanoka.cc/assets/hsr/itemfigures/{}.webp"

    result = {}
    success = 0
    failed = []

    for item_id in ids:
        key = str(item_id)
        if key not in item_all:
            print(f"  ⚠ ID {item_id} 未找到，跳过")
            failed.append(item_id)
            continue

        data = item_all[key]
        name = data.get("item_name", "")

        icon_raw = data.get("item_icon_path", "")
        icon_name = Path(icon_raw).name if icon_raw else f"{item_id}.png"
        stem = Path(icon_name).stem
        icon_name = f"{stem}.png"

        result[key] = {
            "Name": name,
            "Icon": f"itemicon/{icon_name}",
        }

        save_path = os.path.join(img_save_dir, icon_name)
        if not os.path.exists(save_path):
            try:
                img_resp = requests.get(img_url_template.format(item_id), timeout=15)
                img_resp.raise_for_status()
                with open(save_path, "wb") as f:
                    f.write(img_resp.content)
                print(f"  ✓ [{item_id}] {name}")
                success += 1
            except Exception as e:
                print(f"  ✗ [{item_id}] 下载失败: {e}")
                failed.append(item_id)
        else:
            print(f"  • [{item_id}] {name} (已存在)")

    # 生成JS
    js = ["// Auto Generated", "", "var _item = {"]
    sorted_keys = sorted(result.keys(), key=int)
    for i, k in enumerate(sorted_keys):
        entry = json.dumps(result[k], ensure_ascii=False)
        comma = "," if i < len(sorted_keys) - 1 else ""
        js.append(f'    "{k}": {entry}{comma}')
    js.append("};")

    if output_file:
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(js))
        print(f"\n已写入: {output_file}")

    print(f"\n完成: {len(result)}条, 下载图标{success}个, 失败{len(failed)}个")
    return result


# ============================================================
#  generate_item_data - server.py 调用的包装函数
# ============================================================

def generate_item_data(item_ids: List[str], version: str = API_VERSION,
                       ver: str = "4.0", include_dots: bool = False,
                       auto_merge: bool = True) -> str:
    """
    供 server.py 调用：根据ID列表从API获取数据并转换为Item.js格式

    Args:
        item_ids: 物品ID列表
        version: API版本号
        ver: 手动指定的Ver字段值（API不含此字段）
        include_dots: 是否包含"..."占位名
        auto_merge: 是否自动写入Item.js

    Returns:
        处理结果字符串
    """
    import io
    output = io.StringIO()

    global API_VERSION
    API_VERSION = version

    api_url = f"https://static.nanoka.cc/hsr/{version}/{LANG}/item_all.json"
    cache_file = os.path.join(CACHE_DIR, f"item_all_{version}_{LANG}.json")

    # 加载API数据
    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            api_data = json.load(f)
        print(f"从缓存加载: {len(api_data)}条", file=output)
    else:
        try:
            resp = requests.get(api_url, timeout=30)
            resp.raise_for_status()
            api_data = resp.json()
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(api_data, f, ensure_ascii=False, indent=2)
            print(f"下载成功: {len(api_data)}条", file=output)
        except Exception as e:
            return f"下载API数据失败: {e}"

    # 加载本地数据
    local_items, local_content = load_local_items()

    new_items = []
    skipped = []

    for tid in item_ids:
        if tid in local_items:
            skipped.append((tid, "本地已存在"))
            continue

        if tid not in api_data:
            skipped.append((tid, "API中未找到"))
            continue

        api_item = api_data[tid]
        name = api_item.get("item_name", "")

        if name == "..." and not include_dots:
            skipped.append((tid, "占位名(...)"))
            continue

        item = convert_item(api_item, local_items)
        if item is None:
            skipped.append((tid, "转换失败"))
            continue

        item["Ver"] = ver  # 使用手动输入的Ver

        new_items.append(item)

    print(f"\n新增: {len(new_items)} | 跳过: {len(skipped)}", file=output)

    # 按类型分组
    by_type = {}
    for item in new_items:
        tn = TYPE_NAMES.get(item["Type"], f"Type{item['Type']}")
        by_type.setdefault(tn, []).append(item)

    for tn, items in sorted(by_type.items()):
        print(f"  {tn}: {len(items)}个", file=output)
        for item in items:
            print(f"    [{item['_id']}] {item['Name']} | R{item['Rarity']} | {item['Ver']}", file=output)

    if skipped:
        print(f"\n跳过:", file=output)
        for tid, reason in skipped:
            print(f"  {tid}: {reason}", file=output)

    if not new_items:
        return output.getvalue()

    if auto_merge:
        entries = [format_item_entry(item) for item in new_items]
        new_content = insert_into_item_js(local_content, entries)

        with open(BACKUP_PATH, "w", encoding="utf-8") as f:
            f.write(local_content)
        print(f"\n已备份: {BACKUP_PATH}", file=output)

        with open(LOCAL_ITEM_PATH, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"已写入: {LOCAL_ITEM_PATH} (+{len(new_items)}个)", file=output)

        # 验证
        try:
            with open(LOCAL_ITEM_PATH, "r", encoding="utf-8") as f:
                verify = f.read()
            m = re.search(r"var _item = (\{[\s\S]*?\});\s*\n", verify)
            if m:
                eval(m.group(1))
                print("语法验证: OK", file=output)
        except Exception as e:
            print(f"语法验证: FAILED - {e}", file=output)
    else:
        print("\n[auto_merge=False] 未写入文件", file=output)
        for item in new_items:
            print(format_item_entry(item), file=output)

    return output.getvalue()


# ============================================================
#  sync_item_images - 下载物品图片（webp→png）
# ============================================================

IMG_URL = "https://static.nanoka.cc/assets/hsr/itemicons/{}.webp"
IMG_SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "images", "itemicon")


def sync_item_images(item_ids: List[str]) -> str:
    """
    供 server.py 调用：下载物品PNG图标到本地
    """
    output = io.StringIO()

    os.makedirs(IMG_SAVE_DIR, exist_ok=True)

    success = 0
    skipped = 0
    failed = []

    for tid in item_ids:
        save_path = os.path.join(IMG_SAVE_DIR, f"{tid}.png")

        if os.path.exists(save_path):
            print(f"  • [{tid}] 已存在，跳过", file=output)
            skipped += 1
            continue

        try:
            resp = requests.get(IMG_URL.format(tid), timeout=15)
            resp.raise_for_status()

            with Image.open(io.BytesIO(resp.content)) as img:
                img.save(save_path, "PNG")

            print(f"  ✓ [{tid}] 下载成功", file=output)
            success += 1
        except Exception as e:
            print(f"  ✗ [{tid}] 下载失败: {e}", file=output)
            failed.append(tid)

    print(f"\n完成: 成功 {success}, 跳过 {skipped}, 失败 {len(failed)}", file=output)
    if failed:
        print(f"失败ID: {failed}", file=output)

    return output.getvalue()


if __name__ == "__main__":
    main()