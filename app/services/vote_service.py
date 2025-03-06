from fastapi import HTTPException
import asyncio
import json
from typing import List

from ..services.ticket_service import ticket_service
from ..config.redis import RedisConfig

class VoteService:
    def __init__(self):
        # Redis client
        self.redis = RedisConfig.get_redis()
        self.user_votes_key = "user_votes"  # Redis hash key for storing user votes
        
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
        local usernames = cjson.decode(ARGV[1])
        local vote_counts = cjson.decode(ARGV[2])
        local ticket = ARGV[3]
        local voter_username = ARGV[4]
        local timestamp = ARGV[5]
        
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
                    timestamp = timestamp
                }
                redis.call('LPUSH', vote_records_key, cjson.encode(vote_record))
            end
        end
        
        return cjson.encode(result_votes)
        """
        
        try:
            # 准备Lua脚本参数
            timestamp = str(asyncio.get_event_loop().time())
            
            # 执行Lua脚本
            result_json = self.redis.eval(
                vote_script,
                2,  # 2个KEYS参数
                self.user_votes_key,  # KEYS[1]
                "vote_records",  # KEYS[2]
                json.dumps(usernames),  # ARGV[1]
                json.dumps(voteCount),  # ARGV[2]
                ticket,  # ARGV[3]
                voterUsername or "",  # ARGV[4]
                timestamp  # ARGV[5]
            )
            
            # 解析结果
            current_votes = json.loads(result_json)
            
            return {
                "success": True,
                "message": "Votes recorded successfully",
                "usernames": usernames,
                "votes": current_votes
            }
            
        except Exception as e:
            # 脚本执行失败时，回退到普通方法
            return self._vote_for_users_fallback(usernames, voteCount, ticket, voterUsername)
        
    async def get_user_votes(self, username: str):
        """获取用户的投票数"""
        votes = self.redis.hget(self.user_votes_key, username)
        return int(votes) if votes else 0
        

# 创建单例实例        
vote_service = VoteService()