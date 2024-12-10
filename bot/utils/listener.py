import enum
import json
import os
import moviepy.editor as mp
import aiohttp
from utils.connector import AppType
from aiogram.fsm.storage.base import StorageKey
import aioredis
from aiogram import Bot
from aiogram.types import URLInputFile
from bot import dp

class NotificationModel:
    class NotificationType (enum.Enum):
        UPDATE = 0,
        ERROR = 1,
    
    def __init__(self, notification: str, user_id):
        notification_type, notification_message = notification.split(".")
        if notification_type == "Update":
            self.notification_type = NotificationModel.NotificationType.UPDATE
        else:
            self.notification_type = NotificationModel.NotificationType.ERROR
        self.notification_message = notification_message
        self.user_id = int(user_id)

# This is a base class for listeners
class Listener :
    def __init__(self, appType : AppType, 
                 redis_storage: str, generating_queue_table: int):
        self.__redis = aioredis.from_url(f"{redis_storage}", db=generating_queue_table)
        self.__appType = appType
    
    async def listen(self):
        pubsub = self.__redis.pubsub()
        await pubsub.subscribe('generated')
        async for message in pubsub.listen():
            if message['type'] == 'message':
                data = json.loads(message['data'])
                if data['app_type'] == self.__appType.value:
                    await self.handler(data)
    
    async def notifications_listener(self):
        pubsub = self.__redis.pubsub()
        await pubsub.subscribe('notification')
        async for message in pubsub.listen():
            if message['type'] == 'message':
                data = json.loads(message['data'])
                if data['app_type'] == self.__appType.value:
                    await self.notification_handler(NotificationModel(data['notification'], data['user_id']))
    
    async def handler(self, data: dict):
        raise NotImplementedError("Handler method must be implemented")
    
    async def notification_handler(self, notification: NotificationModel):
        raise NotImplementedError("Notification listener must be implemented")

# This is an example of a listener implementation
class ListenerImpl(Listener):
    def __init__(self, appType, redis_storage, generating_queue_table, fsm_storage_table, bot : Bot):
        self.__bot = bot
        self.__redis_fsm = aioredis.from_url(f"{redis_storage}", db=fsm_storage_table)
        super().__init__(appType, redis_storage, generating_queue_table)

    async def __clear_state(self, user_id):
        await self.__redis_fsm.delete(f"fsm:{user_id}:{user_id}:state")
    
    async def handler(self, data: dict):
        video = URLInputFile(data['video'])
        user_id = data['user_id']
        await self.__bot.send_video_note(user_id, video)
        await self.__bot.send_message(user_id, "Your request was:\n\n" + str(data))
        await self.__clear_state(user_id)
    
    async def notification_handler(self, notification: NotificationModel):
        if notification.notification_type == NotificationModel.NotificationType.UPDATE:
            await self.__bot.send_message(notification.user_id, f"Update: {notification.notification_message}")
        else:
            await self.__bot.send_message(notification.user_id, f"Error: {notification.notification_message}")
            await self.__clear_state(notification.user_id)
