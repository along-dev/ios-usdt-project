$ErrorActionPreference = 'Stop'

# 独立复现 Sanitize-EnvFile / Sanitize-Sql 的逻辑，验证行为正确
$SANITIZE_ENV_KEYS = @{
    'JWT_SECRET'             = '${JWT_SECRET}'
    'EXPORT_ENCRYPTION_KEY'  = '${EXPORT_ENCRYPTION_KEY}'
    'DEFAULT_ADMIN_PASSWORD' = '${DEFAULT_ADMIN_PASSWORD}'
}

function Log($msg, $color = 'Gray') { Write-Host $msg -ForegroundColor $color }

function Sanitize-EnvFile {
    param([string]$From, [string]$To)
    $lines = Get-Content -Path $From -Encoding UTF8
    $out = New-Object System.Collections.Generic.List[string]
    $redacted = 0
    foreach ($line in $lines) {
        $trimmed = $line.Trim()
        if ($trimmed -eq '' -or $trimmed.StartsWith('#')) { $out.Add($line); continue }
        $eq = $line.IndexOf('=')
        if ($eq -lt 0) { $out.Add($line); continue }
        $key = $line.Substring(0, $eq).Trim()
        if ($SANITIZE_ENV_KEYS.ContainsKey($key)) {
            $out.Add("$key=$($SANITIZE_ENV_KEYS[$key])")
            $redacted++
        } else {
            $out.Add($line)
        }
    }
    $out | Set-Content -Path $To -Encoding UTF8
    Write-Output "ENV sanitized: redacted=$redacted written=$To"
}

function Sanitize-Sql {
    param([string]$From, [string]$To)
    $lines = Get-Content -Path $From -Encoding UTF8
    $kept = New-Object System.Collections.Generic.List[string]
    $removed = 0
    $pendingInsert = $false
    foreach ($line in $lines) {
        if ($pendingInsert) {
            $removed++
            if ($line -match ';\s*$') { $pendingInsert = $false }
            continue
        }
        if ($line -match '^\s*INSERT\s+INTO\b') {
            $removed++
            if ($line -notmatch ';\s*$') { $pendingInsert = $true }
            continue
        }
        $kept.Add($line)
    }
    $kept | Set-Content -Path $To -Encoding UTF8
    Write-Output "SQL sanitized: removed=$removed kept=$($kept.Count) written=$To"
}

$tmp = 'E:\ios漏洞\_integration\_fix_work\_unit'
New-Item -ItemType Directory -Force -Path $tmp | Out-Null

Sanitize-EnvFile -From 'E:\ios漏洞\ios-xy-main\gasleak-system\.env' -To "$tmp\.env.example"
Sanitize-Sql -From 'E:\潜客\qianke\qianke0301.sql' -To "$tmp\qianke.sql"

Write-Output ''
Write-Output '=== .env.example 全文 ==='
Get-Content "$tmp\.env.example" | ForEach-Object { $_ }
