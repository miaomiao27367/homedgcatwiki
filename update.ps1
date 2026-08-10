<#
.SYNOPSIS
    Wiki 更新脚本 - 从 GitHub 公开仓库下载指定文件
.DESCRIPTION
    根据 filelist.json 清单从 GitHub 下载文件更新本地
    仅当远程版本号大于本地版本号时才执行更新
    无需安装 Git，双击 update.bat 即可运行
#>

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$LIST_FILE   = "filelist.json"
$RAW_BASE    = "https://raw.githubusercontent.com/miaomiao27367/homedgcatwiki/main"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Wiki 更新程序" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ============================================
# 1. 下载远程 filelist.json 并比对版本
# ============================================
Write-Host "[1/3] 检查版本..." -ForegroundColor White

$listUrl = "$RAW_BASE/$LIST_FILE"
try {
    $wc = New-Object System.Net.WebClient
    $wc.Encoding = [System.Text.Encoding]::UTF8
    $remoteListText = $wc.DownloadString($listUrl)
    $remoteList = $remoteListText | ConvertFrom-Json
} catch {
    Write-Host "[错误] 无法获取 filelist.json: $_" -ForegroundColor Red
    Write-Host "  请检查网络连接" -ForegroundColor Yellow
    pause
    exit 1
}

$remoteVersion = $remoteList.version
if (-not $remoteVersion) {
    Write-Host "[错误] filelist.json 缺少 version 字段" -ForegroundColor Red
    pause
    exit 1
}

# 读取本地版本
$localVersion = 0
if (Test-Path $LIST_FILE) {
    try {
        $localList = Get-Content $LIST_FILE -Raw -Encoding UTF8 | ConvertFrom-Json
        $localVersion = $localList.version
        if (-not $localVersion) { $localVersion = 0 }
    } catch {
        $localVersion = 0
    }
}

Write-Host "  远程版本: v$remoteVersion  |  本地版本: v$localVersion" -ForegroundColor Gray

if ($localVersion -ge $remoteVersion) {
    Write-Host ""
    Write-Host "[已是最新] 无需更新 (v$localVersion)" -ForegroundColor Green
    Write-Host ""
    pause
    exit 0
}

Write-Host "  发现新版本: v$localVersion -> v$remoteVersion" -ForegroundColor Yellow
Write-Host ""

# ============================================
# 2. 下载文件
# ============================================
$files = $remoteList.files
if (-not $files -or $files.Count -eq 0) {
    Write-Host "[错误] filelist.json 中无文件" -ForegroundColor Red
    pause
    exit 1
}

$updated = 0
$skipped = 0
$failed  = 0
$total   = $files.Count

Write-Host "[2/3] 下载文件 ($($total) 个)..." -ForegroundColor White

for ($i = 0; $i -lt $total; $i++) {
    $f = $files[$i]
    $remoteUrl = "$RAW_BASE/$f"
    $localPath = Join-Path $scriptDir $f
    $localDir  = Split-Path $localPath -Parent

    $progress = "[$($i + 1)/$total]"
    Write-Host "  $progress $f" -NoNewline

    try {
        $wc = New-Object System.Net.WebClient
        $wc.Encoding = [System.Text.Encoding]::UTF8
        $remoteBytes = $wc.DownloadData($remoteUrl)

        if (-not (Test-Path $localDir)) {
            New-Item -ItemType Directory -Force -Path $localDir | Out-Null
        }
        [System.IO.File]::WriteAllBytes($localPath, $remoteBytes)
        Write-Host " - 已更新" -ForegroundColor Green
        $updated++
    } catch {
        Write-Host " - 失败: $_" -ForegroundColor Red
        $failed++
    }
}

# ============================================
# 3. 保存新版本 filelist.json
# ============================================
Write-Host ""
Write-Host "[3/3] 保存版本记录..." -ForegroundColor White
try {
    [System.IO.File]::WriteAllBytes(
        (Join-Path $scriptDir $LIST_FILE),
        [System.Text.Encoding]::UTF8.GetBytes($remoteListText)
    )
    Write-Host "  已更新本地 filelist.json (v$remoteVersion)" -ForegroundColor Green
} catch {
    Write-Host "  保存失败: $_" -ForegroundColor Yellow
}

# ============================================
# 4. 结果
# ============================================
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  更新完成!  v$localVersion -> v$remoteVersion" -ForegroundColor Cyan
Write-Host "  成功: $updated  |  失败: $failed" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
pause
