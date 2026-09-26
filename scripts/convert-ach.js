#!/usr/bin/env node

/**
 * convert-ach.js — 将旧 JS 数据格式转为 JSON
 *
 * 输入：legacy/ach/data/CH.js（旧 JS 变量 _AchievementData / _AchievementGroup / _Achievement）
 * 输出：
 *   ach/ach.json              # 主数据（全局统计、版本列表、分组列表）
 *   ach/groups/{groupId}.json # 每个分组明细
 *
 * 幂等：重复执行结果一致（基于 JSON 稳定排序）
 */

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.resolve(__dirname, '..');
const LEGACY_DATA = path.join(ROOT, 'legacy', 'ach', 'data', 'CH.js');
const OUT_JSON = path.join(ROOT, 'ach', 'ach.json');
const OUT_GROUPS = path.join(ROOT, 'ach', 'groups');

// ─── 1. 读取并执行旧 JS ──────────────────────────────────────────────────────

function loadLegacyData(filePath) {
    const code = fs.readFileSync(filePath, 'utf-8');
    const sandbox = {
        _AchievementData: null,
        _AchievementGroup: null,
        _Achievement: null,
        console
    };
    const script = new vm.Script(code, { filename: filePath });
    const context = vm.createContext(sandbox);
    script.runInContext(context);
    return {
        achievementData: sandbox._AchievementData,
        achievementGroup: sandbox._AchievementGroup,
        achievement: sandbox._Achievement
    };
}

// ─── 2. 语义版本排序（降序） ──────────────────────────────────────────────────

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

// ─── 3. 主逻辑 ───────────────────────────────────────────────────────────────

function main() {
    console.log('[convert-ach] 读取旧数据...');
    const { achievementData, achievementGroup, achievement } = loadLegacyData(LEGACY_DATA);

    if (!achievement || !achievementGroup) {
        console.error('[convert-ach] 错误：无法解析旧数据文件');
        process.exit(1);
    }

    console.log(`[convert-ach] 成就总数: ${achievement.length}`);
    console.log(`[convert-ach] 分组总数: ${achievementGroup.length}`);

    // ── 3a. 构建分组名称映射 ──
    const groupNameMap = new Map();
    for (const g of achievementGroup) {
        groupNameMap.set(g._id, g.Name);
    }

    // ── 3b. 按 Group 分组明细 ──
    const groupsMap = new Map(); // groupId -> achievements[]
    for (const ach of achievement) {
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

    // ── 3c. 计算统计数据 ──
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

        // 按 id 稳定排序
        items.sort((a, b) => a.id - b.id);

        groups.push({
            id: gid,
            name: groupNameMap.get(gid) || `Group ${gid}`,
            num,
            reward
        });
    }

    // 分组列表按 id 排序
    groups.sort((a, b) => a.id - b.id);

    // 版本列表：语义版本降序
    const versions = semverSortDesc(Array.from(versionSet).filter(Boolean));

    // ── 3d. 写 ach.json ──
    const meta = {
        updatedAt: new Date().toISOString().split('T')[0],
        totalNum,
        totalPrimo,
        versions,
        groups
    };

    fs.mkdirSync(OUT_GROUPS, { recursive: true });
    fs.writeFileSync(OUT_JSON, JSON.stringify(meta, null, 2) + '\n', 'utf-8');
    console.log(`[convert-ach] 写入: ${path.relative(ROOT, OUT_JSON)}`);

    // ── 3e. 写 groups/*.json ──
    for (const [gid, items] of groupsMap) {
        // 按 id 排序
        items.sort((a, b) => a.id - b.id);
        const outPath = path.join(OUT_GROUPS, `${gid}.json`);
        fs.writeFileSync(outPath, JSON.stringify(items, null, 2) + '\n', 'utf-8');
    }

    console.log(`[convert-ach] 分组文件数: ${groupsMap.size}`);

    // ── 3f. 对账 ──
    console.log('\n[convert-ach] === 对账结果 ===');
    console.log(`  totalNum:   ${totalNum}  (旧数据: ${achievementData?.[0]?.Data?.TotalNum ?? 'N/A'})`);
    console.log(`  totalPrimo: ${totalPrimo} (旧数据: ${achievementData?.[0]?.Data?.TotalPrimo ?? 'N/A'})`);

    let mismatch = false;
    for (const g of achievementGroup) {
        const items = groupsMap.get(g._id);
        if (!items) {
            console.warn(`  [警告] 分组 ${g._id} (${g.Name}) 在明细中不存在`);
            mismatch = true;
            continue;
        }
        const actualNum = items.length;
        const actualReward = items.reduce((s, a) => s + a.reward, 0);
        if (actualNum !== g.Num || actualReward !== g.Reward) {
            console.warn(`  [对账失败] 分组 ${g._id} (${g.Name}): 期望 num=${g.Num} reward=${g.Reward}, 实际 num=${actualNum} reward=${actualReward}`);
            mismatch = true;
        }
    }

    if (!mismatch) {
        console.log('  ✓ 所有分组对账通过');
    }

    console.log('[convert-ach] 完成');
}

main();