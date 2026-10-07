# gasleak nginx 镜像（T125 · 容器化新增件 · ⛔ 不影响本机）
# ★ 用途：给 compose 里 `image: gasleak-nginx:${IMAGE_VERSION}` 提供<构建来源>（原无 Dockerfile）。
# ★ nginx 官方镜像机制：/etc/nginx/templates/*.template 启动时用 envsubst 渲染到 conf.d/
#   ⇒ ${APP_BACKEND_HOST}/${ADMIN_BACKEND_HOST}/${ADMIN_DOMAIN}/${LANDING_DOMAIN}/${SSL_CERT}/${SSL_KEY}
#   全部由 compose 的 environment 注入，镜像无需硬编码。
FROM nginx:1.25-alpine

COPY 08-infra/nginx/default.conf.template /etc/nginx/templates/default.conf.template

# 证书与落地页静态：由 compose 以 volume 挂载（⛔ 不 COPY 进镜像，镜像保持无秘密）
RUN mkdir -p /etc/nginx/cert /usr/share/nginx/html/shopg /usr/share/nginx/html/shopins
