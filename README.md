# CAST - Concurrent API for Secure Ticketing

## 项目概述

CAST 是一个高性能、安全的投票系统，允许用户对特定用户名进行投票并查询当前票数。系统通过安全票据（ticket）机制确保投票操作的合法性和安全性。

### 核心功能

- **票据生成**：系统每2秒自动生成一个新的安全票据（ticket），每个票据在有效期内可以进行有限次数的投票操作
- **用户投票**：支持为单个或多个用户同时投票，每次投票计数可配置
- **票数查询**：随时查询指定用户的当前票数

## 技术架构

### 后端技术栈

- **FastAPI + Strawberry GraphQL**：提供高性能的GraphQL API接口
- **Redis**：用于票据和投票计数缓存
- **PostgreSQL**：持久化存储用户投票数据
- **Kafka**：消息队列，确保投票操作的可靠性和扩展性
- **Kubernetes**：容器编排，支持系统水平扩展

### 系统架构图

```
                                       ┌─────────────────┐
                                       │                 │
                                       │ Client Request  │
                                       │                 │
                                       └────────┬────────┘
                                                │
                                                ▼
┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐
                          Kubernetes 集群
│                                                                               │
   ┌────────────────┐           ┌────────────────┐           ┌────────────────┐
│  │                │           │                │           │                │ │
   │Ticket Generator│◄──────────┤  Main Service  │◄──────────┤    Client      │
│  │                │──────────►│   (Multiple)   │──────────►│                │ │
   │                │           │                │           │                │
│  └────────┬───────┘           └───┬───┬────────┘           └────────────────┘ │
            │                       │   │
│           │                       │   │                                       │
            ▼                       │   │
│  ┌────────────────┐               │   │                                       │
   │                │               │   │
│  │     Redis      │◄──────────────┘   │                    ┌────────────────┐ │
   │ (Ticket & Vote)│                   └───────────────────►│                │
│  │                │                                        │     Kafka      │ │
   └────────────────┘                                        │      (MQ)      │
│                                                            │                │ │
                                                             └───────┬────────┘
│                                                                    │          │
                                                                     │
│                                                                    ▼          │
   ┌────────────────┐                                       ┌────────────────┐
│  │                │                                       │                │  │
   │   PostgreSQL   │◄──────────────────────────────────────┤  Vote Consumer │
│  │  (Persistence) │                                       │   (Multiple)│  │  │
   │                │                                       │                │
│  └────────────────┘                                       └────────────────┘  │

└ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘
```

#### 系统工作流程

1. **票据生成**：Ticket Generator服务每2秒生成一个新的安全票据，并将其存储在Redis中
2. **API请求处理**：Main Service提供GraphQL API接口，处理客户端的投票和查询请求
3. **票据验证**：收到投票请求时，Main Service从Redis验证票据的有效性
4. **异步处理**：投票操作被发送到Kafka消息队列，实现系统解耦和高可用
5. **持久化存储**：Vote Consumer服务消费Kafka消息，并将投票结果持久化存储到PostgreSQL，会根据Vote的版本号来保证数据一致性

### 目录结构

```
├── app/                       # 主应用代码
│   ├── config/                # 配置文件
│   ├── database/              # 数据库相关代码
│   ├── models/                # 数据模型
│   ├── schema/                # GraphQL schema定义
│   │   ├── mutations.py       # GraphQL mutations
│   │   ├── queries.py         # GraphQL queries
│   │   └── types.py           # GraphQL 类型定义
│   ├── services/              # 业务逻辑服务
│   │   ├── ticket_service.py  # 票据服务
│   │   └── vote_service.py    # 投票服务
│   └── workers/               # 后台工作进程
├── client/                    # 客户端代码（测试工具）
├── deployment/                # 部署相关文件
├── k8s/                       # Kubernetes配置文件
├── Dockerfile                 # Docker构建文件
├── requirements.txt           # Python依赖
└── build-and-deploy.sh        # 构建和部署脚本
```

## GraphQL API

### Queries

- **query(username: String!): Int!**
  - 查询指定用户的当前票数
  
- **cas(): TicketInfo!**
  - 获取当前有效的票据信息

### Mutations

- **vote(usernames: [String!]!, voteCount: [Int!]!, ticket: String!, voterUsername: String): VoteResult!**
  - 为一个或多个用户投票
  - 需要提供有效的票据
  - 可选择性地记录投票人

## 安装与运行

### Kubernetes 部署

```bash
./build-and-deploy.sh
```

## 系统设计亮点

- **高并发支持**：使用异步IO和高效的数据结构确保高并发场景下的系统性能
- **安全票据机制**：通过基于HMAC的安全票据生成，防止投票作弊
- **水平扩展**：服务组件可独立扩展，支持超大规模用户场景
- **消息队列**：使用Kafka确保投票操作的可靠性和一致性
- **容器化部署**：支持Kubernetes，便于CI/CD和云原生部署
