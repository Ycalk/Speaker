import asyncio
from aiogram import Bot
import aioredis
import json

class QueueListener:
    def __init__(self, redis_url, bot : Bot, queue_key: str, db: int):
        self.queue = queue_key
        self.bot = bot
        with open('utils/texts.json', 'r', encoding='utf-8') as f:
            self.texts = json.load(f)
        self.redis = aioredis.from_url(redis_url, db=db)
        self.user_data = {}
    
    def add_listening_user(self, user_id: int, message_id: int):
        self.user_data[user_id] = message_id
    
    async def __get_list_elements(self):
        index = 0
        while True:
            element = await self.redis.lindex(self.queue, index)
            if element is None:
                break
            element = json.loads(element)
            if "user_id" not in element:
                index += 1
                continue
            user_id = int(element["user_id"])
            if user_id in self.user_data and element["app_type"] == "telegram":
                yield user_id, self.user_data[user_id], index
            index += 1
    
    async def listen(self):
        while True:
            current_users = set()
            async for user_id, message_id, index in self.__get_list_elements():
                current_users.add(user_id)
                if index == 0:
                    await self.bot.edit_message_text(chat_id=user_id, 
                                                     message_id=message_id, text=self.texts['messages']['queue_empty'])
                    self.user_data.pop(user_id)
                else:
                    await self.bot.edit_message_text(chat_id=user_id, 
                                                     message_id=message_id, 
                                                     text=self.texts['messages']['queue_length'].format(queue_length=index))
            for user_id in list(self.user_data.keys()):
                if user_id not in current_users:
                    await self.bot.edit_message_text(chat_id=user_id, 
                                                     message_id=self.user_data[user_id], 
                                                     text=self.texts['messages']['queue_empty'])
                    self.user_data.pop(user_id)
            await asyncio.sleep(1)