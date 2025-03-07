# CAST - Concurrent API for Secure Ticketing

[中文 README](README.md)

## Project Overview

CAST is a high-performance, secure voting system that allows users to vote for specific usernames and query current vote counts. The system ensures the legitimacy and security of voting operations through a secure ticket mechanism.

### Core Features

- **Ticket Generation**: The system automatically generates a new secure ticket every 2 seconds, with each ticket allowing a limited number of voting operations during its validity period
- **User Voting**: Support for simultaneous voting for single or multiple users, with configurable vote counts per operation
- **Vote Count Queries**: Ability to query the current vote count for specified users at any time

## Technical Architecture

### Backend Technology Stack

- **FastAPI + Strawberry GraphQL**: Providing high-performance GraphQL API interfaces
- **Redis**: Used for ticket and vote count caching
- **PostgreSQL**: Persistent storage of user voting data
- **Kafka**: Message queue for asynchronous updates to PostgreSQL, ensuring reliability and scalability of voting operations
- **Kubernetes**: Container orchestration, supporting horizontal system scaling

### System Architecture Diagram

```
                                       ┌─────────────────┐
                                       │                 │
                                       │ Client Request  │
                                       │                 │
                                       └────────┬────────┘
                                                │
                                                ▼
┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐
                          Kubernetes Cluster
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
│  │  (Persistence) │                                       │   (Multiple)   │  │
   │                │                                       │                │
│  └────────────────┘                                       └────────────────┘  │

└ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘
```

#### System Workflow

1. **Ticket Generation**: The Ticket Generator service generates a new secure ticket every 2 seconds and stores it in Redis
2. **API Request Processing**: The Main Service provides GraphQL API interfaces to handle client voting and query requests
3. **Ticket Validation**: Upon receiving a voting request, the Main Service validates the ticket from Redis, using Lua scripts to ensure consistency of available uses
4. **Secure Voting**: Lua scripts are used to ensure the atomicity of voting operations, preventing concurrency issues
5. **Persistent Storage**: Voting operations are sent to the Kafka message queue, and the Vote Consumer service consumes Kafka messages and persistently stores voting results in PostgreSQL, ensuring data consistency through vote version numbers

### Directory Structure

```
├── app/                       # Main application code
│   ├── config/                # Configuration files
│   ├── database/              # Database-related code
│   ├── models/                # Data models
│   ├── schema/                # GraphQL schema definitions
│   │   ├── mutations.py       # GraphQL mutations
│   │   ├── queries.py         # GraphQL queries
│   │   └── types.py           # GraphQL type definitions
│   ├── services/              # Business logic services
│   │   ├── ticket_service.py  # Ticket service
│   │   └── vote_service.py    # Voting service
│   └── workers/               # Background worker processes
│       ├── ticket_generator.py# Ticket generation service
│       └── vote_consumer.py   # Vote consumer service
├── client/                    # Client code (testing tools)
├── deployment/                # Deployment-related files
├── k8s/                       # Kubernetes configuration files
├── Dockerfile                 # Docker build file
├── requirements.txt           # Python dependencies
└── build-and-deploy.sh        # Build and deploy script
```

#### Core Component Details

##### 1. Main Service (app/main.py)
- Adopts FastAPI+Strawberry GraphQL architecture
- Provides GraphQL API interfaces to handle client voting and query requests
- Implements two main queries:
  - `query`: Query the current vote count for a specified user
  - `cas`: Get information about the currently valid ticket
- Implements key mutation operations:
  - `vote`: Vote for one or more users
- Integrates ticket and voting services:
  - Validates ticket validity, using Lua scripts to ensure atomic ticket usage
  - Executes voting operations, using Lua scripts to ensure concurrency safety
  - Asynchronously sends voting records to the Kafka message queue
- Supports horizontal scaling, can deploy multiple instances to increase concurrent processing capacity

##### 2. Ticket Generator (app/workers/ticket_generator.py)
- Runs as an independent microservice
- Generates a new secure ticket every 2 seconds
- Publishes generated tickets to Redis for validation by the main service
- Designed to run as a single instance to ensure globally unique ticket generation

##### 3. Vote Consumer Service (app/workers/vote_consumer.py)
- Consumes voting messages from the Kafka queue
- Persists voting data to PostgreSQL database
- Implements optimistic locking and version control to ensure data consistency
- Features error retry mechanisms and dead letter queue processing (template provided, dead letter logic not yet implemented)
- Supports horizontal scaling, can deploy multiple instances to increase processing capacity

## GraphQL API

### Queries

- **`query(username: String!): Int!`**
  - Query the current vote count for a specified user
  
- **`cas(): TicketInfo!`**
  - Get information about the currently valid ticket

### Mutations

- **`vote(usernames: [String!]!, voteCount: [Int!]!, ticket: String!, voterUsername: String): VoteResult!`**
  - Vote for one or more users
  - Requires a valid ticket
  - Optionally records the voter

## Installation and Operation

### Kubernetes Deployment

```bash
./build-and-deploy.sh
```

## System Design Highlights

- **High Concurrency Support**: Uses asynchronous IO and efficient data structures to ensure system performance in high concurrency scenarios
- **Secure Ticket Mechanism**: Prevents voting fraud through HMAC-based secure ticket generation
- **Horizontal Scaling**: Service components can be scaled independently, supporting large-scale user scenarios
- **Message Queue**: Uses Kafka to ensure reliability and consistency of voting operations
- **Containerized Deployment**: Supports Kubernetes, facilitating CI/CD and cloud-native deployment

# Test Run

## Test Environment
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

## Test Results

By default, you can use the test address `http://localhost:30000/graphql`. Using the testing tools in the client directory, the results are as follows:

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

## Database Verification

Results can be confirmed as persisted through the database.

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