from redis import Redis
from typing import Optional


class RedisConfig:
    _instance: Optional[Redis] = None

    @classmethod
    def get_redis(cls) -> Redis:
        if cls._instance is None:
            cls._instance = Redis(
                host='redis',
                port=6379,
                db=0,
                decode_responses=True  # 自动将响应解码为字符串
            )
        return cls._instance
