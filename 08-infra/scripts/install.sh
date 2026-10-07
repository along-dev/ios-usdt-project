#!/bin/bash
set -e

echo "=========================================="
echo "  Gasleak 系统一键安装脚本"
echo "=========================================="
echo ""

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "❌ 未检测到 Docker，请先安装 Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ 未检测到 docker-compose，请先安装"
    exit 1
fi

echo "✅ Docker 环境检测通过"
echo ""

# 询问域名
echo "=========================================="
echo "  域名配置"
echo "=========================================="
echo ""
echo "请输入您的后台管理域名（例如：admin.example.com）"
echo "如果没有域名，直接按回车跳过，将使用 IP 访问"
echo ""
read -p "域名: " DOMAIN

if [ -z "$DOMAIN" ]; then
    DOMAIN="_"
    echo ""
    echo "✅ 将使用 IP 地址访问"
else
    echo ""
    echo "✅ 已设置域名：$DOMAIN"
fi
echo ""

# 创建 nginx 配置目录和证书目录
echo "📝 正在配置 Nginx..."
mkdir -p nginx/cert
mkdir -p landing/shopg
mkdir -p landing/shopins

# 复制 SSL 证书
cp ios17.cc.cert nginx/cert/
cp ios17.cc.key nginx/cert/

# 生成 nginx 配置
sed "s/DOMAIN_PLACEHOLDER/$DOMAIN/" default.conf.template > nginx/default.conf

echo "✅ Nginx 配置完成"
echo ""

# 加载镜像
echo "📦 正在加载 Docker 镜像（约需 1-2 分钟）..."
docker load -i images.tar
echo "✅ 镜像加载完成"
echo ""

# 启动容器
echo "🚀 正在启动服务..."
docker-compose up -d
echo "✅ 容器启动完成"
echo ""

# 等待 MongoDB 启动
echo "⏳ 等待数据库启动..."
sleep 10

# 恢复 MongoDB 数据
echo "📥 正在恢复 MongoDB 数据..."
docker-compose cp mongo.archive mongo:/tmp/mongo.archive
docker-compose exec -T mongo mongorestore --archive=/tmp/mongo.archive --gzip --drop
echo "✅ MongoDB 数据恢复完成"
echo ""

# 恢复 Redis 数据
echo "📥 正在恢复 Redis 数据..."
docker-compose cp redis.rdb redis:/data/dump.rdb
docker-compose restart redis
echo "✅ Redis 数据恢复完成"
echo ""

# 等待所有服务启动
echo "⏳ 等待所有服务完全启动..."
sleep 15

echo ""
echo "=========================================="
echo "  ✅ 安装完成！"
echo "=========================================="
echo ""
echo "服务状态："
docker-compose ps
echo ""

if [ "$DOMAIN" = "_" ]; then
    echo "访问地址：http://YOUR_SERVER_IP"
else
    echo "访问地址：http://$DOMAIN 或 https://$DOMAIN"
    echo ""
    echo "⚠️  请确保已将域名 $DOMAIN 解析到本服务器 IP"
fi

echo ""
echo "默认账号密码请查看 .env 文件："
echo "  cat .env | grep DEFAULT_ADMIN_PASSWORD"
echo ""
echo "常用命令："
echo "  查看日志: docker-compose logs -f"
echo "  停止服务: docker-compose down"
echo "  启动服务: docker-compose up -d"
echo "  重启服务: docker-compose restart"
echo ""

