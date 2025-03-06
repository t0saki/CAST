# queries.py
import strawberry
from typing import Optional, List
from .types import VoteResult, TicketInfo
from ..services.vote_service import vote_service
from ..services.ticket_service import ticket_service

@strawberry.type
class Query:
    @strawberry.field
    async def query(self, username: str) -> int:
        """查询指定用户的票数"""
        return await vote_service.get_user_votes(username)

    @strawberry.field
    async def cas(self) -> TicketInfo:
        """获取当前有效的票据"""
        ticket = await ticket_service.get_current_ticket()
        return TicketInfo(
            ticket=ticket["id"],
            valid_until=ticket["expiresAt"],
            remaining_usage=ticket["usageCount"]
        )
