param([switch]$StagedOnly)

# Obsidian Git 保持调用这个 PowerShell 入口；完整 diff、递归摘要和快照校验
# 由同目录的 Python 引擎完成。stdout 必须只包含最终 commit 标题。

$ErrorActionPreference = 'SilentlyContinue'
$utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $utf8
$OutputEncoding = $utf8
$env:PYTHONUTF8 = '1'
$fallback = '更新笔记与资料'

# 本脚本位于 .obsidian/plugins/obsidian-git/，上三级是 vault 根。
$vaultRoot = $PSScriptRoot | Split-Path -Parent | Split-Path -Parent | Split-Path -Parent
if (-not $vaultRoot -or -not (Test-Path -LiteralPath $vaultRoot)) {
    Write-Output $fallback
    exit 0
}
Set-Location -LiteralPath $vaultRoot

$engine = Join-Path $PSScriptRoot 'gen_commit.py'
if (-not (Test-Path -LiteralPath $engine)) {
    Write-Output $fallback
    exit 0
}

if ($StagedOnly) {
    $env:OBSIDIAN_GIT_STAGE_MODE = 'staged'
}

$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
    & $python.Source -B $engine
} else {
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($launcher) {
        & $launcher.Source -3 -B $engine
    } else {
        Write-Output $fallback
        exit 0
    }
}

if ($LASTEXITCODE -ne 0) {
    Write-Output $fallback
}
exit 0
