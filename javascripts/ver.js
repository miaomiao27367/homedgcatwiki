var __MANIFEST__ = (function() {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/manifest.json', false);
    xhr.send();
    return JSON.parse(xhr.responseText);
})();

var __GI_CONFIG__ = __MANIFEST__.gi;
var __SR_CONFIG__ = __MANIFEST__.sr;

VER_GI = __GI_CONFIG__.Current_Ver //GI
VER_SR = __SR_CONFIG__.Current_Ver //SR

GI_DATES = (function() {
    var d = {};
    var dates = __GI_CONFIG__.Dates;
    for (var k in dates) {
        d[k] = [k, Date.parse(dates[k])];
    }
    return d;
})();
//测试服倒计时
SR_DATES = (function() {
    var d = {};
    var dates = __SR_CONFIG__.Dates;
    for (var k in dates) {
        d[k] = [k, Date.parse(dates[k])];
    }
    return d;
})();

// 角色数据URL模板
var avatarIdUrls = [
    "/sr/data/CH/Avatar.js",
    "/sr/data/CH/Avatar/{id}.js",
];

// 武器数据URL模板
var weaponIdUrls = [
    "/sr/data/CH/Avatar.js",
    "/sr/data/CH/Weapon/{id}.js",
];

// 创建中间同步面板
var createSyncPanel = function() {
    var panel = $('<div class="sync-center-panel" style="display: none; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 10000; flex-direction: column; gap: 15px; padding: 24px; background-color: rgba(73, 56, 114, 0.98); border-radius: 16px; box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4); min-width: 340px; max-height: 80vh; overflow-y: auto;"></div>');
    
    // 标题
    var title = $('<h3 style="color: white; margin: 0 0 20px 0; text-align: center; font-size: 18px; font-weight: bold;">选择要同步的资源 默认为覆盖更新</h3>');
    
    // 关闭按钮
    var closeBtn = $('<button style="position: absolute; top: 10px; right: 10px; width: 30px; height: 30px; border-radius: 50%; background-color: rgba(255,255,255,0.2); border: none; color: white; font-size: 18px; cursor: pointer; line-height: 30px; text-align: center; padding: 0;" onmouseover="this.style.backgroundColor=rgba(255,255,255,0.3)" onmouseout="this.style.backgroundColor=rgba(255,255,255,0.2)">✕</button>').click(function() {
        panel.hide();
        overlay.hide();
    });
    
    // === Data资源部分 ===
    var dataSection = $('<div style="background-color: rgba(33,150,243,0.2); border-radius: 12px; padding: 15px;"></div>');
    var dataTitle = $('<div style="display: flex; align-items: center; gap: 10px; color: white; font-size: 15px; font-weight: bold; margin-bottom: 12px;"><span>📊</span><span>Data资源</span></div>');
    
    var dataItems = [
        { id: 'data-avatar', label: '角色数据', urls: [] },
        { id: 'data-weapon', label: '武器数据', urls: [] },
        { id: 'data-monster', label: '怪物数据', urls: ["/sr/data/CH/Monster.js"] },
        { id: 'data-chaos', label: '混沌回忆', urls: ["/sr/data/CH/Chaos_1.js","/sr/data/CH/Chaos_2.js","/sr/data/CH/Chaos_star.js"] },
        { id: 'data-fiction', label: '虚构叙事', urls: ["/sr/data/CH/Fiction_1.js","/sr/data/CH/Fiction_2.js","/sr/data/CH/Fiction_star.js"] },
        { id: 'data-apocalypse', label: '末日幻影', urls: ["/sr/data/CH/AS.js","/sr/data/CH/AS_star.js"] },
        { id: 'data-vision', label: '异象仲裁', urls: ["/sr/data/CH/AR.js"] }
    ];

    var dataCheckboxGroup = $('<div style="display: flex; flex-wrap: wrap; gap: 10px;"></div>');
    
    // 角色ID输入框（初始隐藏）
    var avatarIdInput = $('<input type="text" id="avatar-id-input" placeholder="请输入角色ID（多个用逗号分隔）" style="width: 100%; padding: 8px; margin-top: 10px; border: 1px solid rgba(255,255,255,0.3); border-radius: 6px; background-color: rgba(255,255,255,0.1); color: white; font-size: 13px; box-sizing: border-box; display: none;" />');
    
    // 武器ID输入框（初始隐藏）
    var weaponIdInput = $('<input type="text" id="weapon-id-input" placeholder="请输入武器ID（多个用逗号分隔）" style="width: 100%; padding: 8px; margin-top: 10px; border: 1px solid rgba(255,255,255,0.3); border-radius: 6px; background-color: rgba(255,255,255,0.1); color: white; font-size: 13px; box-sizing: border-box; display: none;" />');
    
    dataItems.forEach(function(item) {
        var checkbox = $('<label style="display: flex; align-items: center; gap: 6px; padding: 8px 12px; background-color: rgba(255,255,255,0.1); border-radius: 8px; cursor: pointer;" onmouseover="this.style.backgroundColor=rgba(255,255,255,0.15)" onmouseout="this.style.backgroundColor=rgba(255,255,255,0.1)">' +
            '<input type="checkbox" id="' + item.id + '" style="width: 16px; height: 16px; margin: 0; vertical-align: middle;">' +
            '<span style="color: white; font-size: 14px; line-height: 1;">' + item.label + '</span>' +
        '</label>');

        if (item.id === 'data-avatar') {
            checkbox.find('input').change(function() {
                if ($(this).is(':checked')) {
                    avatarIdInput.show();
                } else {
                    avatarIdInput.hide();
                }
            });
        }
        
        if (item.id === 'data-weapon') {
            checkbox.find('input').change(function() {
                if ($(this).is(':checked')) {
                    weaponIdInput.show();
                } else {
                    weaponIdInput.hide();
                }
            });
        }
        
        dataCheckboxGroup.append(checkbox);
    });
    dataSection.append(dataTitle, dataCheckboxGroup, avatarIdInput, weaponIdInput);

    var jsSection = $('<div style="background-color: rgba(76,175,80,0.2); border-radius: 12px; padding: 15px;"></div>');
    var jsTitle = $('<div style="display: flex; align-items: center; gap: 10px; color: white; font-size: 15px; font-weight: bold; margin-bottom: 12px;"><span>⚙️</span><span>渲染JS</span></div>');
    
    var jsItems = [
        { id: 'js-avatar', label: '角色渲染', urls: ["/javascripts/char.js","/stylesheets/char.css"] },
        { id: 'js-monster', label: '怪物渲染', urls: ["/javascripts/mons.js","/stylesheets/mons.css"] },
        { id: 'js-chaos', label: '混沌回忆渲染', urls: ["/javascripts/chaos.js","/stylesheets/chaos.css"] },
        { id: 'js-fiction', label: '虚构叙事渲染', urls: ["/javascripts/fiction.js","/stylesheets/fiction.css"] },
        { id: 'js-apocalypse', label: '末日幻影渲染', urls: ["/javascripts/as.js","/stylesheets/as.css"] },
        { id: 'js-vision', label: '异象仲裁渲染', urls: ["/javascripts/arbitration.js","/stylesheets/arbitration.css"] },
        { id: 'js-tools', label: 'tools组件', urls: ["/javascripts/tools.js","/stylesheets/tools.css","/tools/index.html"] },
        { id: 'js-ver', label: 'ver本体渲染', urls: ["/javascripts/ver.js"]}
    ];
    
    var jsCheckboxGroup = $('<div style="display: flex; flex-wrap: wrap; gap: 10px;"></div>');
    jsItems.forEach(function(item) {
        var checkbox = $('<label style="display: flex; align-items: center; gap: 6px; padding: 8px 12px; background-color: rgba(255,255,255,0.1); border-radius: 8px; cursor: pointer;" onmouseover="this.style.backgroundColor=rgba(255,255,255,0.15)" onmouseout="this.style.backgroundColor=rgba(255,255,255,0.1)">' +
            '<input type="checkbox" id="' + item.id + '" style="width: 16px; height: 16px;">' +
            '<span style="color: white; font-size: 14px;">' + item.label + '</span>' +
        '</label>');
        jsCheckboxGroup.append(checkbox);
    });
    jsSection.append(jsTitle, jsCheckboxGroup);

    var syncConfig = { dataItems: dataItems, jsItems: jsItems };

    var customSection = $('<div style="background-color: rgba(255,152,0,0.2); border-radius: 12px; padding: 15px;"></div>');
    var customTitle = $('<div style="display: flex; align-items: center; gap: 10px; color: white; font-size: 15px; font-weight: bold; margin-bottom: 12px;"><span>🎨</span><span>自定义资源</span></div>');
    var customInput = $('<input type="text" id="custom-url" placeholder="请输入资源请求地址（支持多个，用逗号分隔）" style="width: 100%; padding: 10px; border: 1px solid rgba(255,255,255,0.3); border-radius: 8px; background-color: rgba(255,255,255,0.1); color: white; font-size: 14px; box-sizing: border-box;" />');
    customSection.append(customTitle, customInput);

    var startSyncBtn = $('<button style="padding: 14px; background-color: #673AB7; border: none; border-radius: 10px; color: white; font-size: 16px; font-weight: bold; cursor: pointer; transition: all 0.2s ease; display: flex; align-items: center; justify-content: center; line-height: 1;" onmouseover="this.style.transform=scale(1.02);this.style.boxShadow=0 4px 12px rgba(103,58,183,0.4)" onmouseout="this.style.transform=scale(1);this.style.boxShadow=none">开始同步</button>').click(function() {
        var selectedUrls = [];

        dataItems.forEach(function(item) {
            if ($('#' + item.id).is(':checked')) {
                if (item.id === 'data-avatar') {
                    var avatarIds = $('#avatar-id-input').val().trim();
                    if (!avatarIds) {
                        alert('请输入角色ID！');
                        return;
                    }
                    var ids = avatarIds.split(',').map(function(id) { return id.trim(); }).filter(function(id) { return id; });
                    ids.forEach(function(id) {
                        avatarIdUrls.forEach(function(template) {
                            var url = template.replace('{id}', id);
                            selectedUrls.push(url);
                        });
                    });
                } else if (item.id === 'data-weapon') {
                    var weaponIds = $('#weapon-id-input').val().trim();
                    if (!weaponIds) {
                        alert('请输入武器ID！');
                        return;
                    }
                    var weaponIdsArray = weaponIds.split(',').map(function(id) { return id.trim(); }).filter(function(id) { return id; });
                    weaponIdsArray.forEach(function(id) {
                        weaponIdUrls.forEach(function(template) {
                            var url = template.replace('{id}', id);
                            selectedUrls.push(url);
                        });
                    });
                } else if (item.urls && item.urls.length > 0) {
                    selectedUrls = selectedUrls.concat(item.urls);
                }
            }
        });

        jsItems.forEach(function(item) {
            if ($('#' + item.id).is(':checked') && item.urls && item.urls.length > 0) {
                selectedUrls = selectedUrls.concat(item.urls);
            }
        });

        var customUrls = $('#custom-url').val().trim();
        if (customUrls) {
            var customUrlArray = customUrls.split(',').map(function(url) { return url.trim(); }).filter(function(url) { return url; });
            selectedUrls = selectedUrls.concat(customUrlArray);
        }
        
        if (selectedUrls.length === 0) {
            alert('请至少选择一项要同步的资源或输入自定义地址！');
            return;
        }

        syncSelectedResources(selectedUrls);
        panel.hide();
        overlay.hide();
    });
    
    // 添加元素到面板
    panel.append(closeBtn, title, dataSection, jsSection, customSection, startSyncBtn);
    
    // 创建遮罩层
    var overlay = $('<div class="sync-overlay" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5); z-index: 9999;"></div>').click(function() {
        panel.hide();
        overlay.hide();
    });
    
    $('body').append(overlay, panel);
    
    // 返回显示函数
    return function showPanel() {
        overlay.show();
        panel.show();
    };
};

// 批量同步选中的资源
var syncSelectedResources = function(urls) {
    var totalUrls = urls.length;
    var successCount = 0;
    var failedCount = 0;
    
    // 向每个url发送PUT update请求
    urls.forEach(function(url) {
        $.ajax({
            url: url,
            type: 'PUT',
            dataType: 'json',
            success: function(response) {
                successCount++;
                console.log('同步成功:', url);
                checkComplete();
            },
            error: function(xhr, status, error) {
                failedCount++;
                console.log('同步失败:', url, error);
                checkComplete();
            }
        });
    });
    
    // 检查是否全部完成
    var checkComplete = function() {
        if (successCount + failedCount === totalUrls) {
            localStorage.setItem('lastBatchSync', new Date().toISOString());
            localStorage.setItem('lastSyncResult', JSON.stringify({ success: successCount, failed: failedCount }));
            
            // 显示同步结果
            var msg = '同步完成！\n\n成功: ' + successCount + ' 个\n失败: ' + failedCount + ' 个';
            if (failedCount > 0) {
                msg += '\n\n部分请求失败，请检查控制台获取详情。';
            }
            alert(msg);
        }
    };
};

// 创建侧边栏
var createSidebar = function(showSyncPanel) {
    // 创建侧边栏容器
    var sidebar = $('<div class="sync-sidebar" style="position: fixed; right: -300px; top: 50%; transform: translateY(-50%); width: 260px; background-color: rgba(39, 54, 62, 0.98); border-radius: 12px 0 0 12px; box-shadow: -4px 0 20px rgba(0, 0, 0, 0.3); z-index: 9998; padding: 20px; transition: right 0.3s ease; display: flex; flex-direction: column; gap: 15px;"></div>');
    
    // 创建遮罩层
    var sidebarOverlay = $('<div class="sync-sidebar-overlay" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.3); z-index: 9997;"></div>').click(function() {
        sidebar.css('right', '-300px');
        sidebarOverlay.hide();
        isOpen = false;
    });
    
    // 侧边栏标题
    var sidebarTitle = $('<h4 style="color: white; margin: 0; font-size: 16px; font-weight: bold; padding-bottom: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">功能菜单</h4>');
    
    // 创建侧边栏按钮
    var createSidebarButton = function(icon, label, onClick) {
        return $('<button style="display: flex; align-items: center; gap: 12px; width: 100%; padding: 12px 15px; background-color: rgba(255,255,255,0.1); border: none; border-radius: 8px; color: white; font-size: 14px; cursor: pointer; transition: all 0.2s ease;" onmouseover="this.style.backgroundColor=rgba(255,255,255,0.15)" onmouseout="this.style.backgroundColor=rgba(255,255,255,0.1)">' +
            '<span style="font-size: 18px;">' + icon + '</span>' +
            '<span>' + label + '</span>' +
        '</button>').click(onClick);
    };
    
    // 刷新按钮
    var refreshBtn = createSidebarButton('↻', '刷新页面', function() {
        localStorage.clear();
        location.reload(true);
    });
    
    // 同步资源按钮
    var syncBtn = createSidebarButton('🔄', '同步资源', function() {
        showSyncPanel();
        sidebar.css('right', '-300px');
        sidebarOverlay.hide();
        isOpen = false;
    });
    
    // 工具按钮
    var toolsBtn = createSidebarButton('🛠️', '工具', function() {
        window.location.href = '/tools';
        sidebar.css('right', '-300px');
        sidebarOverlay.hide();
        isOpen = false;
    });
    
    // Spine Demo 按钮
    var spineDemoBtn = createSidebarButton('🦴', 'Spine Demo', function() {
        window.location.href = '/spine/demo.html';
        sidebar.css('right', '-300px');
        sidebarOverlay.hide();
        isOpen = false;
    });
    
    // 添加元素到侧边栏
    sidebar.append(sidebarTitle, refreshBtn, syncBtn, toolsBtn, spineDemoBtn);
    
    // 添加到页面
    $('body').append(sidebarOverlay, sidebar);
    
    // 返回侧边栏展开/收起函数
    var isOpen = false;
    return function toggleSidebar() {
        isOpen = !isOpen;
        if (isOpen) {
            sidebar.css('right', '0');
            sidebarOverlay.show();
        } else {
            sidebar.css('right', '-300px');
            sidebarOverlay.hide();
        }
    };
};

// 创建功能栏
var create_toolbar = function() {
    // 先创建同步面板，获取显示函数
    var showSyncPanel = createSyncPanel();
    
    // 创建侧边栏，获取切换函数
    var toggleSidebar = createSidebar(showSyncPanel);
    
    // 创建功能栏容器（只保留切换侧边栏的按钮）
    var toolbar = $('<div class="sync-toolbar" style="position: fixed; bottom: 20px; right: 20px; z-index: 9998; display: flex; flex-direction: column; gap: 10px;"></div>');
    
    // 创建圆形按钮
    var createCircleButton = function(icon, color, tooltip, onClick) {
        return $('<div style="position: relative; width: 50px; height: 50px; border-radius: 50%; background-color: ' + color + '; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3); color: white; font-size: 22px; cursor: pointer; transition: all 0.2s ease;" onmouseover="this.style.transform=scale(1.1);this.style.boxShadow=0 4px 12px rgba(0,0,0,0.4)" onmouseout="this.style.transform=scale(1);this.style.boxShadow=0 2px 8px rgba(0,0,0,0.3)" title="' + tooltip + '">' + icon + '</div>').click(onClick);
    };
    
    // 菜单按钮（点击展开侧边栏）
    var menuBtn = createCircleButton('☰', '#27363E', '展开菜单', toggleSidebar);
    
    // 添加按钮到工具栏
    toolbar.append(menuBtn);
    
    // 添加到页面
    $('body').append(toolbar);
};

// 单个资源同步功能（保留用于其他地方调用）
var syncSingleResource = function(url) {
    $.ajax({
        url: url,
        type: 'PUT',
        dataType: 'json',
        success: function(response) {
            console.log('同步成功:', url);
        },
        error: function(xhr, status, error) {
            console.log('同步失败:', url, error);
        }
    });
};

// 页面加载完成后创建功能栏
$(function() {
    create_toolbar();
});