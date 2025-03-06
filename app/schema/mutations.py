# mutations.py
import strawberry
from typing import List
from .types import VoteResult
from ..services.vote_service import vote_service
from ..services.ticket_service import ticket_service

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def vote(self, usernames: List[str], voteCount: List[int], ticket: str, voterUsername: str = None) -> VoteResult:
        """为指定用户投票"""
        result = await vote_service.vote_for_users(usernames, voteCount, ticket, voterUsername)
        return VoteResult(
            success=result["success"],
            message=result["message"],
            usernames=result["usernames"],
            votes=result["votes"]
        )