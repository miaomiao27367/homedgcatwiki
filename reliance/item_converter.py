#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通过 ID 选择物品并将数据从 item_all.json 转换为 item.js 格式
提供id_diff.txt
提供item_all.json
https://static.nanoka.cc/hsr/4.1.53/zh/item_all.json
物品来源url
"""

import json
import re
import requests
import os

# 稀有度映射
rarity_map = {
    "NotNormal": 1,
    "Normal": 2,
    "Rare": 3,
    "VeryRare": 4,
    "SuperRare": 5
}

# 类型映射（需要根据实际数据调整）
type_map = {
    "Virtual": 1,
    "Material": 2,
    # 可以根据实际数据添加更多类型映射
}

img_url=r'https://static.nanoka.cc/assets/hsr/itemfigures/{}.webp'
save_path=r"C:\Users\Lenovo\Desktop\homdgcatwiki\homdgcatwiki\images\itemicon"

# 读取 item_all.json 文件
def load_item_all():
    file_path = r"C:\Users\Lenovo\Desktop\homdgcatwiki\homdgcatwiki\testdata\item_all.json"
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# 读取 item.js 文件，获取类型分组信息和每类的最大索引
def load_item_js():
    file_path = r"C:\Users\Lenovo\Desktop\homdgcatwiki\homdgcatwiki\data\CH\Item.js"
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取类型分组
    type_pattern = r'"(\d+)":\s*\[([\s\S]*?)\]'
    type_matches = re.findall(type_pattern, content)
    
    # 构建类型到物品 ID 的映射和每类的最大索引
    type_to_ids = {}
    type_max_index = {}
    
    for type_id, items_str in type_matches:
        # 提取物品 ID
        id_pattern = r'"_id":\s*(\d+)'
        ids = re.findall(id_pattern, items_str)
        type_to_ids[type_id] = [int(id_str) for id_str in ids]
        
        # 计算该类型的最大索引（数组长度减 1）
        items = items_str.strip().split('},')
        type_max_index[type_id] = len(items) - 1
    
    return type_to_ids, type_max_index

# 根据 ID 从 item_all.json 中获取物品数据
def get_item_by_id(item_all, item_id):
    if str(item_id) in item_all:
        return item_all[str(item_id)]
    return None

# 下载图片并保存
def download_image(item_id, save_dir):
    # 确保保存目录存在
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    # 构建图片 URL
    url = img_url.format(item_id)
    
    # 构建保存路径
    save_path = os.path.join(save_dir, f"{item_id}.png")
    
    try:
        # 下载图片
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # 检查请求是否成功
        
        # 保存图片
        with open(save_path, 'wb') as f:
            f.write(response.content)
        
        print(f"成功下载图片: {item_id}.png")
        return True
    except Exception as e:
        print(f"下载图片失败 (ID: {item_id}): {str(e)}")
        return False

# 将 item_all 格式转换为 item.js 格式
def convert_to_item_js_format(item_data):
    if not item_data:
        return None
    
    # 构建转换后的物品数据
    converted_item = {
        "_id": item_data.get("id"),
        "Type": type_map.get(item_data.get("item_main_type"), 0),
        "Rarity": rarity_map.get(item_data.get("rarity"), 0),
        "Name": item_data.get("item_name", ""),
        "Desc": item_data.get("item_desc", ""),
        "Story": item_data.get("item_bg_desc", "").replace("\\n", "<br>"),
        "Icon": item_data.get("item_icon_path", "").split("/")[-1],  # 提取文件名
        "Pic": item_data.get("item_figure_icon_path", "").split("/")[-1],  # 提取文件名
        "Ver": "1.x"  # 默认版本
    }
    
    # 处理物品来源
    if "item_comefrom" in item_data and item_data["item_comefrom"]:
        src_list = [source["desc"] for source in item_data["item_comefrom"]]
        converted_item["Src"] = src_list
    
    # 下载图片
    item_id = item_data.get("id")
    #if item_id:
     #   download_image(item_id, save_path)
    
    return converted_item

# 从 id_diff.txt 文件中读取 ID
def read_ids_from_file():
    file_path = r"/reliance\id_diff.txt"
    ids = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        ids.append(int(line))
                    except ValueError:
                        print(f"跳过非数字 ID: {line}")
        print(f"从 id_diff.txt 中读取了 {len(ids)} 个 ID")
    except FileNotFoundError:
        print(f"未找到文件: {file_path}")
    
    return ids

# 类型映射
item_type_map = {
    "Virtual": 1,  # 虚拟货币
    "Material": {
        3: 3,      # 培养素材
        8: 7,      # 消耗品
        14: 8,     # 宠物
        "default": 2  # 其他材料
    }
}

# 根据物品数据获取类型
def get_item_type(item_data):
    main_type = item_data.get("item_main_type")
    purpose_type = item_data.get("purpose_type")
    
    if main_type == "Virtual":
        return 1
    elif main_type == "Material":
        if purpose_type in item_type_map["Material"]:
            return item_type_map["Material"][purpose_type]
        else:
            return item_type_map["Material"]["default"]
    return 2  # 默认类型

# 主函数
def main():
    # 加载数据
    item_all = load_item_all()
    
    # 从 id_diff.txt 文件中读取 ID
    item_ids = read_ids_from_file()
    
    # 如果没有读取到 ID，使用默认 ID 列表
    if not item_ids:
        item_ids = [1, 2, 3, 101, 102]  # 默认 ID 列表
        print("未从 id_diff.txt 中读取到 ID，使用默认 ID 列表")
    
    # 按类型分组的物品
    items_by_type = {}
    # 索引映射
    index_map = {}
    # 每类的索引起点（固定值）
    type_index_start = {
        1: 50,   # 类型 1 索引起点
        2: 172,  # 类型 2 索引起点
        3: 69,   # 类型 3 索引起点
        7: 190,  # 类型 7 索引起点
        8: 90   # 类型 8 索引起点
    }
    
    print("\n批量转换结果:")
    for id_num in item_ids:
        item_data = get_item_by_id(item_all, id_num)
        if item_data:
            # 获取物品类型
            item_type = get_item_type(item_data)
            
            # 转换物品数据
            converted_item = convert_to_item_js_format(item_data)
            converted_item["Type"] = item_type  # 设置类型
            
            # 按类型分组
            if item_type not in items_by_type:
                items_by_type[item_type] = []
            
            # 计算索引（从现有最大索引+1开始）
            if item_type in type_index_start:
                current_index = type_index_start[item_type]
            else:
                current_index = 0
            
            items_by_type[item_type].append(converted_item)
            
            # 记录索引
            index_map[str(converted_item["_id"])] = current_index
            
            # 更新索引起点
            type_index_start[item_type] = current_index + 1
            
            print(f"\nID: {id_num}, 名称: {converted_item['Name']}, 类型: {item_type}, 索引: {current_index}")
            print(json.dumps(converted_item, ensure_ascii=False, indent=2))
        else:
            print(f"\n未找到 ID 为 {id_num} 的物品")
    
    # 输出到 data_trans.js 文件
    output_file = r"/reliance\data_trans.js"
    
    # 构建输出内容
    output_content = "// Auto Generated\n\nvar _item = {\n"
    
    # 添加按类型分组的物品
    types = sorted(items_by_type.keys())
    for i, item_type in enumerate(types):
        items = items_by_type[item_type]
        output_content += f"    \"{item_type}\": [\n"
        
        for j, item in enumerate(items):
            item_json = json.dumps(item, ensure_ascii=False, indent=4)
            output_content += f"        {item_json}"
            if j < len(items) - 1:
                output_content += ",\n"
            else:
                output_content += "\n"
        
        output_content += "    ]"
        if i < len(types) - 1:
            output_content += ",\n"
        else:
            output_content += "\n"
    
    output_content += "};\n\n"
    
    # 按类型分组索引映射
    index_by_type = {}
    for item_type, items in items_by_type.items():
        index_by_type[item_type] = {}
        for item in items:
            item_id = str(item["_id"])
            index_by_type[item_type][item_id] = index_map[item_id]
    
    # 构建 _type 映射
    type_map_output = {}
    for item_type, items in items_by_type.items():
        for item in items:
            item_id = str(item["_id"])
            type_map_output[item_id] = str(item["Type"])
    
    # 输出 _type
    output_content += "var _type = {\n"
    
    # 按类型分组输出 _type
    type_by_type = {}
    for item_id, item_type in type_map_output.items():
        if item_type not in type_by_type:
            type_by_type[item_type] = []
        type_by_type[item_type].append(item_id)
    
    # 按类型排序
    sorted_types = sorted(type_by_type.keys())
    for i, item_type in enumerate(sorted_types):
        item_ids = type_by_type[item_type]
        # 排序物品 ID
        sorted_ids = sorted(item_ids, key=lambda x: int(x))
        
        # 添加类型注释
        output_content += f"    // 类型 {item_type} 物品\n"
        
        for j, item_id in enumerate(sorted_ids):
            output_content += f"    \"{item_id}\": \"{item_type}\""
            if j < len(sorted_ids) - 1 or i < len(sorted_types) - 1:
                output_content += ",\n"
            else:
                output_content += "\n"
    
    output_content += "};\n\n"
    
    # 添加索引映射
    output_content += "var _index = {\n"
    
    # 按类型输出索引
    types = sorted(index_by_type.keys())
    for i, item_type in enumerate(types):
        type_indices = index_by_type[item_type]
        # 排序类型内的索引键
        type_keys = sorted(type_indices.keys(), key=lambda x: int(x))
        
        # 添加类型注释
        output_content += f"    // 类型 {item_type} 索引\n"
        
        for j, key in enumerate(type_keys):
            output_content += f"    \"{key}\": {type_indices[key]}"
            if j < len(type_keys) - 1 or i < len(types) - 1:
                output_content += ",\n"
            else:
                output_content += "\n"
    
    output_content += "};\n"
    
    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(output_content)
    
    print(f"\n转换结果已输出到: {output_file}")
    print(f"生成了 {len(items_by_type)} 个类型组和 {len(index_map)} 个索引条目")

# =============================================================================
# 生成 Avatar.js 格式的简化物品数据（仅 Name 和 Icon）
# =============================================================================

def generate_avatar_items(ids, lang='zh', version='4.3.52',
                          img_save_dir=r"C:\Users\Lenovo\Desktop\homdgcatwiki\homdgcatwiki\images\itemicon",
                          output_file=None):
    """
    根据传入的物品 ID 列表，生成 Avatar.js 中 _item 格式的简化数据
    （仅包含 Name 和 Icon 字段），并自动下载对应的 PNG 图标
    
    参数:
        ids: 物品 ID 列表，例如 [2, 110111, 110112]
        lang: 语言代码，默认 'zh' (可选 'zh', 'en' 等)
        version: 游戏版本号，默认 '4.1.53'
        img_save_dir: 图标保存目录，默认 images/itemicon
        output_file: 输出 JS 文件路径，默认输出到 reliance/avatar_item.js
    
    返回:
        dict: 格式为 {"ID": {"Name": "...", "Icon": "itemicon/ID.png"}, ...}
    
    同时会在控制台输出完整的 JS 代码块
    """
    import json
    import requests
    import os
    from pathlib import Path
    
    # ---- 1. 下载 item_all.json ----
    api_url = f"https://static.nanoka.cc/hsr/{version}/{lang}/item_all.json"
    print(f"正在拉取数据: {api_url}")
    
    try:
        resp = requests.get(api_url, timeout=30)
        resp.raise_for_status()
        item_all = resp.json()
        print(f"  ✓ 已加载 {len(item_all)} 条物品数据")
    except Exception as e:
        print(f"  ✗ 下载 item_all.json 失败: {e}")
        return {}
    
    # ---- 2. 确保图片目录存在 ----
    Path(img_save_dir).mkdir(parents=True, exist_ok=True)
    
    # ---- 3. 图片 URL 模板 (webp 源) ----
    img_url_template = r"https://static.nanoka.cc/assets/hsr/itemfigures/{}.webp"
    
    # ---- 4. 遍历 ID，抓取数据和图标 ----
    result = {}
    success = 0
    failed = []
    
    for item_id in ids:
        key = str(item_id)
        if key not in item_all:
            print(f"  ⚠ ID {item_id} 未在 item_all.json 中找到，跳过")
            failed.append(item_id)
            continue
        
        data = item_all[key]
        name = data.get("item_name", "")
        
        # 优先使用 item_icon_path；若缺失则用 id.png 兜底
        icon_path_raw = data.get("item_icon_path", "")
        if icon_path_raw:
            icon_filename = Path(icon_path_raw).name  # 仅取文件名
        else:
            icon_filename = f"{item_id}.png"
        
        # 确保后缀是 .png
        stem = Path(icon_filename).stem
        icon_filename = f"{stem}.png"
        
        result[key] = {
            "Name": name,
            "Icon": f"itemicon/{icon_filename}"
        }
        
        # ---- 5. 下载图标 (webp 保存为 png) ----
        save_path = os.path.join(img_save_dir, icon_filename)
        if not os.path.exists(save_path):
            try:
                img_resp = requests.get(img_url_template.format(item_id), timeout=15)
                img_resp.raise_for_status()
                with open(save_path, "wb") as f:
                    f.write(img_resp.content)
                print(f"  ✓ [{item_id}] {name} -> {icon_filename}")
                success += 1
            except Exception as e:
                print(f"  ✗ [{item_id}] 图片下载失败: {e}")
                failed.append(item_id)
        else:
            print(f"  • [{item_id}] {name} 图标已存在，跳过下载")
    
    # ---- 6. 生成 JS 代码块 ----
    js_lines = ["// Auto Generated", "", "var _item = {"]
    sorted_keys = sorted(result.keys(), key=lambda x: int(x))
    for i, k in enumerate(sorted_keys):
        entry = json.dumps(result[k], ensure_ascii=False)
        comma = "," if i < len(sorted_keys) - 1 else ""
        js_lines.append(f'    "{k}": {entry}{comma}')
    js_lines.append("};")
    js_code = "\n".join(js_lines)
    
    # ---- 7. 写入文件 ----
    if output_file is None:
        output_file = r"C:\Users\Lenovo\Desktop\homdgcatwiki\homdgcatwiki\reliance\avatar_item.js"
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(js_code)
    
    # ---- 8. 汇总输出 ----
    print(f"\n{'='*50}")
    print(f"完成: 成功处理 {len(result)} 条物品，下载图标 {success} 个")
    if failed:
        print(f"失败/跳过 {len(failed)} 个 ID: {failed}")
    print(f"JS 代码已写入: {output_file}")
    print(f"图标保存目录: {img_save_dir}")
    print(f"{'='*50}")
    print("\n--- JS 代码 ---")
    print(js_code)
    
    return result


# 示例：直接运行该脚本时的调用演示
if __name__ == "__main__":
    # 在此处传入你要生成的物品 ID
    demo_ids = [110271, 110272, 110273, 110281, 110282, 110283, 110291, 110292, 110293, 110311, 110312, 110313,110443]
    generate_avatar_items(demo_ids)