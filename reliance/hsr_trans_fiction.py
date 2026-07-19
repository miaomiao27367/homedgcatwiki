#!/usr/bin/env python3
import os
import sys
import json
import re
import requests
from typing import Dict, Any, Optional, List

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

BASE_URL = "https://static.nanoka.cc/hsr"
LANGUAGE = "zh"
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "tempdata")
MONSTER_DB_PATH = os.path.join(PROJECT_ROOT, "data", "CH", "Monster_1.js")
MONSTER_DB_PATH_2 = os.path.join(PROJECT_ROOT, "data", "CH", "Monster_2.js")
LEVEL_CURVES_PATH = os.path.join(PROJECT_ROOT, "data", "LevelCurves.js")


def remove_trailing_commas(json_str: str) -> str:
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)
    return json_str


def replace_param_placeholders(desc: str, params: List[float]) -> str:
    """
    将描述中的#1[i]、#2[i]等占位符替换为实际数值
    params是小数列表，需要根据是否有%符号决定是否乘以100
    """
    result = desc
    for i, param in enumerate(params, 1):
        # 匹配#1[i]%模式（百分比）
        percent_pattern = f'#\\{{{i}\\}}\\[i\\]%' if '{' in desc else f'#{i}\\[i\\]%'
        percent_pattern = f'#{i}\\[i\\]%'
        # 匹配#1[i]模式（普通数值）
        value_pattern = f'#{i}\\[i\\]'
        
        # 如果是百分比，乘以100
        if f'#{i}[i]%' in result:
            percent_value = int(param * 100)
            result = result.replace(f'#{i}[i]%', f'{percent_value}%')
        
        # 如果是普通数值，直接替换
        if f'#{i}[i]' in result:
            # 判断是否是整数
            if param == int(param):
                result = result.replace(f'#{i}[i]', str(int(param)))
            else:
                result = result.replace(f'#{i}[i]', str(param))
    
    return result


def calculate_floor_total_hp(floor_data: Dict[str, Any]) -> int:
    """
    计算每一层的总血量
    公式：第一波(怪物A×9 + 怪物B×9 + 怪物C×2)上下半 + 第二波首领上下半 + 第三波首领上下半
    """
    total_hp = 0
    
    # 处理上半部分
    upper_waves = floor_data.get("Upper", [])
    if upper_waves:
        waves = upper_waves[0].get("Waves", [])
        
        # 第一波：怪物A×9 + 怪物B×9 + 怪物C×2
        if len(waves) >= 1:
            monsters = waves[0].get("Monsters", [])
            if len(monsters) >= 3:
                # 怪物A和怪物B各乘以9，怪物C乘以2
                total_hp += (monsters[0].get("HP") or 0) * 9
                total_hp += (monsters[1].get("HP") or 0) * 9
                total_hp += (monsters[2].get("HP") or 0) * 2
        
        # 第二波：只计算首领（第三个怪物，Num=1）
        if len(waves) >= 2:
            monsters = waves[1].get("Monsters", [])
            if len(monsters) >= 3:
                # 首领是第三个怪物（Num=1）
                boss_hp = monsters[2].get("HP") or 0
                total_hp += boss_hp
        
        # 第三波：只计算首领（第三个怪物，Num=1）
        if len(waves) >= 3:
            monsters = waves[2].get("Monsters", [])
            if len(monsters) >= 3:
                boss_hp = monsters[2].get("HP") or 0
                total_hp += boss_hp
    
    # 处理下半部分
    lower_waves = floor_data.get("Lower", [])
    if lower_waves:
        waves = lower_waves[0].get("Waves", [])
        
        # 第一波：怪物A×9 + 怪物B×9 + 怪物C×2
        if len(waves) >= 1:
            monsters = waves[0].get("Monsters", [])
            if len(monsters) >= 3:
                total_hp += (monsters[0].get("HP") or 0) * 9
                total_hp += (monsters[1].get("HP") or 0) * 9
                total_hp += (monsters[2].get("HP") or 0) * 2
        
        # 第二波：只计算首领
        if len(waves) >= 2:
            monsters = waves[1].get("Monsters", [])
            if len(monsters) >= 3:
                boss_hp = monsters[2].get("HP") or 0
                total_hp += boss_hp
        
        # 第三波：只计算首领
        if len(waves) >= 3:
            monsters = waves[2].get("Monsters", [])
            if len(monsters) >= 3:
                boss_hp = monsters[2].get("HP") or 0
                total_hp += boss_hp
    
    return total_hp


def load_user_fiction_data(story_id: str) -> Dict[str, Any]:
    """
    从用户Fiction_1.js加载指定ID的数据
    """
    fiction_path = os.path.join(PROJECT_ROOT, "data", "CH", "Fiction_1.js")
    
    if not os.path.exists(fiction_path):
        print(f"  用户数据文件不存在: {fiction_path}")
        return {}
    
    with open(fiction_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    start = content.find('var _fiction = [')
    if start == -1:
        print("  未找到 var _fiction = [")
        return {}
    
    # 找到目标ID的位置
    target_id = int(story_id)
    id_pos = content.find(f'"_id": {target_id},', start)
    if id_pos == -1:
        print(f"  未找到 _id: {target_id}")
        return {}
    
    # 找到该ID对应的对象（向前找最近的'{'，向后匹配到对应的'}')
    # 先找到数组开始的位置，然后找第一个元素开始的'{'
    array_start = content.find('[', start)
    first_obj_start = content.find('{', array_start)
    
    # 确保first_obj_start在id_pos之前
    if first_obj_start > id_pos:
        # ID在数组开始之前就找到了，说明有问题
        print(f"  ID {target_id} 位置不正确")
        return {}
    
    # 从数组开始处匹配到ID所在的元素
    # 先找到id_pos之前最近的'{'（应该是该对象的开始）
    obj_start = content.rfind('{', array_start, id_pos)
    
    # 提取该对象（通过大括号匹配）
    brace_count = 0
    current_pos = obj_start
    while current_pos < len(content):
        if content[current_pos] == '{':
            brace_count += 1
        elif content[current_pos] == '}':
            brace_count -= 1
            if brace_count == 0:
                break
        current_pos += 1
    
    obj_str = content[obj_start:current_pos + 1]
    obj_str = remove_trailing_commas(obj_str)
    
    try:
        data = json.loads(obj_str)
        # 检查数据结构
        if "Name" in data:
            print(f"  用户数据Name: {data['Name']}")
        if "Floors" in data and len(data["Floors"]) > 0:
            print(f"  用户数据Floors数: {len(data['Floors'])}")
            if data["Floors"][0].get("Upper"):
                print(f"  第一层Upper数: {len(data['Floors'][0]['Upper'])}")
        return data
    except json.JSONDecodeError as e:
        print(f"  JSON解析错误: {e}")
        return {}


def find_max_buff_blessing_ids() -> tuple[int, int]:
    """
    遍历fiction_1/2.js找到Buff和Blessing的最大ID
    返回: (max_buff_id, max_blessing_id)
    """
    max_buff_id = 0
    max_blessing_id = 0
    
    for file_name in ["Fiction_1.js", "Fiction_2.js"]:
        fiction_path = os.path.join(PROJECT_ROOT, "data", "CH", file_name)
        if not os.path.exists(fiction_path):
            continue
        
        with open(fiction_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 在Buffs数组中查找Buff的ID
        # 找到Buffs数组开始的位置
        buffs_start = content.find('"Buffs": [')
        if buffs_start != -1:
            # 找到下一个]之前的内容
            buffs_end = content.find('],', buffs_start)
            if buffs_end == -1:
                buffs_end = content.find(']', buffs_start)
            buffs_content = content[buffs_start:buffs_end]
            buff_ids = re.findall(r'"_id":\s*(\d+)', buffs_content)
            for buff_id in buff_ids:
                buff_id_int = int(buff_id)
                if buff_id_int > max_buff_id:
                    max_buff_id = buff_id_int
        
        # 在Blessing数组中查找Blessing的ID
        blessing_start = content.find('"Blessing": [')
        if blessing_start != -1:
            blessing_end = content.find('],', blessing_start)
            if blessing_end == -1:
                blessing_end = content.find(']', blessing_start)
            blessing_content = content[blessing_start:blessing_end]
            bless_ids = re.findall(r'"_id":\s*(\d+)', blessing_content)
            for bless_id in bless_ids:
                bless_id_int = int(bless_id)
                if bless_id_int > max_blessing_id:
                    max_blessing_id = bless_id_int
    
    return max_buff_id, max_blessing_id


def find_existing_buff_blessing(name: str, buff_or_blessing: str = "both") -> int:
    """
    在fiction_1/2.js中查找相同名称的Buff或Blessing
    buff_or_blessing: "buff", "blessing", or "both"
    返回: 找到的ID，未找到返回-1
    """
    target_id = -1
    
    for file_name in ["Fiction_1.js", "Fiction_2.js"]:
        fiction_path = os.path.join(PROJECT_ROOT, "data", "CH", file_name)
        if not os.path.exists(fiction_path):
            continue
        
        with open(fiction_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找Buffs数组
        if buff_or_blessing in ["buff", "both"]:
            buffs_start = content.find('"Buffs": [')
            if buffs_start != -1:
                buffs_end = content.find('],', buffs_start)
                if buffs_end == -1:
                    buffs_end = content.find(']', buffs_start)
                buffs_content = content[buffs_start:buffs_end]
                
                # 按名称查找Buff对象
                buff_pattern = r'\{\s*"_id":\s*(\d+)[^}]*?"Name":\s*"([^"]+)"'
                buff_objects = re.findall(buff_pattern, buffs_content, re.DOTALL)
                for obj_id, obj_name in buff_objects:
                    if obj_name == name:
                        target_id = int(obj_id)
                        return target_id
        
        # 查找Blessing数组
        if buff_or_blessing in ["blessing", "both"]:
            blessing_start = content.find('"Blessing": [')
            if blessing_start != -1:
                blessing_end = content.find('],', blessing_start)
                if blessing_end == -1:
                    blessing_end = content.find(']', blessing_start)
                blessing_content = content[blessing_start:blessing_end]
                
                # 按名称查找Blessing对象
                bless_pattern = r'\{\s*"_id":\s*(\d+)[^}]*?"Name":\s*"([^"]+)"'
                bless_objects = re.findall(bless_pattern, blessing_content, re.DOTALL)
                for obj_id, obj_name in bless_objects:
                    if obj_name == name:
                        target_id = int(obj_id)
                        return target_id
    
    return target_id


def load_local_monster_db() -> Dict[str, Any]:
    monster_db = {}
    
    for path in [MONSTER_DB_PATH, MONSTER_DB_PATH_2]:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            start = content.find('var _monster = {')
            if start == -1:
                start = content.find('var _monster_2 = {')
                if start == -1:
                    continue
                prefix_len = len('var _monster_2 = ')
            else:
                prefix_len = len('var _monster = ')
            
            end = content.find('var _monsterlist')
            if end == -1:
                end = content.find('var _kingdoms')
            
            if end == -1:
                brace_count = 1
                current_pos = start + prefix_len
                while current_pos < len(content) and brace_count > 0:
                    if content[current_pos] == '{':
                        brace_count += 1
                    elif content[current_pos] == '}':
                        brace_count -= 1
                    current_pos += 1
                end = current_pos
            
            monster_str = content[start + prefix_len:end]
            monster_str = remove_trailing_commas(monster_str)
            
            try:
                data = json.loads(monster_str)
                monster_db.update(data)
            except json.JSONDecodeError:
                pass
    
    return monster_db


def load_level_curves() -> Dict[str, Any]:
    if not os.path.exists(LEVEL_CURVES_PATH):
        return {}
    
    with open(LEVEL_CURVES_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    start = content.find('var _hardlevelgroup = {')
    if start == -1:
        return {}
    
    end = content.find('var _elitegroup')
    if end == -1:
        end = content.find('var _levelgroup')
    
    if end == -1:
        return {}
    
    curves_str = content[start + len('var _hardlevelgroup = '):end]
    curves_str = remove_trailing_commas(curves_str)
    
    try:
        data = json.loads(curves_str)
        return data.get("1", {})
    except json.JSONDecodeError:
        return {}


def download_story_data(version: str, story_id: str) -> Dict[str, Any]:
    url = f"{BASE_URL}/{version}/{LANGUAGE}/story/{story_id}.json"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"下载数据失败: {e}")
        return {}


def get_monster_hp_multiplier(monster_db: Dict[str, Any], monster_id: str) -> tuple[float, bool, str]:
    """
    获取怪物HP倍数
    返回: (HP倍数, 是否找到, 原始ID)
    """
    # 先尝试直接查找
    monster_info = monster_db.get(monster_id)
    if monster_info and "Stats" in monster_info:
        hp = monster_info["Stats"].get("HP", 1.0)
        return (hp, True, monster_id)
    
    # 如果是9位ID，尝试去掉最后三位得到7位ID
    # 例如: 501211002 -> 5012110
    if len(monster_id) == 9 and monster_id.isdigit():
        base_id = monster_id[:-3]
        monster_info = monster_db.get(base_id)
        if monster_info and "Stats" in monster_info:
            hp = monster_info["Stats"].get("HP", 1.0)
            return (hp, True, base_id)
        return (0, False, base_id)
    
    # 未找到的7位ID，返回1.0作为默认值（不是首领）
    return (1.0, False, "")


def get_monster_spd(monster_db: Dict[str, Any], monster_id: str) -> int:
    monster_info = monster_db.get(monster_id)
    if monster_info and "Stats" in monster_info:
        return int(monster_info["Stats"].get("SPD", 100))
    
    return 100


def get_monster_stance(monster_db: Dict[str, Any], monster_id: str) -> int:
    monster_info = monster_db.get(monster_id)
    if monster_info and "Stats" in monster_info:
        return int(monster_info["Stats"].get("Stance", 5))
    
    return 5


def convert_monster_data(
    monster_waves: List[Dict[str, Any]],
    monster_db: Dict[str, Any],
    level_curves: Dict[str, Any],
    level: int,
    hp_add_values: Dict[int, float] = None
) -> tuple[List[Dict[str, Any]], List[str]]:
    """
    转换怪物数据
    hp_add_values: {wave_idx: hp_add_value}
    返回: (waves列表, 未找到的9位ID列表)
    """
    waves = []
    not_found_9digit_ids = []
    
    # 固定的Num值规则
    # 第一波：12/11/2
    # 第二波和第三波：20/20/1
    num_patterns = [
        [12, 11, 2],   # 第一波
        [20, 20, 1],   # 第二波
        [20, 20, 1]    # 第三波
    ]
    
    # 收集所有波次的怪物ID（从monster_list字段读取）
    all_monster_ids = []
    for wave_data in monster_waves:
        monster_list = wave_data.get("monster_list", [])
        for monster_id_str in monster_list:
            if isinstance(monster_id_str, str) and monster_id_str.isdigit():
                all_monster_ids.append(monster_id_str)
            elif isinstance(monster_id_str, int):
                all_monster_ids.append(str(monster_id_str))
    
    # 去重获取所有怪物
    all_unique_monsters = []
    seen = set()
    for mid in all_monster_ids:
        if mid not in seen:
            seen.add(mid)
            all_unique_monsters.append(mid)
    
    for wave_idx, wave_data in enumerate(monster_waves):
        # 获取当前波次的HPAdd值
        hp_add = hp_add_values.get(wave_idx, 1.0) if hp_add_values else 1.0
        
        # 从monster_list字段收集怪物ID
        monster_list = wave_data.get("monster_list", [])
        monster_ids = []
        for monster_id_str in monster_list:
            if isinstance(monster_id_str, str) and monster_id_str.isdigit():
                monster_ids.append(monster_id_str)
            elif isinstance(monster_id_str, int):
                monster_ids.append(str(monster_id_str))
        
        # 去重并保持顺序
        unique_monster_ids = []
        seen_wave = set()
        for mid in monster_ids:
            if mid not in seen_wave:
                seen_wave.add(mid)
                unique_monster_ids.append(mid)
        
        # 确保有3种怪物（用户格式要求）
        # 第一波：12/11/2（三种小怪）
        # 第二波和第三波：20/20/1（两种小怪+一个首领）
        if wave_idx == 0:
            # 第一波：需要3种小怪
            while len(unique_monster_ids) < 3:
                if unique_monster_ids:
                    unique_monster_ids.append(unique_monster_ids[-1])
        else:
            # 第二波和第三波：需要2个小怪+1个首领
            # 如果只有1个怪物（首领），从其他波次获取小怪
            if len(unique_monster_ids) == 1:
                # 从其他波次找不同的小怪
                boss_id = unique_monster_ids[0]
                minion_ids = [mid for mid in all_unique_monsters if mid != boss_id][:2]
                # 如果找不到其他小怪，使用相同的
                while len(minion_ids) < 2:
                    minion_ids.append(boss_id)
                unique_monster_ids = [minion_ids[0], minion_ids[1], boss_id]
            elif len(unique_monster_ids) == 2:
                # 添加一个首领（使用最后一个怪物）
                unique_monster_ids.append(unique_monster_ids[-1])
            # 如果有3个，保持原样
        
        monsters = []
        # 获取当前波次的Num模式
        pattern_idx = min(wave_idx, len(num_patterns) - 1)
        num_pattern = num_patterns[pattern_idx]
        
        for idx, monster_id_str in enumerate(unique_monster_ids[:3]):
            # 使用固定的Num值
            num = num_pattern[idx] if idx < len(num_pattern) else 1
            
            level_index = str(level - 1)
            base_hp = level_curves.get(level_index, {}).get("HP", 1000)
            hp_multiplier, found, original_id = get_monster_hp_multiplier(monster_db, monster_id_str)
            
            # 如果是9位ID且未找到，记录下来
            if len(monster_id_str) == 9 and not found:
                not_found_9digit_ids.append(monster_id_str)
            
            # 计算HP（如果未找到9位ID则留空）
            if len(monster_id_str) == 9 and not found:
                hp = None  # 留空
            else:
                hp = round(base_hp * hp_multiplier * hp_add)
            
            # 获取SPD和Stance
            spd = get_monster_spd(monster_db, monster_id_str)
            stance = get_monster_stance(monster_db, monster_id_str)
            
            monster_entry = {
                "ID": int(monster_id_str),
                "Num": num,
                "HP": hp,
                "SPD": spd,
                "Stance": stance
            }
            monsters.append(monster_entry)
        
        if monsters:
            waves.append({
                "KeepNum": 5,
                "HPAdd": hp_add,
                "Monsters": monsters
            })
    
    return waves, not_found_9digit_ids


def parse_infinite_list(infinite_list: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    解析infinite_list中的怪物数据
    返回: 每波的怪物数据列表
    """
    waves = []
    
    # 按wave id排序
    wave_ids = sorted(infinite_list.keys())
    
    for wave_id in wave_ids:
        wave_data = infinite_list[wave_id]
        monster_list = wave_data.get("monster_group_id_list", [])
        
        # 提取独特的怪物ID（去除重复）
        unique_monsters = []
        seen = set()
        for monster_id in monster_list:
            if monster_id not in seen:
                seen.add(monster_id)
                unique_monsters.append(str(monster_id))
        
        # 对于第一波（wave_id以"1"结尾），如果有4个怪物，去掉第一个（通常是召唤物）
        # 这是因为用户的Fiction_1.js中第一波只有3个怪物
        if len(unique_monsters) == 4 and wave_id.endswith('1'):
            unique_monsters = unique_monsters[1:]
        
        waves.append({"monster_list": unique_monsters})
    
    return waves


def convert_floor_data(
    floor: Dict[str, Any],
    floor_num: int,
    monster_db: Dict[str, Any],
    level_curves: Dict[str, Any],
    hp_add_values: Dict[int, float] = None
) -> tuple[Dict[str, Any], List[str]]:
    """
    转换楼层数据
    hp_add_values: {wave_idx: hp_add_value}
    返回: (floor数据, 未找到的9位ID列表)
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
    
    upper_monsters = []
    lower_monsters = []
    all_not_found_ids = []
    
    # 从infinite_list1读取上半部分数据
    infinite_list1 = floor.get("infinite_list1", {})
    upper_events = floor.get("event_id_list1", [])
    upper_waves_count = len(infinite_list1) if infinite_list1 else 0
    
    if upper_events and infinite_list1:
        upper_event = upper_events[0]
        upper_level = upper_event.get("level", 55)
        upper_stage_id = upper_event.get("stage_id", floor_num * 100 + 1)
        
        # 解析infinite_list获取怪物数据
        upper_monster_waves = parse_infinite_list(infinite_list1)
        
        # 上半部分使用HPAdd索引0,1,2
        upper_waves, not_found_ids = convert_monster_data(
            upper_monster_waves, monster_db, level_curves, upper_level, hp_add_values
        )
        all_not_found_ids.extend(not_found_ids)
        
        if upper_waves:
            upper_monsters.append({
                "_id": upper_stage_id,
                "Level": upper_level,
                "Waves": upper_waves
            })
    
    # 从infinite_list2读取下半部分数据
    infinite_list2 = floor.get("infinite_list2", {})
    lower_events = floor.get("event_id_list2", [])
    
    if lower_events and infinite_list2:
        lower_event = lower_events[0]
        lower_level = lower_event.get("level", 55)
        lower_stage_id = lower_event.get("stage_id", floor_num * 100 + 2)
        
        # 解析infinite_list获取怪物数据
        lower_monster_waves = parse_infinite_list(infinite_list2)
        
        # 下半部分需要使用HPAdd索引3,4,5，所以创建一个偏移后的HPAdd字典
        lower_hp_add_values = {}
        if hp_add_values:
            for wave_idx in range(len(lower_monster_waves)):
                # 下半部分的HPAdd索引是上半波次数 + 当前波次索引
                original_idx = upper_waves_count + wave_idx
                if original_idx in hp_add_values:
                    lower_hp_add_values[wave_idx] = hp_add_values[original_idx]
        
        lower_waves, not_found_ids = convert_monster_data(
            lower_monster_waves, monster_db, level_curves, lower_level, lower_hp_add_values
        )
        all_not_found_ids.extend(not_found_ids)
        
        if lower_waves:
            lower_monsters.append({
                "_id": lower_stage_id,
                "Level": lower_level,
                "Waves": lower_waves
            })
    
    return {
        "Floor": floor_num,
        "ElemUpper": elem_upper,
        "ElemLower": elem_lower,
        "Upper": upper_monsters,
        "Lower": lower_monsters
    }, all_not_found_ids


def convert_story_data(
    story_data: Dict[str, Any],
    story_id: str,
    monster_db: Dict[str, Any],
    level_curves: Dict[str, Any],
    hp_add_values: Dict[str, Dict[int, float]] = None
) -> tuple[Dict[str, Any], List[str]]:
    """
    转换虚构叙事数据
    hp_add_values: {floor_num: {wave_idx: hp_add_value}}
    返回: (转换后的数据, 未找到的9位ID列表)
    """
    if not story_data:
        return {}, []
    
    group_name = story_data.get("name", "未知")
    story_id_num = int(story_id)
    
    # 获取现有Buff和Blessing的最大ID
    max_buff_id, max_blessing_id = find_max_buff_blessing_ids()
    print(f"  现有Buff最大ID: {max_buff_id}, Blessing最大ID: {max_blessing_id}")
    
    buffs = []
    for buff in story_data.get("option", []):
        buff_name = buff.get("name", "")
        buff_desc = buff.get("desc", "").replace("<color=#f29e38ff>", "<color style='color:#f29e38;'>")
        buff_desc = buff_desc.replace("</color>", "</color>")
        buff_desc = buff_desc.replace("<unbreak>", "").replace("</unbreak>", "")
        
        # 获取param并替换占位符
        buff_params = buff.get("param", [])
        buff_desc = replace_param_placeholders(buff_desc, buff_params)
        
        # 查找是否有相同名称的Buff
        existing_id = find_existing_buff_blessing(buff_name, "buff")
        
        if existing_id != -1:
            buff_id = existing_id
            print(f"  Buff '{buff_name}' 已存在，使用ID: {buff_id}")
        else:
            max_buff_id += 1
            buff_id = max_buff_id
            print(f"  Buff '{buff_name}' 不存在，分配新ID: {buff_id}")
        
        buffs.append({
            "_id": buff_id,
            "Name": buff_name,
            "Desc": buff_desc,
            "SimpleDesc": ""
        })
    
    blessing = []
    for bless in story_data.get("sub_option", []):
        bless_name = bless.get("name", "")
        bless_desc = bless.get("desc", "").replace("<color=#f29e38ff>", "<color style='color:#f29e38;'>")
        bless_desc = bless_desc.replace("</color>", "</color>")
        bless_desc = bless_desc.replace("<unbreak>", "").replace("</unbreak>", "")
        
        # 获取param并替换占位符
        bless_params = bless.get("param", [])
        bless_desc = replace_param_placeholders(bless_desc, bless_params)
        
        # 查找是否有相同名称的Blessing
        existing_id = find_existing_buff_blessing(bless_name, "blessing")
        
        if existing_id != -1:
            bless_id = existing_id
            print(f"  Blessing '{bless_name}' 已存在，使用ID: {bless_id}")
        else:
            max_blessing_id += 1
            bless_id = max_blessing_id
            print(f"  Blessing '{bless.get('name')}' 不存在，分配新ID: {bless_id}")
        
        blessing.append({
            "_id": bless_id,
            "Name": bless.get("name", "祝福"),
            "Desc": bless_desc
        })
    
    floors = []
    all_not_found_ids = []
    levels = story_data.get("level", [])
    
    for i in range(min(4, len(levels))):
        if i < len(levels):
            floor_num = i + 1
            # 获取该楼层的HPAdd值
            floor_hp_add = hp_add_values.get(str(floor_num), {}) if hp_add_values else {}
            floor_result, not_found_ids = convert_floor_data(
                levels[i], floor_num, monster_db, level_curves, floor_hp_add
            )
            floors.append(floor_result)
            all_not_found_ids.extend(not_found_ids)
    
    return {
        "_id": story_id_num,
        "Name": group_name,
        "BST": 1,
        "Buffs": buffs,
        "Blessing": blessing,
        "Floors": floors
    }, all_not_found_ids


def generate_js_file(story_id: str, data: Dict[str, Any]) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    js_content = "// Auto Generated\n\nvar _fiction = [\n    {\n"
    
    js_content += f'        "_id": {data["_id"]},\n'
    js_content += f'        "Name": "{data["Name"]}",\n'
    js_content += f'        "BST": {data["BST"]},\n'
    
    js_content += '        "Buffs": [\n'
    for buff in data["Buffs"]:
        js_content += '            {\n'
        js_content += f'                "_id": {buff["_id"]},\n'
        js_content += f'                "Name": "{buff["Name"]}",\n'
        js_content += f'                "Desc": "{buff["Desc"]}",\n'
        js_content += '                "SimpleDesc": ""\n'
        js_content += '            },\n'
    js_content = js_content.rstrip(",\n") + "\n        ],\n"
    
    js_content += '        "Blessing": [\n'
    for bless in data["Blessing"]:
        js_content += '            {\n'
        js_content += f'                "_id": {bless["_id"]},\n'
        js_content += f'                "Name": "{bless["Name"]}",\n'
        js_content += f'                "Desc": "{bless["Desc"]}"\n'
        js_content += '            },\n'
    js_content = js_content.rstrip(",\n") + "\n        ],\n"
    
    js_content += '        "Floors": [\n'
    for floor in data["Floors"]:
        js_content += '            {\n'
        js_content += f'                "Floor": {floor["Floor"]},\n'
        
        # 计算并添加总血量
        total_hp = calculate_floor_total_hp(floor)
        js_content += f'                "TotalHP": {total_hp},\n'
        
        js_content += '                "ElemUpper": [\n'
        for elem in floor["ElemUpper"]:
            js_content += f'                    "{elem}",\n'
        js_content = js_content.rstrip(",\n") + "\n                ],\n"
        
        js_content += '                "ElemLower": [\n'
        for elem in floor["ElemLower"]:
            js_content += f'                    "{elem}",\n'
        js_content = js_content.rstrip(",\n") + "\n                ],\n"
        
        js_content += '                "Upper": [\n'
        for upper in floor["Upper"]:
            js_content += '                    {\n'
            js_content += f'                        "_id": {upper["_id"]},\n'
            js_content += f'                        "Level": {upper["Level"]},\n'
            js_content += '                        "Waves": [\n'
            for wave in upper["Waves"]:
                js_content += '                            {\n'
                js_content += f'                                "KeepNum": {wave.get("KeepNum", 5)},\n'
                js_content += f'                                "HPAdd": {wave["HPAdd"]},\n'
                js_content += '                                "Monsters": [\n'
                for monster in wave["Monsters"]:
                    js_content += '                                    {\n'
                    js_content += f'                                        "ID": {monster["ID"]},\n'
                    js_content += f'                                        "Num": {monster["Num"]},\n'
                    if monster.get("HP") is None:
                        js_content += '                                        "HP": null,\n'
                    else:
                        js_content += f'                                        "HP": {monster["HP"]},\n'
                    js_content += f'                                        "SPD": {monster["SPD"]},\n'
                    js_content += f'                                        "Stance": {monster["Stance"]}\n'
                    js_content += '                                    },\n'
                js_content = js_content.rstrip(",\n") + "\n                                ]\n"
                js_content += '                            },\n'
            js_content = js_content.rstrip(",\n") + "\n                        ]\n"
            js_content += '                    }\n'
        js_content += '                ],\n'
        
        js_content += '                "Lower": [\n'
        for lower in floor["Lower"]:
            js_content += '                    {\n'
            js_content += f'                        "_id": {lower["_id"]},\n'
            js_content += f'                        "Level": {lower["Level"]},\n'
            js_content += '                        "Waves": [\n'
            for wave in lower["Waves"]:
                js_content += '                            {\n'
                js_content += f'                                "KeepNum": {wave.get("KeepNum", 5)},\n'
                js_content += f'                                "HPAdd": {wave["HPAdd"]},\n'
                js_content += '                                "Monsters": [\n'
                for monster in wave["Monsters"]:
                    js_content += '                                    {\n'
                    js_content += f'                                        "ID": {monster["ID"]},\n'
                    js_content += f'                                        "Num": {monster["Num"]},\n'
                    if monster.get("HP") is None:
                        js_content += '                                        "HP": null,\n'
                    else:
                        js_content += f'                                        "HP": {monster["HP"]},\n'
                    js_content += f'                                        "SPD": {monster["SPD"]},\n'
                    js_content += f'                                        "Stance": {monster["Stance"]}\n'
                    js_content += '                                    },\n'
                js_content = js_content.rstrip(",\n") + "\n                                ]\n"
                js_content += '                            },\n'
            js_content = js_content.rstrip(",\n") + "\n                        ]\n"
            js_content += '                    }\n'
        js_content += '                ]\n'
        js_content += '            },\n'
    js_content = js_content.rstrip(",\n") + "\n        ]\n"
    
    js_content += "    }\n];\n"
    
    file_path = os.path.join(OUTPUT_DIR, f"Fiction_{story_id}.js")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(js_content)
    
    return file_path


def write_to_fiction_1_js(story_id: str, data: Dict[str, Any]) -> bool:
    """
    将生成的数据写入fiction_1.js
    如果已存在相同ID，则替换；否则在开头插入
    返回是否成功
    """
    fiction_path = os.path.join(PROJECT_ROOT, "data", "CH", "Fiction_1.js")
    
    if not os.path.exists(fiction_path):
        print(f"  fiction_1.js不存在: {fiction_path}")
        return False
    
    with open(fiction_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 找到var _fiction = [的位置
    fiction_start = content.find('var _fiction = [')
    if fiction_start == -1:
        print("  未找到 var _fiction = [")
        return False
    
    # 找到_fictionschedule开始的位置
    schedule_start = content.find('var _fictionschedule = [')
    if schedule_start == -1:
        print("  未找到 var _fictionschedule = [")
        return False
    
    # _fiction数组结束在schedule_start之前的]处
    # 使用rfind从schedule_start向前查找]
    fiction_end = content.rfind(']', fiction_start, schedule_start)
    if fiction_end == -1:
        print("  未找到 _fiction 数组结束位置")
        return False
    
    # 生成新数据的JS内容（不带开头的var _fiction = [和结尾的];）
    new_data_js = generate_single_fiction_entry(data)
    
    # 检查是否已存在相同ID
    target_id = int(story_id)
    id_pattern = f'"_id": {target_id},'
    id_pos = content.find(id_pattern, fiction_start, fiction_end)
    
    if id_pos != -1:
        # 已存在，需要替换
        print(f"  fiction_1.js中已存在ID {target_id}，将替换旧数据")
        
        # 找到该条数据的开始位置（向前找{）
        entry_start = content.rfind('{', fiction_start, id_pos)
        if entry_start == -1:
            print("  未找到数据条目开始位置")
            return False
        
        # 找到该条数据的结束位置（向后找}）
        # 需要匹配花括号
        brace_count = 1
        pos = id_pos
        while pos < fiction_end and brace_count > 0:
            pos += 1
            if content[pos] == '{':
                brace_count += 1
            elif content[pos] == '}':
                brace_count -= 1
        
        # 找到匹配的}后，检查后面是什么
        entry_end = pos
        next_char = content[entry_end+1] if entry_end+1 < len(content) else ''
        has_comma = next_char == ','
        
        # 找到entry_start前面的换行符，确保替换从换行符后开始
        line_start = content.rfind('\n', fiction_start, entry_start)
        if line_start == -1:
            line_start = fiction_start
        
        # 生成新数据
        new_data_js = generate_single_fiction_entry(data)
        
        # 确定替换范围和逗号处理
        if has_comma:
            # 原有数据有逗号，新数据末尾也要加逗号，替换范围包括逗号
            new_data_js += ','
            new_content = content[:line_start+1] + new_data_js + content[entry_end+2:]
        else:
            # 原有数据没有逗号（可能是数组最后一个元素），新数据末尾加逗号
            new_data_js += ','
            new_content = content[:line_start+1] + new_data_js + content[entry_end+1:]

        
    else:
        # 不存在，在开头插入
        print(f"  fiction_1.js中不存在ID {target_id}，将在开头插入新数据")
        
        # 找到第一个条目的开始位置（var _fiction = [ 后面的第一个{）
        first_entry_start = content.find('{', fiction_start + len('var _fiction = ['))
        if first_entry_start == -1 or first_entry_start > fiction_end:
            print("  未找到第一个数据条目")
            return False
        
        # 在第一个条目前插入新数据（需要包含逗号分隔）
        new_data_js = generate_single_fiction_entry(data) + ','
        
        # 找到first_entry_start前面的换行符
        line_start = content.rfind('\n', fiction_start, first_entry_start)
        if line_start == -1:
            line_start = fiction_start
        
        # 在换行符后插入新数据
        new_content = content[:line_start+1] + new_data_js + '\n    ' + content[first_entry_start:]
    
    # 写入文件
    with open(fiction_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"  已成功写入 fiction_1.js")
    return True


def generate_single_fiction_entry(data: Dict[str, Any]) -> str:
    """
    生成单个fiction条目的JS内容（不带外层的var _fiction = [和];）
    """
    js_content = '    {\n'
    
    js_content += f'        "_id": {data["_id"]},\n'
    js_content += f'        "Name": "{data["Name"]}",\n'
    js_content += f'        "BST": {data["BST"]},\n'
    
    js_content += '        "Buffs": [\n'
    for buff in data["Buffs"]:
        js_content += '            {\n'
        js_content += f'                "_id": {buff["_id"]},\n'
        js_content += f'                "Name": "{buff["Name"]}",\n'
        js_content += f'                "Desc": "{buff["Desc"]}",\n'
        js_content += '                "SimpleDesc": ""\n'
        js_content += '            },\n'
    js_content = js_content.rstrip(",\n") + "\n        ],\n"
    
    js_content += '        "Blessing": [\n'
    for bless in data["Blessing"]:
        js_content += '            {\n'
        js_content += f'                "_id": {bless["_id"]},\n'
        js_content += f'                "Name": "{bless["Name"]}",\n'
        js_content += f'                "Desc": "{bless["Desc"]}"\n'
        js_content += '            },\n'
    js_content = js_content.rstrip(",\n") + "\n        ],\n"
    
    js_content += '        "Floors": [\n'
    for floor in data["Floors"]:
        js_content += '            {\n'
        js_content += f'                "Floor": {floor["Floor"]},\n'
        
        # 计算并添加总血量
        total_hp = calculate_floor_total_hp(floor)
        js_content += f'                "TotalHP": {total_hp},\n'
        
        js_content += '                "ElemUpper": [\n'
        for elem in floor["ElemUpper"]:
            js_content += f'                    "{elem}",\n'
        js_content = js_content.rstrip(",\n") + "\n                ],\n"
        
        js_content += '                "ElemLower": [\n'
        for elem in floor["ElemLower"]:
            js_content += f'                    "{elem}",\n'
        js_content = js_content.rstrip(",\n") + "\n                ],\n"
        
        js_content += '                "Upper": [\n'
        for upper in floor["Upper"]:
            js_content += '                    {\n'
            js_content += f'                        "_id": {upper["_id"]},\n'
            js_content += f'                        "Level": {upper["Level"]},\n'
            js_content += '                        "Waves": [\n'
            for wave in upper["Waves"]:
                js_content += '                            {\n'
                js_content += f'                                "KeepNum": {wave.get("KeepNum", 5)},\n'
                js_content += f'                                "HPAdd": {wave["HPAdd"]},\n'
                js_content += '                                "Monsters": [\n'
                for monster in wave["Monsters"]:
                    js_content += '                                    {\n'
                    js_content += f'                                        "ID": {monster["ID"]},\n'
                    js_content += f'                                        "Num": {monster["Num"]},\n'
                    if monster.get("HP") is None:
                        js_content += '                                        "HP": null,\n'
                    else:
                        js_content += f'                                        "HP": {monster["HP"]},\n'
                    js_content += f'                                        "SPD": {monster["SPD"]},\n'
                    js_content += f'                                        "Stance": {monster["Stance"]}\n'
                    js_content += '                                    },\n'
                js_content = js_content.rstrip(",\n") + "\n                                ]\n"
                js_content += '                            },\n'
            js_content = js_content.rstrip(",\n") + "\n                        ]\n"
            js_content += '                    },\n'
        js_content = js_content.rstrip(",\n") + "\n                ],\n"
        
        js_content += '                "Lower": [\n'
        for lower in floor["Lower"]:
            js_content += '                    {\n'
            js_content += f'                        "_id": {lower["_id"]},\n'
            js_content += f'                        "Level": {lower["Level"]},\n'
            js_content += '                        "Waves": [\n'
            for wave in lower["Waves"]:
                js_content += '                            {\n'
                js_content += f'                                "KeepNum": {wave.get("KeepNum", 5)},\n'
                js_content += f'                                "HPAdd": {wave["HPAdd"]},\n'
                js_content += '                                "Monsters": [\n'
                for monster in wave["Monsters"]:
                    js_content += '                                    {\n'
                    js_content += f'                                        "ID": {monster["ID"]},\n'
                    js_content += f'                                        "Num": {monster["Num"]},\n'
                    if monster.get("HP") is None:
                        js_content += '                                        "HP": null,\n'
                    else:
                        js_content += f'                                        "HP": {monster["HP"]},\n'
                    js_content += f'                                        "SPD": {monster["SPD"]},\n'
                    js_content += f'                                        "Stance": {monster["Stance"]}\n'
                    js_content += '                                    },\n'
                js_content = js_content.rstrip(",\n") + "\n                                ]\n"
                js_content += '                            },\n'
            js_content = js_content.rstrip(",\n") + "\n                        ]\n"
            js_content += '                    },\n'
        js_content = js_content.rstrip(",\n") + "\n                ]\n"
        js_content += '            },\n'
    js_content = js_content.rstrip(",\n") + "\n        ]\n"
    
    js_content += '    }'
    
    return js_content


def generate_fiction_data(story_id: str, version: str = "4.3.52", hp_add_values: Dict[str, Dict[int, float]] = None) -> tuple[str, List[str], Dict[str, Any]]:
    """
    生成虚构叙事数据
    hp_add_values: {floor_num: {wave_idx: hp_add_value}}
    返回: (结果消息, 未找到的9位ID列表, 转换后的数据)
    """
    print(f"开始处理虚构叙事 {story_id}...")
    
    monster_db = load_local_monster_db()
    level_curves = load_level_curves()
    
    story_data = download_story_data(version, story_id)
    
    if not story_data:
        return "无法获取虚构叙事数据，退出", [], {}
    
    converted_data, not_found_ids = convert_story_data(
        story_data, story_id, monster_db, level_curves, hp_add_values
    )
    
    # 生成到tempdata
    file_path = generate_js_file(story_id, converted_data)
    
    # 写入fiction_1.js
    write_to_fiction_1_js(story_id, converted_data)
    
    result = f"虚构叙事 {story_id} 数据生成完成！\n  tempdata文件: {file_path}\n  已写入 fiction_1.js"
    
    return result, not_found_ids, converted_data


def main():
    version = "4.3.52"
    
    print("="*60)
    print("虚构叙事数据转换工具")
    print("="*60)
    
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python hsr_trans_fiction.py <ID>")
        print("  例如: python hsr_trans_fiction.py 2024")
        print("\n运行后会提示您输入每一层每一波的HPAdd值")
        return
    
    story_id = sys.argv[1]
    
    # 先下载数据以确定层数和波次
    print("\n正在下载数据以确定层数和波次...")
    story_data = download_story_data(version, story_id)
    
    if not story_data:
        print("无法获取虚构叙事数据")
        return
    
    hp_add_values = {}
    levels = story_data.get("level", [])
    
    print("\n" + "="*60)
    print("请输入每一层每一波的HPAdd值")
    print("="*60)
    
    for floor_idx in range(min(4, len(levels))):
        floor_num = floor_idx + 1
        floor_data = levels[floor_idx]
        
        # 获取上半和下半的波次数量（从infinite_list获取）
        infinite_list1 = floor_data.get("infinite_list1", {})
        infinite_list2 = floor_data.get("infinite_list2", {})
        
        upper_waves = len(infinite_list1) if infinite_list1 else 0
        lower_waves = len(infinite_list2) if infinite_list2 else 0
        
        # 上半部分
        if upper_waves > 0:
            for wave_idx in range(upper_waves):
                while True:
                    try:
                        hp_add = float(input(f"请输入第{floor_num}层上半部分第{wave_idx + 1}波的HPAdd值: "))
                        break
                    except ValueError:
                        print("  请输入有效的数字！")
                
                if str(floor_num) not in hp_add_values:
                    hp_add_values[str(floor_num)] = {}
                hp_add_values[str(floor_num)][wave_idx] = hp_add
        
        # 下半部分
        if lower_waves > 0:
            for wave_idx in range(lower_waves):
                while True:
                    try:
                        hp_add = float(input(f"请输入第{floor_num}层下半部分第{wave_idx + 1}波的HPAdd值: "))
                        break
                    except ValueError:
                        print("  请输入有效的数字！")
                
                if str(floor_num) not in hp_add_values:
                    hp_add_values[str(floor_num)] = {}
                hp_add_values[str(floor_num)][wave_idx + upper_waves] = hp_add
    
    print(f"\n目标ID: {story_id}")
    print(f"版本: {version}")
    
    result, not_found_ids, converted_data = generate_fiction_data(story_id, version, hp_add_values)
    print(result)
    
    # 输出未找到的9位ID列表
    if not_found_ids:
        print("\n" + "="*60)
        print("未能在Monster_1/2.js中找到的9位ID列表:")
        print("="*60)
        for monster_id in sorted(set(not_found_ids)):
            base_id = monster_id[:-3]
            print(f"  {monster_id} (原始: {base_id})")
        print("\n请手动补充这些怪物的HP数据。")


if __name__ == "__main__":
    main()