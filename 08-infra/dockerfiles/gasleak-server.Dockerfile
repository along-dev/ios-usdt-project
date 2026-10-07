# gasleak Node 后端镜像（T125 · 容器化新增件 · ⛔ 不影响本机）
# ★ 用途：给 compose 里 `image: gasleak-server:${IMAGE_VERSION}` 提供<构建来源>。
FROM node:20-alpine

WORKDIR /app
# 仅装生产依赖（⛔ 不装 devDependencies）
COPY 02-backend-node/package.json 02-backend-node/package-lock.json ./
RUN npm ci --omit=dev

# 源码（src_restored = 运行时入口）
COPY 02-backend-node/src_restored ./src_restored
# ★ F-T125-1 返修：ecosystem.config.cjs 文件存在 ⇒ 直接 COPY（⛔ 原 `2>/dev/null || true` 是 shell 语法、非 COPY 语法，dest 被解析成 `true` ⇒ build 必失败）
COPY 02-backend-node/ecosystem.config.cjs ./ecosystem.config.cjs

# 端口与启动（对齐 package.json "start": node --env-file-if-exists=.env src_restored/app.js）
ENV NODE_ENV=production
EXPOSE 3000
CMD ["node", "src_restored/app.js"]
