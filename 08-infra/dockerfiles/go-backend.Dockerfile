# Go 后端镜像（T125 · 容器化新增件 · ⛔ 不影响本机）
# ★ 交叉编译：CGO_ENABLED=0 产出纯静态 Linux 二进制（⛔ 不依赖本机 _i2c1_server.exe / X: subst）。
# ★ 多阶段：golang 构建 → alpine 运行。
FROM golang:1.20-alpine AS build

WORKDIR /src
ENV CGO_ENABLED=0 GOOS=linux GOARCH=amd64
COPY 01-backend-go/go.mod 01-backend-go/go.sum ./
RUN go mod download
COPY 01-backend-go ./
RUN go build -o /gva-server .

FROM alpine:3.18
RUN apk add --no-cache ca-certificates tzdata && mkdir -p /app
COPY --from=build /gva-server /app/gva-server
# ★ F-T125-4 返修：resource/（casbin rbac_model.conf 等 cwd 相对依赖）——
#   core/server.go:55 启动期 Casbin Init() 失败即 Fatal("casbin 初始化失败")，
#   config.docker.yaml.example:39 model-path='./resource/rbac_model.conf'（cwd 相对）
#   ⇒ 容器 /app 下必须有 resource/，否则服务拒绝启动。
COPY --from=build /src/resource /app/resource
WORKDIR /app
# ★ 配置：容器内用 config.docker.yaml（由 compose 挂载或 env 注入），⛔ 不改本机 config.yaml.example
EXPOSE 8888
CMD ["/app/gva-server"]
