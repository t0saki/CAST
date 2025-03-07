from redis import Redis, RedisError
from typing import Optional
import time
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RedisConfig:
    _instance: Optional[Redis] = None
    _max_retries = 3
    _retry_delay = 2  # 秒

    @classmethod
    def get_redis(cls) -> Redis:
        if cls._instance is None:
            for attempt in range(cls._max_retries):
                try:
                    cls._instance = Redis(
                        host='redis',
                        port=6379,
                        db=0,
                        decode_responses=True,  # 自动将响应解码为字符串
                        socket_connect_timeout=5,  # 连接超时
                        socket_timeout=5,        # 操作超时
                        retry_on_timeout=True    # 超时时重试
                    )
                    # 测试连接是否成功
                    cls._instance.ping()
                    logger.info("Redis连接成功建立")
                    break
                except RedisError as e:
                    logger.error(
                        f"Redis连接失败 (尝试 {attempt+1}/{cls._max_retries}): {str(e)}")
                    if attempt < cls._max_retries - 1:
                        time.sleep(cls._retry_delay)
                    else:
                        logger.critical("无法连接到Redis，已达到最大重试次数")
                        # 返回实例但记录了失败状态，允许应用启动但会在操作时报错
                        cls._instance = Redis(
                            host='redis',
                            port=6379,
                            db=0,
                            decode_responses=True
                        )
        return cls._instance
