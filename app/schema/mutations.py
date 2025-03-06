# mutations.py
import strawberry
from typing import List
from .types import VoteResult
from ..services.vote_service import vote_service
from ..services.ticket_service import ticket_service

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def vote(self, usernames: List[str], ticket: str) -> VoteResult:
        """为指定用户投票"""
        # 验证票据
        # 调用vote_service进行投票

        # mock 投票成功
        return VoteResult(success=True, message="投票成功", usernames=usernames, votes=[1, 2, 3])