module.exports = {
  apps: [{
    name: 'gasleak',
    script: './src_restored/app.js',
    // ★ 修复（F1-C4）：原为 `parseInt(process.env.WORKERS) || 'max'`。
    //   与 src_restored/app.js:193 的 `parseInt(process.env.WORKERS || '1')` 语义冲突 ——
    //   漏配 WORKERS 时 PM2 取 'max'（= CPU 核数，多实例），app 取 1 ⇒ totalWorkers=1
    //   ⇒ app.js:198 的 instanceOnly 守卫被跳过 ⇒ 每个 worker 都注册定时任务 ⇒ N× 重复归集。
    //   改为与 app.js 同源的默认值：漏配即退化为单实例（安全侧：宁可少注册，不可重复注册）。
    instances: parseInt(process.env.WORKERS || '1'),
    exec_mode: 'cluster',
    max_restarts: 10,
    min_uptime: 5000,
    restart_delay: 3000,
    exp_backoff_restart_delay: 100,
    max_memory_restart: '1G',
    kill_timeout: 5000,
    wait_ready: true,
    listen_timeout: 10000,
    node_args: '--max-old-space-size=1024',
    env_file: '.env',
    out_file: '/dev/null',
    error_file: '/dev/null',
    env: {
      NODE_ENV: 'production',
    },
  }]
}
