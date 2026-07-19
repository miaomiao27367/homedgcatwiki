const fs = require('fs');
const path = require('path');

// 获取脚本所在目录的上级目录（项目根目录）
const projectRoot = path.join(__dirname, '..');

// 读取 Avatar.js 文件（从项目根目录开始）
const avatarPath = path.join(projectRoot, 'data', 'CH', 'Avatar.js');
const content = fs.readFileSync(avatarPath, 'utf-8');

// 找到 _avatar 数组的开始和结束位置
const startMarker = 'var _avatar = [';
const startIndex = content.indexOf(startMarker);

if (startIndex === -1) {
    console.error('无法找到 _avatar 数组开始位置');
    process.exit(1);
}

// 找到数组结束的 ] （计算括号匹配）
let depth = 1;
let pos = startIndex + startMarker.length;
while (pos < content.length && depth > 0) {
    if (content[pos] === '[') depth++;
    if (content[pos] === ']') depth--;
    pos++;
}

const endIndex = pos - 1;

// 提取数组内容（从 [ 开始到 ] 结束）
let avatarJson = content.substring(startIndex + startMarker.length - 1, endIndex + 1);

// 移除尾随逗号（JSON 不支持尾随逗号，但 JavaScript 支持）
avatarJson = avatarJson.replace(/,\s*]/g, ']').replace(/,\s*}/g, '}');

// 解析 JSON
const avatarArray = JSON.parse(avatarJson);
console.log(`找到 ${avatarArray.length} 个角色`);

// 生成完整的索引表（使用负数偏移量）
let searchAvatar = 'var _search_avatar = {\n';

avatarArray.forEach((avatar, index) => {
    const offset = index - avatarArray.length + 1; // 负数偏移量
    const id = avatar._id;
    const name = avatar.Name;

    // 添加 ID 索引
    searchAvatar += `    "${id}": ${offset},\n`;
    // 添加中文名索引
    if (name && name.trim()) {
        searchAvatar += `    "${name}": ${offset},\n`;
    }
});

searchAvatar += '}';

// 写入文件（输出到项目根目录）
const outputPath = path.join(projectRoot, 'search_avatar_generated.js');
fs.writeFileSync(outputPath, searchAvatar, 'utf-8');
console.log(`索引表已生成到 ${outputPath}`);
