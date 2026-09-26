#!/usr/bin/env node

/**
 * update-ach.js — 上游全量成就数据更新脚本
 *
 * 用法：node scripts/update-ach.js <上游数据文件路径>
 *
 * 上游数据文件格式：与旧 _Achievement 数组格式一致的 JS 文件
 * （或通过 stdin 传入 JSON 数组）
 *
 * 逻辑：
 *   1. 读取上游全量成就数组
 *   2. 按 Group 分组
 *   3. 与 ach/groups/{id}.json 比较，变了才写
 *   4. 重算并写 ach/ach.json
 *
 * 输出：控制台打印新增/修改/删除条数
 *
 * 验收标准：连续跑两次，第二次输出 0 变更
 */

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.resolve(__dirname, '..');
const ACH_JSON = path.join(ROOT, 'ach', 'ach.json');
const GROUPS_DIR = path.join(ROOT, 'ach', 'groups');

// ─── 工具函数 ────────────────────────────────────────────────────────────────

function semverSortDesc(versions) {
    return versions.sort((a, b) => {
        const pa = a.split('.').map(Number);
        const pb = b.split('.').map(Number);
        for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
            const na = pa[i] || 0;
            const nb = pb[i] || 0;
            if (na !== nb) return nb - na;
        }
        return 0;
    });
}

function loadExistingGroup(gid) {
    const p = path.join(GROUPS_DIR, `${gid}.json`);
    if (fs.existsSync(p)) {
        return JSON.parse(fs.readFileSync(p, 'utf-8'));
    }
    return null;
}

function loadExistingMeta() {
    if (fs.existsSync(ACH_JSON)) {
        return JSON.parse(fs.readFileSync(ACH_JSON, 'utf-8'));
    }
    return null;
}

function loadUpstreamFromFile(filePath) {
    const code = fs.readFileSync(filePath, 'utf-8').trim();
    // 尝试 JSON parse 先
    if (code.startsWith('[') || code.startsWith('{')) {
        try { return JSON.parse(code); } catch (e) { /* fallthrough */ }
    }
    // 否则作为 JS 执行，提取变量
    const sandbox = {
        _Achievement: null,
        _AchievementGroup: null,
        _AchievementData: null,
        console
    };
    const script = new vm.Script(code, { filename: filePath });
    const context = vm.createContext(sandbox);
    script.runInContext(context);

    // 优先返回 _Achievement 数组
    if (Array.isArray(sandbox._Achievement)) {
        return sandbox._Achievement;
    }
    // 返回 sandbox 本身（让调用方决定）
    return sandbox;
}

function deepEqual(a, b) {
    return JSON.stringify(a) === JSON.stringify(b);
}

// ─── 主逻辑 ──────────────────────────────────────────────────────────────────

function main() {
    const upstreamFile = process.argv[2];

    if (!upstreamFile) {
        console.error('用法: node scripts/update-ach.js <上游数据文件路径>');
        console.error('上游文件可以是:');
        console.error('  - 旧格式 JS: legacy/ach/data/CH.js (需含 _Achievement 变量)');
        console.error('  - JSON 文件: 符合 _Achievement 格式的 JSON 数组');
        process.exit(1);
    }

    const upstreamPath = path.resolve(ROOT, upstreamFile);
    console.log(`[update-ach] 读取上游数据: ${upstreamPath}`);

    let rawData;
    try {
        rawData = loadUpstreamFromFile(upstreamPath);
    } catch (e) {
        console.error(`[update-ach] 读取失败: ${e.message}`);
        process.exit(1);
    }

    // 兼容旧格式: 如果是 {_Achievement: [...]} 或包含 _Achievement 对象
    let achievements;
    if (Array.isArray(rawData)) {
        achievements = rawData;
    } else if (rawData._Achievement && Array.isArray(rawData._Achievement)) {
        achievements = rawData._Achievement;
    } else {
        // 尝试找第一个数组属性
        const arrKey = Object.keys(rawData).find(k => Array.isArray(rawData[k]));
        if (arrKey) {
            achievements = rawData[arrKey];
            console.log(`[update-ach] 从对象属性 "${arrKey}" 读取数组`);
        } else {
            console.error('[update-ach] 无法识别的数据格式，需要成就数组');
            process.exit(1);
        }
    }

    console.log(`[update-ach] 上游成就数: ${achievements.length}`);

    // ── 按 Group 分组 ──
    const groupsMap = new Map();
    for (const ach of achievements) {
        const gid = ach.Group;
        if (!groupsMap.has(gid)) {
            groupsMap.set(gid, []);
        }
        groupsMap.get(gid).push({
            id: ach._id,
            name: ach.Name,
            desc: ach.Desc,
            ver: ach.Ver || '',
            hidden: !!ach.Hidden,
            reward: ach.Reward,
            total: ach.Total
        });
    }

    // ── 与现有文件比较 ──
    let added = 0;
    let modified = 0;
    let deleted = 0;

    fs.mkdirSync(GROUPS_DIR, { recursive: true });

    for (const [gid, items] of groupsMap) {
        // 稳定排序
        items.sort((a, b) => a.id - b.id);

        const existing = loadExistingGroup(gid);
        const newStr = JSON.stringify(items);

        if (!existing) {
            // 新增分组
            fs.writeFileSync(path.join(GROUPS_DIR, `${gid}.json`), newStr + '\n', 'utf-8');
            added++;
            console.log(`  [+] 新增分组 ${gid} (${items.length} 条)`);
        } else if (!deepEqual(existing, items)) {
            // 分组已变更
            fs.writeFileSync(path.join(GROUPS_DIR, `${gid}.json`), newStr + '\n', 'utf-8');
            modified++;
            const oldCnt = existing.length;
            const diff = items.length - oldCnt;
            console.log(`  [~] 分组 ${gid}: ${oldCnt} → ${items.length} 条${diff > 0 ? ' (+' + diff + ')' : diff < 0 ? ' (' + diff + ')' : ''}`);
        }
    }

    // 检查已删除的分组
    const existingFiles = fs.readdirSync(GROUPS_DIR).filter(f => f.endsWith('.json'));
    for (const f of existingFiles) {
        const gid = parseInt(f.replace('.json', ''), 10);
        if (!groupsMap.has(gid)) {
            fs.unlinkSync(path.join(GROUPS_DIR, f));
            deleted++;
            console.log(`  [-] 删除分组 ${gid}`);
        }
    }

    // ── 重新计算并写 ach.json ──
    let totalNum = 0;
    let totalPrimo = 0;
    const versionSet = new Set();
    const groups = [];

    for (const [gid, items] of groupsMap) {
        const num = items.length;
        const reward = items.reduce((s, a) => s + a.reward, 0);
        totalNum += num;
        totalPrimo += reward;
        for (const a of items) {
            if (a.ver) versionSet.add(a.ver);
        }
        groups.push({ id: gid, name: items[0]?.name || `Group ${gid}`, num, reward });
    }

    // 从旧 meta 恢复分组名称（因为上游可能不含分组名）
    const existingMeta = loadExistingMeta();
    if (existingMeta && existingMeta.groups) {
        const nameMap = new Map(existingMeta.groups.map(g => [g.id, g.name]));
        for (const g of groups) {
            if (nameMap.has(g.id)) {
                g.name = nameMap.get(g.id);
            }
        }
    }

    groups.sort((a, b) => a.id - b.id);
    const versions = semverSortDesc(Array.from(versionSet).filter(Boolean));

    const meta = {
        updatedAt: new Date().toISOString().split('T')[0],
        totalNum,
        totalPrimo,
        versions,
        groups
    };

    fs.writeFileSync(ACH_JSON, JSON.stringify(meta, null, 2) + '\n', 'utf-8');

    // ── 汇总 ──
    console.log('\n[update-ach] === 更新汇总 ===');
    console.log(`  新增分组: ${added}`);
    console.log(`  修改分组: ${modified}`);
    console.log(`  删除分组: ${deleted}`);
    console.log(`  总成就数: ${totalNum}`);
    console.log(`  总原石数: ${totalPrimo}`);
    console.log(`  版本数:   ${versions.length}`);
    console.log('[update-ach] 完成');
}

main();