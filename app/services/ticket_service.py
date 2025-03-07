import hmac
import hashlib
import time
from datetime import datetime
import json
from ..config.redis import RedisConfig


class TicketService:
    def __init__(self):
        self.max_usage_limit = 100  # 票据使用上限
        self.secret_key = b'cast_secret_key'  # HMAC密钥，保留用于验证
        self.redis = RedisConfig.get_redis()
        self.ticket_key_prefix = "ticket:"
        self.user_votes_key = "user_votes:"
        self.user_ticket_key = "user_ticket:"
        self.vote_queue_key = "vote_queue"

    async def get_current_ticket(self):
        """获取当前有效票据"""
        # 获取当前票据ID
        current_ticket_id = self.redis.get("current_ticket")

        if not current_ticket_id:
            # 如果没有当前票据，返回错误信息
            return {
                "id": "",
                "expiresAt": "",
                "usageCount": 0,
                "error": "No active ticket available"
            }

        # 获取票据详细信息
        ticket_info_json = self.redis.get(
            f"{self.ticket_key_prefix}{current_ticket_id}")
        if not ticket_info_json:
            # 票据信息不存在，返回错误
            return {
                "id": "",
                "expiresAt": "",
                "usageCount": 0,
                "error": "Ticket information not found"
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


    def get_user_votes(self, username):
        """获取用户的票数"""
        votes = self.redis.hget("user_votes", username)
        if votes is None:
            return 0
        return int(votes)


# 创建单例实例
ticket_service = TicketService()
