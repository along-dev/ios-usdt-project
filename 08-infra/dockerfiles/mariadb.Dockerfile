# MariaDB 镜像（T125 · 容器化新增件 · ⛔ 不影响本机）
# ★ 用途：容器内 MariaDB（对齐本机 11.4.4），启动时用 schema 初始化。
# ★ 初始化：/docker-entrypoint-initdb.d/*.sql 首启自动执行（官方镜像机制）。
FROM mariadb:11.4

# schema（qianke.sql 全量建库建表；⛔ 不改 07-db 源文件，仅 COPY 进镜像）
COPY 07-db/schema/qianke.sql /docker-entrypoint-initdb.d/00-qianke.sql

EXPOSE 3306
