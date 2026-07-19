#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动下载并转换混沌回忆数据脚本
功能：从 nanoka.cc 下载 maze 数据，结合本地怪物数据库，转换为现有 JS 格式

使用方法：
    python hsr_trans_chaos.py                         # 交互模式（输入ID和倍率）
    python hsr_trans_chaos.py <ID> --default          # 指定ID，使用默认倍率
    python hsr_trans_chaos.py <ID> 1.0 1.0 ...        # 指定ID和12层倍率

示例：
    python hsr_trans_chaos.py 1033 --default
    python hsr_trans_chaos.py 1034 1.0 1.0 1.0 1.0 1.0 1.1 1.1 1.0 1.0 1.4 2.0 5.2
"""

import os
import sys
import json
import re
import requests
from typing import Dict, Any, Optional, List


# 获取脚本所在目录的父目录（项目根目录）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

BASE_URL = "https://static.nanoka.cc/hsr"
LANGUAGE = "zh"
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "tempdata")
MONSTER_DB_PATH = os.path.join(PROJECT_ROOT, "data", "CH", "Monster_1.js")
LEVEL_CURVES_PATH = os.path.join(PROJECT_ROOT, "data", "LevelCurves.js")


CHAOS_HARD_LEVEL_GROUP = "3"


# 默认环境HP倍率表（从 Chaos_1.js 实际数据提取）
DEFAULT_HP_RATIO_TABLE = {
    273: 1.0,    # 第1-5层（精英组ID 273，无额外HP字段）
    274: 1.1,    # 第6层（Level 80）
    275: 1.1,    # 第7层（Level 82）
    276: 1.4,    # 第10层（Level 90）
    277: 2.0,    # 第11层（Level 92）
    278: 5.2,    # 第12层（Level 95）
}


# 楼层与精英组ID对应表
FLOOR_ELITE_GROUP_MAP = {
    1: 273,
    2: 273,
    3: 273,
    4: 273,
    5: 273,
    6: 274,      # Level 80, HP: 1.1
    7: 275,      # Level 82, HP: 1.1
    8: 273,      # Level 85, 默认1.0
    9: 273,      # Level 88, 默认1.0
    10: 276,     # Level 90, HP: 1.4
    11: 277,     # Level 92, HP: 2.0
    12: 293,     # Level 95, HP: 5.2（新版本精英组ID）
}

# 默认环境HP倍率表（从 Chaos_1.js 实际数据提取）
DEFAULT_HP_RATIO_TABLE = {
    273: 1.0,    # 第1-5层（精英组ID 273，无额外HP字段）
    274: 1.1,    # 第6层（Level 80）
    275: 1.1,    # 第7层（Level 82）
    276: 1.4,    # 第10层（Level 90）
    277: 2.0,    # 第11层（Level 92）
    278: 5.2,    # 第12层旧精英组（Level 95）
    293: 5.2,    # 第12层新精英组（Level 95）
}


# 楼层与等级对应表
FLOOR_LEVEL_MAP = {
    1: 68,
    2: 70,
    3: 73,
    4: 75,
    5: 78,
    6: 80,
    7: 82,
    8: 85,
    9: 88,
    10: 90,
    11: 92,
    12: 95,
}


def remove_trailing_commas(json_str: str) -> str:
    """
    移除 JSON 字符串中的尾随逗号
    """
    # 移除 }, 后面的逗号
    json_str = re.sub(r',\s*}', '}', json_str)
    # 移除 ], 后面的逗号
    json_str = re.sub(r',\s*]', ']', json_str)
    return json_str


def load_local_monster_db() -> Dict[str, Any]:
    """
    加载本地怪物数据库
    """
    monster_data = {}
    
    if os.path.exists(MONSTER_DB_PATH):
        with open(MONSTER_DB_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        
        start = content.find('var _monster = {')
        if start != -1:
            end = content.find('var _monsterlist')
            if end != -1:
                monster_str = content[start + len('var _monster = '):end]
                monster_str = remove_trailing_commas(monster_str)
                try:
                    monster_data = json.loads(monster_str)
                    print(f"成功加载本地怪物数据库: {len(monster_data)} 条记录")
                except json.JSONDecodeError as e:
                    print(f"解析怪物数据库失败: {e}")
            else:
                print("未找到 _monsterlist 变量")
        else:
            print("未找到 _monster 变量")
    
    monster_2_path = os.path.join(PROJECT_ROOT, "data", "CH", "Monster_2.js")
    if os.path.exists(monster_2_path):
        with open(monster_2_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        start = content.find('var _monster = {')
        if start != -1:
            end = content.find('var _monsterlist')
            if end != -1:
                monster_str = content[start + len('var _monster = '):end]
                monster_str = remove_trailing_commas(monster_str)
                try:
                    monster_data_2 = json.loads(monster_str)
                    monster_data.update(monster_data_2)
                    print(f"成功加载 Monster_2.js: {len(monster_data_2)} 条记录")
                except json.JSONDecodeError as e:
                    print(f"解析 Monster_2.js 失败: {e}")
    
    print(f"最终怪物数据库大小: {len(monster_data)}")
    return monster_data


def load_level_curves() -> Dict[str, Any]:
    """
    加载 LevelCurves.js 数据
    """
    result = {
        "hardlevelgroup": {},
        "elitegroup": {}
    }
    
    if os.path.exists(LEVEL_CURVES_PATH):
        with open(LEVEL_CURVES_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找 _hardlevelgroup 变量
        start = content.find('var _hardlevelgroup = {')
        if start != -1:
            end = content.find('var _elitegroup')
            if end != -1:
                curves_str = content[start + len('var _hardlevelgroup = '):end]
                curves_str = remove_trailing_commas(curves_str)
                try:
                    result["hardlevelgroup"] = json.loads(curves_str)
                    print(f"成功加载 _hardlevelgroup，包含 {len(result['hardlevelgroup'])} 个组")
                    
                    # 检查是否包含 HardLevelGroup = 3
                    if "3" in result["hardlevelgroup"]:
                        print(f"HardLevelGroup 3 包含 {len(result['hardlevelgroup']['3'])} 个等级")
                        # 检查等级68（索引67）
                        if "67" in result["hardlevelgroup"]["3"]:
                            hp_val = result["hardlevelgroup"]["3"]["67"]["HP"]
                            print(f"等级68 的基础HP: {hp_val}")
                except json.JSONDecodeError as e:
                    print(f"解析 _hardlevelgroup 失败: {e}")
            else:
                print("未找到 _elitegroup 变量")
        else:
            print("未找到 _hardlevelgroup 变量")
    
    return result


def download_maze_data(version: str, maze_id: str) -> Optional[List[Dict[str, Any]]]:
    """
    下载混沌回忆数据
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    local_file = os.path.join(OUTPUT_DIR, f"maze_{maze_id}_{version}.json")
    
    if os.path.exists(local_file):
        try:
            with open(local_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"从本地缓存加载迷宫数据 {maze_id} 的 {version} 版本")
            return data
        except Exception as e:
            print(f"读取本地缓存失败: {e}")
    
    url = f"{BASE_URL}/{version}/{LANGUAGE}/maze/{maze_id}.json"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        data = response.json()
        print(f"成功下载迷宫数据 {maze_id} 的 {version} 版本")
        
        try:
            with open(local_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"已缓存到本地: {local_file}")
        except Exception as e:
            print(f"缓存失败: {e}")
        
        return data
    
    except requests.exceptions.RequestException as e:
        print(f"下载失败: {e}")
        return None


def format_buff_desc(desc: str, param: List[float]) -> str:
    """
    格式化 Buff 描述文本
    """
    if not desc:
        return ""
    
    desc = desc.replace('<color=#f29e38ff>', '<color style=\'color:#f29e38;\'>')
    desc = desc.replace('</color>', '</color>')
    desc = desc.replace('<unbreak>', '')
    desc = desc.replace('</unbreak>', '')
    desc = desc.replace('\\n', '<br>')
    
    for i, p in enumerate(param, 1):
        placeholder = f'#{i}[i]'
        if p < 1 and p != 0:
            value_str = f"{p * 100:.0f}"
        else:
            value_str = f"{p:.0f}"
        desc = desc.replace(placeholder, value_str)
    
    return desc


def calculate_monster_hp(
    monster_id: int,
    monster_db: Dict[str, Any],
    level: int,
    level_curves: Dict[str, Any],
    hp_ratio: float
) -> int:
    """
    计算怪物的实际HP（混沌回忆专用公式）
    
    公式: HP = 混沌回忆基础HP × 怪物HP倍数 × 环境HP倍率
    """
    level_index = level - 1
    
    monster_info = monster_db.get(str(monster_id), {})
    stats = monster_info.get("Stats", {})
    
    monster_hp_ratio = stats.get("HP", 1.0)
    
    hardlevelgroup = level_curves.get("hardlevelgroup", {})
    chaos_data = hardlevelgroup.get(CHAOS_HARD_LEVEL_GROUP, {})
    level_data = chaos_data.get(str(level_index), {})
    chaos_base_hp = level_data.get("HP", 1000)
    
    hp = int(chaos_base_hp * monster_hp_ratio * hp_ratio)
    
    return hp


def calculate_monster_spd(
    monster_id: int,
    monster_db: Dict[str, Any],
    level: int,
    level_curves: Dict[str, Any]
) -> int:
    """
    计算怪物的实际SPD
    
    公式: SPD = 怪物基础SPD × 等级SPD系数
    """
    level_index = level - 1
    
    monster_info = monster_db.get(str(monster_id), {})
    stats = monster_info.get("Stats", {})
    
    monster_spd = stats.get("SPD", 100)
    
    hardlevelgroup = level_curves.get("hardlevelgroup", {})
    chaos_data = hardlevelgroup.get(CHAOS_HARD_LEVEL_GROUP, {})
    level_data = chaos_data.get(str(level_index), {})
    spd_multiplier = level_data.get("SPD", 1.0)
    
    spd = int(monster_spd * spd_multiplier)
    
    return spd


def convert_monster_data(
    monster_list: List[Dict[str, int]], 
    monster_db: Dict[str, Any],
    level: int,
    level_curves: Dict[str, Any],
    hp_ratio: float
) -> List[List[Dict[str, Any]]]:
    """
    转换怪物数据
    """
    converted = []
    
    for wave_idx, wave in enumerate(monster_list):
        wave_monsters = []
        for key in sorted(wave.keys()):
            monster_id = wave[key]
            
            monster_info_db = monster_db.get(str(monster_id), {})
            stats = monster_info_db.get("Stats", {})
            
            hp = calculate_monster_hp(
                monster_id, monster_db, level, level_curves, hp_ratio
            )
            
            spd = calculate_monster_spd(
                monster_id, monster_db, level, level_curves
            )
            stance = int(stats.get("Stance", 5))
            
            monster_data = {
                "ID": monster_id,
                "HP": hp,
                "SPD": spd,
                "Stance": stance
            }
            
            hp_count = monster_info_db.get("HPCount", 0)
            if hp_count > 1:
                monster_data["HPCount"] = hp_count
            
            wave_monsters.append(monster_data)
        converted.append(wave_monsters)
    
    return converted


def convert_floor_data(
    floor: Dict[str, Any], 
    floor_num: int,
    monster_db: Dict[str, Any],
    level_curves: Dict[str, Any],
    floor_hp_ratio: float  # 直接使用楼层倍率，而不是通过精英组ID查找
) -> Dict[str, Any]:
    """
    转换单个楼层数据
    """
    damage_type_map = {
        "Physical": "Phys",
        "Fire": "Fire",
        "Ice": "Ice",
        "Thunder": "Elec",
        "Wind": "Wind",
        "Quantum": "Quantum",
        "Imaginary": "Imaginary"
    }
    
    elem_upper = [damage_type_map.get(d, d) for d in floor.get("damage_type1", [])]
    elem_lower = [damage_type_map.get(d, d) for d in floor.get("damage_type2", [])]
    
    upper_event = floor.get("event_id_list1", [{}])[0]
    lower_event = floor.get("event_id_list2", [{}])[0]
    
    upper_level = upper_event.get("level", FLOOR_LEVEL_MAP.get(floor_num, 68))
    lower_level = lower_event.get("level", FLOOR_LEVEL_MAP.get(floor_num, 68))
    upper_elite_group = upper_event.get("elite_group", FLOOR_ELITE_GROUP_MAP.get(floor_num, 273))
    lower_elite_group = lower_event.get("elite_group", FLOOR_ELITE_GROUP_MAP.get(floor_num, 273))
    
    # 直接使用楼层倍率
    upper_hp_ratio = floor_hp_ratio
    lower_hp_ratio = floor_hp_ratio
    
    upper_monsters = []
    if upper_event:
        upper_monsters.append({
            "_id": upper_event.get("stage_id", 0),
            "Level": upper_level,
            "HardLevelGroup": 3,
            "EliteGroup": {
                "ID": upper_elite_group,
                "HP": upper_hp_ratio
            },
            "Monsters": convert_monster_data(
                upper_event.get("monster_list", []), 
                monster_db, 
                upper_level,
                level_curves,
                upper_hp_ratio
            )
        })
    
    lower_monsters = []
    if lower_event:
        lower_monsters.append({
            "_id": lower_event.get("stage_id", 0),
            "Level": lower_level,
            "HardLevelGroup": 3,
            "EliteGroup": {
                "ID": lower_elite_group,
                "HP": lower_hp_ratio
            },
            "Monsters": convert_monster_data(
                lower_event.get("monster_list", []), 
                monster_db, 
                lower_level,
                level_curves,
                lower_hp_ratio
            )
        })
    
    hp_single = 0
    for wave in upper_monsters[0].get("Monsters", []) if upper_monsters else []:
        for m in wave:
            hp_single += m["HP"] * m.get("HPCount", 1)
    for wave in lower_monsters[0].get("Monsters", []) if lower_monsters else []:
        for m in wave:
            hp_single += m["HP"] * m.get("HPCount", 1)
    
    hp_multi = int(hp_single * 0.8)
    
    return {
        "Floor": floor_num,
        "ElemUpper": elem_upper,
        "ElemLower": elem_lower,
        "HPSingle": hp_single,
        "HPMulti": hp_multi,
        "Upper": upper_monsters,
        "Lower": lower_monsters
    }


def convert_maze_data(
    maze_data: List[Dict[str, Any]], 
    maze_id: str,
    monster_db: Dict[str, Any],
    level_curves: Dict[str, Any],
    floor_hp_ratios: List[float]  # 楼层倍率列表：[第1层倍率, 第2层倍率, ..., 第12层倍率]
) -> Dict[str, Any]:
    """
    转换完整的迷宫数据
    """
    if not maze_data:
        return {}
    
    first_floor = maze_data[0]
    group_name = first_floor.get("group_name", "未知")
    
    buff_id = int(maze_id) * 1000 + 146
    
    buff_desc = format_buff_desc(first_floor.get("desc", ""), first_floor.get("param", []))
    
    floors = []
    for i, floor in enumerate(maze_data, 1):
        # 获取该楼层的倍率
        floor_ratio = floor_hp_ratios[i - 1] if i <= len(floor_hp_ratios) else 1.0
        floors.append(convert_floor_data(floor, i, monster_db, level_curves, floor_ratio))
    
    return {
        "_id": int(maze_id),
        "Name": group_name,
        "Buff": {
            "_id": buff_id,
            "Name": "记忆紊流",
            "Desc": buff_desc
        },
        "Floors": floors
    }


def generate_js_file(maze_id: str, converted_data: Dict[str, Any]) -> None:
    """
    生成 JS 文件
    """
    output_file = os.path.join(OUTPUT_DIR, f"Chaos_{maze_id}.js")
    
    # 生成JSON字符串，使用8空格缩进
    json_str = json.dumps(converted_data, ensure_ascii=False, indent=4)
    
    # 调整缩进：将每行增加4个空格（除了第一行）
    lines = json_str.split('\n')
    adjusted_lines = []
    for i, line in enumerate(lines):
        if i == 0:
            adjusted_lines.append("    " + line)  # 第一行加4空格
        else:
            adjusted_lines.append("    " + line)  # 其他行也加4空格
    
    adjusted_json = '\n'.join(adjusted_lines)
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("// Auto Generated\n\n")
        f.write("var _chaos = [\n")
        f.write(adjusted_json + "\n")
        f.write("]\n\n")
        
        f.write("// Schedule\n")
        f.write("var _chaosschedule = [\n")
        f.write(f"    {{\n")
        f.write(f'        "_id": {maze_id},\n')
        f.write(f'        "Name": "{converted_data["Name"]}",\n')
        f.write('        "Time": ""\n')
        f.write("    }\n")
        f.write("]\n\n")
        
        f.write("// HP Data\n")
        f.write("var _chaoshp = {}\n\n")
        
        f.write("// Dict\n")
        f.write(f'var _chaosdict = {{"{maze_id}": 0}}\n')
    
    print(f"成功生成JS文件: {output_file}")


def generate_chaos_data(maze_id: str, version: str, floor_hp_ratios: List[float]) -> str:
    """
    封装的生成混沌回忆数据的函数
    
    Args:
        maze_id: 混沌回忆ID
        version: nanoka.cc版本号
        floor_hp_ratios: 楼层HP倍率列表，格式: [第1层倍率, 第2层倍率, ..., 第12层倍率]
    """
    if maze_id is None or version is None:
        return "错误：必须传入 maze_id 和 version 参数"
    
    if not floor_hp_ratios or len(floor_hp_ratios) < 12:
        return "错误：必须传入12个楼层的环境HP倍率"
    
    print(f"开始处理混沌回忆 {maze_id}...")
    
    monster_db = load_local_monster_db()
    level_curves = load_level_curves()
    
    maze_data = download_maze_data(version, maze_id)
    
    if not maze_data:
        return "无法获取迷宫数据，退出"
    
    converted_data = convert_maze_data(maze_data, maze_id, monster_db, level_curves, floor_hp_ratios)
    
    generate_js_file(maze_id, converted_data)
    
    return f"混沌回忆 {maze_id} 数据生成完成！"


# 默认楼层HP倍率列表（第1层到第12层）
DEFAULT_FLOOR_HP_RATIOS = [
    1.0,   # 第1层 (Lv.68)
    1.0,   # 第2层 (Lv.70)
    1.0,   # 第3层 (Lv.73)
    1.0,   # 第4层 (Lv.75)
    1.0,   # 第5层 (Lv.78)
    1.1,   # 第6层 (Lv.80)
    1.1,   # 第7层 (Lv.82)
    1.0,   # 第8层 (Lv.85)
    1.0,   # 第9层 (Lv.88)
    1.4,   # 第10层 (Lv.90)
    2.0,   # 第11层 (Lv.92)
    5.2,   # 第12层 (Lv.95)
]


def get_floor_hp_ratios(use_default: bool = False) -> List[float]:
    """
    获取用户输入的楼层HP倍率列表
    
    Args:
        use_default: 是否直接使用默认配置，跳过交互
    
    Returns:
        楼层HP倍率列表: [第1层倍率, 第2层倍率, ..., 第12层倍率]
    """
    if use_default:
        print("使用默认倍率配置")
        return DEFAULT_FLOOR_HP_RATIOS
    
    print("\n" + "="*60)
    print("环境HP倍率配置")
    print("="*60)
    
    # 显示默认配置
    print("默认倍率配置:")
    for floor in range(1, 13):
        ratio = DEFAULT_FLOOR_HP_RATIOS[floor - 1]
        level = FLOOR_LEVEL_MAP.get(floor, 68)
        print(f"  第{floor}层 (Lv.{level}): 倍率 {ratio}x")
    
    print("\n是否使用默认配置？")
    use_default_input = input("输入 'y' 使用默认配置，其他键自定义: ").strip().lower()
    
    if use_default_input == 'y':
        print("使用默认倍率配置")
        return DEFAULT_FLOOR_HP_RATIOS
    
    # 用户自定义配置
    print("\n自定义倍率配置:")
    custom_ratios = []
    
    for floor in range(1, 13):
        default_ratio = DEFAULT_FLOOR_HP_RATIOS[floor - 1]
        level = FLOOR_LEVEL_MAP.get(floor, 68)
        
        while True:
            try:
                ratio_str = input(f"  第{floor}层 (Lv.{level}): 默认{default_ratio}x, 输入新倍率(直接回车使用默认): ")
                if ratio_str.strip() == "":
                    ratio = default_ratio
                else:
                    ratio = float(ratio_str)
                break
            except ValueError:
                print("  请输入有效数字")
        
        custom_ratios.append(ratio)
    
    return custom_ratios


def main():
    """
    主函数
    """
    # 默认版本号
    version = "4.3.52"
    
    print("="*60)
    print("混沌回忆数据转换工具")
    print("="*60)
    
    # 解析命令行参数
    maze_id = None
    floor_hp_ratios = None
    
    if len(sys.argv) > 1:
        # 第一个参数是ID或--default
        if sys.argv[1] == "--default":
            # 无ID参数，使用默认配置，需要交互输入ID
            print("请输入混沌回忆ID:")
            maze_id = input("ID: ").strip()
            floor_hp_ratios = get_floor_hp_ratios(use_default=True)
        else:
            # 第一个参数是ID
            maze_id = sys.argv[1]
            
            if len(sys.argv) > 2:
                if sys.argv[2] == "--default":
                    print(f"目标ID: {maze_id}")
                    print(f"版本: {version}")
                    floor_hp_ratios = get_floor_hp_ratios(use_default=True)
                elif len(sys.argv) >= 14:
                    # 从命令行参数获取每层的环境倍率
                    # 参数顺序: ID 第1层 第2层 ... 第12层
                    try:
                        floor_hp_ratios = [float(x) for x in sys.argv[2:14]]
                        print(f"目标ID: {maze_id}")
                        print(f"版本: {version}")
                        print("使用命令行指定的环境倍率:")
                        for floor, ratio in enumerate(floor_hp_ratios, 1):
                            level = FLOOR_LEVEL_MAP.get(floor, 68)
                            print(f"  第{floor}层 (Lv.{level}): {ratio}x")
                    except ValueError:
                        print("错误：环境倍率必须是数字")
                        print("使用方法: python hsr_trans_chaos.py <ID> 1.0 1.0 1.0 ...")
                        return
                else:
                    print("错误：需要提供12个环境倍率值")
                    print("使用方法: python hsr_trans_chaos.py <ID> 1.0 1.0 1.0 ...")
                    return
            else:
                # 只有ID参数，进入交互模式输入倍率
                print(f"目标ID: {maze_id}")
                print(f"版本: {version}")
                floor_hp_ratios = get_floor_hp_ratios()
    else:
        # 无参数，完全交互模式
        print("请输入混沌回忆ID:")
        maze_id = input("ID: ").strip()
        print(f"版本: {version}")
        floor_hp_ratios = get_floor_hp_ratios()
    
    if not maze_id:
        print("错误：必须提供混沌回忆ID")
        return
    
    print("\n" + "="*60)
    print("当前使用的环境HP倍率:")
    for floor in range(1, 13):
        ratio = floor_hp_ratios[floor - 1]
        level = FLOOR_LEVEL_MAP.get(floor, 68)
        print(f"  第{floor}层 (Lv.{level}): {ratio}x")
    print("="*60)
    
    result = generate_chaos_data(maze_id, version, floor_hp_ratios)
    print(result)


if __name__ == "__main__":
    main()