#!/usr/bin/env python3
"""
GraphQL Client for Little Vote System

This client provides methods to interact with the GraphQL API of the Little Vote system.
It supports all three operations: cas (get ticket), vote, and query.
"""

import asyncio
import json
from typing import List, Optional
import sys

import httpx


class LittleVoteClient:
    """Client for interacting with the Little Vote GraphQL API."""

    def __init__(self, base_url: str = "http://localhost:8000/graphql"):
        """
        Initialize the client with the GraphQL endpoint URL.

        Args:
            base_url: The URL of the GraphQL endpoint
        """
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def execute_query(self, query: str, variables: Optional[dict] = None) -> dict:
        """
        Execute a GraphQL query or mutation.

        Args:
            query: The GraphQL query or mutation string
            variables: Optional variables for the query

        Returns:
            The response data as a dictionary
        """
        payload = {
            "query": query,
            "variables": variables or {}
        }

        response = await self.client.post(
            self.base_url,
            json=payload,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code != 200:
            error_msg = f"GraphQL request failed with status {response.status_code}: {response.text}"
            print(error_msg, file=sys.stderr)
            raise Exception(error_msg)

        result = response.json()

        if "errors" in result:
            error_msg = f"GraphQL query returned errors: {json.dumps(result['errors'], indent=2)}"
            print(error_msg, file=sys.stderr)
            raise Exception(error_msg)

        return result["data"]

    async def get_ticket(self) -> dict:
        """
        Get the current valid ticket (cas operation).

        Returns:
            A dictionary containing ticket information
        """
        query = """
        query GetTicket {
            cas {
                ticket
                validUntil
                remainingUsage
            }
        }
        """

        result = await self.execute_query(query)
        return result["cas"]

    async def query_votes(self, username: str) -> int:
        """
        Query the vote count for a specific user.

        Args:
            username: The username to query votes for

        Returns:
            The number of votes for the user
        """
        query = """
        query QueryVotes($username: String!) {
            query(username: $username)
        }
        """

        variables = {"username": username}
        result = await self.execute_query(query, variables)
        return result["query"]

    async def vote(self, usernames: List[str], vote_count: List[int] = None, ticket: str = None, voter_username: str = None) -> dict:
        """
        Vote for one or more users using a valid ticket.

        Args:
            usernames: List of usernames to vote for
            vote_count: List of vote counts for each username (default: 1 vote for each user)
            ticket: A valid ticket obtained from get_ticket()
            voter_username: Optional username of the voter

        Returns:
            A dictionary containing vote results
        """
        # 如果未提供vote_count，为每个用户设置默认投票数为1
        if vote_count is None:
            vote_count = [1] * len(usernames)

        mutation = """
        mutation Vote($usernames: [String!]!, $voteCount: [Int!]!, $ticket: String!) {
            vote(usernames: $usernames, voteCount: $voteCount, ticket: $ticket) {
                success
                message
                usernames
                votes
            }
        }
        """

        variables = {
            "usernames": usernames,
            "voteCount": vote_count,
            "ticket": ticket
        }

        # Only add voterUsername to variables if it's provided
        if voter_username:
            variables["voterUsername"] = voter_username
        result = await self.execute_query(mutation, variables)
        return result["vote"]


async def run_demo():
    """Run a demonstration of the client functionality."""
    client = LittleVoteClient()

    try:
        print("===== Little Vote Client Demo =====")

        # 1. Get a ticket
        print("\n🎟️ Getting a ticket...")
        ticket_info = await client.get_ticket()
        print(f"Ticket: {ticket_info['ticket']}")
        print(f"Valid until: {ticket_info['validUntil']}")
        print(f"Remaining usage: {ticket_info['remainingUsage']}")

        ticket = ticket_info["ticket"]

        # 2. Vote for some users
        test_users = ["alice", "bob", "charlie"]
        test_vote_counts = [1, 2, 3]  # 为每个用户设置不同的投票数
        print(f"\n🗳️ Voting for users: {', '.join(test_users)}")
        print(f"With vote counts: {test_vote_counts}")
        vote_result = await client.vote(test_users, test_vote_counts, ticket)

        print(f"Vote success: {vote_result['success']}")
        print(f"Message: {vote_result['message']}")
        if vote_result['success']:
            for username, votes in zip(vote_result['usernames'], vote_result['votes']):
                print(f"  • {username}: {votes} votes")

        # 3. Query votes for each user
        print("\n📊 Querying vote counts:")
        for username in test_users:
            votes = await client.query_votes(username)
            print(f"  • {username}: {votes} votes")

        # 4. Try with an invalid ticket
        print("\n❌ Testing with invalid ticket...")
        try:
            invalid_result = await client.vote(["alice"], [1], "invalid_ticket_123")
            print(f"Result: {invalid_result}")
        except Exception as e:
            print(f"Error (expected): {str(e)}")

        # 5. Test ticket usage limits (if we have enough remaining uses)
        if ticket_info['remainingUsage'] >= 3:
            print("\n🔄 Testing multiple votes with same ticket...")

            for i in range(3):
                print(f"\nAttempt {i+1}:")
                try:
                    repeat_result = await client.vote(["repeated_user"], [1], ticket)
                    print(f"Vote success: {repeat_result['success']}")
                    if repeat_result['success']:
                        print(
                            f"Votes for repeated_user: {repeat_result['votes'][0]}")
                except Exception as e:
                    print(f"Error: {str(e)}")
                    break

        # 6. Test ticket expiration
        print("\n🕒 Testing ticket expiration...")
        await asyncio.sleep(2)  # Wait for ticket to expire

        try:
            expired_result = await client.vote(["alice"], [1], ticket)
            print(f"Vote success: {expired_result['success']}")
            if expired_result['success']:
                print(f"Votes for alice: {expired_result['votes'][0]}")
        except Exception as e:
            print(f"Error (expected): {str(e)}")

        # 7. Query votes after expiration
        print("\n📊 Querying votes after expiration:")
        votes = await client.query_votes("alice")
        print(f"  • alice: {votes} votes")

    finally:
        await client.close()


if __name__ == "__main__":
    """Entry point for the client demo."""
    asyncio.run(run_demo())
