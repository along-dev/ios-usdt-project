# =============================================================================
# rollback.ps1 —— 回滚脚本（R3-3 / 审核 E 的 E-08）
# =============================================================================
# ★ 背景：本项目此前【无 git】，回滚靠按卡手工备份 —— 无统一基线、无命名规范。
#   本轮已建立 git 基线（首次提交 0333158）。
#
# ★ 本脚本提供【按提交回滚】能力，并守护关键不变量。
#
# 用法：
#   .\rollback.ps1 -List                  # 列出可回滚的提交
#   .\rollback.ps1 -Show [commit]         # 查看某提交改了什么
#   .\rollback.ps1 -DryRun [commit]       # 预演回滚（不改文件）
#   .\rollback.ps1 -To [commit]           # 回滚到指定提交（★ 会改文件）
#   .\rollback.ps1 -Guard                 # 只校验守护不变量
# =============================================================================

param(
    [switch]$List,
    [switch]$Guard,
    [string]$Show,
    [string]$DryRun,
    [string]$To
)

$Repo = 'E:\USDT项目'
Set-Location $Repo

# ★ E: 是 exFAT ⇒ 需要 safe.directory
git config --global --add safe.directory 'E:/USDT项目' 2>$null | Out-Null

# ---- 守护不变量 --------------------------------------------------------------
# ★★ T89（⌛2026-10-06）：本表与 `E:\ios漏洞\_integration\_fix_work\verify_d4c2_credentials.py`
#    的 `AUTH_BASELINE` **钉的是同一批件的内容 sha** ⇒ ★★ **两处必须同步改**。
#    ⛔ 只改一处 ⇒ 另一处必报「不匹配」：`rollback.ps1 -Guard` 报 `VIOLATED` ／ D4-C2 判据 `V8` **FAIL**。
#    ★ 重算一条命令（★ 在仓库根跑，把路径换成要重算的件）：
#      python -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" 09-docs/spec/contracts.md
#    ★ 口径：**本表的 `Expect` 写<小写>**（比对时把 `Get-FileHash` 的 `.Hash` 转了 `.ToLower()`）；
#      **`verify_d4c2_credentials.py` 的 `AUTH_BASELINE` 写<大写>**（比对时 `.hexdigest().upper()`）⇒ ⛔ 别照抄。
$GUARDS = @(
    @{ Path = '_manifest.sha256';      Expect = 'b940dc19a76f1627ed185f9af54ff79f0f3dac4fcece0f86f78c3c9cdbdb58c2' },
    @{ Path = '09-docs\spec\contracts.md'; Expect = '0e03048ddfbe6945dba0cfda5c9dae17b3b50b9ac485a83f921913e49e337358' }
)

function Test-Guards {
    # ★ PowerShell 陷阱（本脚本实测踩到）：
    #   函数内若用 Write-Output 输出文本 + return 返回值，
    #   调用方 `$null = Test-Guards` 会【连文本一起丢弃】⇒ 静默无输出。
    #   ⇒ 文本一律用 Write-Host（不经管道），返回值仍用 return。
    Write-Host "=== 守护不变量校验 ==="
    $allOk = $true
    foreach ($g in $GUARDS) {
        $p = Join-Path $Repo $g.Path
        if (-not (Test-Path $p)) {
            Write-Host "  [!!] 缺失: $($g.Path)"
            $allOk = $false
            continue
        }
        $h = (Get-FileHash $p -Algorithm SHA256).Hash.ToLower()
        $ok = ($h -eq $g.Expect)
        if (-not $ok) { $allOk = $false }
        Write-Host "  $(if ($ok) { '[OK]' } else { '[!!]' }) $($g.Path)"
        if (-not $ok) {
            Write-Host "        期望: $($g.Expect)"
            Write-Host "        实际: $h"
        }
    }
    Write-Host ""
    Write-Host "GUARD_RESULT=$(if ($allOk) { 'OK' } else { 'VIOLATED' })"
    return $allOk
}

if ($Guard) { $null = Test-Guards; exit 0 }

# ---- 列出提交 ---------------------------------------------------------------
if ($List) {
    Write-Output "=== 可回滚的提交 ==="
    git log --oneline --decorate -30
    Write-Output ""
    Write-Output "总提交数: $((git rev-list --count HEAD))"
    exit 0
}

# ---- 查看某提交 -------------------------------------------------------------
if ($Show) {
    Write-Output "=== 提交 $Show 的改动 ==="
    git show --stat $Show
    exit 0
}

# ---- 预演回滚 ---------------------------------------------------------------
if ($DryRun) {
    Write-Output "=== 预演：回滚到 $DryRun ==="
    Write-Output ""
    Write-Output "--- 将会被还原/删除的文件 ---"
    git diff --stat $DryRun HEAD
    Write-Output ""
    Write-Output "★ 这只是预演，未修改任何文件。"
    Write-Output "  确认无误后执行: .\rollback.ps1 -To $DryRun"
    exit 0
}

# ---- 实际回滚 ---------------------------------------------------------------
if ($To) {
    Write-Output "=== 回滚到 $To ==="
    Write-Output ""

    # ★ 先备份当前状态（用 git stash 保留未提交改动）
    $dirty = (git status --porcelain | Measure-Object).Count
    if ($dirty -gt 0) {
        Write-Output "  检测到 $dirty 项未提交改动 ⇒ 先 stash 备份"
        git stash push -u -m "rollback-precursor-$(Get-Date -Format yyyyMMdd-HHmmss)"
        Write-Output "  （可用 git stash list / git stash pop 恢复）"
    }

    Write-Output ""
    Write-Output "--- 回滚 ---"
    git checkout $To -- . 2>&1 | Select-Object -First 5
    Write-Output "  已 checkout $To"

    Write-Output ""
    $null = Test-Guards

    Write-Output ""
    Write-Output "★ 注意：checkout 只还原【文件内容】，不移动 HEAD。"
    Write-Output "  如需在历史中移动，请手动执行: git reset --hard $To"
    exit 0
}

# ---- 无参数：显示帮助 + 守护校验 ----------------------------------------------
Write-Output "rollback.ps1 —— 回滚脚本"
Write-Output ""
Write-Output "用法："
Write-Output "  .\rollback.ps1 -List              列出可回滚的提交"
Write-Output "  .\rollback.ps1 -Show [commit]     查看某提交改了什么"
Write-Output "  .\rollback.ps1 -DryRun [commit]   预演回滚（不改文件）"
Write-Output "  .\rollback.ps1 -To [commit]       回滚到指定提交（★ 会改文件）"
Write-Output "  .\rollback.ps1 -Guard             只校验守护不变量"
Write-Output ""
$null = Test-Guards
