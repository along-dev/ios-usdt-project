param(
    [Parameter(Mandatory = $true)][string]$Path
)
# 为 PowerShell 脚本补写 UTF-8 BOM（若无则加）。
# 安全做法：先读入内存，构造新数组，再整体 WriteAllBytes；任何一步失败都不触碰原文件。
$raw = [System.IO.File]::ReadAllBytes($Path)
if ($raw.Length -eq 0) { throw "文件为空，拒绝操作: $Path" }

$hasBom = ($raw.Length -ge 3 -and $raw[0] -eq 0xEF -and $raw[1] -eq 0xBB -and $raw[2] -eq 0xBF)
if ($hasBom) {
    Write-Output "ALREADY_BOM: $Path (size=$($raw.Length))"
    return
}

$outBytes = New-Object 'byte[]' ($raw.Length + 3)
$outBytes[0] = 0xEF
$outBytes[1] = 0xBB
$outBytes[2] = 0xBF
[Array]::Copy($raw, 0, $outBytes, 3, $raw.Length)

# 先写临时文件并校验，再原子替换，避免中途失败留下半截文件
$tmp = "$Path.bomtmp"
[System.IO.File]::WriteAllBytes($tmp, $outBytes)
$chk = [System.IO.File]::ReadAllBytes($tmp)
if ($chk.Length -ne $outBytes.Length) { throw "临时文件写入不完整" }
Move-Item -Path $tmp -Destination $Path -Force
Write-Output "BOM_ADDED: $Path (size=$($outBytes.Length))"
