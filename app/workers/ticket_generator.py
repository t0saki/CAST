"""
票据生成服务入口点

这个服务作为独立的微服务运行，负责生成票据。
设计成单个实例运行，以保证全局唯一的票据生成。
"""

import asyncio
import signal
from fastapi import FastAPI
from contextlib import asynccontextmanager

from ..services.ticket_generator_service import ticket_generator_service
from ..config.redis import RedisConfig

# 初始化Redis连接（确保在服务启动时已连接）
_ = RedisConfig.get_redis()

# 创建应用实例
app = FastAPI(title="Ticket Generator Service")

# 信号处理，确保优雅关闭
stop_event = asyncio.Event()


def handle_signal(sig):
    """处理终止信号"""
    print(f"Received signal {sig}, preparing to close service...")
    stop_event.set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 设置信号处理器
    for sig in (signal.SIGINT, signal.SIGTERM):
        asyncio.get_event_loop().add_signal_handler(
            sig, lambda s=sig: handle_signal(s)
        )

    # 启动票据生成器
    generator_task = asyncio.create_task(
        ticket_generator_service.start_ticket_generator())

    print("Ticket generation service has started...")
    yield

    # 等待生成器任务结束
    stop_event.set()
    try:
        await asyncio.wait_for(generator_task, timeout=5.0)
    except asyncio.TimeoutError:
        print("Forcing ticket generator shutdown...")
        generator_task.cancel()

    print("Ticket generation service has stopped")


# 设置应用生命周期管理
app.router.lifespan_context = lifespan


@app.get("/health")
async def health_check():
    """健康检查端点，包括检查Redis连接状态"""
    health_status = {"service": "ticket-generator"}

    # 检查Redis连接
    redis_client = RedisConfig.get_redis()
    try:
        # 尝试执行简单的Redis操作
        redis_client.ping()
        health_status["redis"] = "connected"
        health_status["status"] = "healthy"
    except Exception as e:
        health_status["redis"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    return health_status


if __name__ == "__main__":
    # 当直接运行此文件时，启动票据生成服务
    # 注意：在生产环境中，应该使用 uvicorn 启动
    import uvicorn
    uvicorn.run("app.workers.ticket_generator:app",
                host="0.0.0.0", port=8001, log_level="info")
