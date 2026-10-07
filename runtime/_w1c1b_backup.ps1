$ErrorActionPreference = 'Stop'
$src = 'E:\ios漏洞\_integration\build_unified.ps1'
$bak = 'E:\ios漏洞\_integration\build_unified.ps1.bak_w1c1b'
if (Test-Path $bak) { Write-Output 'BAK_EXISTS' } else { Copy-Item $src $bak; Write-Output 'BAK_CREATED' }
Write-Output ("src_sha256=" + (Get-FileHash $src -Algorithm SHA256).Hash)
Write-Output ("bak_sha256=" + (Get-FileHash $bak -Algorithm SHA256).Hash)
Write-Output ("src_bytes=" + (Get-Item $src).Length)
