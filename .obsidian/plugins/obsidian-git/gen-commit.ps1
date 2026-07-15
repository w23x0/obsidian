# gen-commit.ps1
# 用 DeepSeek API 根据 git diff 生成中文 commit message。
# 无法访问 API 时，回退为包含改动文件名的中文摘要，避免无意义的日期提交。
# API key 从 %USERPROFILE%\.deepseek-api-key 读取（vault 外，不入 git）。

$ErrorActionPreference = 'SilentlyContinue'

# 切到 vault 根（本脚本位于 .obsidian/plugins/obsidian-git/ 下，上三级即 vault 根）
$vaultRoot = $PSScriptRoot | Split-Path -Parent | Split-Path -Parent | Split-Path -Parent
if ($vaultRoot -and (Test-Path $vaultRoot)) { Set-Location $vaultRoot }

$changedNames = git diff --cached --name-only
if (-not $changedNames) { $changedNames = git diff HEAD --name-only }
$nameList = @($changedNames | ForEach-Object { Split-Path $_ -Leaf } | Where-Object { $_ } | Select-Object -First 3)
if ($nameList.Count -gt 0) {
    $fallback = "更新笔记：" + ($nameList -join "、")
} else {
    $fallback = "更新笔记与资料"
}

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
$sys = @"
你是 git commit message 生成器。根据 diff 输出中文提交说明：第一行是准确、具体的标题，限 50 字以内；空一行后，再用 2 至 4 行简洁说明重要改动、涉及的资料或结论。不要编造 diff 中没有的内容，不要使用引号、前缀或 Markdown 标题。
"@
$usr = "根据下面的 diff 生成提交说明：`n`n$diff"
$body = @{
    model       = "deepseek-chat"
    messages    = @(
        @{ role = "system"; content = $sys }
        @{ role = "user";   content = $usr }
    )
    max_tokens  = 800
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
        $msg = ($msg -replace "\r\n?", "`n").Trim().Trim('"').Trim("'").Trim()
    }
    if (-not $msg) { Write-Output $fallback } else { Write-Output $msg }
} catch {
    Write-Output $fallback
}
