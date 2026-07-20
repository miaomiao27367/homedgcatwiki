#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动下载并转换光锥数据脚本
功能：从新网站API下载光锥数据，并转换为现有JS格式
"""

import os
import json
import requests
from typing import Dict, Any, Optional

BASE_URL = "https://static.nanoka.cc/hsr"
LANGUAGE = "zh"  # 可选: en, zh, ja, ko
OUTPUT_DIR = "./sr/data/CH/Weapon"
OUTPUT_DIR2 = "./tempdata"

# 确保输出目录存在
os.makedirs(OUTPUT_DIR, exist_ok=True)

def download_weapon_data(weapon_id: str, version: str = "4.1.53") -> Dict[str, Any]:
    """
    下载光锥数据

    Args:
        weapon_id: 光锥ID
        version: 版本号 (4.1.51/4.1.52/4.1.53)
    """
    os.makedirs(OUTPUT_DIR2, exist_ok=True)
    
    # 构建本地文件路径
    local_file = os.path.join(OUTPUT_DIR2, f"weapon_{weapon_id}_{version}.json")
    
    # 检查本地文件是否存在
    if os.path.exists(local_file):
        try:
            with open(local_file, 'r', encoding='utf-8') as f:
                weapon_data = json.load(f)
            return weapon_data
        except Exception as e:
            print(f"读取本地缓存文件失败: {e}")
            # 读取失败，继续尝试下载
    
    # 从网络下载
    url = f"https://static.nanoka.cc/hsr/{version}/{LANGUAGE}/lightcone/{weapon_id}.json"

    try:
        response = requests.get(url)
        response.raise_for_status()

        # 解析JSON数据
        weapon_data = response.json()

        # 缓存到本地
        try:
            with open(local_file, 'w', encoding='utf-8') as f:
                json.dump(weapon_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"缓存数据到本地失败: {e}")
            # 缓存失败不影响返回数据
        
        return weapon_data

    except requests.exceptions.RequestException as e:
        print(f"下载光锥 {weapon_id} 的 {version} 版本数据失败: {e}")
        return None


def download_all_versions_data(weapon_id: str, versions: Dict[str, str]) -> Optional[Dict[str, Dict[str, Any]]]:
    """
    下载所有版本的光锥数据

    Args:
        weapon_id: 光锥ID
        versions: 版本配置字典，格式: {"v1": "4.3.51", "v2": "4.3.52"}

    Returns:
        包含所有版本数据的字典: {"v1": data_4.1.51, "v2": data_4.1.52}
        如果任何版本下载失败，返回 None
    """
    all_data = {}

    for version_key, version_value in versions.items():
        data = download_weapon_data(weapon_id, version_value)
        if data:
            all_data[version_key] = data
        else:
            print(f"错误: 无法获取 {version_key} ({version_value}) 版本数据")
            return None

    return all_data

def format_description(desc: str, param_list: list = None) -> str:
    """
    格式化描述文本
    将HTML格式转换为游戏内格式
    
    Args:
        desc: 原始描述文本
        param_list: 参数列表（用于精炼数据的参数替换）
    """
    if not desc:
        return ""

    # 替换颜色标记
    desc = desc.replace('<color=#f29e38ff>', '').replace('</color>', '')
    # 替换unbreak标记
    desc = desc.replace('<unbreak>', '').replace('</unbreak>', '')
    # 处理换行符
    desc = desc.replace('\n', ' <br> ')

    # 如果有参数列表，进行参数替换（用于精炼数据）
    if param_list:
        # 构建所有精炼等级的参数值
        all_params = []
        for i in range(1, 6):  # 精炼1-5级
            level_params = param_list.get(str(i), {}).get("param_list", [])
            all_params.append(level_params)

        # 找出最大参数个数
        max_param_count = 11

        # 辅助函数：检查所有值是否相同，如果相同只返回一个，否则返回所有
        def get_unique_values(values):
            if not values:
                return []
            # 检查所有值是否相同
            first_value = values[0]
            all_same = all(v == first_value for v in values)
            if all_same:
                return [first_value]  # 所有值相同，只返回第一个
            return values  # 值不同，返回所有

        # 循环处理所有参数（#1[i]%, #2[i]%, ... #n[i]% 等）
        for param_index in range(max_param_count):
            i = param_index + 1  # 参数编号从1开始

            # 处理 #{i}[i]% 格式（百分比）
            param_values_percent = []
            for params in all_params:
                if len(params) > param_index:
                    value = params[param_index] * 100
                    param_values_percent.append(f"<color style='color:#f29e38;'>{value:.0f}%</color>")
            if param_values_percent:
                # 优化：如果所有精炼等级数值相同，只显示一个
                unique_values = get_unique_values(param_values_percent)
                desc = desc.replace(f'#{i}[i]%', ' / '.join(unique_values))

            # 处理 #{i}[f1]% 格式（百分比，保留一位小数）
            param_values_f1_percent = []
            for params in all_params:
                if len(params) > param_index:
                    value = params[param_index] * 100
                    param_values_f1_percent.append(f"<color style='color:#f29e38;'>{value:.1f}%</color>")
            if param_values_f1_percent:
                unique_values = get_unique_values(param_values_f1_percent)
                desc = desc.replace(f'#{i}[f1]%', ' / '.join(unique_values))

            # 处理 #{i}[f2]% 格式（百分比，保留两位小数）
            param_values_f2_percent = []
            for params in all_params:
                if len(params) > param_index:
                    value = params[param_index] * 100
                    param_values_f2_percent.append(f"<color style='color:#f29e38;'>{value:.2f}%</color>")
            if param_values_f2_percent:
                unique_values = get_unique_values(param_values_f2_percent)
                desc = desc.replace(f'#{i}[f2]%', ' / '.join(unique_values))

            # 处理 #{i}[i] 格式（数值）
            param_values_no_percent = []
            for params in all_params:
                if len(params) > param_index:
                    value = params[param_index]
                    param_values_no_percent.append(f"<color style='color:#f29e38;'>{value:.0f}</color>")
            if param_values_no_percent:
                unique_values = get_unique_values(param_values_no_percent)
                desc = desc.replace(f'#{i}[i]', ' / '.join(unique_values))

    # 确保没有残留的转义字符
    desc = desc.replace('\\n', ' <br> ')
    return desc

def convert_weapon_data(weapon_id: str, all_versions_data: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    转换光锥数据
    """
    # 使用最新版本的数据作为基础
    latest_version = list(all_versions_data.keys())[-1] if all_versions_data else "v3"
    base_weapon_data = all_versions_data.get(latest_version, {}) or {}
    
    # 提取基本信息
    name = base_weapon_data.get("name") or ""
    desc = base_weapon_data.get("desc") or ""

    # 格式化描述
    formatted_desc = desc.replace('\n', '<br>') if desc else ""

    # 构建输出数据
    weapon_desc = {
        weapon_id: formatted_desc
    }

    weapon_skill = {
        weapon_id: {}
    }

    # 为每个版本生成对应的精炼描述
    for version_key in all_versions_data:
        version_data = all_versions_data[version_key]
        refinements = version_data.get("refinements") or {}
        refinement_name = refinements.get("name") or ""
        refinement_desc = refinements.get("desc") or ""
        refinement_levels = refinements.get("level") or {}

        # 格式化精炼描述
        formatted_refinement_desc = format_description(refinement_desc, refinement_levels)

        # 添加到weapon_skill
        weapon_skill[weapon_id][version_key] = {
            "Name": refinement_name,
            "Desc": [formatted_refinement_desc]
        }

    # 添加Live版本（使用最新版本的数据）
    if all_versions_data:
        latest_version_data = all_versions_data[latest_version]
        latest_refinements = latest_version_data.get("refinements") or {}
        latest_refinement_name = latest_refinements.get("name") or ""
        latest_refinement_desc = latest_refinements.get("desc") or ""
        latest_refinement_levels = latest_refinements.get("level") or {}
        latest_formatted_refinement_desc = format_description(latest_refinement_desc, latest_refinement_levels)
        
        weapon_skill[weapon_id]["Live"] = {
            "Name": latest_refinement_name,
            "Desc": [latest_formatted_refinement_desc]
        }

    return weapon_desc, weapon_skill

def generate_js_file(weapon_id: str, weapon_desc: Dict[str, Any], weapon_skill: Dict[str, Any]) -> None:
    """
    生成JS文件
    """
    output_file = os.path.join(OUTPUT_DIR, f"{weapon_id}.js")
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("// Auto Generated\n\n")

        # 写入光锥描述
        f.write("var _weapondesc_ = {\n")
        if weapon_desc:
            for weapon_id, desc in weapon_desc.items():
                f.write(f'    "{weapon_id}": "{desc}"\n')
        f.write("}\n\n")
        
        # 写入光锥技能
        f.write("var _weaponskill_ = {\n")
        if weapon_skill:
            for weapon_id, skill_info in weapon_skill.items():
                f.write(f'    "{weapon_id}": {{\n')
                for version_key, version_info in skill_info.items():
                    f.write(f'        "{version_key}": {{\n')
                    f.write(f'            "Name": "{version_info["Name"]}",\n')
                    f.write(f'            "Desc": [\n')
                    for desc in version_info["Desc"]:
                        f.write(f'                "{desc}"\n')
                    f.write(f'            ]\n')
                    f.write(f'        }},\n')
                # 移除最后一个逗号
                f.seek(f.tell() - 2)
                f.write('\n    },\n')
        # 移除最后一个逗号
        f.seek(f.tell() - 2)
        f.write('\n}\n')


def calculate_final_stats(weapon_data: Dict[str, Any]) -> Dict[str, float]:
    """
    计算光锥的最终属性数值

    Args:
        weapon_data: 光锥数据

    Returns:
        包含最终属性数值的字典
    """
    if not weapon_data:
        return {"HP": 0, "ATK": 0, "DEF": 0}
    stats = weapon_data.get("stats") or []
    
    # 获取最高等级的数据（通常是最后一个）
    if stats:
        max_level_stats = stats[-1] or {}
        base_hp = max_level_stats.get("base_hp") or 0
        base_hp_add = max_level_stats.get("base_hp_add") or 0
        max_level = max_level_stats.get("max_level") or 80
        
        base_attack = max_level_stats.get("base_attack") or 0
        base_attack_add = max_level_stats.get("base_attack_add") or 0
        
        base_defence = max_level_stats.get("base_defence") or 0
        base_defence_add = max_level_stats.get("base_defence_add") or 0
        
        # 计算最终数值：base + (add × 等级)
        final_hp = base_hp + (base_hp_add * max_level)
        final_atk = base_attack + (base_attack_add * max_level)
        final_def = base_defence + (base_defence_add * max_level)
        
        return {
            "HP": round(final_hp, 2),
            "ATK": round(final_atk, 2),
            "DEF": round(final_def, 2)
        }
    return {"HP": 0, "ATK": 0, "DEF": 0}

def get_materials(weapon_data: Dict[str, Any]) -> list:
    """
    提取光锥的材料信息（使用 promotion5 的数据）

    规则:
      1. 选取 promotion == 5 的那一条 stat 数据
      2. 从 promotion_cost_list 中忽略 item_id == 2 的通用材料（信用点）
      3. 将剩余材料倒序排列：原列表第3项(末尾) → 第1位，原列表第2项 → 第2位
         例: [2, 110293, 116003] → 过滤后 [110293, 116003] → 倒序 [116003, 110293]

    Args:
        weapon_data: 光锥数据

    Returns:
        材料ID列表 [mat1, mat2]
    """
    if not weapon_data:
        return [0, 0]
    materials = []
    stats = weapon_data.get("stats") or []

    # 1) 明确找到 promotion == 5 的那一条数据（若找不到则回退到倒数第二条）
    target_stat = None
    for s in stats:
        if s and s.get("promotion") == 5:
            target_stat = s
            break
    if target_stat is None and len(stats) >= 2:
        target_stat = stats[-2]  # 回退：最后一条 promotion_cost_list 为空，用倒数第二条

    if target_stat:
        promotion_cost = target_stat.get("promotion_cost_list") or []

        # 2) 过滤掉 item_id == 2 的通用材料
        filtered = [item.get("item_id") for item in promotion_cost
                    if item.get("item_id") and item.get("item_id") != 2]

        # 3) 倒序排列：3号位 → 首位，2号位 → 二号位
        #    去重并保证顺序稳定
        seen = set()
        for item_id in reversed(filtered):
            if item_id not in seen:
                seen.add(item_id)
                materials.append(item_id)

    # 确保至少返回两个材料ID
    while len(materials) < 2:
        materials.append(0)

    return materials[:2]  # 只返回前两个材料ID

def generate_avatar_weapon_data(weapon_id: str, weapon_data: Dict[str, Any], major_version: str) -> None:
    """
    生成光锥avatar数据
    """
    if not weapon_data:
        weapon_data = {}
    # 提取基本信息
    name = weapon_data.get("name") or ""
    rarity_str = weapon_data.get("rarity") or ""
    base_type = weapon_data.get("base_type") or ""
    desc = (weapon_data.get("desc") or "").replace('\\n', '\n')
    
    # 转换稀有度
    rarity = 5 if "Rarity5" in rarity_str else 4 if "Rarity4" in rarity_str else 3
    
    # 转换命途类型
    path_map = {
        "Warlock": "Nihility",
        "Guardian": "Preservation",
        "Mage": "Erudition",
        "Rogue": "Hunt",
        "Shaman": "Harmony",
        "Warrior": "Destruction",
        "Priest": "Abundance",
        "Memory": "Remembrance",
        "Elation": "Elation"
    }
    path = path_map.get(base_type, "Nihility")
    
    # 计算最终属性
    stats = calculate_final_stats(weapon_data)
    
    # 获取材料信息
    materials = get_materials(weapon_data)
    
    # 构建数据结构
    weapon_avatar_data = {
        "_id": int(weapon_id),
        "Ver": f"{float(major_version) + 0.1:.1f}",
        "Name": name,
        "Desc": desc,
        "Rarity": rarity,
        "Path": path,
        "Skill": int(weapon_id),
        "Pic": f"{weapon_id}.png",
        "Mat": materials,
        "Stats": stats
    }
    
    # 保存到文件
    os.makedirs(OUTPUT_DIR2, exist_ok=True)
    output_file = os.path.join(OUTPUT_DIR2, f"{weapon_id}basic.js")
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("// Auto Generated\n\n")
        f.write("var _weapon = [\n")
        f.write(f"    {json.dumps(weapon_avatar_data, ensure_ascii=False, indent=4)}\n")
        f.write("]\n")


def merge_weapon_to_avatar_js(weapon_id: str) -> str:
    """
    将生成的光锥avatar基础数据自动拼接到Avatar.js的_weapon数组中

    Args:
        weapon_id: 光锥ID
    Returns:
        拼接结果描述
    """
    basic_file = os.path.join(OUTPUT_DIR2, f"{weapon_id}basic.js")
    avatar_js = "./sr/data/CH/Avatar.js"

    if not os.path.exists(basic_file):
        return ""

    with open(basic_file, 'r', encoding='utf-8') as f:
        content = f.read()

    start = content.find('{')
    end = content.rfind('}')
    if start < 0 or end < 0:
        return ""
    weapon_entry = json.loads(content[start:end+1])
    weapon_id_str = str(weapon_entry.get('_id', ''))

    with open(avatar_js, 'r', encoding='utf-8') as f:
        js_content = f.read()

    if f'"_id": {weapon_id_str}' in js_content:
        return "光锥条目已存在，无需拼接"

    new_json = json.dumps(weapon_entry, ensure_ascii=False, indent=4)
    new_json = '\n'.join('    ' + line for line in new_json.split('\n'))

    pattern = 'var _weapon = [\n    {'
    if pattern not in js_content:
        return "错误：无法定位 _weapon 数组起始位置"
    js_content = js_content.replace(pattern, f'var _weapon = [\n{new_json},\n    {{', 1)

    with open(avatar_js, 'w', encoding='utf-8') as f:
        f.write(js_content)

    return f"已自动拼接光锥 {weapon_id_str} 到 Avatar.js（开头）"


def generate_weapon_data(weapon_id: str, major_version: str = None, minor_versions: list = None) -> str:
    """
    封装的生成光锥数据的函数，供其他程序调用

    Args:
        weapon_id: 光锥ID
        major_version: 大版本号，例如 "4.3"
        minor_versions: 小版本号列表，例如 [".51", ".52"]
    """

    # 参数检查：必须传入所有参数
    if weapon_id is None or major_version is None or minor_versions is None:
        return "错误：必须传入 weapon_id、major_version 和 minor_versions 参数"
    
    # 组装 versions 字典
    versions = {}
    for i, minor_ver in enumerate(minor_versions, 1):
        versions[f"v{i}"] = f"{major_version}{minor_ver}"

    # 下载所有版本的光锥数据
    all_versions_data = download_all_versions_data(weapon_id, versions)

    if not all_versions_data:
        return "至少有一个版本的数据下载失败，退出程序"

    # 转换数据
    weapon_desc, weapon_skill = convert_weapon_data(weapon_id, all_versions_data)

    # 生成JS文件
    generate_js_file(weapon_id, weapon_desc, weapon_skill)

    # 生成光锥avatar数据（使用最新版本的数据）
    if versions:
        latest_version = list(versions.keys())[-1]
        if latest_version in all_versions_data:
            generate_avatar_weapon_data(weapon_id, all_versions_data[latest_version], major_version)

    # 自动拼接到Avatar.js
    merge_msg = merge_weapon_to_avatar_js(weapon_id)
    result = f"光锥 {weapon_id} 数据生成完成！"
    if merge_msg:
        result += "\n" + merge_msg
    return result


def main():
    """
    主函数（调试入口）
    """
    idlist = ["23060", "23061", "23062"]
    for id in idlist:
        generate_weapon_data(id, major_version="4.3", minor_versions=[".51", ".52"])


if __name__ == "__main__":
    main()