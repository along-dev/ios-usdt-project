# 广告线验证专用：在 3001 起第二个 Node 实例（不动共享的 3000）
# 用 Start-Process 才能真正 detach；定时任务由 _ad3001.env 里的 NODE_APP_INSTANCE=99 跳过。
$ErrorActionPreference = 'Stop'
$node = 'E:\CTF\runtime\node\node.exe'
$wd   = 'E:\USDT项目\02-backend-node'
$envf = 'X:\_integration\_fix_work\_ad3001.env'
$out  = 'X:\_integration\_fix_work\_ad3001.out'
$err  = 'X:\_integration\_fix_work\_ad3001.err'

$p = Start-Process -FilePath $node `
    -ArgumentList @("--env-file-if-exists=$envf", 'src_restored/app.js') `
    -WorkingDirectory $wd -WindowStyle Hidden `
    -RedirectStandardOutput $out -RedirectStandardError $err -PassThru

Write-Output "started pid=$($p.Id)"
