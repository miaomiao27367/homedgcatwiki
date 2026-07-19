import http.server
import socketserver
import os
import urllib.request
import shutil
import requests
from PIL import Image
import io
import re
import threading
import json

from urllib.parse import urlparse, unquote

from reliance.hsr_trans import generate_character_data
from reliance.hsr_trans_weapon import generate_weapon_data
from reliance.hsr_trans_mons_skills import generate_monster_data, generate_monster_basic_data, merge_missing_ee_data
from reliance.hsr_trans_ar import generate_ar_data
from reliance.hsr_trans_as import generate_as_data
from reliance.hsr_trans_fiction import generate_fiction_data
from reliance.hsr_trans_chaos import generate_chaos_data
from reliance.gi_trans import gi_character_update

data_url2="26.192.21.124:9080"
data_url1="26.118.195.109:8080"


def save_hsr_cache(character_ids, major_version, minor_versions):
    """保存用户选择的HSR更新参数到缓存文件"""
    log_dir = './logs'
    os.makedirs(log_dir, exist_ok=True)
    cache_file = os.path.join(log_dir, 'hsr_trans_avatar.txt')
    
    try:
        cache_data = {
            'character_ids': character_ids,
            'major_version': major_version,
            'minor_versions': minor_versions
        }
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=4)
        print(f"[缓存] 已保存用户选择: {cache_file}")
        return True
    except Exception as e:
        print(f"[缓存] 保存失败: {e}")
        return False


def load_hsr_cache():
    """从缓存文件读取用户选择的HSR更新参数"""
    cache_file = './logs/hsr_trans_avatar.txt'
    
    if not os.path.exists(cache_file):
        return None
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        print(f"[缓存] 已读取用户选择: {cache_file}")
        return cache_data
    except Exception as e:
        print(f"[缓存] 读取失败: {e}")
        return None


def save_hsr_weapon_cache(weapon_ids, major_version, minor_versions):
    """保存用户选择的HSR光锥更新参数到缓存文件"""
    log_dir = './logs'
    os.makedirs(log_dir, exist_ok=True)
    cache_file = os.path.join(log_dir, 'hsr_trans_weapon.txt')
    
    try:
        cache_data = {
            'weapon_ids': weapon_ids,
            'major_version': major_version,
            'minor_versions': minor_versions
        }
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=4)
        print(f"[缓存] 已保存光锥用户选择: {cache_file}")
        return True
    except Exception as e:
        print(f"[缓存] 保存失败: {e}")
        return False


def load_hsr_weapon_cache():
    """从缓存文件读取用户选择的HSR光锥更新参数"""
    cache_file = './logs/hsr_trans_weapon.txt'
    
    if not os.path.exists(cache_file):
        return None
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        print(f"[缓存] 已读取光锥用户选择: {cache_file}")
        return cache_data
    except Exception as e:
        print(f"[缓存] 读取失败: {e}")
        return None


def save_gi_cache(character_ids, major_version, minor_versions):
    """保存用户选择的GI更新参数到缓存文件"""
    log_dir = './logs'
    os.makedirs(log_dir, exist_ok=True)
    cache_file = os.path.join(log_dir, 'gi_trans_avatar.txt')
    
    try:
        cache_data = {
            'character_ids': character_ids,
            'major_version': major_version,
            'minor_versions': minor_versions
        }
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=4)
        print(f"[缓存] 已保存GI用户选择: {cache_file}")
        return True
    except Exception as e:
        print(f"[缓存] 保存失败: {e}")
        return False


def load_gi_cache():
    """从缓存文件读取用户选择的GI更新参数"""
    cache_file = './logs/gi_trans_avatar.txt'
    
    if not os.path.exists(cache_file):
        return None
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        print(f"[缓存] 已读取GI用户选择: {cache_file}")
        return cache_data
    except Exception as e:
        print(f"[缓存] 读取失败: {e}")
        return None


class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):

    def log_404(self, path):
        """记录404请求到日志文件"""
        log_dir = './logs'
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, '404_log.txt')
        
        # 获取客户端IP
        client_ip = self.client_address[0]
        # 获取时间
        import time
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        
        # 日志内容
        log_entry = f"[{timestamp}] IP: {client_ip} | Path: {path}\n"
        
        # 追加写入日志
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)

    def _download_single_file(self, url, save_path, file_name):
        """下载单个文件（线程函数）"""
        try:
            response = requests.get(url)
            response.raise_for_status()

            with Image.open(io.BytesIO(response.content)) as img:
                img.save(save_path, 'PNG')

            print(f'✓ 成功下载 {file_name}')
            return True
        except Exception as e:
            print(f'✗ 下载失败 {file_name}: {str(e)}')
            return False

    def get_skill_icons(self, character_id):
        """获取角色技能图标（多线程版本）"""
        print(f"[GET Skill Icons] 开始获取角色 {character_id} 的技能图标...")

        # 下载目录（使用相对路径，基于服务器运行目录）
        base_url1 = f'https://static.nanoka.cc/assets/hsr/skillicons/SkillIcon_{character_id}_{{}}.webp'
        base_url2 = f'https://static.nanoka.cc/assets/hsr/rank/_dependencies/textures/{character_id}/{character_id}_Rank_{{}}.webp'

        download_dir1 = os.path.join(os.getcwd(), 'images', 'skillicons', 'avatar', str(character_id))
        download_dir2 = os.path.join(os.getcwd(), 'images', 'rank', '_dependencies', 'textures', str(character_id))

        # 确保目录存在
        if not os.path.exists(download_dir1):
            os.makedirs(download_dir1)
        if not os.path.exists(download_dir2):
            os.makedirs(download_dir2)

        namelist = ['Rank1', 'Rank2', 'Rank3', 'Rank4', 'Rank5', 'Rank6', "SkillTree1", "SkillTree2", "SkillTree3",
                    "Ultra", "Normal", "Maze", "Elation", "BP", "Passive","Assist"]

        # 创建线程列表
        threads = []

        # 添加 Rank 图标下载任务
        for i in range(1, 7):
            png_file_name = f'{character_id}_Rank_{i}.png'
            png_file_path = os.path.join(download_dir2, png_file_name)
            url = base_url2.format(i)

            thread = threading.Thread(
                target=self._download_single_file,
                args=(url, png_file_path, png_file_name)
            )
            threads.append(thread)

        # 添加技能图标下载任务
        for name in namelist:
            png_file_name = f'SkillIcon_{character_id}_{name}.png'
            png_file_path = os.path.join(download_dir1, png_file_name)
            url = base_url1.format(name)

            thread = threading.Thread(
                target=self._download_single_file,
                args=(url, png_file_path, png_file_name)
            )
            threads.append(thread)

        # 启动所有线程
        print(f"[GET Skill Icons] 启动 {len(threads)} 个下载线程...")
        for thread in threads:
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        print('\n下载完成！')
        return True, None

    def handle_avatar_image(self, path):
        """处理角色图片更新请求"""
        # 检查是否是技能图标路径，需要单独处理
        skillicons_match = re.search(r'skillicons/avatar/(\d+)$', path)
        if skillicons_match:
            character_id = skillicons_match.group(1)
            print(f"[PUT Avatar Image] 调用 get_skill_icons 函数，角色ID: {character_id}")
            return self.get_skill_icons(character_id)

        # 定义路径模式映射（普通图片）
        path_patterns = [
            {'pattern': r'avatarshopicon/avatar/(\d+)\.png$', 'folder': 'avatarshopicon/avatar',
             'remote_folder': 'avatarshopicon'},
            {'pattern': r'avataricon/avatar/(\d+)\.png$', 'folder': 'avataricon/avatar', 'remote_folder': 'avataricon'},
            {'pattern': r'avatardrawcard/(\d+)\.png$', 'folder': 'avatardrawcard', 'remote_folder': 'avatardrawcard'}
        ]

        # 匹配路径模式
        character_id = None
        folder_name = None
        remote_folder = None

        for pattern_info in path_patterns:
            match = re.search(pattern_info['pattern'], path)
            if match:
                character_id = match.group(1)
                folder_name = pattern_info['folder']
                remote_folder = pattern_info['remote_folder']
                break

        if not character_id:
            print(f"[PUT Avatar Image] ✗ 无法从路径中提取角色ID: {path}")
            return False, "无法从路径中提取角色ID"

        print(f"[PUT Avatar Image] 角色ID: {character_id}, 类型: {folder_name}")

        local_path = os.path.join(os.getcwd(), path.lstrip('/'))
        local_dir = os.path.dirname(local_path)

        # 确保目录存在
        os.makedirs(local_dir, exist_ok=True)

        if folder_name == 'avataricon/avatar':
            temp="avatarroundicon"
        else:
            temp=remote_folder

        remote_url = f"https://static.nanoka.cc/assets/hsr/{temp}/{character_id}.webp"

        try:
            response = requests.get(remote_url)
            response.raise_for_status()

            with Image.open(io.BytesIO(response.content)) as img:
                img.save(local_path, 'PNG')

            print(f'[PUT Avatar Image] ✓ 成功下载并转换 {folder_name}/{character_id}.png')
            return True, None

        except Exception as e:
            print(f'[PUT Avatar Image] ✗ 下载失败 {folder_name}/{character_id}: {str(e)}')
            return False, str(e)

    def handle_weapon_image(self, path):

        # 判断是 medium icon 还是 max figure
        is_medium = '/images/lightconemediumicon/' in path
        is_max = '/images/lightconemaxfigures/' in path

        if not (is_medium or is_max):
            print(f"[PUT Weapon Image] ✗ 无法识别图片类型: {path}")
            return False, "无法识别图片类型"

        # 提取武器ID
        if is_medium:
            match = re.search(r'lightconemediumicon/(\d+)\.png$', path)
            folder_name = 'lightconemediumicon'
        else:
            match = re.search(r'lightconemaxfigures/(\d+)\.png$', path)
            folder_name = 'lightconemaxfigures'

        if not match:
            print(f"[PUT Weapon Image] ✗ 无法从路径中提取武器ID: {path}")
            return False, "无法从路径中提取武器ID"

        weapon_id = match.group(1)
        print(f"[PUT Weapon Image] 武器ID: {weapon_id}, 类型: {folder_name}")

        local_path = os.path.join(os.getcwd(), path.lstrip('/'))
        local_dir = os.path.dirname(local_path)

        os.makedirs(local_dir, exist_ok=True)

        remote_url = f"https://static.nanoka.cc/assets/hsr/{folder_name}/{weapon_id}.webp"

        try:
            response = requests.get(remote_url)
            response.raise_for_status()

            with Image.open(io.BytesIO(response.content)) as img:
                img.save(local_path, 'PNG')

            print(f'[PUT Weapon Image] ✓ 成功下载并转换 {folder_name}/{weapon_id}.png')
            return True, None

        except Exception as e:
            print(f'[PUT Weapon Image] ✗ 下载失败 {folder_name}/{weapon_id}: {str(e)}')
            return False, str(e)

    def handle_monster_image(self, path):
        """处理怪物图片更新请求"""
        match = re.search(r'Monster_(\d+)\.png$', path)
        if match:
            monster_id = match.group(1)
            local_path = os.path.join(os.getcwd(), path.lstrip('/'))
            local_dir = os.path.dirname(local_path)
            os.makedirs(local_dir, exist_ok=True)

            basic_url = 'https://static.nanoka.cc/assets/hsr/monsterfigure/Monster_{}.webp'
            remote_url = basic_url.format(monster_id)

            try:
                response = requests.get(remote_url)
                response.raise_for_status()

                with Image.open(io.BytesIO(response.content)) as img:
                    img.save(local_path, 'PNG')

                print(f'[PUT Monster Image] ✓ 成功下载并转换 Monster_{monster_id}.png')
                return True, None

            except Exception as e:
                print(f'[PUT Monster Image] ✗ 下载失败 Monster_{monster_id}: {str(e)}')
                return False, str(e)
        else:
            print(f"[PUT Monster Image] ✗ 无法从路径中提取怪物ID: {path}")
            return False, "无法从路径中提取怪物ID"

    def download_and_save_file(self, path):
        """通用文件下载和保存方法"""
        try:
            # 构建远程请求URL
            remote_url = f"http://{data_url1}{path}"
            print(f"[Download] 正在从 {remote_url} 下载...")
            
            # 发送GET请求获取数据
            with urllib.request.urlopen(remote_url) as response:
                data = response.read()
            
            # 构建本地文件路径
            local_path = os.path.join(os.getcwd(), path.lstrip('/'))
            local_dir = os.path.dirname(local_path)
            
            # 确保目录存在
            os.makedirs(local_dir, exist_ok=True)
            
            # 如果本地文件存在，备份到 olddata 文件夹
            if os.path.exists(local_path):
                # 获取当前日期 mm/dd
                import time
                date_str = time.strftime('%m/%d')
                
                # 构建备份路径
                backup_dir = os.path.join(os.getcwd(), 'olddata', date_str, os.path.dirname(path.lstrip('/')))
                os.makedirs(backup_dir, exist_ok=True)
                
                # 获取文件名
                filename = os.path.basename(local_path)
                backup_path = os.path.join(backup_dir, filename)
                
                # 复制文件到备份目录
                shutil.copy2(local_path, backup_path)
                print(f"[Download] 已备份旧文件到 {backup_path}")
            
            # 写入新文件
            with open(local_path, 'wb') as f:
                f.write(data)
            
            print(f"[Download] 文件已保存到 {local_path}")
            
            return True, None
            
        except Exception as e:
            print(f"[Download] 下载失败: {str(e)}")
            return False, str(e)

    def do_PUT(self):
        """处理PUT update请求：根据路径类型分发到不同处理函数"""
        # 解析请求路径
        parsed_path = urlparse(self.path)
        path = unquote(parsed_path.path)
        
        # 输出到控制台
        print(f"[PUT Update] Path: {path}")
        
        # 只处理 .js、.png、.html 文件，以及 skillicons/avatar 路径（用于触发技能图标批量下载）
        is_skillicons_path = '/images/skillicons/avatar/' in path
        if not (path.endswith('.js') or path.endswith('.png') or path.endswith('.html') or path.endswith('.css') or is_skillicons_path):
            # 发送成功响应
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(b'{"status": "success", "message": "Update request received"}')
            print("-" * 50)
            return
        
        # 根据路径模式分发到不同处理函数
        success = False
        error_msg = None
        
        if '/images/avatarshopicon/avatar/' in path or '/images/avataricon/avatar/' in path or '/images/avatardrawcard/' in path or '/images/skillicons/avatar/' in path:
            # 角色图片
            success, error_msg = self.handle_avatar_image(path)
        elif '/images/lightconemediumicon/' in path or '/images/lightconemaxfigures/' in path:
            # 武器图片
            success, error_msg = self.handle_weapon_image(path)
        elif '/images/monsterfigure/' in path:
            # 怪物图片
            success, error_msg = self.handle_monster_image(path)
        else:
            # 其他文件（.js 和其他 .png）使用通用处理
            success, error_msg = self.download_and_save_file(path)
        
        # 发送响应
        try:
            if success:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(b'{"status": "success", "message": "File downloaded successfully"}')
            else:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(f'{{"status": "error", "message": "{error_msg}"}}'.encode('utf-8'))
        except ConnectionAbortedError:
            print(f"[PUT] 客户端断开连接: {path}")
        except Exception as e:
            print(f"[PUT] 发送响应失败 {path}: {str(e)}")
        
        print("-" * 50)

    def do_GET(self):
        try:
            # 解析请求路径
            parsed_path = urlparse(self.path)
            path = unquote(parsed_path.path)

            # 读取HSR缓存
            if path == '/hsr_load_cache':
                cache_data = load_hsr_cache()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                if cache_data:
                    self.wfile.write(json.dumps({"status": "success", "data": cache_data}, ensure_ascii=False).encode('utf-8'))
                else:
                    self.wfile.write(json.dumps({"status": "empty"}, ensure_ascii=False).encode('utf-8'))
                print("-" * 50)
                return

            # 读取HSR光锥缓存
            if path == '/hsr_weapon_load_cache':
                cache_data = load_hsr_weapon_cache()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                if cache_data:
                    self.wfile.write(json.dumps({"status": "success", "data": cache_data}, ensure_ascii=False).encode('utf-8'))
                else:
                    self.wfile.write(json.dumps({"status": "empty"}, ensure_ascii=False).encode('utf-8'))
                print("-" * 50)
                return

            # 读取GI角色缓存
            if path == '/gi_load_cache':
                cache_data = load_gi_cache()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                if cache_data:
                    self.wfile.write(json.dumps({"status": "success", "data": cache_data}, ensure_ascii=False).encode('utf-8'))
                else:
                    self.wfile.write(json.dumps({"status": "empty"}, ensure_ascii=False).encode('utf-8'))
                print("-" * 50)
                return

            # 确保路径以 / 结尾时指向目录;此功能仅用于映射根目录index
            if path.endswith('/'):
                path = path + 'index.html'

            # 构建完整文件路径
            #lstrip为去除左侧的/
            file_path = os.path.join(os.getcwd(), path.lstrip('/'))

            # 是目录处理
            if os.path.isdir(file_path):
                # 如果是目录，尝试访问index.html
                file_path = os.path.join(file_path, 'index.html')
                path = path + '/index.html'
            
            # 检查文件是否存在
            file_exists = os.path.exists(file_path) and os.path.isfile(file_path)
            
            if file_exists:
                self.path = path
            else:
                # 记录404请求
                self.log_404(self.path)

            # 调用父类方法处理请求
            super().do_GET()
        except ConnectionAbortedError:
            # 客户端断开连接，忽略此错误
            print(f"[GET] 客户端断开连接: {self.path}")
        except Exception as e:
            print(f"[GET] 处理请求失败 {self.path}: {str(e)}")

    # 重写send_response方法，添加编码头
    def send_response(self, code, message=None):
        super().send_response(code, message)
        # 根据文件类型设置正确的Content-Type
        if self.path.endswith('.js'):
            self.send_header('Content-Type', 'application/javascript; charset=utf-8')
        elif self.path.endswith('.html'):
            self.send_header('Content-Type', 'text/html; charset=utf-8')
        elif self.path.endswith('.css'):
            self.send_header('Content-Type', 'text/css; charset=utf-8')

    def do_POST(self):
        """处理POST请求"""
        parsed_path = urlparse(self.path)
        path = unquote(parsed_path.path)

        print(f"[POST] 收到请求: {path}")

        # 最先处理 /hsr_update
        if path == '/hsr_update':
            try:
                # 读取请求体
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                
                # 尝试解析JSON
                try:
                    request_data = json.loads(post_data.decode('utf-8'))
                    character_ids = request_data.get('character_ids', [])
                    major_version = request_data.get('major_version')
                    minor_versions = request_data.get('minor_versions')
                    
                    print(f"[hsr_update] 收到参数: character_ids={character_ids}, major_version={major_version}, minor_versions={minor_versions}")
                except:
                    # 如果解析失败，用默认值
                    character_ids = ["1510"]
                    major_version = "4.3"
                    minor_versions = [".51", ".52"]
                    print(f"[hsr_update] 使用默认参数: character_ids={character_ids}, major_version={major_version}, minor_versions={minor_versions}")

                try:
                    # 保存用户选择到缓存
                    save_hsr_cache(character_ids, major_version, minor_versions)
                    
                    results = []
                    for character_id in character_ids:
                        print(f"[hsr_update] 开始处理角色 {character_id}...")
                        str_return = generate_character_data(character_id, major_version, minor_versions)
                        results.append(f"角色 {character_id}: {str_return}")
                    
                    final_output = "\n".join(results)
                    response_data = {"status": "success", "message": f"成功处理 {len(character_ids)} 个角色", "stdout": final_output}
                    
                except Exception as e:

                    error_msg = str(e)
                    print(f"[hsr_update] 执行失败: {error_msg}")
                    response_data = {"status": "error", "message": "数据更新失败", "stderr": f"抛出异常: {error_msg}"}
                
                # 发送响应
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))
                
            except Exception as e:
                print(f"[hsr_update] 处理失败: {str(e)}")
                error_msg = str(e).replace('"', '\\"')
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(f'{{"status": "error", "message": "{error_msg}"}}'.encode('utf-8'))
            
            print("-" * 50)
            return

        # 处理 /hsr_update_weapon
        if path == '/hsr_update_weapon':
            try:
                # 读取请求体
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                
                # 尝试解析JSON
                try:
                    request_data = json.loads(post_data.decode('utf-8'))
                    weapon_ids = request_data.get('weapon_ids', [])
                    major_version = request_data.get('major_version')
                    minor_versions = request_data.get('minor_versions')
                    
                    print(f"[hsr_update_weapon] 收到参数: weapon_ids={weapon_ids}, major_version={major_version}, minor_versions={minor_versions}")
                except:
                    # 如果解析失败，用默认值
                    weapon_ids = ["23060"]
                    major_version = "4.3"
                    minor_versions = [".51", ".52"]
                    print(f"[hsr_update_weapon] 使用默认参数: weapon_ids={weapon_ids}, major_version={major_version}, minor_versions={minor_versions}")

                try:
                    # 保存用户选择到缓存
                    save_hsr_weapon_cache(weapon_ids, major_version, minor_versions)
                    
                    results = []
                    for weapon_id in weapon_ids:
                        print(f"[hsr_update_weapon] 开始处理光锥 {weapon_id}...")
                        str_return = generate_weapon_data(weapon_id, major_version, minor_versions)
                        results.append(f"光锥 {weapon_id}: {str_return}")
                    
                    final_output = "\n".join(results)
                    response_data = {"status": "success", "message": f"成功处理 {len(weapon_ids)} 个光锥", "stdout": final_output}
                    
                except Exception as e:
                    error_msg = str(e)
                    print(f"[hsr_update_weapon] 执行失败: {error_msg}")
                    response_data = {"status": "error", "message": "光锥数据更新失败", "stderr": f"抛出异常: {error_msg}"}
                
                # 发送响应
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))
                
            except Exception as e:
                print(f"[hsr_update_weapon] 处理失败: {str(e)}")
                error_msg = str(e).replace('"', '\\"')
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(f'{{"status": "error", "message": "{error_msg}"}}'.encode('utf-8'))
            
            print("-" * 50)
            return

        # 处理 /hsr_update_monster (多线程处理)
        if path == '/hsr_update_monster':
            try:
                # 读取请求体
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                
                # 尝试解析JSON
                try:
                    request_data = json.loads(post_data.decode('utf-8'))
                    monster_ids = request_data.get('monster_ids', [])
                    version = request_data.get('version')
                    
                    print(f"[hsr_update_monster] 收到参数: monster_ids={monster_ids}, version={version}")
                except:
                    # 如果解析失败，用默认值
                    monster_ids = ["8015030"]
                    version = "4.3.51"
                    print(f"[hsr_update_monster] 使用默认参数: monster_ids={monster_ids}, version={version}")

                try:
                    # 使用多线程处理每个怪物ID
                    results = []
                    threads = []
                    result_lock = threading.Lock()
                    
                    def process_monster(monster_id, ver):
                        """单个怪物处理函数（在线程中执行）"""
                        try:
                            print(f"[hsr_update_monster] 开始处理怪物 {monster_id}...")
                            str_return = generate_monster_data(monster_id, ver)
                            with result_lock:
                                results.append(f"怪物 {monster_id}: {str_return}")
                        except Exception as e:
                            with result_lock:
                                results.append(f"怪物 {monster_id}: 处理异常 - {str(e)}")
                    
                    # 创建并启动所有线程
                    for monster_id in monster_ids:
                        t = threading.Thread(target=process_monster, args=(monster_id, version))
                        t.daemon = True
                        threads.append(t)
                        t.start()
                    
                    # 等待所有线程完成
                    for t in threads:
                        t.join()
                    
                    # 合并 EE 数据：比对 skill 文件中没有引用的 eeid，写入 EE.js 并删除 *_ee.js
                    try:
                        merge_result = merge_missing_ee_data()
                        results.append(f"EE合并: {merge_result}")
                    except Exception as e:
                        results.append(f"EE合并失败: {str(e)}")
                    
                    final_output = "\n".join(results)
                    response_data = {"status": "success", "message": f"成功处理 {len(monster_ids)} 个怪物", "stdout": final_output}
                    
                except Exception as e:
                    error_msg = str(e)
                    print(f"[hsr_update_monster] 执行失败: {error_msg}")
                    response_data = {"status": "error", "message": "怪物数据更新失败", "stderr": f"抛出异常: {error_msg}"}
                
                # 发送响应
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))
                
            except Exception as e:
                print(f"[hsr_update_monster] 处理失败: {str(e)}")
                error_msg = str(e).replace('"', '\\"')
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(f'{{"status": "error", "message": "{error_msg}"}}'.encode('utf-8'))
            
            print("-" * 50)
            return

        # 处理 /hsr_update_ar
        if path == '/hsr_update_ar':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)

                try:
                    request_data = json.loads(post_data.decode('utf-8'))
                    peak_id = request_data.get('peak_id', '')
                    version = request_data.get('version', '')

                    print(f"[hsr_update_ar] 收到参数: peak_id={peak_id}, version={version}")
                except:
                    peak_id = "2"
                    version = "4.3.52"
                    print(f"[hsr_update_ar] 使用默认参数: peak_id={peak_id}, version={version}")

                try:
                    str_return = generate_ar_data(peak_id, version)
                    response_data = {"status": "success", "message": f"AR数据生成完成", "stdout": str_return}

                except Exception as e:
                    error_msg = str(e)
                    print(f"[hsr_update_ar] 执行失败: {error_msg}")
                    response_data = {"status": "error", "message": "AR数据生成失败", "stderr": f"抛出异常: {error_msg}"}

                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))

            except Exception as e:
                print(f"[hsr_update_ar] 处理失败: {str(e)}")
                error_msg = str(e).replace('"', '\\"')
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(f'{{"status": "error", "message": "{error_msg}"}}'.encode('utf-8'))

            print("-" * 50)
            return

        # 处理 /hsr_update_as
        if path == '/hsr_update_as':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)

                try:
                    request_data = json.loads(post_data.decode('utf-8'))
                    boss_id = request_data.get('boss_id', '')
                    version = request_data.get('version', '')

                    print(f"[hsr_update_as] 收到参数: boss_id={boss_id}, version={version}")
                except:
                    boss_id = "3018"
                    version = "4.3.52"
                    print(f"[hsr_update_as] 使用默认参数: boss_id={boss_id}, version={version}")

                try:
                    str_return = generate_as_data(boss_id, version)
                    response_data = {"status": "success", "message": f"AS数据生成完成", "stdout": str_return}

                except Exception as e:
                    error_msg = str(e)
                    print(f"[hsr_update_as] 执行失败: {error_msg}")
                    response_data = {"status": "error", "message": "AS数据生成失败", "stderr": f"抛出异常: {error_msg}"}

                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))

            except Exception as e:
                print(f"[hsr_update_as] 处理失败: {str(e)}")
                error_msg = str(e).replace('"', '\\"')
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(f'{{"status": "error", "message": "{error_msg}"}}'.encode('utf-8'))

            print("-" * 50)
            return

        # 处理 /hsr_update_fiction
        if path == '/hsr_update_fiction':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)

                try:
                    request_data = json.loads(post_data.decode('utf-8'))
                    story_id = request_data.get('story_id', '')
                    version = request_data.get('version', '')
                    monster_overrides = request_data.get('monster_overrides', None)

                    print(f"[hsr_update_fiction] 收到参数: story_id={story_id}, version={version}, monster_overrides={'有' if monster_overrides else '无'}")
                except:
                    story_id = "101"
                    version = "4.3.52"
                    monster_overrides = None
                    print(f"[hsr_update_fiction] 使用默认参数: story_id={story_id}, version={version}")

                try:
                    # 仿照hsr_trans_fiction.py的__main__构造hp_add_values
                    # monster_overrides: 8个元素(4层×2半波)，每个为null或[v1, v2, v3]
                    # 转换为: {floor_num: {wave_idx: hp_add_value}}
                    hp_add_values = None
                    if monster_overrides:
                        hp_add_values = {}
                        for floor_idx in range(4):
                            floor_num = str(floor_idx + 1)
                            # 上半: wave_idx 0,1,2
                            upper_vals = monster_overrides[floor_idx * 2]
                            if upper_vals:
                                hp_add_values[floor_num] = {}
                                for wave_idx, val in enumerate(upper_vals):
                                    hp_add_values[floor_num][wave_idx] = float(val)
                            # 下半: wave_idx 3,4,5
                            lower_vals = monster_overrides[floor_idx * 2 + 1]
                            if lower_vals:
                                if floor_num not in hp_add_values:
                                    hp_add_values[floor_num] = {}
                                for wave_idx, val in enumerate(lower_vals):
                                    hp_add_values[floor_num][wave_idx + 3] = float(val)

                    str_return, not_found_ids, converted_data = generate_fiction_data(story_id, version, hp_add_values)
                    response_data = {"status": "success", "message": f"虚构叙事数据生成完成", "stdout": str_return}

                except Exception as e:
                    error_msg = str(e)
                    print(f"[hsr_update_fiction] 执行失败: {error_msg}")
                    response_data = {"status": "error", "message": "虚构叙事数据生成失败", "stderr": f"抛出异常: {error_msg}"}

                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))

            except Exception as e:
                print(f"[hsr_update_fiction] 处理失败: {str(e)}")
                error_msg = str(e).replace('"', '\\"')
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(f'{{"status": "error", "message": "{error_msg}"}}'.encode('utf-8'))

            print("-" * 50)
            return

        # 处理 /hsr_update_chaos
        if path == '/hsr_update_chaos':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)

                try:
                    request_data = json.loads(post_data.decode('utf-8'))
                    maze_id = request_data.get('maze_id', '')
                    version = request_data.get('version', '')
                    hp_ratios = request_data.get('hp_ratios', None)

                    print(f"[hsr_update_chaos] 收到参数: maze_id={maze_id}, version={version}, hp_ratios={hp_ratios}")
                except:
                    maze_id = "1033"
                    version = "4.3.52"
                    hp_ratios = None
                    print(f"[hsr_update_chaos] 使用默认参数: maze_id={maze_id}, version={version}")

                try:
                    if hp_ratios and len(hp_ratios) == 12:
                        str_return = generate_chaos_data(maze_id, version, hp_ratios)
                    else:
                        from reliance.hsr_trans_chaos import DEFAULT_FLOOR_HP_RATIOS
                        str_return = generate_chaos_data(maze_id, version, DEFAULT_FLOOR_HP_RATIOS)
                    response_data = {"status": "success", "message": f"混沌回忆数据生成完成", "stdout": str_return}

                except Exception as e:
                    error_msg = str(e)
                    print(f"[hsr_update_chaos] 执行失败: {error_msg}")
                    response_data = {"status": "error", "message": "混沌回忆数据生成失败", "stderr": f"抛出异常: {error_msg}"}

                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))

            except Exception as e:
                print(f"[hsr_update_chaos] 处理失败: {str(e)}")
                error_msg = str(e).replace('"', '\\"')
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(f'{{"status": "error", "message": "{error_msg}"}}'.encode('utf-8'))

            print("-" * 50)
            return

        # 处理 /gi_update
        if path == '/gi_update':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                
                try:
                    request_data = json.loads(post_data.decode('utf-8'))
                    character_ids = request_data.get('character_ids', [])
                    major_version = request_data.get('major_version')
                    minor_versions = request_data.get('minor_versions')
                    
                    print(f"[gi_update] 收到参数: character_ids={character_ids}, major_version={major_version}, minor_versions={minor_versions}")
                except:
                    character_ids = ["10000003"]
                    major_version = "6.7"
                    minor_versions = [".52", ".53"]
                    print(f"[gi_update] 使用默认参数: character_ids={character_ids}, major_version={major_version}, minor_versions={minor_versions}")

                try:
                    save_gi_cache(character_ids, major_version, minor_versions)
                    
                    results = []
                    for character_id in character_ids:
                        print(f"[gi_update] 开始处理角色 {character_id}...")
                        success, msg = gi_character_update(character_id, major_version, minor_versions)
                        results.append(f"角色 {character_id}: {msg}")
                    
                    final_output = "\n".join(results)
                    response_data = {"status": "success", "message": f"成功处理 {len(character_ids)} 个角色", "stdout": final_output}
                    
                except Exception as e:
                    error_msg = str(e)
                    print(f"[gi_update] 执行失败: {error_msg}")
                    response_data = {"status": "error", "message": "GI数据更新失败", "stderr": f"抛出异常: {error_msg}"}
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))
                
            except Exception as e:
                print(f"[gi_update] 处理失败: {str(e)}")
                error_msg = str(e).replace('"', '\\"')
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(f'{{"status": "error", "message": "{error_msg}"}}'.encode('utf-8'))
            
            print("-" * 50)
            return

        # 其他 POST 请求处理...
        # 如果没有匹配的处理，返回 404
        self.send_response(404)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(b'{"status": "error", "message": "Not Found"}')
        print("-" * 50)

if __name__ == "__main__":
    PORT = 9080
    Handler = CustomHTTPRequestHandler
    
    # 使用多线程TCPServer，避免下载时阻塞其他请求
    with socketserver.ThreadingTCPServer(("", PORT), Handler) as httpd:
        httpd.daemon_threads = True  # 设置守护线程
        httpd.allow_reuse_address = True  # 允许地址重用
        print(f"服务器启动在 http://localhost:{PORT} (多线程模式)")
        httpd.serve_forever()