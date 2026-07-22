#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动下载并转换SR遗器(仪器)数据脚本
功能：从API下载遗器套装数据，并转换为现有JS格式
API: https://static.nanoka.cc/hsr/{version}/zh/relicset/{id}.json

输出格式:
  - _relic:  用于 Relic.js 中的套装基础信息
  - _relicitem_: 用于 Relic/{id}.js 中的部件详细信息
"""

import os
import re
import json
import requests
from typing import Dict, Any, Optional, List

BASE_URL = 'https://static.nanoka.cc/hsr'
LANGUAGE = 'zh'
CACHE_DIR = './tempdata'
OUTPUT_RELIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'sr', 'data', 'CH', 'Relic')
OUTPUT_IMAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'images', 'itemfigures')
IMAGE_BASE_URL = 'https://static.nanoka.cc/assets/hsr/itemfigures'

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(OUTPUT_RELIC_DIR, exist_ok=True)
os.makedirs(OUTPUT_IMAGE_DIR, exist_ok=True)


def download_relic_data(relic_id: str, version: str) -> Optional[Dict[str, Any]]:
    """下载遗器套装数据，优先使用本地缓存"""
    local_file = os.path.join(CACHE_DIR, f'relic_{relic_id}_{version}.json')
    if os.path.exists(local_file):
        try:
            with open(local_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f'读取本地缓存失败: {e}')

    url = f'{BASE_URL}/{version}/{LANGUAGE}/relicset/{relic_id}.json'
    try:
        print(f'  [下载] {url}')
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()

        with open(local_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return data
    except requests.exceptions.RequestException as e:
        print(f'下载遗器 {relic_id} 失败: {e}')
        return None


def format_relic_desc(desc: str, param_list: List[float]) -> str:
    """
    格式化遗器描述文本，将API占位符替换为实际参数值

    API格式 -> 本地格式:
      #N[i]%    -> <b>int(param*100)%</b>
      #N[i]     -> <b>int(param)</b>
      #N[f1]%   -> <b>param*100(1位小数)%</b>
      #N[f2]%   -> <b>param*100(2位小数)%</b>
      <unbreak> -> 移除
    """
    if not desc:
        return ''

    desc = desc.replace('<unbreak>', '').replace('</unbreak>', '')
    desc = desc.replace('\n', ' ')

    if param_list:
        for i, param in enumerate(param_list, 1):
            # 按优先级匹配: #N[i]%, #N[i], #N[f1]%, #N[f2]%
            patterns = [
                (f'#{i}[i]%', lambda p: f'<b>{int(p * 100)}%</b>'),
                (f'#{i}[i]', lambda p: f'<b>{int(p)}</b>'),
                (f'#{i}[f1]%', lambda p: f'<b>{p * 100:.1f}%</b>'),
                (f'#{i}[f2]%', lambda p: f'<b>{p * 100:.2f}%</b>'),
            ]
            for pattern, formatter in patterns:
                if pattern in desc:
                    desc = desc.replace(pattern, formatter(param))
                    break

    return desc


def extract_icon_filename(icon_path: str) -> str:
    """从完整路径提取图标文件名"""
    if not icon_path:
        return ''
    return os.path.basename(icon_path)


def download_relic_image(icon_path: str) -> bool:
    """
    下载遗器套装图片，从API的icon路径提取ID并下载webp转PNG

    Args:
        icon_path: API中的icon路径，如 'SpriteOutput/ItemIcon/71059.png'

    Returns:
        是否下载成功
    """
    if not icon_path:
        return False

    filename = os.path.basename(icon_path)  # 71059.png
    icon_id = os.path.splitext(filename)[0]  # 71059

    save_path = os.path.join(OUTPUT_IMAGE_DIR, f'{icon_id}.png')

    if os.path.exists(save_path):
        print(f'  [图片] {icon_id}.png (已存在，跳过)')
        return True

    url = f'{IMAGE_BASE_URL}/{icon_id}.webp'
    try:
        print(f'  [图片] 下载 {url}')
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        from PIL import Image
        import io
        with Image.open(io.BytesIO(response.content)) as img:
            img.save(save_path, 'PNG')

        print(f'  [图片] ✓ 已保存 {save_path}')
        return True
    except Exception as e:
        print(f'  [图片] ✗ 下载失败 ({icon_id}): {e}')
        return False


def convert_to_relic_format(relic_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    将API数据转换为 _relic 格式 (用于 Relic.js)

    API:
      { "name": "套装名", "icon": "SpriteOutput/ItemIcon/71059.png",
        "require_num": { "2": {"desc": "...", "param_list": [...]}, ... } }

    _relic:
      { "_id": 328, "Name": "套装名", "Icon": "71059.png",
        "Skills": ["2件套效果...", "4件套效果..."] }
    """
    if not relic_data:
        return {}

    icon = extract_icon_filename(relic_data.get('icon', ''))
    skills = []
    require_num = relic_data.get('require_num', {})

    for num_key in sorted(require_num.keys(), key=int):
        effect = require_num[num_key]
        desc = effect.get('desc', '')
        param_list = effect.get('param_list', [])
        formatted = format_relic_desc(desc, param_list)
        if formatted:
            skills.append(formatted)

    return {
        '_id': 0,
        'Name': relic_data.get('name', ''),
        'Icon': icon,
        'Skills': skills
    }


def convert_to_relicitem_format(relic_data: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    将API数据转换为 _relicitem_ 格式 (用于 Relic/{id}.js)

    API parts:
      { "31251": {"name": "部件名", "desc": "描述", "story": "故事"}, ... }

    _relicitem_:
      [ { "Name": "部件名", "Desc": "描述", "Story": "故事",
          "Icon": "IconRelic_125_1.png" }, ... ]
    """
    if not relic_data:
        return []

    parts = relic_data.get('parts', {})
    items = []
    relic_id = relic_data.get('_id', '?')

    for idx, (part_id, part_info) in enumerate(parts.items(), 1):
        desc = (part_info.get('desc') or '')
        story = (part_info.get('story') or '')
        desc = desc.replace('\\n', '<br>').replace('\n', '<br>')
        story = story.replace('\\n', '<br>').replace('\n', '<br>')

        item = {
            'Name': part_info.get('name', ''),
            'Desc': desc,
            'Story': story,
            'Icon': f'IconRelic_{relic_id}_{idx}.png'
        }
        items.append(item)

    return items


def generate_relic_js(relic_id: str, relic_items: List[Dict[str, str]]) -> str:
    """生成 Relic/{id}.js 文件内容"""
    js_content = '// Auto Generated\n\nvar _relicitem_ = {\n'
    items_json = json.dumps(relic_items, ensure_ascii=False, indent=8)
    js_content += f'    "{relic_id}": {items_json}\n'
    js_content += '}\n'
    return js_content


AVATAR_JS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'sr', 'data', 'CH', 'Avatar.js')
RELIC_JS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'sr', 'data', 'CH', 'Relic.js')


def parse_relic_object() -> tuple:
    """解析 Relic.js 中的 _relic 对象，返回 (行列表, 对象起始行, 301条目结束行)

    返回:
        (lines, obj_start_line, insert_after_301_line)
        insert_after_301_line: key为"301"的条目结束的 } 行号
    """
    if not os.path.exists(RELIC_JS_PATH):
        print(f'  [警告] 找不到 {RELIC_JS_PATH}')
        return None, 0, 0

    with open(RELIC_JS_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    obj_start = 0
    insert_after_301 = 0

    in_relic = False
    brace_depth = 0

    for i, line in enumerate(lines):
        if not in_relic:
            if 'var _relic = {' in line:
                in_relic = True
                obj_start = i
            continue

        for ch in line:
            if ch == '{':
                brace_depth += 1
            elif ch == '}':
                brace_depth -= 1
                if brace_depth == 0 and not insert_after_301:
                    for j in range(i - 1, max(i - 30, obj_start), -1):
                        if '"301"' in lines[j] and ':' in lines[j]:
                            insert_after_301 = i
                            break
                if brace_depth == 0:
                    obj_end = i
                    break

    if obj_start == 0:
        print('  [错误] 无法解析 _relic 对象')
        return None, 0, 0

    return lines, obj_start, insert_after_301


def find_301_key(lines: List[str]) -> int:
    """在给定的行列表中查找 key为"301"的条目结束的 } 行号"""
    brace_depth = 0
    in_301 = False
    for i, line in enumerate(lines):
        if '"301"' in line and ':' in line:
            in_301 = True
        if in_301:
            for ch in line:
                if ch == '{':
                    brace_depth += 1
                elif ch == '}':
                    brace_depth -= 1
                    if brace_depth == 0:
                        return i
    return 0


def insert_relic_entries(new_entries: List[Dict[str, Any]]) -> bool:
    """
    将新的遗器条目插入到 Relic.js 的 _relic 对象中

    规则:
      - ID > 300: 插入到对象头部 (var _relic = { 之后)
      - ID < 300: 插入到 key为"301"的条目之后
    """
    if not new_entries:
        return True

    if not os.path.exists(RELIC_JS_PATH):
        print(f'  [错误] 找不到 {RELIC_JS_PATH}')
        return False

    with open(RELIC_JS_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    parsed, obj_start, insert_after_301 = parse_relic_object()

    if parsed is None:
        return False

    high_entries = sorted(
        [e for e in new_entries if e['_id'] > 300],
        key=lambda x: x['_id'], reverse=True
    )
    low_entries = sorted(
        [e for e in new_entries if e['_id'] < 300],
        key=lambda x: x['_id'], reverse=True
    )

    if not high_entries and not low_entries:
        print('  没有需要插入的条目')
        return True

    def format_entry(entry):
        parts = []
        parts.append(f'    "{entry["_id"]}": {{')
        parts.append(f'        "_id": {entry["_id"]},')
        parts.append(f'        "Name": "{entry["Name"]}",')
        parts.append(f'        "Icon": "{entry["Icon"]}",')
        if len(entry['Skills']) == 1:
            parts.append('        "Skills": [')
            parts.append(f'            "{entry["Skills"][0]}"')
            parts.append('        ]')
        else:
            parts.append('        "Skills": [')
            for skill in entry['Skills']:
                parts.append(f'            "{skill}",')
            parts.append('        ]')
        parts.append('    },')
        return '\n'.join(parts) + '\n'

    result_lines = []

    if high_entries:
        for i, line in enumerate(lines):
            result_lines.append(line)
            if i == obj_start:
                for entry in high_entries:
                    result_lines.append(format_entry(entry))
                    print(f'  [插入头部] ID: {entry["_id"]} - {entry["Name"]}')
    else:
        result_lines = list(lines)

    if low_entries:
        after_301 = find_301_key(result_lines)

        if after_301:
            final_lines = []
            for i, line in enumerate(result_lines):
                final_lines.append(line)
                if i == after_301:
                    for entry in low_entries:
                        final_lines.append(format_entry(entry))
                        print(f'  [插入301后] ID: {entry["_id"]} - {entry["Name"]}')
            result_lines = final_lines
        else:
            print('  [警告] 找不到301条目，无法插入ID<300的遗器')

    with open(RELIC_JS_PATH, 'w', encoding='utf-8') as f:
        f.writelines(result_lines)

    print(f'  [完成] Relic.js 已更新')
    return True


def batch_process(relic_ids: List[str], version: str, auto_merge: bool = False):
    """批量处理遗器ID"""
    relic_entries = []
    relic_js_files = []

    for relic_id in relic_ids:
        print(f'\n--- 处理遗器 ID: {relic_id} ---')

        data = download_relic_data(relic_id, version)
        if not data:
            print(f'  [失败] 无法获取遗器 {relic_id} 的数据')
            continue

        data['_id'] = relic_id

        # 下载遗器图片
        download_relic_image(data.get('icon', ''))

        # _relic 格式
        relic_entry = convert_to_relic_format(data)
        relic_entry['_id'] = int(relic_id)
        print(f'\n  [_relic 条目]:')
        print(f'  {json.dumps(relic_entry, ensure_ascii=False, indent=2)}')

        relic_entries.append(relic_entry)

        # _relicitem_ 格式
        relic_items = convert_to_relicitem_format(data)
        if relic_items:
            js_content = generate_relic_js(relic_id, relic_items)
            output_file = os.path.join(OUTPUT_RELIC_DIR, f'{relic_id}.js')

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(js_content)

            print(f'\n  [_relicitem_ 文件] 已保存到: {output_file}')
            relic_js_files.append(output_file)

            for item in relic_items:
                print(f'    - {item["Name"]} ({item["Icon"]})')

    print(f'\n{"=" * 60}')
    print(f'  处理完成! 共处理 {len(relic_entries)} 个遗器')
    print(f'  Relic JS 文件输出目录: {OUTPUT_RELIC_DIR}')
    print(f'{"=" * 60}')

    if auto_merge and relic_entries:
        print(f'\n  [自动拼接] 正在更新 Relic.js...')
        insert_relic_entries(relic_entries)
    elif relic_entries:
        print(f'\n  [_relic 批量条目] 可直接复制到 Relic.js:')
        for entry in relic_entries:
            print(f'    {json.dumps(entry, ensure_ascii=False)},')


def main():
    """主函数：交互式输入遗器ID和版本号"""
    print('=' * 60)
    print('  SR 遗器(仪器)数据转换工具')
    print('=' * 60)

    version = input('请输入版本号 (如 4.4.52): ').strip()
    if not version:
        version = '4.4.52'

    relic_ids_input = input('请输入遗器ID (多个用逗号分隔): ').strip()
    relic_ids = [x.strip() for x in relic_ids_input.split(',') if x.strip()]

    if not relic_ids:
        print('未输入有效ID，退出。')
        return

    auto_merge = input('是否自动拼接到 Relic.js? (y/n, 默认n): ').strip().lower()
    do_merge = auto_merge == 'y' or auto_merge == 'yes'

    print(f'\n版本: {version}')
    print(f'遗器ID: {relic_ids}')
    print(f'自动拼接: {"是" if do_merge else "否"}')

    batch_process(relic_ids, version, auto_merge=do_merge)


def generate_relic_data(relic_ids: List[str], version: str, auto_merge: bool = True) -> str:
    """
    供 server.py 调用的包装函数
    下载并转换遗器数据，可选自动拼接到 Relic.js

    Args:
        relic_ids: 遗器ID列表
        version: 版本号
        auto_merge: 是否自动拼接到 Relic.js

    Returns:
        处理结果字符串
    """
    import io
    output = io.StringIO()

    relic_entries = []

    for relic_id in relic_ids:
        print(f'--- 处理遗器 ID: {relic_id} ---', file=output)
        data = download_relic_data(relic_id, version)
        if not data:
            print(f'[失败] 无法获取遗器 {relic_id} 的数据', file=output)
            continue

        data['_id'] = relic_id

        # 下载遗器图片
        download_relic_image(data.get('icon', ''))

        relic_entry = convert_to_relic_format(data)
        relic_entry['_id'] = int(relic_id)
        print(f'[_relic] {json.dumps(relic_entry, ensure_ascii=False)}', file=output)
        relic_entries.append(relic_entry)

        relic_items = convert_to_relicitem_format(data)
        if relic_items:
            js_content = generate_relic_js(relic_id, relic_items)
            output_file = os.path.join(OUTPUT_RELIC_DIR, f'{relic_id}.js')
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(js_content)
            print(f'[_relicitem_] 已保存: {output_file}', file=output)
            for item in relic_items:
                print(f'  - {item["Name"]} ({item["Icon"]})', file=output)

    if auto_merge and relic_entries:
        print('--- 自动拼接 Relic.js ---', file=output)
        success = insert_relic_entries(relic_entries)
        if success:
            print('[完成] Relic.js 已更新', file=output)
        else:
            print('[失败] 拼接失败', file=output)

    return output.getvalue()


if __name__ == '__main__':
    main()