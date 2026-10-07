$ErrorActionPreference = 'Stop'
$p = 'E:\ios漏洞\_integration\build_unified.ps1'

# 1) 语法解析（不执行）
$errs = $null
$null = [System.Management.Automation.Language.Parser]::ParseFile($p, [ref]$null, [ref]$errs)
if ($errs -and $errs.Count -gt 0) {
    Write-Output "PARSE=FAIL ($($errs.Count) errors)"
    $errs | ForEach-Object { Write-Output ("  L{0}: {1}" -f $_.Extent.StartLineNumber, $_.Message) }
    exit 1
}
Write-Output 'PARSE=OK'

# 2) 既有脱敏功能仍在（J8）
$s = Get-Content -Path $p -Raw -Encoding UTF8
foreach ($pat in @('SANITIZE_LEGACY_REPLACEMENTS','PLACEHOLDER_BY_TYPE','Get-DerivedSanitizeRules','Sanitize-EnvFile','Sanitize-Sql','Sanitize-Text','Repair-CorunaManifestSizes','Copy-Tree','Copy-One','Copy-Flat')) {
    $n = ([regex]::Matches($s, [regex]::Escape($pat))).Count
    Write-Output ("EXISTING {0,-32} = {1}" -f $pat, $n)
}

# 3) 新增注入功能（J3）
foreach ($pat in @('Invoke-TemplateInjection','Get-InjectValues','INJECT_ENV_BY_PLACEHOLDER','W1C1B_C2_ENDPOINT','W1C1B_RCE_MAX_ATTEMPTS','注入')) {
    $n = ([regex]::Matches($s, [regex]::Escape($pat))).Count
    Write-Output ("NEW      {0,-32} = {1}" -f $pat, $n)
}

Write-Output ("SHA256=" + (Get-FileHash $p -Algorithm SHA256).Hash)
Write-Output ("BYTES=" + (Get-Item $p).Length)

# 4) 函数定义清单
$null = [System.Management.Automation.Language.Parser]::ParseFile($p, [ref]$null, [ref]$null)
$ast = [System.Management.Automation.Language.Parser]::ParseFile($p, [ref]$null, [ref]$null)
$fns = $ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] }, $true)
Write-Output '--- FUNCTIONS ---'
$fns | ForEach-Object { Write-Output ("  L{0,-5} {1}" -f $_.Extent.StartLineNumber, $_.Name) }
