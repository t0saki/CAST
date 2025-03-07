import asyncio
import strawberry
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter
from contextlib import asynccontextmanager

from .schema.queries import Query
from .schema.mutations import Mutation
from .database.db import init_db
from .services.ticket_service import ticket_service

# 创建GraphQL schema
schema = strawberry.Schema(query=Query, mutation=Mutation)

# 创建GraphQL路由
graphql_app = GraphQLRouter(schema)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 初始化数据库
    await init_db()
    # 启动票据生成器
    asyncio.create_task(ticket_service.start_ticket_generator())
    yield

# 创建FastAPI应用
app = FastAPI(title="Little Vote", lifespan=lifespan)

# 添加GraphQL路由
app.include_router(graphql_app, prefix="/graphql")
