#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动下载并转换角色数据脚本
功能：根据角色ID从新网站API下载数据，并转换为现有JS格式
基于1502角色数据结构的映射分析
"""

import os
import json
import requests
from typing import Dict, Any, Optional


BASE_URL = "https://static.nanoka.cc/hsr"
LANGUAGE = "zh"  # 可选: en, zh, ja, ko
OUTPUT_DIR = "./tempdata"
OUTPUT_DIR2 = "./sr/data/CH/Avatar"
DEBUG_OUTPUT_DIR = "./tempoutput"

# 确保输出目录存在
os.makedirs(OUTPUT_DIR, exist_ok=True)


def download_character_data(character_id: str, version: str ) -> Optional[Dict[str, Any]]:
    """
    下载角色数据

    Args:
        character_id: 角色ID
        version: 版本号 (4.x.51/4.x.52/4.x.53)
    """
    # 定义OUTPUT_DIR目录路径
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 构建本地文件路径
    local_file = os.path.join(OUTPUT_DIR, f"{character_id}_{version}.json")
    
    # 检查本地文件是否存在
    if os.path.exists(local_file):
        try:
            with open(local_file, 'r', encoding='utf-8') as f:
                character_data = json.load(f)
            return character_data
        except Exception as e:
            print(f"读取本地缓存文件失败: {e}")
            # 读取失败，继续尝试下载
    
    # 从网络下载
    url = f"https://static.nanoka.cc/hsr/{version}/{LANGUAGE}/character/{character_id}.json"

    try:
        response = requests.get(url)
        response.raise_for_status()

        # 解析JSON数据
        character_data = response.json()

        # 缓存到本地
        try:
            with open(local_file, 'w', encoding='utf-8') as f:
                json.dump(character_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"缓存数据到本地失败: {e}")
            # 缓存失败不影响返回数据
        
        return character_data

    except requests.exceptions.RequestException as e:
        print(f"下载角色 {character_id} 的 {version} 版本数据失败: {e}")
        return None


def download_all_versions_data(character_id: str, versions: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
    """
    下载所有版本的角色数据

    Args:
        character_id: 角色ID
        versions: 版本配置字典，格式: {"v1": "4.3.51", "v2": "4.3.52"}，不传入则使用默认值

    Returns:
        包含所有版本数据的字典: {"v1": data_4.1.51, "v2": data_4.1.52, "v3": data_4.1.53}
    """
    all_data = {}

    for version_key, version_value in versions.items():
        data = download_character_data(character_id, version_value)
        if data:
            all_data[version_key] = data
        else:
            print(f"警告: 无法获取 {version_key} 版本数据")

    return all_data

def format_description(desc: str, param_list: list = None) -> str:
    """
    格式化描述文本
    将HTML格式转换为游戏内格式

    Args:
        desc: 原始描述文本
        param_list: 参数列表（用于天赋树和星魂数据的参数替换）
    """
    if not desc:
        return ""

    # 替换颜色标记
    desc = desc.replace('<color=#f29e38ff>', '').replace('</color>', '')
    # 替换unbreak标记
    desc = desc.replace('<unbreak>', '').replace('</unbreak>', '')
    # 处理换行符，将\n替换为空格或<br>标签
    desc = desc.replace('\n', ' ')
    
    # 如果有参数列表，进行参数替换（用于天赋树和星魂数据）
    if param_list:
        for i, param in enumerate(param_list, 1):
            # 根据参数值判断是否为百分比
            if param <= 1:  # 小于等于1的值是百分比（包括1.0表示100%）
                if param == int(param):
                    # 整数百分比（如1.0 -> 100%）
                    param_str = f"<b><color style='color:#f29e38'>{int(param*100)}%</color></b>"
                else:
                    # 小数百分比（如0.001 -> 0.1%）
                    param_str = f"<b><color style='color:#f29e38'>{param*100:.1f}%</color></b>"
            else:  # 大于1的值是具体数值
                param_str = f"<b><color style='color:#f29e38'>{int(param) if param == int(param) else param}</color></b>"

            # 先替换带格式的占位符
            desc = desc.replace(f'#{i}[f2]%', param_str.rstrip('%'))
            desc = desc.replace(f'#{i}[f1]%', param_str.rstrip('%'))
            desc = desc.replace(f'#{i}[i]', param_str)
            desc = desc.replace(f'#{i}%', param_str.rstrip('%'))
            desc = desc.replace(f'#{i}', param_str)

            # 清理可能的双百分号
            desc = desc.replace('</b>%', '</b>')

            # 清理残余的 [i] 标记
            desc = desc.replace('[i]', '')
            desc = desc.replace('[f1]', '')
            desc = desc.replace('[f2]', '')

    else:
        # 技能数据的参数格式转换（保持占位符格式）
        # 根据参数类型进行转换
        # 整数参数：[i] -> [f]
        for i in range(1, 11):  # 处理#1到#10的占位符
            desc = desc.replace(f'#{i}[i]', f' <b>#{i}[f]</b> ')

        # 百分比参数：[f1]% -> [p]
        for i in range(1, 11):  # 处理#1到#10的占位符
            desc = desc.replace(f'#{i}[f1]%', f'@ <b>#{i}[p]</b> #')
            desc = desc.replace(f' <b>#{i}[f]</b> %', f'@ <b>#{i}[p]</b> #')
            desc = desc.replace(f'#{i}[f2]%', f'@ <b>#{i}[p]</b> #')


    # 保留HTML标签（如<u>、<br>）
    # 确保没有残留的\n字符
    desc = desc.replace('\\n', ' ')
    # 最后清理可能的双百分号
    desc = desc.replace('</b>%', '</b>')
    return desc

def _map_skill_tag(skill_tag: str) -> str:
    """
    映射技能标签
    """
    tag_map = {
        "Blast": "扩散",
        "Support": "辅助",
        "MazeAttack": "",
        "AoEAttack": "群攻"
    }
    if skill_tag is None:
        return ""
    return tag_map.get(skill_tag, skill_tag)

def _map_attack_type(skill_type: str) -> str:
    """
    映射攻击类型
    """
    attack_map = {
        "Normal": "Normal",
        "BPSkill": "BPSkill",
        "Ultra": "Ultra",
        "Passive": "None",
        "Maze": "Maze",
        "ElationDamage": "ElationDamage",
        "MazeNormal": "MazeNormal",
        "Assist": "Assist",
    }
    if skill_type is None:
        return "None"
    return attack_map.get(skill_type, "None")


def _get_skill_icon_type(skill_type: str) -> str:
    """
    获取技能图标类型
    """
    if skill_type is None:
        return ""

    icon_type = skill_type
    # 替换映射
    icon_type = icon_type.replace("BPSkill", "BP")
    icon_type = icon_type.replace("ElationDamage", "Elation")
    icon_type = icon_type.replace("MazeNormal", "Normal")

    return icon_type


def _convert_bp_value(skill_info: Dict[str, Any]) -> int:
    """
    转换BP值：先判断bpneed，如果为正值则转换为负值；再判断bpadd，有值就填入
    """
    bp_add = skill_info.get("bp_add")
    bp_need = skill_info.get("bp_need")

    # 先判断bp_need：如果为正值，则转换为负值；如果为负值，则不采纳
    if bp_need is not None and bp_need > 0:
        return -bp_need

    # 再判断bp_add：如果有值，就直接填入
    if bp_add is not None:
        return bp_add

    # 默认值
    return 0

def convert_skill_data_old(character_id: str, skills: Dict[str, Any]) -> Dict[str, Any]:
    """
    转换技能数据
    """
    skill_data = {}
    
    for skill_id, skill_info in skills.items():
        # 提取技能等级数据
        levels = skill_info.get("level", {})
        
        # 构建Params数组
        params = []
        for level_key in sorted(levels.keys(), key=lambda x: int(x)):
            level_info = levels[level_key]
            param_list = level_info.get("param_list", [])
            params.append(param_list)
        
        # 提取技能类型
        skill_type = skill_info.get("type")

        # 构建技能数据
        skill_data[skill_id] = {
            "Live": {
                "Name": skill_info.get("name", ""),
                "MaxLevel": len(levels),
                "Type": skill_info.get("type_name", ""),
                "Tag": _map_skill_tag(skill_info.get("tag", "")),
                "Desc": format_description(skill_info.get("desc", ""), None),
                "Params": params,
                "BP": _convert_bp_value(skill_info),
                "SPAdd": skill_info.get("sp_base", 0) or 0,
                "AttackType": _map_attack_type(skill_type),
                "Stance": [x / 30 for x in skill_info.get("show_stance_list", [0, 0, 0])],
                "Icon": skill_info.get("icon", "").replace(".png", "") or f"SkillIcon_{character_id}_{_get_skill_icon_type(skill_info.get('type', ''))}"
            }
        }
    
    return skill_data


def convert_skill_data(character_id: str, skills: Dict[str, Any], skilltrees: Dict[str, Any] = None, version_key: str = "v6", memosprite: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    转换技能数据（支持多版本，包含忆灵数据）
    """
    skill_data = {}

    for skill_key, skill_info in skills.items():
        skill_id = int(skill_info.get("id", 0))
        if skill_id == 0:
            continue

        # 提取技能等级数据
        levels = skill_info.get("level", {})

        # 构建Params数组
        params = []
        for level_key in sorted(levels.keys(), key=lambda x: int(x)):
            level_info = levels[level_key]
            param_list = level_info.get("param_list", [])
            params.append(param_list)

        icon = ""
        if skilltrees:
            for point_data in skilltrees.values():
                for level_data in point_data.values():
                    if skill_id in level_data.get("level_up_skill_id", []):
                        icon = level_data.get("icon", "")
                        break
                if icon:
                    break

        # 使用 icon，如果没有则生成默认路径
        icon = icon.replace(".png","") if icon else f"SkillIcon_{character_id}_{_get_skill_icon_type(skill_info.get('type', ''))}"

        # 转换技能数据
        converted_skill = {
            "Name": skill_info.get("name", ""),
            "MaxLevel": 15,
            "Type": skill_info.get("type_name", ""),
            "Tag": _map_skill_tag(skill_info.get("tag", "")),
            "Desc": format_description(skill_info.get("desc", ""), None),
            "Params": params,
            "BP": _convert_bp_value(skill_info),
            "SPAdd": skill_info.get("sp_base", 0) or 0,
            "AttackType": _map_attack_type(skill_info.get("type", "")),
            "Stance": [x / 30 for x in skill_info.get("show_stance_list", [0, 0, 0])],
            "Icon": icon,
            "EE": []
        }

        skill_data[str(skill_id)] = converted_skill

    # 处理忆灵（memosprite）数据
    if memosprite and "skills" in memosprite:
        memosprite_skills = memosprite["skills"]
        for skill_key, skill_info in memosprite_skills.items():
            skill_id = int(skill_key)
            if skill_id == 0:
                continue

            # 提取技能等级数据
            levels = skill_info.get("level", {})

            # 构建Params数组
            params = []
            for level_key in sorted(levels.keys(), key=lambda x: int(x)):
                level_info = levels[level_key]
                param_list = level_info.get("param_list", [])
                params.append(param_list)

            # 生成忆灵技能图标
            icon = f"SkillIcon_{character_id}_Servant{skill_key[-1]}" if len(skill_key) > 0 else f"SkillIcon_{character_id}_Servant"

            # 转换忆灵技能数据
            converted_skill = {
                "Name": skill_info.get("name", ""),
                "MaxLevel": len(levels) if levels else 10,
                "Type": skill_info.get("type_name", ""),
                "Tag": _map_skill_tag(skill_info.get("tag", "")),
                "Desc": format_description(skill_info.get("desc", ""), None),
                "Params": params,
                "BP": _convert_bp_value(skill_info),
                "SPAdd": skill_info.get("sp_base", 0) or 0,
                "AttackType": "Servant",
                "Stance": [x / 30 for x in skill_info.get("show_stance_list", [0, 0, 0])],
                "Icon": icon,
                "EE": []
            }

            skill_data[str(skill_id)] = converted_skill

    return skill_data


def convert_skill_tree_data(character_id: str, skill_trees: Dict[str, Any], version_key: str = "v3") -> Dict[str, Any]:
    """
    转换天赋树数据（支持多版本）

    Args:
        character_id: 角色ID
        skill_trees: 天赋树数据
        version_key: 版本标识 (v1/v2/v3)
    """

    # 初始化天赋树数据结构（直接返回数据，不包含Live层级）
    tree_data: Dict[str, Dict[str, Any]] = {
        character_id: {
                          "Add": {},
                          "Tree1": {
                              "Name": "",
                              "Desc": "",
                              "Icon": ""
                          },
                          "Tree2": {
                              "Name": "",
                              "Desc": "",
                              "Icon": ""
                          },
                          "Tree3": {
                              "Name": "",
                              "Desc": "",
                              "Icon": ""
                          }
        }
    }

    # 提取天赋树节点信息
    tree_nodes = []

    # 查找point06, point07, point08中的天赋树节点
    for point_key in ["point06", "point07", "point08"]:
        if point_key in skill_trees:
            point_data = skill_trees[point_key]
            for level_key, level_data in point_data.items():
                point_name = level_data.get("point_name")
                point_desc = level_data.get("point_desc")
                param_list = level_data.get("param_list", [])
                icon = level_data.get("icon", "")

                if point_name and point_desc:
                    # 格式化描述文本（传入参数列表进行具体数值替换）
                    formatted_desc = format_description(point_desc, param_list)
                    tree_nodes.append({
                        "name": point_name,
                        "desc": formatted_desc,
                        "icon": icon.replace(".png", "")
                    })

    # 填充天赋树节点
    for i, node in enumerate(tree_nodes[:3]):
        tree_key = f"Tree{i + 1}"
        tree_data[character_id][tree_key] = {
            "Name": node["name"],
            "Desc": node["desc"],
            "Icon": node["icon"]
        }

    # 提取基础属性加成
    # 查找所有有status_add_list的节点，累加属性值
    for point_key, point_data in skill_trees.items():
        for level_key, level_data in point_data.items():
            status_add_list = level_data.get("status_add_list", [])
            for status in status_add_list:
                property_type = status.get("property_type")
                value = status.get("value", 0)

                if property_type:
                    if property_type not in tree_data[character_id]["Add"]:
                        tree_data[character_id]["Add"][property_type] = 0.0
                    tree_data[character_id]["Add"][property_type] += value

    return tree_data


def convert_rank_data(character_id: str, ranks: Dict[str, Any], version_key: str = "v3") -> Dict[str, Any]:
    """
    转换星魂数据
    """
    rank_data = {}

    for rank_key, rank_info in ranks.items():
        rank_id = int(rank_info.get("id", 0))
        if rank_id == 0:
            continue

        # 从rank_key获取rank值（"1", "2", "3"等）
        rank_value = int(rank_key)

        # 构建星魂数据（直接返回数据，不包含Live层级）
        rank_data[str(rank_id)] = {
            "Rank": rank_value,
            "Name": rank_info.get("name", ""),
            "Desc": format_description(rank_info.get("desc", ""), rank_info.get("param_list", [])),
            "Icon": rank_info.get("icon", "").replace(".png", "")
        }

    return rank_data


def _convert_material_list(material_list: list) -> Dict[str, int]:
    """
    将API的material_list转换为{ "item_id": item_num }格式
    """
    result = {}
    for mat in material_list:
        item_id = str(mat.get("item_id", ""))
        item_num = mat.get("item_num", 0)
        if item_id and item_num > 0:
            result[item_id] = item_num
    return result


def convert_mtc_data(character_id: str, character_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    转换培养材料数据（_mtc_）

    Args:
        character_id: 角色ID
        character_data: 完整的角色API数据

    Returns:
        _mtc_ 数据结构
    """
    mtc = {
        "Promotion": [{}, {}, {}, {}, {}, {}, {}, {}],
        "Skills": [],
        "Points": [],
        "Traces": []
    }

    stats = character_data.get("stats", {})
    skill_trees = character_data.get("skill_trees", {})
    skills = character_data.get("skills", {})

    # 1. 提取突破材料（Promotion）
    # stats.0.cost → Promotion[1], stats.5.cost → Promotion[6]
    for i in range(0, 7):
        stat_key = str(i)
        if stat_key in stats:
            cost = stats[stat_key].get("cost", [])
            if cost:
                mtc["Promotion"][i + 1] = _convert_material_list(cost)

    # 2. 识别技能点（point_type: 2 → Skills）
    # point_type: 1 → Points, point_type: 3 → Traces
    skill_points = {}  # {point_key: {levels...}}
    points_group = {}  # {point_name: {"levels": [...], "status_totals": {}}}  跨所有节点合并
    traces_data = []   # 额外能力数据

    for point_key, point_data in skill_trees.items():
        point_type = None
        for level_key, level_data in point_data.items():
            pt = level_data.get("point_type", 0)
            if pt:
                point_type = pt
                break

        if point_type == 2:
            skill_points[point_key] = point_data
        elif point_type == 1:
            # Points: 属性加成——收集所有节点，稍后按point_name合并
            for level_key, level_data in point_data.items():
                name = level_data.get("point_name", "")
                mat_list = level_data.get("material_list", [])
                if not name or not mat_list:
                    continue
                if name not in points_group:
                    points_group[name] = {"levels": [], "status_totals": {}}
                points_group[name]["levels"].append(mat_list)
                status_list = level_data.get("status_add_list", [])
                for s in status_list:
                    sname = s.get("name", "")
                    sval = s.get("value", 0)
                    if sname:
                        points_group[name]["status_totals"][sname] = \
                            points_group[name]["status_totals"].get(sname, 0) + sval
        elif point_type == 3:
            # Traces: 额外能力（只取第一级）
            first_level = point_data.get("1", {})
            name = first_level.get("point_name", "")
            mat_list = first_level.get("material_list", [])
            if name and mat_list:
                traces_data.append({
                    "Name": name,
                    "Mat": _convert_material_list(mat_list)
                })

    # 处理合并后的 Points
    for pname, pdata in points_group.items():
        merged_mat = {}
        for mat_list in pdata["levels"]:
            for mat in mat_list:
                item_id = str(mat.get("item_id", ""))
                item_num = mat.get("item_num", 0)
                if item_id and item_num > 0:
                    merged_mat[item_id] = merged_mat.get(item_id, 0) + item_num

        if merged_mat:
            display_name = pname
            if pdata["status_totals"]:
                stat_parts = []
                for sname, sval in pdata["status_totals"].items():
                    if sval * 100 > 100:
                        stat_parts.append(f"{sname} +{sval:.0f}")
                    else:
                        stat_parts.append(f"{sname} +{sval * 100:.1f}%")
                if stat_parts:
                    display_name = '，'.join(stat_parts)
            mtc["Points"].append({
                "Name": display_name,
                "Mat": merged_mat
            })

    mtc["Traces"] = traces_data

    # 3. 处理技能升级材料（Skills）
    # 按 point01~point05 顺序，对应普攻/战技/终结技/天赋/附加技
    for point_key in sorted(skill_points.keys()):
        point_data = skill_points[point_key]
        max_level = 0
        mats = []

        # 收集所有等级的材料
        level_data_map = {}
        for level_key, level_data in point_data.items():
            try:
                lvl = int(level_key)
            except ValueError:
                lvl = 0
            level_data_map[lvl] = level_data
            if lvl > max_level:
                max_level = lvl

        # 获取技能名称
        skill_name = ""
        for lvl in sorted(level_data_map.keys()):
            ld = level_data_map[lvl]
            skill_ids = ld.get("level_up_skill_id", [])
            if skill_ids:
                skill_id = str(skill_ids[0])
                if skill_id in skills:
                    skill_name = skills[skill_id].get("type_name", "")
                break

        if not skill_name:
            skill_name = point_key

        # 从第2级开始收集材料（第1级通常是默认解锁，material_list为空）
        for lvl in sorted(level_data_map.keys()):
            if lvl <= 1:
                continue
            ld = level_data_map[lvl]
            mat_list = ld.get("material_list", [])
            if mat_list:
                mats.append(_convert_material_list(mat_list))

        mtc["Skills"].append({
            "Name": skill_name,
            "Level": max_level,
            "Mats": mats
        })

    return {character_id: mtc}

def extract_avatar_base_info(character_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    从角色数据中提取avatar基本信息
    """
    # 直接从角色数据中提取基本信息
    avatar_info: Dict[str, Any] = {
        "name": character_data.get("name", ""),
        "desc": character_data.get("desc", ""),
        "rarity": character_data.get("rarity", ""),
        "sp_need": character_data.get("sp_need", 180),
        "base_type": character_data.get("base_type", ""),
        "damage_type": character_data.get("damage_type", ""),
        "avatar_vo_tag": character_data.get("avatar_vo_tag", "")
    }

    # 提取CV信息
    chara_info = character_data.get("chara_info", {})
    va_info = chara_info.get("va", {})
    avatar_info["cv"] = [
        va_info.get("chinese"),
        va_info.get("english"),
        va_info.get("japanese"),
        va_info.get("korean")
    ]

    # 提取阵营信息
    avatar_info["camp"] = chara_info.get("camp", 0)

    return avatar_info


def calculate_final_stats(character_data: Dict[str, Any], level: int = 80) -> Dict[str, float]:
    """
    计算角色的最终属性数值

    Args:
        character_data: 角色数据
        level: 角色等级（默认80级）

    Returns:
        包含最终属性数值的字典
    """
    stats_data = character_data.get("stats", {})

    # 获取最高等级的数据（通常是等级6）
    max_level_key = max([int(k) for k in stats_data.keys() if k.isdigit()], default=6)
    max_level_stats = stats_data.get(str(max_level_key), {})

    # 计算最终数值：base + (add × 等级)
    hp_base = max_level_stats.get("hp_base", 0)
    hp_add = max_level_stats.get("hp_add", 0)
    atk_base = max_level_stats.get("attack_base", 0)
    atk_add = max_level_stats.get("attack_add", 0)
    def_base = max_level_stats.get("defence_base", 0)
    def_add = max_level_stats.get("defence_add", 0)

    final_stats = {
        "HP": round(hp_base + (hp_add * level), 3),
        "ATK": round(atk_base + (atk_add * level), 3),
        "DEF": round(def_base + (def_add * level), 3),
        "SPD": max_level_stats.get("speed_base", 101),
        "Aggro": max_level_stats.get("base_aggro", 100)
    }

    return final_stats


def generate_avatar_basic_file(character_id: str, character_data: Dict[str, Any], skill_data: Dict[str, Any],
                               rank_data: Dict[str, Any], major_version: str) -> None:
    """
    生成avatar基本数据文件（id+basic.js）
    """
    output_file = os.path.join(OUTPUT_DIR, f"{character_id}basic.js")

    # 提取角色基本信息
    avatar_info = extract_avatar_base_info(character_data)

    # 构建技能ID列表
    skill_ids = list(skill_data.keys()) if skill_data else []
    rank_ids = list(rank_data.keys()) if rank_data else []

    # 转换数据格式
    # 稀有度转换：CombatPowerAvatarRarityType5 -> 5
    rarity_str = avatar_info.get("rarity", "")
    rarity = 5 if "Type5" in rarity_str else 4 if "Type4" in rarity_str else 3

    # 元素转换：Physical -> Phys
    damage_type = avatar_info.get("damage_type", "")
    element_map = {
        "Physical": "Phys",
        "Fire": "Fire",
        "Ice": "Ice",
        "Thunder": "Elec",
        "Wind": "Wind",
        "Quantum": "Quantum",
        "Imaginary": "Imaginary"
    }
    element = element_map.get(damage_type, "Phys")

    # 命途类型转换
    path_map = {
        "Elation": "Elation",
        "Warrior": "Destruction",
        "Hunt": "Hunt",
        "Mage": "Erudition",
        "Harmony": "Harmony",
        "Nihility": "Nihility",
        "Preservation": "Preservation",
        "Abundance": "Abundance",
        "Memory": "Remembrance"
    }
    path = path_map.get(avatar_info.get("base_type", ""), "Elation")

    # 构建avatar数据结构（根据Avatar.js的实际结构）
    avatar_data: Dict[str, Any] = {
        "_id": int(character_id),
        "Ver": f"{float(major_version) + 0.1:.1f}",  # 版本号，major_version + 0.1
        "Name": avatar_info.get("name", "null but why?"),
        "Desc": avatar_info.get("desc","null but why?").replace('\\n', '\n'),
        "Rarity": rarity,
        "Element": element,
        "Path": path,
        "SP": float(avatar_info.get("sp_need", -1)),
        "Skills": skill_ids,
        "BydSkills": [],  # 备用技能，通常为空
        "Ranks": rank_ids,
        "Icon": f"avatarshopicon/Avatar/{character_id}",
        "Pic": f"avatardrawcard/{character_id}.png",
        "Mat": [110263, 110431, 116003, 110508],  # 材料数据，需要从其他来源获取
        "Stats": calculate_final_stats(character_data),
        "CV": avatar_info.get("cv", [None, None, None, None]),
        "Camp": avatar_info.get("camp", 0),
        "V": ["Live"]
    }

    # 添加忆灵（Servant）数据
    memosprite = character_data.get("memosprite", {})
    if memosprite:
        servant_id = int(f"1{character_id}")  # 例如：1512 -> 11512
        servant_name = memosprite.get("name", "")
        servant_icon = memosprite.get("icon", "")
        # 提取icon路径中的文件名部分
        if servant_icon:
            # 例如: "SpriteOutput/ServantIconTeam/11512B.png" -> "servanticonteam/11512B.png"
            icon_parts = servant_icon.split("/")
            if len(icon_parts) >= 2:
                servant_icon = f"servanticonteam/{icon_parts[-1]}".replace(".png", ".png")
        else:
            servant_icon = f"servanticonteam/{servant_id}B.png"
        
        avatar_data["Servant"] = {
            "_id": servant_id,
            "Name": servant_name,
            "Icon": servant_icon,
            "Aggro": float(memosprite.get("aggro", 100))
        }

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("// Auto Generated\n\n")
        f.write(json.dumps(avatar_data, ensure_ascii=False, indent=4))
        f.write("\n")


AVATAR_JS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'sr', 'data', 'CH', 'Avatar.js')


def merge_avatar_to_avatar_js(character_id: str) -> str:
    """
    将生成的avatar基础数据插入到 Avatar.js 的 _avatar 对象中
    新条目插入到对象头部 (var _avatar = { 之后)

    Args:
        character_id: 角色ID
    Returns:
        拼接结果描述
    """
    basic_file = os.path.join(OUTPUT_DIR, f"{character_id}basic.js")
    avatar_js = AVATAR_JS_PATH

    if not os.path.exists(basic_file):
        return ""

    with open(basic_file, 'r', encoding='utf-8') as f:
        content = f.read()

    start = content.find('{')
    end = content.rfind('}')
    if start < 0 or end < 0:
        return ""
    avatar_entry = json.loads(content[start:end+1])
    avatar_id = str(avatar_entry.get('_id', ''))

    if not os.path.exists(avatar_js):
        return f"错误：找不到 Avatar.js ({avatar_js})"

    with open(avatar_js, 'r', encoding='utf-8') as f:
        js_content = f.read()

    if f'"{avatar_id}":' in js_content:
        return "角色条目已存在，无需拼接"

    new_json = json.dumps(avatar_entry, ensure_ascii=False, indent=4)
    new_json = '\n'.join('    ' + line for line in new_json.split('\n'))

    new_entry = f'    "{avatar_id}": {new_json},\n'

    pattern = 'var _avatar = {\n'
    if pattern not in js_content:
        return "错误：无法定位 _avatar 对象起始位置"
    js_content = js_content.replace(pattern, pattern + new_entry, 1)

    with open(avatar_js, 'w', encoding='utf-8') as f:
        f.write(js_content)

    return f"已自动拼接角色 {avatar_id} 到 Avatar.js（头部）"


def generate_js_file(character_id: str, all_versions_skill_data: Dict[str, Any], all_versions_tree_data: Dict[str, Any],
                     all_versions_rank_data: Dict[str, Any], versions: Dict[str, str],
                     mtc_data: Dict[str, Any] = None, recommend_data: Dict[str, Any] = None,
                     output_dir: str = None) -> None:
    """
    生成角色详情JS文件（支持多版本）

    Args:
        character_id: 角色ID
        all_versions_skill_data: 所有版本的技能数据
        all_versions_tree_data: 所有版本的天赋树数据
        all_versions_rank_data: 所有版本的星魂数据
        versions: 版本配置字典，格式: {"v1": "4.3.51", "v2": "4.3.52"}
        mtc_data: 培养材料数据（可选）
        output_dir: 输出目录（默认OUTPUT_DIR2）
    """
    if output_dir is None:
        output_dir = OUTPUT_DIR2
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{character_id}.js")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("// Auto Generated\n\n")

        # 生成版本列表
        version_list = list(versions.keys())
        f.write("var _versions_ = {\n")
        f.write(f'    "{character_id}": {json.dumps(version_list, ensure_ascii=False)}\n')
        f.write("}\n\n")

        # 生成技能数据（多版本）
        f.write("var _avatarskill_ = {\n")
        # 获取第一个有效的版本键作为遍历基准
        first_version = list(all_versions_skill_data.keys())[0] if all_versions_skill_data else ""
        for skill_id in all_versions_skill_data.get(first_version, {}).keys():
            f.write(f'    "{skill_id}": {{\n')
            for version_key in versions.keys():
                if version_key in all_versions_skill_data and skill_id in all_versions_skill_data[version_key]:
                    # 优化Params格式，确保在一行内显示
                    skill_data = all_versions_skill_data[version_key][skill_id]
                    if "Params" in skill_data:
                        # 保存原始Params
                        original_params = skill_data["Params"]
                        # 生成紧凑格式的Params字符串
                        params_str = json.dumps(original_params, ensure_ascii=False, separators=(',', ':'))
                        # 先将Params替换为字符串
                        skill_data["Params"] = params_str
                        # 生成技能数据的JSON字符串
                        skill_json = json.dumps(skill_data, ensure_ascii=False, indent=8)
                        # 移除Params字符串的引号，使其成为数组
                        skill_json = skill_json.replace(f'"{params_str}"', params_str)
                        f.write(f'        "{version_key}": {skill_json},\n')
                    else:
                        f.write(f'        "{version_key}": {json.dumps(skill_data, ensure_ascii=False, indent=8)},\n')
            f.seek(f.tell() - 2)
            f.write("\n    },\n")
        f.write("}\n\n")

        # 生成天赋树数据（多版本）
        f.write("var _avatarskilltree_ = {\n")
        first_version = list(all_versions_tree_data.keys())[0] if all_versions_tree_data else ""
        for tree_id in all_versions_tree_data.get(first_version, {}).keys():
            f.write(f'    "{tree_id}": {{\n')
            for version_key in versions.keys():
                if version_key in all_versions_tree_data and tree_id in all_versions_tree_data[version_key]:
                    tree_data = all_versions_tree_data[version_key][tree_id]
                    # 移除Live层级，直接使用版本数据
                    if "Live" in tree_data:
                        tree_data = tree_data["Live"]
                    f.write(f'        "{version_key}": {json.dumps(tree_data, ensure_ascii=False, indent=8)},\n')
            f.seek(f.tell() - 2)
            f.write("\n    },\n")
        f.write("}\n\n")

        # 生成星魂数据（多版本）
        f.write("var _avatarrank_ = {\n")
        first_version = list(all_versions_rank_data.keys())[0] if all_versions_rank_data else ""
        for rank_id in all_versions_rank_data.get(first_version, {}).keys():
            f.write(f'    "{rank_id}": {{\n')
            for version_key in versions.keys():
                if version_key in all_versions_rank_data and rank_id in all_versions_rank_data[version_key]:
                    rank_data = all_versions_rank_data[version_key][rank_id]
                    # 移除Live层级，直接使用版本数据
                    if "Live" in rank_data:
                        rank_data = rank_data["Live"]
                    f.write(f'        "{version_key}": {json.dumps(rank_data, ensure_ascii=False, indent=8)},\n')
            f.seek(f.tell() - 2)
            f.write("\n    },\n")
        f.write("}\n\n")


        # 其他固定数据（保持不变）
        f.write("var _story_ = [\n")
        f.write("    {\n")
        f.write('        "Name": "",\n')
        f.write('        "Desc": ""\n')
        f.write("    }\n")
        f.write("]\n\n")

        f.write("var _voice_ = [\n")
        f.write("    {\n")
        f.write('        "Name": "",\n')
        f.write('        "Desc": ""\n')
        f.write("    }\n")
        f.write("]\n\n")

        f.write("var _notes_ = [\n")
        f.write("    {\n")
        f.write('        "Name": "",\n')
        f.write('        "Desc": ""\n')
        f.write("    }\n")
        f.write("]\n\n")

        f.write("var _adiff_ = [\n")
        f.write("    {\n")
        f.write('        "Name": "",\n')
        f.write('        "Desc": ""\n')
        f.write("    }\n")
        f.write("]\n\n")

        f.write("var _mtc_ = ")
        if mtc_data:
            f.write(json.dumps(mtc_data, ensure_ascii=False, indent=4))
            f.write("\n")
        else:
            f.write("[\n")
            f.write("    {\n")
            f.write('        "Name": "",\n')
            f.write('        "Desc": ""\n')
            f.write("    }\n")
            f.write("]\n")

        f.write("\nvar _recommend_ = ")
        if recommend_data:
            f.write(json.dumps(recommend_data, ensure_ascii=False, indent=4))
            f.write("\n")
        else:
            f.write("{\n")
            f.write('    "' + character_id + '": {\n')
            f.write('        "relics": {},\n')
            f.write('        "lightcones": [],\n')
            f.write('        "teams": []\n')
            f.write('    }\n')
            f.write("}\n")


def generate_character_data(character_id: str, major_version: str = None, minor_versions: list = None,
                            debug: bool = False) -> str:
    """
    封装的生成角色数据的函数，供其他程序调用

    Args:
        character_id: 角色ID
        major_version: 大版本号，例如 "4.3"
        minor_versions: 小版本号列表，例如 [".51", ".52"]
        debug: 调试模式，输出到tempoutput而不走合并流程
    """

    # 参数检查：必须传入所有参数
    if character_id is None or major_version is None or minor_versions is None:
        return "错误：必须传入 character_id、major_version 和 minor_versions 参数"
    
    # 组装 versions 字典
    versions = {}
    for i, minor_ver in enumerate(minor_versions, 1):
        versions[f"v{i}"] = f"{major_version}{minor_ver}"

    # 下载所有版本的角色数据
    all_versions_data = download_all_versions_data(character_id, versions)

    if not all_versions_data:
        return "无法下载任何版本的角色数据，退出程序"

    # 初始化所有版本的数据容器
    all_versions_skill_data = {}
    all_versions_tree_data = {}
    all_versions_rank_data = {}

    # 处理每个版本的数据
    for version_key, character_data in all_versions_data.items():

        # 提取技能、天赋树、星魂数据
        skills = character_data.get("skills", {})
        skill_trees = character_data.get("skill_trees", {})
        ranks = character_data.get("ranks", {})
        memosprite = character_data.get("memosprite", {})

        # 转换数据
        all_versions_skill_data[version_key] = convert_skill_data(character_id, skills, skill_trees, version_key, memosprite)
        all_versions_tree_data[version_key] = convert_skill_tree_data(character_id, skill_trees, version_key)
        all_versions_rank_data[version_key] = convert_rank_data(character_id, ranks, version_key)

    # 生成角色详情JS文件（多版本）
    # 使用最新版本的数据提取培养材料
    mtc_data = None
    recommend_data = None
    if versions:
        latest_version = list(versions.keys())[-1]
        if latest_version in all_versions_data:
            char_data = all_versions_data[latest_version]
            mtc_data = convert_mtc_data(character_id, char_data)
            recommend_data = {
                character_id: {
                    "relics": char_data.get("relics", {}),
                    "lightcones": char_data.get("lightcones", []),
                    "teams": char_data.get("teams", [])
                }
            }
    output_dir = DEBUG_OUTPUT_DIR if debug else OUTPUT_DIR2
    generate_js_file(character_id, all_versions_skill_data, all_versions_tree_data, all_versions_rank_data,
                     versions, mtc_data, recommend_data, output_dir=output_dir)

    if debug:
        return f"角色 {character_id} 调试数据已生成至 {output_dir}/{character_id}.js"

    # 生成avatar基本数据文件（使用最新版本的数据）
    if versions:
        latest_version = list(versions.keys())[-1]
        if latest_version in all_versions_data:
            generate_avatar_basic_file(character_id, all_versions_data[latest_version],
                                       all_versions_skill_data[latest_version],
                                       all_versions_rank_data[latest_version],
                                       major_version)

    # 自动拼接到Avatar.js
    merge_msg = merge_avatar_to_avatar_js(character_id)
    result = f"角色 {character_id} 数据生成完成！"
    if merge_msg:
        result += "\n" + merge_msg
    return result

def main():
    idlist = ["1508", "1509", "1510"]
    for i in idlist:
        generate_character_data(i, major_version="4.3", minor_versions=[".51", ".52"])


def main_debug():
    """调试模式：输出到tempoutput，不走合并流程"""
    idlist = ["1505", "1506", "1507","1508", "1509", "1510"]
    for i in idlist:
        result = generate_character_data(i, major_version="4.4", minor_versions=[".51"], debug=True)
        print(result)


if __name__ == "__main__":
    main_debug()