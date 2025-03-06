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
        # 调用vote_service获取票数
        pass

    @strawberry.field
    async def cas(self) -> TicketInfo:
        """获取当前有效的票据"""
        # 调用ticket_service获取票据
        pass