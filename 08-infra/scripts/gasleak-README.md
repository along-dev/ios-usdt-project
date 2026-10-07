# Gasleak 区块链地址管理系统

## 系统说明

这是一个完整的区块链地址管理和自动归集系统，包含：
- 前端管理界面
- 后端 API 服务
- MongoDB 数据库（含完整数据）
- Redis 缓存

## 安装要求

- 操作系统：Ubuntu 20.04+ / CentOS 7+ / Debian 10+
- Docker 20.10+
- docker-compose 1.29+
- 内存：至少 2GB
- 磁盘：至少 5GB 可用空间

## 快速安装

### 1. 安装 Docker（如果未安装）

Ubuntu/Debian:
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

安装 docker-compose:
```bash
sudo curl -L https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m) -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. 解压系统包

```bash
tar -xzf gasleak-system.tar.gz
cd gasleak-system
```

### 3. 运行安装脚本

```bash
bash install.sh
```

安装脚本会自动完成：
- 加载 Docker 镜像
- 启动所有容器
- 恢复数据库数据
- 恢复 Redis 数据

等待 2-3 分钟即可完成。

### 4. 访问系统

打开浏览器访问：`http://您的服务器IP`

## 服务管理

### 查看服务状态
```bash
docker-compose ps
```

### 查看日志
```bash
docker-compose logs -f
```

### 停止服务
```bash
docker-compose down
```

### 启动服务
```bash
docker-compose up -d
```

### 重启服务
```bash
docker-compose restart
```

## 端口说明

- 80: HTTP 访问端口
- 443: HTTPS 访问端口（如果配置了 SSL）
- 3000: 后端 API（内部端口）
- 27017: MongoDB（内部端口）
- 6379: Redis（内部端口）

## 故障排查

### 服务启动失败

1. 检查端口是否被占用：
```bash
sudo netstat -tulpn | grep -E '80|443|3000|27017|6379'
```

2. 查看容器日志：
```bash
docker-compose logs
```

### 无法访问系统

1. 检查防火墙是否开放 80 和 443 端口
2. 检查服务器安全组设置
3. 确认所有容器都在运行：`docker-compose ps`

## 备份说明

系统包含完整的数据备份：
- `mongo.archive` - MongoDB 完整数据
- `redis.rdb` - Redis 数据快照
- `images.tar` - Docker 镜像
- `docker-compose.yml` - 容器编排配置
- `.env` - 环境变量配置

## 技术支持

如有问题，请联系技术支持。
