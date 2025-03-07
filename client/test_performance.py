#!/usr/bin/env python3
"""
Performance Testing Script for Little Vote System

This script tests the performance and concurrency handling of the Little Vote system.
It simulates multiple users voting simultaneously using the same ticket.
"""

import asyncio
import time
import random
from typing import List, Dict, Any
import statistics
import argparse

from vote_client import LittleVoteClient


async def measure_request_time(func, *args, **kwargs) -> float:
    """
    Measure the time it takes to execute a function.

    Args:
        func: The async function to measure
        args, kwargs: Arguments to pass to the function

    Returns:
        The execution time in seconds
    """
    start_time = time.time()
    result = await func(*args, **kwargs)
    end_time = time.time()
    return end_time - start_time, result


async def concurrent_votes(
    client: LittleVoteClient,
    usernames: List[str],
    ticket: str,
    num_requests: int
) -> Dict[str, Any]:
    """
    Perform multiple vote requests concurrently.

    Args:
        client: The LittleVoteClient instance
        usernames: List of usernames to vote for
        ticket: The ticket to use for voting
        num_requests: Number of concurrent vote requests

    Returns:
        Dictionary with test results
    """
    # Create a list of vote tasks
    tasks = []
    for _ in range(num_requests):
        # Randomly select a username from the list for each vote
        username = random.choice(usernames)
        # 随机生成1-3之间的投票数
        vote_count = random.randint(1, 3)
        tasks.append(measure_request_time(
            client.vote, [username], [vote_count], ticket))

    # Execute all vote requests concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process the results
    success_count = 0
    failure_count = 0
    response_times = []
    exceptions = []

    for result in results:
        if isinstance(result, Exception):
            failure_count += 1
            exceptions.append(str(result))
        else:
            response_time, vote_result = result
            response_times.append(response_time)
            if vote_result.get('success', False):
                success_count += 1
            else:
                failure_count += 1
                exceptions.append(vote_result.get('message', 'Unknown error'))

    # Calculate statistics
    stats = {
        'total_requests': num_requests,
        'successful_requests': success_count,
        'failed_requests': failure_count,
        'avg_response_time': statistics.mean(response_times) if response_times else 0,
        'min_response_time': min(response_times) if response_times else 0,
        'max_response_time': max(response_times) if response_times else 0,
        'exceptions': exceptions[:5]  # Show only first 5 exceptions
    }

    return stats


async def test_ticket_renewal(client: LittleVoteClient, wait_seconds: int = 3) -> Dict[str, Any]:
    """
    Test that tickets are properly renewed after the specified time period.

    Args:
        client: The LittleVoteClient instance
        wait_seconds: Seconds to wait for ticket renewal

    Returns:
        Dictionary with test results
    """
    # Get the first ticket
    first_ticket = await client.get_ticket()
    print(f"First ticket: {first_ticket['ticket'][:10]}...")

    # Wait for the ticket to renew
    print(f"Waiting {wait_seconds} seconds for ticket renewal...")
    await asyncio.sleep(wait_seconds)

    # Get the second ticket
    second_ticket = await client.get_ticket()
    print(f"Second ticket: {second_ticket['ticket'][:10]}...")

    # Check if the tickets are different
    tickets_differ = first_ticket['ticket'] != second_ticket['ticket']

    return {
        'first_ticket': first_ticket,
        'second_ticket': second_ticket,
        'tickets_differ': tickets_differ
    }


async def test_ticket_usage_limit(
    client: LittleVoteClient,
    username: str,
    max_attempts: int = 200
) -> Dict[str, Any]:
    """
    Test the usage limit of a ticket by voting repeatedly until it fails.

    Args:
        client: The LittleVoteClient instance
        username: Username to vote for
        max_attempts: Maximum number of vote attempts

    Returns:
        Dictionary with test results
    """
    # Get a fresh ticket
    ticket_info = await client.get_ticket()
    ticket = ticket_info['ticket']

    print(f"Testing ticket usage limit with ticket: {ticket[:10]}...")

    successful_votes = 0
    for attempt in range(1, max_attempts + 1):
        try:
            result = await client.vote([username], [1], ticket)
            if result.get('success', False):
                successful_votes += 1
                if attempt % 10 == 0:
                    print(f"Successful votes so far: {successful_votes}")
            else:
                print(
                    f"Vote failed after {successful_votes} successful attempts: {result.get('message')}")
                break
        except Exception as e:
            print(
                f"Exception after {successful_votes} successful attempts: {str(e)}")
            break

    return {
        'ticket': ticket,
        'successful_votes': successful_votes,
        'reached_limit': successful_votes < max_attempts
    }


async def run_performance_tests(base_url: str, concurrency: int = 10):
    """
    Run a series of performance tests on the Little Vote server.

    Args:
        base_url: The URL of the GraphQL endpoint
        concurrency: Number of concurrent requests for testing
    """
    client = LittleVoteClient(base_url)

    try:
        print("\n===== LITTLE VOTE PERFORMANCE TESTS =====\n")

        # 1. Test ticket renewal
        print("\n----- Testing Ticket Renewal -----")
        renewal_results = await test_ticket_renewal(client)
        print(f"Tickets differ: {renewal_results['tickets_differ']}")

        # 2. Get a fresh ticket for voting tests
        ticket_info = await client.get_ticket()
        ticket = ticket_info['ticket']
        print(f"\nUsing ticket: {ticket[:10]}... for performance tests")

        # 3. Generate random usernames for testing
        test_users = [f"test_user_{i}" for i in range(1, 6)]

        # 4. Test concurrent voting with the same ticket
        print(f"\n----- Testing {concurrency} Concurrent Votes -----")
        concurrency_results = await concurrent_votes(client, test_users, ticket, concurrency)

        print(f"Total requests: {concurrency_results['total_requests']}")
        print(
            f"Successful requests: {concurrency_results['successful_requests']}")
        print(f"Failed requests: {concurrency_results['failed_requests']}")
        print(
            f"Average response time: {concurrency_results['avg_response_time']:.4f} seconds")
        print(
            f"Min response time: {concurrency_results['min_response_time']:.4f} seconds")
        print(
            f"Max response time: {concurrency_results['max_response_time']:.4f} seconds")

        if concurrency_results['failed_requests'] > 0:
            print("\nSample exceptions:")
            for i, exc in enumerate(concurrency_results['exceptions'], 1):
                print(f"  {i}. {exc}")

        # 5. Test ticket usage limit
        print("\n----- Testing Ticket Usage Limit -----")
        limit_username = "usage_limit_test_user"
        limit_results = await test_ticket_usage_limit(client, limit_username)

        print(
            f"Successful votes before limit: {limit_results['successful_votes']}")
        print(f"Reached the limit: {limit_results['reached_limit']}")

        # 6. Query final vote counts for test users
        print("\n----- Final Vote Counts -----")
        for username in test_users + [limit_username]:
            try:
                votes = await client.query_votes(username)
                print(f"  • {username}: {votes} votes")
            except Exception as e:
                print(f"  • {username}: Error querying votes - {str(e)}")

    finally:
        await client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Performance testing for Little Vote system")
    parser.add_argument(
        "--url", default="http://localhost:30000/graphql", help="GraphQL endpoint URL")
    parser.add_argument("--concurrency", type=int, default=20,
                        help="Number of concurrent requests")
    args = parser.parse_args()

    asyncio.run(run_performance_tests(args.url, args.concurrency))
