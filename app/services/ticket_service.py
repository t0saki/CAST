import asyncio
import hmac
import hashlib
import time
from datetime import datetime
import json
from ..config.redis import RedisConfig


class TicketService:
    def __init__(self):
        self.max_usage_limit = 100  # 票据使用上限
        self.secret_key = b'little_vote_secret_key'  # HMAC密钥
        self.redis = RedisConfig.get_redis()
        self.ticket_key_prefix = "ticket:"
        self.user_votes_key = "user_votes:"
        self.user_ticket_key = "user_ticket:"
        self.vote_queue_key = "vote_queue"

    async def start_ticket_generator(self):
        """启动票据生成器，每2秒生成一个新票据"""
        while True:
            await self.generate_new_ticket()
            await asyncio.sleep(2)  # 每2秒生成一次

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

        # 使用管道确保原子操作
        pipe = self.redis.pipeline()

        # 存储新票据信息
        pipe.set(f"{self.ticket_key_prefix}{ticket_id}",
                 json.dumps(ticket_info))

        # 更新当前有效票据
        pipe.set("current_ticket", ticket_id)

        # 设置过期时间（稍大于2秒，确保在新票据生成前不过期）
        pipe.expire(f"{self.ticket_key_prefix}{ticket_id}", 5)

        # 执行所有操作，但不使用await
        pipe.execute()

        return ticket_info

    async def get_current_ticket(self):
        """获取当前有效票据"""
        # 获取当前票据ID
        current_ticket_id = self.redis.get("current_ticket")

        if not current_ticket_id:
            # 如果没有当前票据，生成一个
            ticket_info = await self.generate_new_ticket()
            return {
                "id": ticket_info["id"],
                "expiresAt": ticket_info["expiresAt"],
                "usageCount": ticket_info["usageCount"]
            }

        # 获取票据详细信息
        ticket_info_json = self.redis.get(
            f"{self.ticket_key_prefix}{current_ticket_id}")
        if not ticket_info_json:
            # 票据信息不存在，重新生成
            ticket_info = await self.generate_new_ticket()
            return {
                "id": ticket_info["id"],
                "expiresAt": ticket_info["expiresAt"],
                "usageCount": ticket_info["usageCount"]
            }

        ticket_info = json.loads(ticket_info_json)
        return {
            "id": ticket_info["id"],
            "expiresAt": ticket_info["expiresAt"],
            "usageCount": ticket_info.get("usageCount", 0)
        }

    async def validate_ticket(self, ticket):
        """验证票据是否有效，使用Lua脚本确保原子性"""
        # 定义Lua脚本，实现原子化的获取、验证和更新操作
        validate_script = """
        local ticket_key = KEYS[1]
        local max_usage_limit = tonumber(ARGV[1])
        local current_time = ARGV[2]
        
        -- 获取票据信息
        local ticket_info_json = redis.call('GET', ticket_key)
        
        -- 检查票据是否存在
        if not ticket_info_json then
            return {0, "Invalid ticket"}
        end
        
        -- 解析票据信息（在Lua中解析JSON）
        local ticket_info = cjson.decode(ticket_info_json)
        
        -- 检查使用次数是否超过限制
        if ticket_info["usageCount"] >= max_usage_limit then
            return {0, "Ticket usage limit exceeded"}
        end
        
        -- 检查票据是否过期
        if current_time > ticket_info["expiresAt"] then
            return {0, "Ticket expired"}
        end
        
        -- 验证通过，更新使用次数
        ticket_info["usageCount"] = ticket_info["usageCount"] + 1
        
        -- 更新票据信息
        redis.call('SET', ticket_key, cjson.encode(ticket_info))
        
        return {1, "Ticket valid"}
        """

        # 准备脚本参数
        ticket_key = f"{self.ticket_key_prefix}{ticket}"
        current_time = datetime.now().isoformat()

        # 执行Lua脚本
        try:
            result = self.redis.eval(
                validate_script,
                1,  # 1个KEYS参数
                ticket_key,  # KEYS[1]
                self.max_usage_limit,  # ARGV[1]
                current_time  # ARGV[2]
            )

            # 解析结果
            is_valid = bool(result[0])
            message = result[1]

            return is_valid, message

        except Exception as e:
            # 如果脚本执行失败（例如Redis不支持EVAL或语法错误），使用备用方法
            return self._validate_ticket_fallback(ticket)

    def get_user_votes(self, username):
        """获取用户的票数"""
        votes = self.redis.hget("user_votes", username)
        if votes is None:
            return 0
        return int(votes)


# 创建单例实例
ticket_service = TicketService()
