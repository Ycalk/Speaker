import enum
import json
from utils.connector import AppType
from keyboards.keyboards import main_keyboard
import aioredis
from aiogram import Bot
from aiogram.types import URLInputFile

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
        self.texts = json.load(open('utils/texts.json', 'r', encoding='utf-8'))
        with open('utils/stickers.json', 'r', encoding='utf-8') as f:
            self.stickers = json.load(f)

    async def __clear_state(self, user_id):
        await self.__redis_fsm.delete(f"fsm:{user_id}:{user_id}:state")
    
    
    async def __send_congratulations(self, user_id, celebrity_code, user_name, gender):
        ending = ""
        if not gender or gender == "Gender.UNKNOWN":
            ending = "(а)"
        elif gender == "Gender.FEMALE":
            ending = "а"
        if celebrity_code.startswith("vidos_good"):
            await self.__bot.send_message(user_id, 
                                          self.texts['messages']['on_create_good_behavior'].format(
                                              name=user_name.capitalize(), ending=ending),
                                          reply_markup=main_keyboard(is_new=True))
        elif celebrity_code.startswith("vidos_bad"):
            await self.__bot.send_message(user_id, 
                                          self.texts['messages']['on_create_bad_behavior'].format(
                                              name=user_name.capitalize(), ending=ending),
                                          reply_markup=main_keyboard(is_new=True))
        else:
            await self.__bot.send_message(user_id, 
                                          self.texts['messages']['on_create'],
                                          reply_markup=main_keyboard(is_new=True))
        
    
    async def handler(self, data: dict):
        video = URLInputFile(data['video'])
        user_id = data['user_id']
        await self.__bot.send_video_note(user_id, video)
        await self.__clear_state(user_id)
        await self.__send_congratulations(user_id, data['celebrity_code'], data['user_name'], data['gender'])
        await self.__bot.send_sticker(user_id, self.stickers['share'])
    
    async def notification_handler(self, notification: NotificationModel):
        if notification.notification_type == NotificationModel.NotificationType.ERROR:
            await self.__bot.send_message(notification.user_id, self.texts['messages']['generation_error'])
            await self.__clear_state(notification.user_id)
