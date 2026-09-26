# reliance/

## 目录结构
- gi/           原神相关更新脚本
- hsr/          星穹铁道相关更新脚本
- shared/       跨游戏共享工具（paths.py 等）
- gi/ach/、hsr/ach/   成就更新脚本（占位）

## 脚本依赖关系
- hsr/endgame/* 依赖 hsr/endgame/sync_elite.py
- gi/monster_v2/build.py 和 update.py 依赖 gi/monster_v2/utils.py
- 其余脚本互相独立，只被 server.py 调用

## 调用入口
server.py 顶部 import，POST 路由见 server.py 的 do_POST。
每个脚本同时支持 `python -m reliance.<path>` 直接调用。

## 路径推导
优先用 reliance/shared/paths.py 的常量，不要用 cwd 相对路径。
用 __file__ 推导时注意层数。