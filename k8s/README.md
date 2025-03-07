# Little Vote - Kubernetes 部署指南

本文档描述了如何使用 Kubernetes 部署 Little Vote 投票系统的各个组件。

## 系统架构

Little Vote 系统包含以下组件：

1. **主服务 (Main Service)**: 处理客户端的投票和查询请求
2. **票据生成服务 (Ticket Generator)**: 每 2 秒生成一个新的 ticket
3. **投票消费者 (Vote Consumer)**: 处理消息队列中的投票消息并持久化
4. **PostgreSQL**: 数据持久化存储
5. **Redis**: 用于缓存票据和投票信息
6. **Kafka & Zookeeper**: 消息队列系统，用于异步处理投票

## 先决条件

- Kubernetes 集群 (1.19+)
- kubectl 命令行工具
- 已配置的 kubeconfig
- Docker (用于构建镜像)

## 快速开始

1. 构建 Docker 镜像:

```bash
docker build -t little-vote:latest .
```

2. 部署所有 Kubernetes 资源:

```bash
kubectl apply -k k8s/
```

或者直接运行部署脚本:

```bash
./build-and-deploy.sh
```

## 目录结构

```
k8s/
├── namespace.yaml                # 命名空间定义
├── configmaps/                   # 配置映射
│   └── app-config.yaml          # 应用配置
├── secrets/                      # 密钥配置
│   └── app-secrets.yaml         # 应用密钥
├── deployments/                  # 应用部署
│   ├── main-service.yaml        # 主服务
│   ├── ticket-generator.yaml    # 票据生成服务
│   └── vote-consumer.yaml       # 投票消费者
├── services/                     # 服务定义
│   ├── main-service.yaml        # 主服务的服务
│   ├── ticket-generator.yaml    # 票据生成服务的服务
│   ├── postgres.yaml            # PostgreSQL服务
│   ├── redis.yaml               # Redis服务
│   ├── kafka.yaml               # Kafka服务
│   └── zookeeper.yaml           # Zookeeper服务
├── statefulsets/                 # 有状态服务
│   ├── postgres.yaml            # PostgreSQL
│   ├── redis.yaml               # Redis
│   ├── kafka.yaml               # Kafka
│   └── zookeeper.yaml           # Zookeeper
├── ingress/                      # 入口配置
│   └── little-vote-ingress.yaml # 应用入口
└── kustomization.yaml           # Kustomize配置
```

## 访问服务

部署完成后，可以通过以下URL访问服务：

- 主服务 API: `http://little-vote.example.com/`
- 票据生成服务: `http://little-vote.example.com/ticket`

注意：需要将 `little-vote.example.com` 解析到您的 Ingress 控制器的外部 IP 地址。

## 扩展

要扩展服务，可以使用以下命令：

```bash
# 扩展主服务实例数
kubectl scale deployment/main-service -n little-vote --replicas=4

# 扩展投票消费者实例数
kubectl scale deployment/vote-consumer -n little-vote --replicas=4
```

## 监控

您可以使用 Kubernetes Dashboard 或其他监控工具(如 Prometheus 和 Grafana)来监控服务状态：

```bash
kubectl -n little-vote get all

# 查看 Pod 日志
kubectl -n little-vote logs deployment/main-service

# 查看 Pod 详情
kubectl -n little-vote describe pod <pod-name>
```

## 故障排除

如果遇到问题，可以检查以下内容：

1. 确认所有 Pod 是否正常运行：
   ```bash
   kubectl -n little-vote get pods
   ```

2. 检查 Pod 日志：
   ```bash
   kubectl -n little-vote logs <pod-name>
   ```

3. 检查服务连接：
   ```bash
   kubectl -n little-vote exec <pod-name> -- curl -s main-service
   ```

4. 检查 ConfigMap 和 Secret：
   ```bash
   kubectl -n little-vote get configmaps
   kubectl -n little-vote get secrets
   ``` 