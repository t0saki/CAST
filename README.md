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
- **Kafka**：消息队列，异步更新PG，确保投票操作的可靠性和扩展性
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

# 测试运行

## 测试环境
```bash
❯ kubectl -n cast get all
NAME                                   READY   STATUS    RESTARTS      AGE
pod/kafka-0                            1/1     Running   0             35s
pod/main-service-5455bfc967-6zfbw      1/1     Running   2 (25s ago)   35s
pod/main-service-5455bfc967-mjghc      1/1     Running   2 (26s ago)   35s
pod/postgres-0                         1/1     Running   0             35s
pod/redis-0                            1/1     Running   0             35s
pod/ticket-generator-87f5cdbf7-8fnvw   1/1     Running   0             35s
pod/vote-consumer-6f4b65b845-nv67r     1/1     Running   2 (30s ago)   35s
pod/vote-consumer-6f4b65b845-vngww     1/1     Running   2 (30s ago)   35s
pod/zookeeper-0                        1/1     Running   0             35s

NAME                       TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)        AGE
service/kafka              ClusterIP   None            <none>        9092/TCP       35s
service/main-service       NodePort    10.97.245.208   <none>        80:30000/TCP   35s
service/postgres           ClusterIP   None            <none>        5432/TCP       35s
service/redis              ClusterIP   10.109.25.162   <none>        6379/TCP       35s
service/ticket-generator   ClusterIP   10.101.194.35   <none>        8001/TCP       35s
service/zookeeper          ClusterIP   10.102.148.18   <none>        2181/TCP       35s

NAME                               READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/main-service       2/2     2            2           35s
deployment.apps/ticket-generator   1/1     1            1           35s
deployment.apps/vote-consumer      2/2     2            2           35s

NAME                                         DESIRED   CURRENT   READY   AGE
replicaset.apps/main-service-5455bfc967      2         2         2       35s
replicaset.apps/ticket-generator-87f5cdbf7   1         1         1       35s
replicaset.apps/vote-consumer-6f4b65b845     2         2         2       35s

NAME                         READY   AGE
statefulset.apps/kafka       1/1     35s
statefulset.apps/postgres    1/1     35s
statefulset.apps/redis       1/1     35s
statefulset.apps/zookeeper   1/1     35s
```


## 测试结果

使用client目录下的测试工具，结果如下：

- `vote_client.py`

```bash
❯ python vote_client.py
===== Little Vote Client Demo =====

🎟️ Getting a ticket...
Ticket: b7cfc783f97fbecba0585beec51a5d0d3751865f95b7ca94f66b733bae069232
Valid until: 2025-03-07T09:03:43
Remaining usage: 0

🗳️ Voting for users: alice, bob, charlie
With vote counts: [1, 2, 3]
Vote success: True
Message: Votes recorded successfully
  • alice: 1 votes
  • bob: 2 votes
  • charlie: 3 votes

📊 Querying vote counts:
  • alice: 1 votes
  • bob: 2 votes
  • charlie: 3 votes

❌ Testing with invalid ticket...
Result: {'success': False, 'message': 'Invalid ticket', 'usernames': [], 'votes': []}

🕒 Testing ticket expiration...
Vote success: False

📊 Querying votes after expiration:
  • alice: 1 votes
```

- `test_performance.py`

```bash
python test_performance.py

===== LITTLE VOTE PERFORMANCE TESTS =====


----- Testing Ticket Renewal -----
First ticket: 89a88a52fd...
Waiting 3 seconds for ticket renewal...
Second ticket: 3142b9569e...
Tickets differ: True

Using ticket: 3142b9569e... for performance tests

----- Testing 20 Concurrent Votes -----
Total requests: 20
Successful requests: 20
Failed requests: 0
Average response time: 0.1766 seconds
Min response time: 0.1593 seconds
Max response time: 0.1889 seconds

----- Testing Ticket Usage Limit -----
Testing ticket usage limit with ticket: 3142b9569e...
Successful votes so far: 10
Successful votes so far: 20
Successful votes so far: 30
Successful votes so far: 40
Successful votes so far: 50
Successful votes so far: 60
Successful votes so far: 70
Successful votes so far: 80
Vote failed after 80 successful attempts: Ticket usage limit exceeded
Successful votes before limit: 80
Reached the limit: True

----- Final Vote Counts -----
  • test_user_1: 15 votes
  • test_user_2: 4 votes
  • test_user_3: 8 votes
  • test_user_4: 7 votes
  • test_user_5: 5 votes
  • usage_limit_test_user: 80 votes
```

## 数据库验证

可以通过数据库确认结果已持久化。

```bash
❯ kubectl -n cast exec -it pod/postgres-0 -- psql -U postgres -d cast -c "SELECT * FROM votes;"
 id |       username        | count | version 
----+-----------------------+-------+---------
  1 | alice                 |     1 |       1
  2 | bob                   |     2 |       1
  3 | charlie               |     3 |       1
  4 | test_user_1           |    15 |      17
  6 | test_user_2           |     4 |      19
  5 | test_user_3           |     8 |      20
  8 | test_user_5           |     5 |      14
  7 | test_user_4           |     7 |      21
  9 | usage_limit_test_user |    80 |     101
(9 rows)
```
