// 工具页面主逻辑
var ToolsApp = {
    currentTool: null,

    // 初始化
    init: function() {
        this.bindEvents();
        this.showTool('hsr-update');
        this.loadHSRCache();
        this.loadHSRWeaponCache();
        this.loadGICache();
    },

    // 加载HSR角色缓存
    loadHSRCache: async function() {
        try {
            var response = await fetch('/hsr_load_cache');
            var result = await response.json();
            
            if (result.status === 'success' && result.data) {
                var data = result.data;
                if (data.character_ids && data.character_ids.length > 0) {
                    document.getElementById('hsrCharacterId').value = data.character_ids.join(', ');
                }
                if (data.major_version) {
                    document.getElementById('hsrMajorVersion').value = data.major_version;
                }
                if (data.minor_versions && data.minor_versions.length > 0) {
                    var container = document.getElementById('characterMinorVersionsContainer');
                    container.innerHTML = '';
                    for (var i = 0; i < data.minor_versions.length; i++) {
                        var div = document.createElement('div');
                        div.className = 'minor-versions';
                        div.innerHTML = '<input type="text" class="minorVersion" value="' + data.minor_versions[i] + '" placeholder=".51">';
                        container.appendChild(div);
                    }
                }
            }
        } catch (e) {
            console.log('加载角色缓存失败:', e);
        }
    },

    // 加载HSR光锥缓存
    loadHSRWeaponCache: async function() {
        try {
            var response = await fetch('/hsr_weapon_load_cache');
            var result = await response.json();
            
            if (result.status === 'success' && result.data) {
                var data = result.data;
                if (data.weapon_ids && data.weapon_ids.length > 0) {
                    document.getElementById('hsrWeaponId').value = data.weapon_ids.join(', ');
                }
                if (data.major_version) {
                    document.getElementById('hsrWeaponMajorVersion').value = data.major_version;
                }
                if (data.minor_versions && data.minor_versions.length > 0) {
                    var container = document.getElementById('weaponMinorVersionsContainer');
                    container.innerHTML = '';
                    for (var i = 0; i < data.minor_versions.length; i++) {
                        var div = document.createElement('div');
                        div.className = 'minor-versions';
                        div.innerHTML = '<input type="text" class="minorVersion" value="' + data.minor_versions[i] + '" placeholder=".51">';
                        container.appendChild(div);
                    }
                }
            }
        } catch (e) {
            console.log('加载光锥缓存失败:', e);
        }
    },

    // 加载GI角色缓存
    loadGICache: async function() {
        try {
            var response = await fetch('/gi_load_cache');
            var result = await response.json();
            
            if (result.status === 'success' && result.data) {
                var data = result.data;
                if (data.character_ids && data.character_ids.length > 0) {
                    document.getElementById('giCharacterId').value = data.character_ids.join(', ');
                }
                if (data.version_map) {
                    var pairs = [];
                    for (var key in data.version_map) {
                        pairs.push(key + ':' + data.version_map[key]);
                    }
                    document.getElementById('giVersionMap').value = pairs.join(', ');
                }
            }
        } catch (e) {
            console.log('加载GI缓存失败:', e);
        }
    },

    // 绑定事件
    bindEvents: function() {
        var self = this;

        // 侧边栏菜单点击
        document.querySelectorAll('.tools-sidebar-item').forEach(function(item) {
            item.addEventListener('click', function() {
                var toolId = this.getAttribute('data-tool');
                self.showTool(toolId);
            });
        });

        // 返回按钮
        document.getElementById('backBtn').addEventListener('click', function() {
            window.location.href = '/';
        });
    },

    // 显示指定工具
    showTool: function(toolId) {
        // 更新侧边栏选中状态
        document.querySelectorAll('.tools-sidebar-item').forEach(function(item) {
            item.classList.remove('active');
            if (item.getAttribute('data-tool') === toolId) {
                item.classList.add('active');
            }
        });

        // 更新内容区
        document.querySelectorAll('.tools-section').forEach(function(section) {
            section.classList.remove('active');
            if (section.id === toolId) {
                section.classList.add('active');
            }
        });

        this.currentTool = toolId;
    },

    // 添加角色小版本输入框
    addCharacterMinorVersion: function() {
        var container = document.getElementById('characterMinorVersionsContainer');
        var newGroup = document.createElement('div');
        newGroup.className = 'minor-versions';
        newGroup.innerHTML = ' <input type="text" class="minorVersion" placeholder=".53"> <input type="text" class="minorVersion" placeholder=".53"> <button type="button" class="btn-remove" onclick="ToolsApp.removeMinorVersion(this)">×</button>';
        container.appendChild(newGroup);
    },

    // 添加光锥小版本输入框
    addWeaponMinorVersion: function() {
        var container = document.getElementById('weaponMinorVersionsContainer');
        var newGroup = document.createElement('div');
        newGroup.className = 'minor-versions';
        newGroup.innerHTML = ' <input type="text" class="minorVersion" placeholder=".53"> <input type="text" class="minorVersion" placeholder=".53"> <button type="button" class="btn-remove" onclick="ToolsApp.removeMinorVersion(this)">×</button>';
        container.appendChild(newGroup);
    },

    // 删除一行输入框
    removeMinorVersion: function(btn) {
        var group = btn.parentElement;
        var container = group.parentElement;
        // 至少保留一行
        if (container.querySelectorAll('.minor-versions').length > 1) {
            group.remove();
        }
    },

    // 发送HSR角色更新请求
    sendHSRUpdate: async function() {
        var submitBtn = document.getElementById('hsrSubmitBtn');
        var btnText = document.getElementById('hsrBtnText');
        var resultDiv = document.getElementById('hsrResult');

        var minorVersionInputs = document.querySelectorAll('#hsr-update .minorVersion');
        var minorVersions = Array.from(minorVersionInputs)
            .map(function(input) { return input.value.trim(); })
            .filter(function(value) { return value; });

        var characterIdText = document.getElementById('hsrCharacterId').value.trim();
        var characterIds = characterIdText
            .split(/[\s,]+/)
            .map(function(id) { return id.trim(); })
            .filter(function(id) { return id; });

        var data = {
            character_ids: characterIds,
            major_version: document.getElementById('hsrMajorVersion').value.trim(),
            minor_versions: minorVersions
        };

        submitBtn.disabled = true;
        btnText.innerHTML = '<span class="loading"></span>处理中...';
        resultDiv.style.display = 'none';

        try {
            var response = await fetch('/hsr_update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            var result = await response.json();

            resultDiv.style.display = 'block';
            resultDiv.className = 'result ' + result.status;
            document.getElementById('hsrResultTitle').textContent =
                result.status === 'success' ? '✓ 更新成功' : '✗ 更新失败';
            document.getElementById('hsrResultMessage').textContent = result.message;

            var outputText = result.stdout || result.stderr || '';
            document.getElementById('hsrResultOutput').textContent = outputText;
            document.getElementById('hsrResultOutput').style.display = outputText ? 'block' : 'none';

        } catch (error) {
            resultDiv.style.display = 'block';
            resultDiv.className = 'result error';
            document.getElementById('hsrResultTitle').textContent = '✗ 请求失败';
            document.getElementById('hsrResultMessage').textContent = '网络错误，请重试';
            document.getElementById('hsrResultOutput').textContent = error.toString();
            document.getElementById('hsrResultOutput').style.display = 'block';
        } finally {
            submitBtn.disabled = false;
            btnText.textContent = '发送更新请求';
        }
    },

    // 发送HSR光锥更新请求
    sendHSRWeaponUpdate: async function() {
        var submitBtn = document.getElementById('hsrWeaponSubmitBtn');
        var btnText = document.getElementById('hsrWeaponBtnText');
        var resultDiv = document.getElementById('hsrWeaponResult');

        var minorVersionInputs = document.querySelectorAll('#hsr-weapon-update .minorVersion');
        var minorVersions = Array.from(minorVersionInputs)
            .map(function(input) { return input.value.trim(); })
            .filter(function(value) { return value; });

        var weaponIdText = document.getElementById('hsrWeaponId').value.trim();
        var weaponIds = weaponIdText
            .split(/[\s,]+/)
            .map(function(id) { return id.trim(); })
            .filter(function(id) { return id; });

        var data = {
            weapon_ids: weaponIds,
            major_version: document.getElementById('hsrWeaponMajorVersion').value.trim(),
            minor_versions: minorVersions
        };

        submitBtn.disabled = true;
        btnText.innerHTML = '<span class="loading"></span>处理中...';
        resultDiv.style.display = 'none';

        try {
            var response = await fetch('/hsr_update_weapon', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            var result = await response.json();

            resultDiv.style.display = 'block';
            resultDiv.className = 'result ' + result.status;
            document.getElementById('hsrWeaponResultTitle').textContent =
                result.status === 'success' ? '✓ 更新成功' : '✗ 更新失败';
            document.getElementById('hsrWeaponResultMessage').textContent = result.message;

            var outputText = result.stdout || result.stderr || '';
            document.getElementById('hsrWeaponResultOutput').textContent = outputText;
            document.getElementById('hsrWeaponResultOutput').style.display = outputText ? 'block' : 'none';

        } catch (error) {
            resultDiv.style.display = 'block';
            resultDiv.className = 'result error';
            document.getElementById('hsrWeaponResultTitle').textContent = '✗ 请求失败';
            document.getElementById('hsrWeaponResultMessage').textContent = '网络错误，请重试';
            document.getElementById('hsrWeaponResultOutput').textContent = error.toString();
            document.getElementById('hsrWeaponResultOutput').style.display = 'block';
        } finally {
            submitBtn.disabled = false;
            btnText.textContent = '发送更新请求';
        }
    },

    // 发送HSR怪物更新请求
    sendHSRMonsterUpdate: async function() {
        var submitBtn = document.getElementById('hsrMonsterSubmitBtn');
        var btnText = document.getElementById('hsrMonsterBtnText');
        var resultDiv = document.getElementById('hsrMonsterResult');

        var monsterIdText = document.getElementById('hsrMonsterId').value.trim();
        var monsterIds = monsterIdText
            .split(/[\s,]+/)
            .map(function(id) { return id.trim(); })
            .filter(function(id) { return id; });

        var data = {
            monster_ids: monsterIds,
            version: document.getElementById('hsrMonsterVersion').value.trim()
        };

        submitBtn.disabled = true;
        btnText.innerHTML = '<span class="loading"></span>处理中...';
        resultDiv.style.display = 'none';

        try {
            var response = await fetch('/hsr_update_monster', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            var result = await response.json();

            resultDiv.style.display = 'block';
            resultDiv.className = 'result ' + result.status;
            document.getElementById('hsrMonsterResultTitle').textContent =
                result.status === 'success' ? '✓ 更新成功' : '✗ 更新失败';
            document.getElementById('hsrMonsterResultMessage').textContent = result.message;

            var outputText = result.stdout || result.stderr || '';
            document.getElementById('hsrMonsterResultOutput').textContent = outputText;
            document.getElementById('hsrMonsterResultOutput').style.display = outputText ? 'block' : 'none';

        } catch (error) {
            resultDiv.style.display = 'block';
            resultDiv.className = 'result error';
            document.getElementById('hsrMonsterResultTitle').textContent = '✗ 请求失败';
            document.getElementById('hsrMonsterResultMessage').textContent = '网络错误，请重试';
            document.getElementById('hsrMonsterResultOutput').textContent = error.toString();
            document.getElementById('hsrMonsterResultOutput').style.display = 'block';
        } finally {
            submitBtn.disabled = false;
            btnText.textContent = '发送更新请求';
        }
    },

    // 发送HSR AR更新请求
    sendHSRArUpdate: async function() {
        var submitBtn = document.getElementById('hsrArSubmitBtn');
        var btnText = document.getElementById('hsrArBtnText');
        var resultDiv = document.getElementById('hsrArResult');

        var data = {
            peak_id: document.getElementById('hsrArPeakId').value.trim(),
            version: document.getElementById('hsrArVersion').value.trim()
        };

        submitBtn.disabled = true;
        btnText.innerHTML = '<span class="loading"></span>处理中...';
        resultDiv.style.display = 'none';

        try {
            var response = await fetch('/hsr_update_ar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            var result = await response.json();

            resultDiv.style.display = 'block';
            resultDiv.className = 'result ' + result.status;
            document.getElementById('hsrArResultTitle').textContent =
                result.status === 'success' ? '✓ 更新成功' : '✗ 更新失败';
            document.getElementById('hsrArResultMessage').textContent = result.message;

            var outputText = result.stdout || result.stderr || '';
            document.getElementById('hsrArResultOutput').textContent = outputText;
            document.getElementById('hsrArResultOutput').style.display = outputText ? 'block' : 'none';

        } catch (error) {
            resultDiv.style.display = 'block';
            resultDiv.className = 'result error';
            document.getElementById('hsrArResultTitle').textContent = '✗ 请求失败';
            document.getElementById('hsrArResultMessage').textContent = '网络错误，请重试';
            document.getElementById('hsrArResultOutput').textContent = error.toString();
            document.getElementById('hsrArResultOutput').style.display = 'block';
        } finally {
            submitBtn.disabled = false;
            btnText.textContent = '发送更新请求';
        }
    },

    // 发送HSR AS更新请求
    sendHSRAsUpdate: async function() {
        var submitBtn = document.getElementById('hsrAsSubmitBtn');
        var btnText = document.getElementById('hsrAsBtnText');
        var resultDiv = document.getElementById('hsrAsResult');

        var data = {
            boss_id: document.getElementById('hsrAsBossId').value.trim(),
            version: document.getElementById('hsrAsVersion').value.trim()
        };

        submitBtn.disabled = true;
        btnText.innerHTML = '<span class="loading"></span>处理中...';
        resultDiv.style.display = 'none';

        try {
            var response = await fetch('/hsr_update_as', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            var result = await response.json();

            resultDiv.style.display = 'block';
            resultDiv.className = 'result ' + result.status;
            document.getElementById('hsrAsResultTitle').textContent =
                result.status === 'success' ? '✓ 更新成功' : '✗ 更新失败';
            document.getElementById('hsrAsResultMessage').textContent = result.message;

            var outputText = result.stdout || result.stderr || '';
            document.getElementById('hsrAsResultOutput').textContent = outputText;
            document.getElementById('hsrAsResultOutput').style.display = outputText ? 'block' : 'none';

        } catch (error) {
            resultDiv.style.display = 'block';
            resultDiv.className = 'result error';
            document.getElementById('hsrAsResultTitle').textContent = '✗ 请求失败';
            document.getElementById('hsrAsResultMessage').textContent = '网络错误，请重试';
            document.getElementById('hsrAsResultOutput').textContent = error.toString();
            document.getElementById('hsrAsResultOutput').style.display = 'block';
        } finally {
            submitBtn.disabled = false;
            btnText.textContent = '发送更新请求';
        }
    },

    // 发送HSR Fiction更新请求
    sendHSRFictionUpdate: async function() {
        var submitBtn = document.getElementById('hsrFictionSubmitBtn');
        var btnText = document.getElementById('hsrFictionBtnText');
        var resultDiv = document.getElementById('hsrFictionResult');

        var monsterOverrides = [];
        var floors = document.querySelectorAll('#hsrFictionMonsterOverrides .monster-floor');
        var hasAnyValue = false;
        for (var f = 0; f < floors.length; f++) {
            var inputs = floors[f].querySelectorAll('input');
            for (var i = 0; i < inputs.length; i++) {
                var val = inputs[i].value.trim();
                if (val) {
                    hasAnyValue = true;
                    var parts = val.split(/\s+/);
                    var v1 = parseFloat(parts[0]) || 1.0;
                    var v2 = parseFloat(parts[1]) || 1.0;
                    var v3 = parseFloat(parts[2]) || 1.0;
                    monsterOverrides.push([v1, v2, v3]);
                } else {
                    monsterOverrides.push(null);
                }
            }
        }

        var data = {
            story_id: document.getElementById('hsrFictionStoryId').value.trim(),
            version: document.getElementById('hsrFictionVersion').value.trim(),
            monster_overrides: hasAnyValue ? monsterOverrides : null
        };

        submitBtn.disabled = true;
        btnText.innerHTML = '<span class="loading"></span>处理中...';
        resultDiv.style.display = 'none';

        try {
            var response = await fetch('/hsr_update_fiction', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            var result = await response.json();

            resultDiv.style.display = 'block';
            resultDiv.className = 'result ' + result.status;
            document.getElementById('hsrFictionResultTitle').textContent =
                result.status === 'success' ? '✓ 更新成功' : '✗ 更新失败';
            document.getElementById('hsrFictionResultMessage').textContent = result.message;

            var outputText = result.stdout || result.stderr || '';
            document.getElementById('hsrFictionResultOutput').textContent = outputText;
            document.getElementById('hsrFictionResultOutput').style.display = outputText ? 'block' : 'none';

        } catch (error) {
            resultDiv.style.display = 'block';
            resultDiv.className = 'result error';
            document.getElementById('hsrFictionResultTitle').textContent = '✗ 请求失败';
            document.getElementById('hsrFictionResultMessage').textContent = '网络错误，请重试';
            document.getElementById('hsrFictionResultOutput').textContent = error.toString();
            document.getElementById('hsrFictionResultOutput').style.display = 'block';
        } finally {
            submitBtn.disabled = false;
            btnText.textContent = '发送更新请求';
        }
    },

    // 发送HSR Chaos更新请求
    sendHSRChaosUpdate: async function() {
        var submitBtn = document.getElementById('hsrChaosSubmitBtn');
        var btnText = document.getElementById('hsrChaosBtnText');
        var resultDiv = document.getElementById('hsrChaosResult');

        var hpRatiosStr = document.getElementById('hsrChaosHpRatios').value.trim();
        var hpRatios = null;
        if (hpRatiosStr) {
            hpRatios = hpRatiosStr.split(',').map(function(s) {
                return parseFloat(s.trim());
            });
        }

        var data = {
            maze_id: document.getElementById('hsrChaosMazeId').value.trim(),
            version: document.getElementById('hsrChaosVersion').value.trim(),
            hp_ratios: hpRatios
        };

        submitBtn.disabled = true;
        btnText.innerHTML = '<span class="loading"></span>处理中...';
        resultDiv.style.display = 'none';

        try {
            var response = await fetch('/hsr_update_chaos', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            var result = await response.json();

            resultDiv.style.display = 'block';
            resultDiv.className = 'result ' + result.status;
            document.getElementById('hsrChaosResultTitle').textContent =
                result.status === 'success' ? '✓ 更新成功' : '✗ 更新失败';
            document.getElementById('hsrChaosResultMessage').textContent = result.message;

            var outputText = result.stdout || result.stderr || '';
            document.getElementById('hsrChaosResultOutput').textContent = outputText;
            document.getElementById('hsrChaosResultOutput').style.display = outputText ? 'block' : 'none';

        } catch (error) {
            resultDiv.style.display = 'block';
            resultDiv.className = 'result error';
            document.getElementById('hsrChaosResultTitle').textContent = '✗ 请求失败';
            document.getElementById('hsrChaosResultMessage').textContent = '网络错误，请重试';
            document.getElementById('hsrChaosResultOutput').textContent = error.toString();
            document.getElementById('hsrChaosResultOutput').style.display = 'block';
        } finally {
            submitBtn.disabled = false;
            btnText.textContent = '发送更新请求';
        }
    },

    // 发送GI角色更新请求
    sendGIUpdate: async function() {
        var submitBtn = document.getElementById('giSubmitBtn');
        var btnText = document.getElementById('giBtnText');
        var resultDiv = document.getElementById('giResult');

        var characterIdText = document.getElementById('giCharacterId').value.trim();
        var characterIds = characterIdText
            .split(/[\s,]+/)
            .map(function(id) { return id.trim(); })
            .filter(function(id) { return id; });

        var versionMapText = document.getElementById('giVersionMap').value.trim();
        var versionMap = {};
        if (versionMapText) {
            var pairs = versionMapText.split(',');
            for (var i = 0; i < pairs.length; i++) {
                var parts = pairs[i].split(':');
                if (parts.length === 2) {
                    versionMap[parts[0].trim()] = parts[1].trim();
                }
            }
        }

        var data = {
            character_ids: characterIds,
            version_map: versionMap
        };

        submitBtn.disabled = true;
        btnText.innerHTML = '<span class="loading"></span>处理中...';
        resultDiv.style.display = 'none';

        try {
            var response = await fetch('/gi_update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            var result = await response.json();

            resultDiv.style.display = 'block';
            resultDiv.className = 'result ' + result.status;
            document.getElementById('giResultTitle').textContent =
                result.status === 'success' ? '✓ 更新成功' : '✗ 更新失败';
            document.getElementById('giResultMessage').textContent = result.message;

            var outputText = result.stdout || result.stderr || '';
            document.getElementById('giResultOutput').textContent = outputText;
            document.getElementById('giResultOutput').style.display = outputText ? 'block' : 'none';

        } catch (error) {
            resultDiv.style.display = 'block';
            resultDiv.className = 'result error';
            document.getElementById('giResultTitle').textContent = '✗ 请求失败';
            document.getElementById('giResultMessage').textContent = '网络错误，请重试';
            document.getElementById('giResultOutput').textContent = error.toString();
            document.getElementById('giResultOutput').style.display = 'block';
        } finally {
            submitBtn.disabled = false;
            btnText.textContent = '发送更新请求';
        }
    },

    // 发送GI角色图片同步请求
    sendGIAvatarImgSync: async function() {
        var btn = document.getElementById('giAvatarImgSyncBtn');
        var btnText = document.getElementById('giAvatarImgBtnText');
        var resultDiv = document.getElementById('giAvatarImgResult');

        var idText = document.getElementById('giAvatarImgId').value.trim();
        var ids = idText
            ? idText.split(/[\s,]+/).map(function(id) { return id.trim(); }).filter(function(id) { return id; })
            : [];

        var data = { ids: ids };

        btn.disabled = true;
        btnText.innerHTML = '<span class="loading"></span>同步中...';
        resultDiv.style.display = 'none';

        try {
            var response = await fetch('/gi_sync_avatar_image', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            var result = await response.json();
            resultDiv.style.display = 'block';
            resultDiv.className = 'result ' + result.status;
            document.getElementById('giAvatarImgResultTitle').textContent =
                result.status === 'success' ? '✓ 同步完成' : '✗ 同步失败';
            document.getElementById('giAvatarImgResultMessage').textContent = result.message;
            var out = result.stdout || result.stderr || '';
            document.getElementById('giAvatarImgResultOutput').textContent = out;
            document.getElementById('giAvatarImgResultOutput').style.display = out ? 'block' : 'none';
        } catch (error) {
            resultDiv.style.display = 'block';
            resultDiv.className = 'result error';
            document.getElementById('giAvatarImgResultTitle').textContent = '✗ 请求失败';
            document.getElementById('giAvatarImgResultMessage').textContent = '网络错误，请重试';
            document.getElementById('giAvatarImgResultOutput').textContent = error.toString();
            document.getElementById('giAvatarImgResultOutput').style.display = 'block';
        } finally {
            btn.disabled = false;
            btnText.textContent = '同步角色图片';
        }
    },

    // 发送HSR角色图片同步请求
    sendHSRAvatarImgSync: async function() {
        var btn = document.getElementById('hsrAvatarImgSyncBtn');
        var btnText = document.getElementById('hsrAvatarImgBtnText');
        var resultDiv = document.getElementById('hsrAvatarImgResult');

        var idText = document.getElementById('hsrAvatarImgId').value.trim();
        var ids = idText
            ? idText.split(/[\s,]+/).map(function(id) { return id.trim(); }).filter(function(id) { return id; })
            : [];

        var data = { ids: ids };

        btn.disabled = true;
        btnText.innerHTML = '<span class="loading"></span>同步中...';
        resultDiv.style.display = 'none';

        try {
            var response = await fetch('/hsr_sync_avatar_image', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            var result = await response.json();
            resultDiv.style.display = 'block';
            resultDiv.className = 'result ' + result.status;
            document.getElementById('hsrAvatarImgResultTitle').textContent =
                result.status === 'success' ? '✓ 同步完成' : '✗ 同步失败';
            document.getElementById('hsrAvatarImgResultMessage').textContent = result.message;
            var out = result.stdout || result.stderr || '';
            document.getElementById('hsrAvatarImgResultOutput').textContent = out;
            document.getElementById('hsrAvatarImgResultOutput').style.display = out ? 'block' : 'none';
        } catch (error) {
            resultDiv.style.display = 'block';
            resultDiv.className = 'result error';
            document.getElementById('hsrAvatarImgResultTitle').textContent = '✗ 请求失败';
            document.getElementById('hsrAvatarImgResultMessage').textContent = '网络错误，请重试';
            document.getElementById('hsrAvatarImgResultOutput').textContent = error.toString();
            document.getElementById('hsrAvatarImgResultOutput').style.display = 'block';
        } finally {
            btn.disabled = false;
            btnText.textContent = '同步角色图片';
        }
    },

    // 发送HSR武器图片同步请求
    sendHSRWeaponImgSync: async function() {
        var btn = document.getElementById('hsrWeaponImgSyncBtn');
        var btnText = document.getElementById('hsrWeaponImgBtnText');
        var resultDiv = document.getElementById('hsrWeaponImgResult');

        var idText = document.getElementById('hsrWeaponImgId').value.trim();
        var ids = idText
            ? idText.split(/[\s,]+/).map(function(id) { return id.trim(); }).filter(function(id) { return id; })
            : [];

        var data = { ids: ids };

        btn.disabled = true;
        btnText.innerHTML = '<span class="loading"></span>同步中...';
        resultDiv.style.display = 'none';

        try {
            var response = await fetch('/hsr_sync_weapon_image', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            var result = await response.json();
            resultDiv.style.display = 'block';
            resultDiv.className = 'result ' + result.status;
            document.getElementById('hsrWeaponImgResultTitle').textContent =
                result.status === 'success' ? '✓ 同步完成' : '✗ 同步失败';
            document.getElementById('hsrWeaponImgResultMessage').textContent = result.message;
            var out = result.stdout || result.stderr || '';
            document.getElementById('hsrWeaponImgResultOutput').textContent = out;
            document.getElementById('hsrWeaponImgResultOutput').style.display = out ? 'block' : 'none';
        } catch (error) {
            resultDiv.style.display = 'block';
            resultDiv.className = 'result error';
            document.getElementById('hsrWeaponImgResultTitle').textContent = '✗ 请求失败';
            document.getElementById('hsrWeaponImgResultMessage').textContent = '网络错误，请重试';
            document.getElementById('hsrWeaponImgResultOutput').textContent = error.toString();
            document.getElementById('hsrWeaponImgResultOutput').style.display = 'block';
        } finally {
            btn.disabled = false;
            btnText.textContent = '同步光锥图片';
        }
    },

    // 发送HSR怪物图片同步请求
    sendHSRMonsterImgSync: async function() {
        var btn = document.getElementById('hsrMonsterImgSyncBtn');
        var btnText = document.getElementById('hsrMonsterImgBtnText');
        var resultDiv = document.getElementById('hsrMonsterImgResult');

        var idText = document.getElementById('hsrMonsterImgId').value.trim();
        var ids = idText
            ? idText.split(/[\s,]+/).map(function(id) { return id.trim(); }).filter(function(id) { return id; })
            : [];

        var data = { ids: ids };

        btn.disabled = true;
        btnText.innerHTML = '<span class="loading"></span>同步中...';
        resultDiv.style.display = 'none';

        try {
            var response = await fetch('/hsr_sync_monster_image', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            var result = await response.json();
            resultDiv.style.display = 'block';
            resultDiv.className = 'result ' + result.status;
            document.getElementById('hsrMonsterImgResultTitle').textContent =
                result.status === 'success' ? '✓ 同步完成' : '✗ 同步失败';
            document.getElementById('hsrMonsterImgResultMessage').textContent = result.message;
            var out = result.stdout || result.stderr || '';
            document.getElementById('hsrMonsterImgResultOutput').textContent = out;
            document.getElementById('hsrMonsterImgResultOutput').style.display = out ? 'block' : 'none';
        } catch (error) {
            resultDiv.style.display = 'block';
            resultDiv.className = 'result error';
            document.getElementById('hsrMonsterImgResultTitle').textContent = '✗ 请求失败';
            document.getElementById('hsrMonsterImgResultMessage').textContent = '网络错误，请重试';
            document.getElementById('hsrMonsterImgResultOutput').textContent = error.toString();
            document.getElementById('hsrMonsterImgResultOutput').style.display = 'block';
        } finally {
            btn.disabled = false;
            btnText.textContent = '同步怪物图片';
        }
    }

};

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    ToolsApp.init();
});