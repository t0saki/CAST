#!/usr/bin/env python
# -*- coding: utf-8 -*-

from app.config.kafka import KafkaConfig
import asyncio
import json
import os
import signal
import sys
from aiokafka import AIOKafkaConsumer
from sqlalchemy import select
from ..models.vote import Vote
from ..database.db import async_session
import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../..')))


class VoteConsumer:
    """投票消息消费者"""

    def __init__(self):
        # 从环境变量获取Kafka配置
        self.bootstrap_servers = os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.topic = KafkaConfig.VOTES_TOPIC
        self.group_id = os.getenv("KAFKA_CONSUMER_GROUP_ID", "vote_processor")
        self.consumer = None
        self.running = False

    async def start(self):
        """启动消费者"""
        self.running = True

        # 设置信号处理器用于优雅关闭
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(
                sig, lambda: asyncio.create_task(self.shutdown()))

        self.consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            auto_offset_reset="earliest",  # 从最早的消息开始消费
            enable_auto_commit=False,      # 禁用自动提交，我们将手动提交
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )

        # 启动消费者
        await self.consumer.start()
        print(f"Started consuming from {self.topic}...")

        try:
            # 消费消息
            async for msg in self.consumer:
                if not self.running:
                    break

                # 初始化重试计数
                retry_count = 0
                max_retries = 3
                processed = False

                # 重试机制
                while retry_count < max_retries and not processed:
                    try:
                        # 处理消息
                        await self.process_message(msg.value, msg.partition, msg.offset)

                        # 标记为处理成功
                        processed = True

                        # 手动提交偏移量
                        await self.consumer.commit()

                    except Exception as e:
                        retry_count += 1
                        if retry_count >= max_retries:
                            # 达到最大重试次数，记录错误并考虑发送到死信队列
                            print(
                                f"Failed to process message after {max_retries} attempts: {e}")
                            await self.send_to_dead_letter_queue(msg.value, str(e))
                            # 仍然提交偏移量，避免同一消息一直卡住消费进度
                            await self.consumer.commit()
                        else:
                            # 等待一段时间后重试
                            wait_time = 2 ** retry_count  # 指数退避策略
                            print(
                                f"Retry {retry_count}/{max_retries} after {wait_time}s. Error: {e}")
                            await asyncio.sleep(wait_time)
        finally:
            await self.shutdown()

    async def process_message(self, vote_data, partition, offset):
        """处理单个投票消息"""
        print(
            f"Processing vote: {vote_data} (partition={partition}, offset={offset})")

        try:
            username = vote_data.get('target')
            new_count = vote_data.get('count', 1)
            new_version = vote_data.get('version', 1)

            if not username:
                print(f"Invalid vote data: missing username")
                return

            # 获取数据库会话
            async with async_session() as session:
                # 使用乐观锁和版本控制保证数据一致性
                # 1. 查询当前记录
                stmt = select(Vote).where(Vote.username ==
                                          username).with_for_update()
                result = await session.execute(stmt)
                vote = result.scalars().first()

                if vote:
                    # 2. 只有当新版本号大于当前版本号时才更新
                    if new_version > vote.version:
                        vote.count = new_count
                        vote.version = new_version
                        print(
                            f"Updated vote for {username}: count={new_count}, version={new_version}")
                    else:
                        print(
                            f"Skipped outdated vote for {username}: current_version={vote.version}, message_version={new_version}")
                else:
                    # 3. 如果记录不存在，创建新记录
                    new_vote = Vote(
                        username=username,
                        count=new_count,
                        version=new_version
                    )
                    session.add(new_vote)
                    print(
                        f"Created new vote for {username}: count={new_count}, version={new_version}")

                # 4. 提交事务
                await session.commit()
        except Exception as e:
            print(f"Error processing vote: {str(e)}")

    async def shutdown(self):
        """关闭消费者"""
        print("Shutting down consumer...")
        self.running = False
        if self.consumer:
            await self.consumer.stop()

    async def send_to_dead_letter_queue(self, message, error_reason):
        """发送失败消息到死信队列，方便后续处理和分析"""
        try:
            # 这里可以实现发送到死信队列的逻辑
            # 例如：发送到专门的Kafka主题、写入数据库或日志系统等
            dlq_message = {
                "original_message": message,
                "error": error_reason,
                "timestamp": str(datetime.datetime.now())
            }
            print(f"Message sent to dead letter queue: {dlq_message}")

            # TODO: 实际发送到死信队列的代码
            # 例如：
            # await producer.send_and_wait("vote_dlq", json.dumps(dlq_message).encode("utf-8"))
        except Exception as e:
            print(f"Failed to send message to dead letter queue: {e}")


async def main():
    """主函数"""
    consumer = VoteConsumer()
    await consumer.start()

if __name__ == "__main__":
    asyncio.run(main())
