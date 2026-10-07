#!/usr/bin/env bash
# 停止 ios-usdt-project 本地核心闭环
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "==> 停止应用进程"
# 按端口杀进程（8888 Go / 3313 Node / 8080 落地页 / 8898 管理台）
for port in 8888 3313 8080 8898; do
  pid=$(netstat -ano 2>/dev/null | grep -E ":$port\b.*LISTENING" | awk '{print $NF}' | head -1)
  if [ -n "${pid:-}" ]; then
    taskkill //F //PID "$pid" >/dev/null 2>&1 && echo "  已停端口 $port (PID $pid)"
  fi
done
echo "==> 停止数据库容器"
docker compose -f "$ROOT/local/docker-compose.db.yml" down
echo "完成（数据卷保留在 local/data/）"
