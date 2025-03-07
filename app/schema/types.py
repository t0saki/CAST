import strawberry
from typing import List


@strawberry.type
class VoteResult:
    success: bool
    message: str
    usernames: List[str]
    votes: List[int]


@strawberry.type
class TicketInfo:
    ticket: str
    valid_until: str
    remaining_usage: int
