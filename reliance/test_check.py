#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提取 Item.js 和 item_new.json 文件中的所有 id 并按顺序排序
"""

import re
import json

# 读取 Item.js 文件中所有 _id 字段并排序
def extract_item_js_ids():
    # 读取文件路径
    file_path = r"C:\Users\Lenovo\Desktop\homdgcatwiki\homdgcatwiki\data\CH\Item.js"

    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 提取所有 _id 字段的值
    id_pattern = r'"_id":\s*(\d+)'
    ids = re.findall(id_pattern, content)

    # 将字符串转换为整数
    id_list = [int(id_str) for id_str in ids]

    # 去重并排序
    id_list = list(set(id_list))
    id_list.sort()

    # 输出结果
    print("所有 Item.js 中的 _id 按顺序排序:")
    print("-" * 50)
    for id_num in id_list:
        print(id_num)

    print("-" * 50)
    print(f"总共有 {len(id_list)} 个 Item.js ID")
    return id_list


# 读取 item_new.json 文件中的所有 id 并排序
def extract_item_ids():
    # 读取文件路径
    file_path = "C:\\Users\\Lenovo\\Desktop\\homdgcatwiki\\homdgcatwiki\\testdata\\item_new.json"

    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 提取所有 id（键就是 id）
    id_list = []
    for key in data.keys():
        try:
            # 将键转换为整数
            id_num = int(key)
            id_list.append(id_num)
        except ValueError:
            # 忽略非数字的键
            pass

    # 排序
    id_list.sort()

    # 输出结果
    print("\n所有 item_new.json 的 id 按顺序排序:")
    print("-" * 50)
    for id_num in id_list:
        print(id_num)

    print("-" * 50)
    print(f"总共有 {len(id_list)} 个 Item ID")
    return id_list

# 比对 Item.js 和 item_new.json 中的 ID，并输出差异到 txt 文件
def compare_ids(item_js_ids, item_new_ids):
    # 找出在 Item.js 中存在但在 item_new.json 中不存在的 ID
    missing_in_item_new = [id_num for id_num in item_js_ids if id_num not in item_new_ids]

    # 排序
    missing_in_item_new.sort()

    # 找出在 item_new.json 中存在但在 Item.js 中不存在的 ID
    missing_in_item_js = [id_num for id_num in item_new_ids if id_num not in item_js_ids]

    # 排序
    missing_in_item_js.sort()

    # 输出结果到控制台
    print("\nItem.js 中存在但在 item_new.json 中缺失的 ID:")
    print("-" * 50)
    if missing_in_item_new:
        for id_num in missing_in_item_new:
            print(id_num)
        print("-" * 50)
        print(f"总共有 {len(missing_in_item_new)} 个缺失的 ID")
    else:
        print("没有缺失的 ID")

    print("\nitem_new.json 中存在但在 Item.js 中缺失的 ID:")
    print("-" * 50)
    if missing_in_item_js:
        # 只显示前50个，避免输出过多
        if len(missing_in_item_js) > 50:
            print("显示前50个缺失的 ID（共 {} 个）:".format(len(missing_in_item_js)))
            for id_num in missing_in_item_js[:50]:
                print(id_num)
        else:
            for id_num in missing_in_item_js:
                print(id_num)
        print("-" * 50)
        print(f"总共有 {len(missing_in_item_js)} 个缺失的 ID")
    else:
        print("没有缺失的 ID")

    # 输出差异到 txt 文件
    output_file = r"/reliance\id_diff.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("Item.js 中存在但在 item_new.json 中缺失的 ID:\n")
        f.write("-" * 50 + "\n")
        for id_num in missing_in_item_new:
            f.write(str(id_num) + "\n")
        f.write("-" * 50 + "\n")
        f.write(f"总共有 {len(missing_in_item_new)} 个缺失的 ID\n\n")

        f.write("item_new.json 中存在但在 Item.js 中缺失的 ID:\n")
        f.write("-" * 50 + "\n")
        for id_num in missing_in_item_js:
            f.write(str(id_num) + "\n")
        f.write("-" * 50 + "\n")
        f.write(f"总共有 {len(missing_in_item_js)} 个缺失的 ID\n")

    print(f"\n差异 ID 已输出到文件: {output_file}")

    return missing_in_item_new, missing_in_item_js

# 主函数
if __name__ == "__main__":
    item_js_ids = extract_item_js_ids()
    item_new_ids = extract_item_ids()
    compare_ids(item_js_ids, item_new_ids)