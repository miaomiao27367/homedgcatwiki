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

// 创建侧边栏
var createSidebar = function() {
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
    sidebar.append(sidebarTitle, refreshBtn, toolsBtn, spineDemoBtn);
    
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
    // 创建侧边栏，获取切换函数
    var toggleSidebar = createSidebar();
    
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

// 页面加载完成后创建功能栏
$(function() {
    create_toolbar();
});