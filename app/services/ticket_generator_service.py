import asyncio
import hmac
import hashlib
import time
from datetime import datetime
import json
from ..config.redis import RedisConfig


class TicketGeneratorService:
    """专门负责生成票据的服务，设计为以单实例方式部署"""

    def __init__(self):
        self.secret_key = b'cast_secret_key'  # HMAC密钥
        self.redis = RedisConfig.get_redis()
        self.ticket_key_prefix = "ticket:"

    async def start_ticket_generator(self):
        """启动票据生成器，每2秒生成一个新票据"""
        while True:
            try:
                result = await self.generate_new_ticket()
                if result and "error" in result:
                    # 如果遇到错误，等待较短时间后重试
                    print(f"票据生成失败，将在1秒后重试: {result['error']}")
                    await asyncio.sleep(1)  # 错误后较短重试时间
                    continue
                # 正常情况，每2秒生成一次
                await asyncio.sleep(2)
            except Exception as e:
                # 捕获其他未预期的错误
                print(f"票据生成器遇到意外错误: {str(e)}")
                await asyncio.sleep(1)  # 错误后较短重试时间

    async def generate_new_ticket(self):
        """生成新票据，使用HMAC配合时间戳"""
        timestamp = int(time.time())
        # 创建HMAC，使用时间戳作为消息
        h = hmac.new(self.secret_key, str(timestamp).encode(), hashlib.sha256)
        ticket_id = h.hexdigest()

        # 计算过期时间（2秒后）
        expires_at = datetime.fromtimestamp(timestamp + 2).isoformat()

        # 将票据信息存储到Redis中
        ticket_info = {
            "id": ticket_id,
            "expiresAt": expires_at,
            "usageCount": 0,
            "createdAt": datetime.fromtimestamp(timestamp).isoformat()
        }

        try:
            # 使用管道确保原子操作
            pipe = self.redis.pipeline()

            # 存储新票据信息
            pipe.set(f"{self.ticket_key_prefix}{ticket_id}",
                     json.dumps(ticket_info))

            # 更新当前有效票据
            pipe.set("current_ticket", ticket_id)

            # 设置过期时间（稍大于2秒，确保在新票据生成前不过期）
            pipe.expire(f"{self.ticket_key_prefix}{ticket_id}", 5)

            # 执行所有操作
            pipe.execute()

            return ticket_info
        except Exception as e:
            # 记录错误并返回详细信息
            error_msg = f"Redis连接错误: {str(e)}"
            print(f"[错误] {error_msg}")
            # 如果有日志系统，可以记录详细错误
            # logger.error(error_msg)
            return {"error": error_msg, "status": "failed"}


# 创建单例实例
ticket_generator_service = TicketGeneratorService()
