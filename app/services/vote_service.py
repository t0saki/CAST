import json
from typing import List
import time

from ..services.ticket_service import ticket_service
from ..config.redis import RedisConfig
from ..config.kafka import KafkaConfig


class VoteService:
    def __init__(self):
        # Redis client
        self.redis = RedisConfig.get_redis()
        self.user_votes_key = "user_votes"  # Redis hash key for storing user votes
        self.vote_version_key = "vote_version"  # Redis key for global vote version

    async def vote_for_users(self, usernames: List[str], voteCount: List[int], ticket: str, voterUsername: str = None):
        """为多个用户投票"""
        # 验证票据
        is_valid, message = await ticket_service.validate_ticket(ticket)

        if not is_valid:
            return {
                "success": False,
                "message": message,
                "usernames": [],
                "votes": []
            }

        # 确保voteCount列表长度与usernames列表长度相同
        if len(voteCount) != len(usernames):
            return {
                "success": False,
                "message": "Vote count list must have the same length as usernames list",
                "usernames": [],
                "votes": []
            }

        # 使用Lua脚本实现原子性投票操作
        vote_script = """
        local user_votes_key = KEYS[1]
        local vote_records_key = KEYS[2]
        local vote_version_key = KEYS[3]
        local usernames = cjson.decode(ARGV[1])
        local vote_counts = cjson.decode(ARGV[2])
        local ticket = ARGV[3]
        local voter_username = ARGV[4]
        local timestamp = ARGV[5]
        
        -- 增加全局投票版本号
        local current_version = redis.call('INCR', vote_version_key)
        
        -- 存储更新后的投票数
        local result_votes = {}
        
        -- 更新每个用户的票数
        for i, username in ipairs(usernames) do
            -- 增加投票数
            redis.call('HINCRBY', user_votes_key, username, vote_counts[i])
            
            -- 获取更新后的票数
            local updated_votes = redis.call('HGET', user_votes_key, username)
            table.insert(result_votes, tonumber(updated_votes))
            
            -- 如果有投票人信息，记录投票行为
            if voter_username ~= '' then
                local vote_record = {
                    voter = voter_username,
                    target = username,
                    count = vote_counts[i],
                    ticket = ticket,
                    timestamp = timestamp,
                    version = current_version
                }
                redis.call('LPUSH', vote_records_key, cjson.encode(vote_record))
            end
        end
        
        -- 返回更新后的票数和当前版本
        return cjson.encode({votes = result_votes, version = current_version})
        """

        # 准备Lua脚本参数
        timestamp = str(time.time())

        # 执行Lua脚本
        result_json = self.redis.eval(
            vote_script,
            3,  # 3个KEYS参数
            self.user_votes_key,  # KEYS[1]
            "vote_records",  # KEYS[2]
            self.vote_version_key,  # KEYS[3]
            json.dumps(usernames),  # ARGV[1]
            json.dumps(voteCount),  # ARGV[2]
            ticket,  # ARGV[3]
            voterUsername or "",  # ARGV[4]
            timestamp  # ARGV[5]
        )

        # 解析结果
        result = json.loads(result_json)
        current_votes = result["votes"]
        current_version = result["version"]

        # 发送投票事件到Kafka
        await self._send_vote_events_to_kafka(usernames, current_votes, ticket, voterUsername, timestamp, current_version)

        return {
            "success": True,
            "message": "Votes recorded successfully",
            "usernames": usernames,
            "votes": current_votes,
            "version": current_version
        }

    async def _send_vote_events_to_kafka(self, usernames: List[str], vote_counts: List[int],
                                         ticket: str, voter_username: str = None, timestamp: str = None, version: int = None):
        """将投票事件发送到Kafka"""
        try:
            # 获取Kafka生产者
            producer = await KafkaConfig.get_producer()

            # 如果没有提供时间戳，使用当前时间
            if not timestamp:
                timestamp = str(time.time())

            if version is None:
                raise ValueError("Version is required")

            # 为每个投票创建并发送一个Kafka消息
            for i, username in enumerate(usernames):
                # 创建消息数据
                vote_event = {
                    "voter": voter_username or "anonymous",
                    "target": username,
                    "count": vote_counts[i],
                    "ticket": ticket,
                    "timestamp": timestamp,
                    "version": version
                }

                # 序列化消息
                value = json.dumps(vote_event).encode('utf-8')

                # 发送消息到Kafka
                await producer.send_and_wait(
                    topic=KafkaConfig.VOTES_TOPIC,
                    value=value,
                    # 使用目标用户名作为key，确保相同用户的投票进入相同分区
                    key=username.encode('utf-8')
                )
        except Exception as e:
            # 记录错误但不中断投票流程
            print(f"Error sending vote events to Kafka: {str(e)}")

    async def get_user_votes(self, username: str):
        """获取用户的投票数"""
        votes = self.redis.hget(self.user_votes_key, username)
        return int(votes) if votes else 0


# 创建单例实例
vote_service = VoteService()
