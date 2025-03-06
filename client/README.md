# Little Vote Client

This directory contains client tools for testing and interacting with the Little Vote GraphQL API.

## Files

- `vote_client.py` - The main client library for interacting with the Little Vote API
- `test_performance.py` - A script for testing performance and concurrency handling
- `requirements.txt` - Dependencies required to run the client

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Basic Client Demo

The basic client demo demonstrates the core functionality of the Little Vote system:

```bash
python vote_client.py
```

This will:
1. Get a ticket from the server
2. Vote for some test users with the ticket
3. Query the vote counts for those users
4. Test with an invalid ticket
5. Test multiple votes with the same ticket

### Performance Testing

The performance testing script tests the server's handling of concurrent requests and other performance characteristics:

```bash
python test_performance.py
```

For custom settings:

```bash
python test_performance.py --url http://yourserver:port/graphql --concurrency 50
```

Options:
- `--url` - The URL of the GraphQL endpoint (default: http://localhost:8000/graphql)
- `--concurrency` - Number of concurrent vote requests to test (default: 20)

## GraphQL Operations

The client supports all three operations provided by the Little Vote API:

1. **cas** - Get the current valid ticket
   ```python
   ticket_info = await client.get_ticket()
   ```

2. **vote** - Vote for one or more users using a valid ticket
   ```python
   result = await client.vote(["username1", "username2"], ticket)
   ```

3. **query** - Query the vote count for a specific user
   ```python
   vote_count = await client.query_votes("username")
   ```

## Expected API Response Format

The client expects the server to respond with the following data formats:

### Get Ticket (cas)
```json
{
  "data": {
    "cas": {
      "ticket": "ticket-string",
      "validUntil": "timestamp-or-expiry-string",
      "remainingUsage": 100
    }
  }
}
```

### Vote
```json
{
  "data": {
    "vote": {
      "success": true,
      "message": "Vote successful",
      "usernames": ["user1", "user2"],
      "votes": [5, 3]
    }
  }
}
```

### Vote with vote_count
```graphql
mutation Vote($usernames: [String!]!, $voteCount: [Int!]!, $ticket: String!, $voterUsername: String) {
  vote(usernames: $usernames, voteCount: $voteCount, ticket: $ticket, voterUsername: $voterUsername) {
    success
    message
    usernames
    votes
  }
}
```

Variables (with optional voterUsername):
```json
{
  "usernames": ["user1", "user2"],
  "voteCount": [2, 3],
  "ticket": "ticket-string",
  "voterUsername": "voter1"
}
```

Variables (without voterUsername):
```json
{
  "usernames": ["user1", "user2"],
  "voteCount": [2, 3],
  "ticket": "ticket-string"
}
```

Response:
```json
{
  "data": {
    "vote": {
      "success": true,
      "message": "Vote successful",
      "usernames": ["user1", "user2"],
      "votes": [5, 3]
    }
  }
}
```

### Query
```json
{
  "data": {
    "query": 5
  }
}
``` 