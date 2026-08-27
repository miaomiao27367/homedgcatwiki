#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gi_item_converter.py - GI物品数据补全/更新脚本
================================================
用法:
  python gi_item_converter.py                  # 补全missing_ids.txt中的所有ID
  python gi_item_converter.py 110281 110282    # 补全指定ID
  python gi_item_converter.py --dry            # 仅预览，不写入文件
  python gi_item_converter.py --all            # 包含非34分类的类型

数据来源:
  item_all.json: https://static.nanoka.cc/gi/{ver}/zh/item_all.json

API字段 -> 本地字段:
  id           -> _id
  name         -> Name
  desc         -> Desc
  rank         -> Rarity
  icon         -> Icon
  type         -> Type (保留) + SortType (映射)
  source_list  -> Src (逗号拼接)
"""

import json
import os
import sys
import re
import io
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from PIL import Image

# ============================================================
#  配置
# ============================================================
API_VERSION = "6.7.52"
LANG = "zh"
API_URL = f"https://static.nanoka.cc/gi/{API_VERSION}/{LANG}/item_all.json"
CACHE_DIR = "tempdata"
LOCAL_ITEM_PATH = "gi/CH/item.js"
MISSING_IDS_PATH = "missing_ids.txt"
BACKUP_PATH = "gi/CH/item.js.bak"

# SortType映射表 (API Type字符串 -> SortType整数)
API_TYPE_TO_SORTTYPE = {
    "稀有货币": 9, "通用货币": 9, "高级兑换券": 9, "普通兑换券": 9,
    "限定祈愿道具": 13, "祈愿道具": 13,
    "七国徽印": 14, "徽印": 14, "贵重物品": 14,
    "食物": 7,
    "食材": 8,
    "蒙德区域特产": 5, "璃月区域特产": 5, "素材": 5, "锻造用矿石": 5,
    "稻妻区域特产": 5, "须弥区域特产": 5, "枫丹区域特产": 5,
    "纳塔区域特产": 5, "挪德卡莱区域特产": 5, "至冬区域特产": 5, "雪山材料": 5,
    "角色培养素材": 1,
    "角色与武器培养素材": 2,
    "角色突破素材": 3, "角色天赋素材": 3,
    "武器突破素材": 4, "圣遗物突破素材": 4,
    "小道具": 12, "冒险道具": 12, "消耗品": 12, "鱼饵": 12, "鱼竿": 12,
    "角色经验素材": 15, "武器强化素材": 15, "圣遗物强化素材": 15,
    "药剂": 16,
    "鱼": 17,
    "精炼材料": 18,
    "任务道具": 19, "任务物品": 19, "传说任务解锁道具": 19,
    "摆设图纸": 20, "摆设套装图纸": 20,
    "食谱": 21,
    "命之座激活": 22,
    "角色解锁": 23, "角色成长": 23, "角色装扮": 23,
    "锻造图纸": 24, "鱼饵图纸": 24, "枪械配件蓝图": 24, "合成图纸": 24,
    "圣物匣": 25,
    "碎果裂片": 26, "碎果细屑": 26, "碎果残块": 26, "烟花": 26, "海灯节材料": 26,
}

# 仅34分类的SortType
VALID_SORTTYPES = set(range(1, 19))

os.makedirs(CACHE_DIR, exist_ok=True)


# ============================================================
#  数据加载
# ============================================================

def load_api_data() -> Dict[str, Any]:
    """加载API数据，优先本地缓存"""
    cache_file = os.path.join(CACHE_DIR, f"gi_item_all_{API_VERSION}_{LANG}.json")

    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"从缓存加载API数据: {len(data)}条")
        return data

    print(f"正在下载: {API_URL}")
    try:
        resp = requests.get(API_URL, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"下载成功并缓存: {len(data)}条")
        return data
    except Exception as e:
        print(f"下载失败: {e}")
        # 尝试使用本地item_all.json
        local_file = "item_all.json"
        if os.path.exists(local_file):
            with open(local_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"使用本地item_all.json: {len(data)}条")
            return data
        sys.exit(1)


def load_local_items() -> Tuple[Dict, str, str]:
    """读取本地item.js，返回(数据, 前缀, 后缀)"""
    with open(LOCAL_ITEM_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    m = re.search(r"var _items = ([\s\S]*?)\nvar index_food", content)
    if not m:
        raise ValueError("无法解析item.js中的_items块")
    raw = m.group(1).strip()
    if raw.endswith(";"):
        raw = raw[:-1]
    local = json.loads(raw)
    pre = content[:m.start()]
    post = content[m.end():]
    return local, pre, post


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

def get_sorttype(api_type: str) -> int:
    """API type -> SortType，非34分类返回-1"""
    st = API_TYPE_TO_SORTTYPE.get(api_type, -1)
    return st if st in VALID_SORTTYPES else -1


def convert_item(api_item: Dict, item_id: str) -> Dict:
    """将API数据转换为本地格式"""
    api_type = api_item.get("type", "")
    st = get_sorttype(api_type)

    src = api_item.get("source_list", [])
    if isinstance(src, list):
        src = ", ".join(src)
    elif not src:
        src = ""

    return {
        "_id": int(item_id) if item_id.isdigit() else item_id,
        "SortType": st if st >= 0 else 0,
        "Rarity": api_item.get("rank", 0),
        "Name": api_item.get("name", ""),
        "Desc": api_item.get("desc", ""),
        "Icon": api_item.get("icon", ""),
        "Type": api_type,
        "Src": src,
    }


# ============================================================
#  输出
# ============================================================

def format_item_entry(item: Dict) -> str:
    """格式化为单条JS记录"""
    lines = [
        f'    "{item["_id"]}": {{',
        f'        "_id": {item["_id"]},',
        f'        "SortType": {item["SortType"]},',
        f'        "Rarity": {item["Rarity"]},',
        f'        "Name": {json.dumps(item["Name"], ensure_ascii=False)},',
        f'        "Desc": {json.dumps(item["Desc"], ensure_ascii=False)},',
        f'        "Icon": {json.dumps(item["Icon"], ensure_ascii=False)},',
        f'        "Type": {json.dumps(item["Type"], ensure_ascii=False)},',
    ]
    if item.get("Src"):
        lines.append(f'        "Src": {json.dumps(item["Src"], ensure_ascii=False)},')
    if item.get("Pic"):
        lines.append(f'        "Pic": {json.dumps(item["Pic"], ensure_ascii=False)},')
    # 去掉最后一个逗号
    lines[-1] = lines[-1].rstrip(",")
    lines.append("    }")
    return "\n".join(lines)


def write_items(items: Dict, pre: str, post: str):
    """写入item.js（按ID排序）"""
    sorted_items = dict(sorted(items.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0))
    items_json = json.dumps(sorted_items, ensure_ascii=False, indent=4)
    new_content = pre + "var _items = " + items_json + ";\n\nvar index_food" + post

    with open(LOCAL_ITEM_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)


# ============================================================
#  主流程
# ============================================================

def main():
    args = sys.argv[1:]
    is_dry = "--dry" in args
    include_all = "--all" in args
    target_ids = [a for a in args if not a.startswith("--") and a.isdigit()]

    if not target_ids:
        target_ids = read_missing_ids()
        if not target_ids:
            print("未指定ID且未找到missing_ids.txt")
            print("用法: python gi_item_converter.py [ID...] [--dry] [--all]")
            sys.exit(1)

    print(f"{'='*50}")
    print(f"GI Item Converter (API v{API_VERSION})")
    print(f"目标ID: {len(target_ids)}个")
    print(f"{'='*50}")

    api_data = load_api_data()
    local_items, pre, post = load_local_items()

    new_items = []
    updated = []
    skipped = []

    for tid in target_ids:
        tid_str = str(tid)

        if tid_str not in api_data:
            skipped.append((tid, "API未找到"))
            continue

        api_item = api_data[tid_str]
        api_type = api_item.get("type", "")
        st = get_sorttype(api_type)

        if not include_all and st < 0:
            skipped.append((tid, f"非34分类({api_type})"))
            continue

        item = convert_item(api_item, tid_str)

        if tid_str in local_items:
            local_items[tid_str] = item
            updated.append(item)
        else:
            local_items[tid_str] = item
            new_items.append(item)

    print(f"\n新增: {len(new_items)} | 更新: {len(updated)} | 跳过: {len(skipped)}")

    # 预览(前10)
    all_changed = new_items + updated
    if all_changed:
        print(f"\n--- 预览 (前10个) ---")
        for item in all_changed[:10]:
            print(f"  [{item['_id']}] {item['Name']} | {item['Type']} | R{item['Rarity']} | ST{item['SortType']}")
        if len(all_changed) > 10:
            print(f"  ... 还有{len(all_changed) - 10}个")

    if skipped:
        print(f"\n--- 跳过 ({len(skipped)}) ---")
        for tid, reason in skipped[:20]:
            print(f"  {tid}: {reason}")
        if len(skipped) > 20:
            print(f"  ... 还有{len(skipped) - 20}个")

    if is_dry:
        print("\n[dry模式] 未写入文件")
        return

    if not all_changed:
        print("\n无变更")
        return

    # 备份
    with open(BACKUP_PATH, "w", encoding="utf-8") as f:
        with open(LOCAL_ITEM_PATH, "r", encoding="utf-8") as src:
            f.write(src.read())
    print(f"\n已备份: {BACKUP_PATH}")

    # 写入
    write_items(local_items, pre, post)
    print(f"已写入: {LOCAL_ITEM_PATH}")

    # 验证
    try:
        with open(LOCAL_ITEM_PATH, "r", encoding="utf-8") as f:
            verify = f.read()
        m = re.search(r"var _items = ([\s\S]*?)\nvar index_food", verify)
        if m:
            raw = m.group(1).strip()
            if raw.endswith(";"):
                raw = raw[:-1]
            json.loads(raw)
            print("语法验证: OK")
    except Exception as e:
        print(f"语法验证: FAILED - {e}")


# ============================================================
#  server.py 调用接口
# ============================================================

def generate_gi_item_data(item_ids: List[str], version: str = API_VERSION,
                          include_all: bool = False, auto_merge: bool = True) -> str:
    """
    供 server.py 调用：根据ID列表从API获取数据并合并到item.js

    Args:
        item_ids: 物品ID列表
        version: API版本号
        include_all: 是否包含非34分类
        auto_merge: 是否自动写入item.js

    Returns:
        处理结果字符串
    """
    import io
    output = io.StringIO()

    global API_VERSION
    API_VERSION = version

    api_url = f"https://static.nanoka.cc/gi/{version}/{LANG}/item_all.json"
    cache_file = os.path.join(CACHE_DIR, f"gi_item_all_{version}_{LANG}.json")

    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            api_data = json.load(f)
        print(f"从缓存加载: {len(api_data)}条", file=output)
    else:
        try:
            resp = requests.get(api_url, timeout=60)
            resp.raise_for_status()
            api_data = resp.json()
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(api_data, f, ensure_ascii=False, indent=2)
            print(f"下载成功: {len(api_data)}条", file=output)
        except Exception as e:
            print(f"下载失败: {e}", file=output)
            return output.getvalue()

    local_items, pre, post = load_local_items()

    new_count = 0
    skip_count = 0
    unmapped = {}  # {id: type} 未映射到已知SortType的物品

    for tid in item_ids:
        tid_str = str(tid)
        if tid_str not in api_data:
            skip_count += 1
            continue

        api_item = api_data[tid_str]
        api_type = api_item.get("type", "")
        st = get_sorttype(api_type)

        if not include_all and st < 0:
            skip_count += 1
            continue

        item = convert_item(api_item, tid_str)
        local_items[tid_str] = item
        new_count += 1

        if st == 0:
            unmapped[tid_str] = api_type

    if auto_merge and new_count > 0:
        with open(BACKUP_PATH, "w", encoding="utf-8") as f:
            with open(LOCAL_ITEM_PATH, "r", encoding="utf-8") as src:
                f.write(src.read())
        write_items(local_items, pre, post)
        print(f"已写入 {LOCAL_ITEM_PATH}", file=output)

    print(f"新增/更新: {new_count} | 跳过: {skip_count}", file=output)
    if unmapped:
        print(f"\n⚠ 未映射分类 (SortType=0 → 其他):", file=output)
        for uid, utype in unmapped.items():
            print(f"  ID {uid}: \"{utype}\"", file=output)

    return output.getvalue(), unmapped


# ============================================================
#  sync_gi_item_images - 下载物品图片（webp→png）
# ============================================================

GI_IMG_URL = "https://static.nanoka.cc/assets/gi/UI_ItemIcon_{}.webp"
GI_IMG_SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "homdgcat-res", "Mat")


def sync_gi_item_images(item_ids: List[str]) -> str:
    """
    供 server.py 调用：下载GI物品PNG图标到本地
    """
    import io as _io
    output = _io.StringIO()

    os.makedirs(GI_IMG_SAVE_DIR, exist_ok=True)

    success = 0
    skipped = 0
    failed = []

    for tid in item_ids:
        save_path = os.path.join(GI_IMG_SAVE_DIR, f"UI_ItemIcon_{tid}.png")

        if os.path.exists(save_path):
            print(f"  o [{tid}] 已存在，跳过", file=output)
            skipped += 1
            continue

        try:
            resp = requests.get(GI_IMG_URL.format(tid), timeout=15)
            resp.raise_for_status()

            with Image.open(_io.BytesIO(resp.content)) as img:
                img.save(save_path, "PNG")

            print(f"  v [{tid}] 下载成功", file=output)
            success += 1
        except Exception as e:
            print(f"  x [{tid}] 下载失败: {e}", file=output)
            failed.append(tid)

    print(f"\n完成: 成功 {success}, 跳过 {skipped}, 失败 {len(failed)}", file=output)
    if failed:
        print(f"失败ID: {failed}", file=output)

    return output.getvalue()


if __name__ == "__main__":
    main()