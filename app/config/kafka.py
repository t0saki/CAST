from aiokafka import AIOKafkaProducer
import os
from typing import Optional


class KafkaConfig:
    """Kafka配置类"""

    _producer: Optional[AIOKafkaProducer] = None

    @classmethod
    async def get_producer(cls) -> AIOKafkaProducer:
        """获取Kafka生产者实例"""
        if cls._producer is None:
            # 从环境变量获取配置，如果没有则使用默认值
            kafka_bootstrap_servers = os.getenv(
                "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

            # 创建生产者
            cls._producer = AIOKafkaProducer(
                bootstrap_servers=kafka_bootstrap_servers,
                retry_backoff_ms=500,  # 重试间隔
                request_timeout_ms=5000,  # 请求超时时间（毫秒）
                enable_idempotence=True  # 启用幂等性，确保消息只被发送一次
            )

            # 启动生产者
            await cls._producer.start()

        return cls._producer

    @classmethod
    async def close_producer(cls):
        """关闭Kafka生产者"""
        if cls._producer is not None:
            await cls._producer.stop()
            cls._producer = None

    # 投票事件的topic名称
    VOTES_TOPIC = "votes"
