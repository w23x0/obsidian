# gen-commit.ps1
# 用 DeepSeek API 根据 git diff 生成一句话中文 commit message。
# 失败 / 无 key / 无改动 时回退到 "vault backup: <时间>"，保证 commit 不中断。
# API key 从 %USERPROFILE%\.deepseek-api-key 读取（vault 外，不入 git）。

$ErrorActionPreference = 'SilentlyContinue'

# 切到 vault 根（本脚本位于 .obsidian/plugins/obsidian-git/ 下，上三级即 vault 根）
$vaultRoot = $PSScriptRoot | Split-Path -Parent | Split-Path -Parent | Split-Path -Parent
if ($vaultRoot -and (Test-Path $vaultRoot)) { Set-Location $vaultRoot }

$ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$fallback = "vault backup: $ts"

# 1. 读 API key（vault 外文件）
$keyFile = Join-Path $env:USERPROFILE ".deepseek-api-key"
if (-not (Test-Path $keyFile)) { Write-Output $fallback; exit 0 }
$apiKey = (Get-Content $keyFile -Raw).Trim()
if (-not $apiKey) { Write-Output $fallback; exit 0 }

# 2. 拿 diff：优先已暂存的，空则看相对 HEAD 的全部改动
$diff = git diff --cached
if (-not $diff) { $diff = git diff HEAD }
if (-not $diff) { Write-Output $fallback; exit 0 }

# 3. 截断，避免 token 爆炸
if ($diff.Length -gt 8000) { $diff = $diff.Substring(0, 8000) + "`n...[diff truncated]" }

# 4. 调 DeepSeek
$sys = "你是 git commit message 生成器。只输出一句话中文总结，不超过30字，不加引号、句号、前缀。"
$usr = "根据下面的 diff 用一句简短中文总结这次改动：`n`n$diff"
$body = @{
    model       = "deepseek-chat"
    messages    = @(
        @{ role = "system"; content = $sys }
        @{ role = "user";   content = $usr }
    )
    max_tokens  = 512
    temperature = 0.2
    stream      = $false
} | ConvertTo-Json -Depth 10 -Compress

try {
    $bodyBytes = [System.Text.Encoding]::UTF8.GetBytes($body)
    $r = Invoke-WebRequest -Uri "https://api.deepseek.com/chat/completions" `
        -Method Post `
        -Headers @{ Authorization = "Bearer $apiKey" } `
        -ContentType "application/json; charset=utf-8" `
        -Body $bodyBytes `
        -TimeoutSec 30 `
        -UseBasicParsing
    $json = [System.Text.Encoding]::UTF8.GetString($r.RawContentStream.ToArray())
    $resp = $json | ConvertFrom-Json

    $msg = $resp.choices[0].message.content
    if ($msg) {
        $msg = ($msg -replace "[\r\n]+", " ").Trim().Trim('"').Trim("'").Trim()
    }
    if (-not $msg) { Write-Output $fallback } else { Write-Output $msg }
} catch {
    Write-Output $fallback
}
