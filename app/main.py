import asyncio
import strawberry
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter
from contextlib import asynccontextmanager

from .schema.queries import Query
from .schema.mutations import Mutation
from .database.db import init_db

# 创建GraphQL schema
schema = strawberry.Schema(query=Query, mutation=Mutation)

# 创建GraphQL路由
graphql_app = GraphQLRouter(schema)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 初始化数据库
    await init_db()
    # 票据生成服务已经移动到独立的服务中
    yield

# 创建FastAPI应用
app = FastAPI(title="Little Vote", lifespan=lifespan)

# 添加GraphQL路由
app.include_router(graphql_app, prefix="/graphql")
