#!/usr/bin/env bash
# 一键启动 ios-usdt-project 本地核心闭环（Git Bash / WSL 均可）
# 顺序：数据库容器 -> Go(8888) -> Node(3313) -> 落地页(8080) -> 管理台(8898)
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOGD="$ROOT/local/logs"
mkdir -p "$LOGD"

echo "==> [1/5] 启动数据库容器 (MariaDB 13306 / Mongo 27018 / Redis 16379)"
docker compose -f "$ROOT/local/docker-compose.db.yml" up -d
echo "    等待健康检查..."
for i in $(seq 1 30); do
  h=$(docker inspect -f '{{.State.Health.Status}}' iusdt-mariadb iusdt-mongo iusdt-redis 2>/dev/null | tr '\n' ' ')
  [ "$h" = "healthy healthy healthy " ] && break
  sleep 2
done
echo "    容器状态: $(docker ps --format '{{.Names}}={{.Status}}' | grep iusdt | tr '\n' ' ')"

echo "==> [2/5] 启动 Go 后端 (8888)"
( cd "$ROOT/01-backend-go" && ./qianke-server.exe > "$LOGD/go.log" 2>&1 & )
sleep 6

echo "==> [3/5] 启动 Node 后端 (3313)"
export PATH="$(dirname "$(command -v node)"):$PATH"
( cd "$ROOT/02-backend-node" && npm start > "$LOGD/node.log" 2>&1 & )
sleep 12

echo "==> [4/5] 启动落地页服务器 (8080, /api -> Node)"
( cd "$ROOT/local" && python landing-server.py > "$LOGD/landing.log" 2>&1 & )
sleep 3

echo "==> [5/5] 启动管理台 dev server (8898)"
export PATH="$(dirname "$(command -v node)"):$PATH"
( cd "$ROOT/03-web-admin" && npx vite --host --mode development > "$LOGD/admin.log" 2>&1 & )
sleep 8

echo ""
echo "==================== 就绪 ===================="
echo "  Go 后端    : http://127.0.0.1:8888   (admin / 123456)"
echo "  Node 后端  : http://127.0.0.1:3313"
echo "  落地页     : http://127.0.0.1:8080/landing-pages/bokepx/"
echo "  管理台     : http://127.0.0.1:8898"
echo "  数据库     : MariaDB 13306 / MongoDB 27018 / Redis 16379"
echo "  日志目录   : $LOGD"
echo "=============================================="
